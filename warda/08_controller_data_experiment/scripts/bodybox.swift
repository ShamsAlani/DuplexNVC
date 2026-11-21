// Human body boxes with Apple Vision (VNDetectHumanRectanglesRequest, full body), the body
// counterpart of the baseline's facebox.swift. Same input and output layout, plus confidence
// and the detection time of each frame.
// Output: {"width", "height", "frames": [{"i", "bodies": [[x, y, w, h, confidence]], "ms"}]},
// pixel boxes, origin top-left.
// usage: swiftc -O bodybox.swift -o bodybox && ./bodybox <image_dir> <out.json>
import Foundation
import Vision
import ImageIO

let args = CommandLine.arguments
guard args.count == 3 else { print("usage: bodybox <image_dir> <out.json>"); exit(2) }
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
    let req = VNDetectHumanRectanglesRequest()
    req.upperBodyOnly = false                     // whole person, so people seen from behind count too
    let t0 = DispatchTime.now().uptimeNanoseconds
    try VNImageRequestHandler(cgImage: img, options: [:]).perform([req])
    let ms = Double(DispatchTime.now().uptimeNanoseconds - t0) / 1e6
    let bodies: [[Double]] = (req.results ?? []).map { obs in
        let b = obs.boundingBox                   // normalised, origin bottom-left
        return [Double((b.minX * CGFloat(W)).rounded()), Double(((1 - b.maxY) * CGFloat(H)).rounded()),
                Double((b.width * CGFloat(W)).rounded()), Double((b.height * CGFloat(H)).rounded()),
                Double(obs.confidence)]
    }
    frames.append(["i": i, "bodies": bodies, "ms": ms])
}
let out: [String: Any] = ["width": W, "height": H, "frames": frames]
try JSONSerialization.data(withJSONObject: out, options: [.prettyPrinted]).write(to: URL(fileURLWithPath: args[2]))
print("body boxes for \(frames.count) frames -> \(args[2])")
