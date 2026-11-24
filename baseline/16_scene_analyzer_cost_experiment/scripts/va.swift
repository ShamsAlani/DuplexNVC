// va.swift: the scene analyzer of Step 7 as a separate process during a call. Reads the call's camera frames (NV12),
// paces itself at 30 fps and every N frames runs Apple Vision face detection and body (human rectangle) detection on
// the frame, as the controller's analyzer would (Step 8: the larger of the face and body counts).
//   va <camera.nv12> <width> <height> <every N frames> <cpu: 0|1> <seconds> <out.csv>
// cpu = 1 pins both requests to the CPU. Writes one row per analysis: frame, ms, faces, bodies; prints a summary.
// Build: swiftc -O -o va va.swift
import CoreML
import CoreVideo
import Foundation
import Vision

let a = CommandLine.arguments
guard a.count >= 8, let w = Int(a[2]), let h = Int(a[3]), let every = Int(a[4]), let secs = Double(a[6]) else {
    FileHandle.standardError.write("usage: va <camera.nv12> <w> <h> <every> <cpu 0|1> <seconds> <out.csv>\n".data(using: .utf8)!)
    exit(2)
}
let cpu = a[5] == "1"
guard let data = FileManager.default.contents(atPath: a[1]) else { print("va: cannot read \(a[1])"); exit(1) }
let fsz = w * h * 3 / 2
let nf = data.count / fsz
guard nf > 0 else { print("va: no frames"); exit(1) }

func pixelBuffer(_ k: Int) -> CVPixelBuffer? {
    var pb: CVPixelBuffer?
    let attrs = [kCVPixelBufferIOSurfacePropertiesKey as String: [:]] as CFDictionary
    guard CVPixelBufferCreate(nil, w, h, kCVPixelFormatType_420YpCbCr8BiPlanarVideoRange, attrs, &pb) == kCVReturnSuccess,
          let p = pb else { return nil }
    CVPixelBufferLockBaseAddress(p, [])
    data.withUnsafeBytes { (raw: UnsafeRawBufferPointer) in
        let base = raw.baseAddress!.advanced(by: k * fsz)
        for plane in 0..<2 {
            let dst = CVPixelBufferGetBaseAddressOfPlane(p, plane)!
            let stride = CVPixelBufferGetBytesPerRowOfPlane(p, plane)
            let rows = plane == 0 ? h : h / 2
            let src = base.advanced(by: plane == 0 ? 0 : w * h)
            for r in 0..<rows { memcpy(dst.advanced(by: r * stride), src.advanced(by: r * w), w) }
        }
    }
    CVPixelBufferUnlockBaseAddress(p, [])
    return p
}

func pinToCPU(_ req: VNRequest) {
    if #available(macOS 14.0, *) {
        if let stages = try? req.supportedComputeStageDevices {
            for (stage, devs) in stages {
                if let c = devs.first(where: { if case .cpu = $0 { return true } else { return false } }) {
                    try? req.setComputeDevice(c, for: stage)
                }
            }
        }
    } else {
        req.usesCPUOnly = true
    }
}

var out = "frame,ms,faces,bodies\n"
var ms: [Double] = []
let t0 = Date()
var i = 0
while true {
    let due = t0.addingTimeInterval(Double(i) / 30.0)
    let wait = due.timeIntervalSinceNow
    if wait > 0 { Thread.sleep(forTimeInterval: wait) }
    if Date().timeIntervalSince(t0) >= secs { break }
    if i % every == 0, let pb = pixelBuffer(i % nf) {
        let faces = VNDetectFaceRectanglesRequest()
        let bodies = VNDetectHumanRectanglesRequest()
        if cpu { pinToCPU(faces); pinToCPU(bodies) }
        let s = Date()
        try? VNImageRequestHandler(cvPixelBuffer: pb, options: [:]).perform([faces, bodies])
        let d = Date().timeIntervalSince(s) * 1000
        ms.append(d)
        out += "\(i),\(String(format: "%.3f", d)),\(faces.results?.count ?? 0),\(bodies.results?.count ?? 0)\n"
    }
    i += 1
}
try? out.write(toFile: a[7], atomically: true, encoding: .utf8)
let srt = ms.sorted()
let med = srt.isEmpty ? 0 : srt[srt.count / 2]
let p95 = srt.isEmpty ? 0 : srt[min(srt.count - 1, Int(Double(srt.count) * 0.95))]
print(String(format: "va: %d analyses (every %d frames, %@), median %.2f ms, p95 %.2f ms, per frame pair %.3f ms",
             ms.count, every, cpu ? "CPU" : "default units", med, p95, med / Double(every)))
