// Face boxes on the ORIGINAL (display-resolution) frames with Apple Vision, the same detector
// the Phase-2 scene analyzer will use. Output: pixel boxes [x, y, w, h], origin top-left.
// usage: swiftc -O facebox.swift -o facebox && ./facebox <image_dir> <out.json>
import Foundation
import Vision
import ImageIO

let args = CommandLine.arguments
guard args.count == 3 else { print("usage: facebox <image_dir> <out.json>"); exit(2) }
let files = try FileManager.default.contentsOfDirectory(at: URL(fileURLWithPath: args[1]),
                                                        includingPropertiesForKeys: nil)
    .filter { ["png", "jpg", "jpeg"].contains($0.pathExtension.lowercased()) }
    .sorted { $0.lastPathComponent < $1.lastPathComponent }
var frames: [[String: Any]] = []
var W = 0, H = 0
for (i, url) in files.enumerated() {
    guard let src = CGImageSourceCreateWithURL(url as CFURL, nil),
          let img = CGImageSourceCreateImageAtIndex(src, 0, nil) else { continue }
    W = img.width; H = img.height
    let req = VNDetectFaceRectanglesRequest()
    try VNImageRequestHandler(cgImage: img, options: [:]).perform([req])
    let faces: [[Int]] = (req.results ?? []).map { obs in
        let b = obs.boundingBox                       // normalised, origin bottom-left
        return [Int((b.minX * CGFloat(W)).rounded()), Int(((1 - b.maxY) * CGFloat(H)).rounded()),
                Int((b.width * CGFloat(W)).rounded()), Int((b.height * CGFloat(H)).rounded())]
    }
    frames.append(["i": i, "faces": faces])
}
let out: [String: Any] = ["width": W, "height": H, "frames": frames]
try JSONSerialization.data(withJSONObject: out, options: [.prettyPrinted]).write(to: URL(fileURLWithPath: args[2]))
print("face boxes for \(frames.count) frames -> \(args[2])")
