// matte: person segmentation masks for a span of a video, as raw 8-bit gray frames on stdout.
//
//   matte <video> <startSeconds> <durationSeconds> <width> <height> | ffmpeg -f rawvideo -pix_fmt gray -s WxH -r 30 -i - ...
//
// Uses Apple Vision's person segmentation (accurate quality), about 10 ms a frame on
// Apple Silicon. Compiled by install.sh: swiftc -O scripts/matte.swift -o bin/matte
import AVFoundation
import CoreImage
import Foundation
import Vision

let args = CommandLine.arguments
guard args.count == 6, let start = Double(args[2]), let dur = Double(args[3]), let W = Int(args[4]), let H = Int(args[5]) else {
    FileHandle.standardError.write("usage: matte <video> <start> <duration> <width> <height>\n".data(using: .utf8)!)
    exit(2)
}

let asset = AVURLAsset(url: URL(fileURLWithPath: args[1]))
let sema = DispatchSemaphore(value: 0)
var videoTrack: AVAssetTrack?
Task {
    videoTrack = try? await asset.loadTracks(withMediaType: .video).first
    sema.signal()
}
sema.wait()
guard let track = videoTrack, let reader = try? AVAssetReader(asset: asset) else {
    FileHandle.standardError.write("cannot read video\n".data(using: .utf8)!)
    exit(1)
}
reader.timeRange = CMTimeRange(start: CMTime(seconds: start, preferredTimescale: 600), duration: CMTime(seconds: dur, preferredTimescale: 600))
let output = AVAssetReaderTrackOutput(track: track, outputSettings: [kCVPixelBufferPixelFormatTypeKey as String: kCVPixelFormatType_32BGRA])
reader.add(output)
reader.startReading()

let request = VNGeneratePersonSegmentationRequest()
request.qualityLevel = .accurate
request.outputPixelFormat = kCVPixelFormatType_OneComponent8
let context = CIContext(options: [.workingColorSpace: NSNull()])
var buffer = [UInt8](repeating: 0, count: W * H)
let out = FileHandle.standardOutput
var frames = 0

while let sample = output.copyNextSampleBuffer() {
    guard let pixels = CMSampleBufferGetImageBuffer(sample) else { continue }
    let handler = VNImageRequestHandler(cvPixelBuffer: pixels, options: [:])
    try? handler.perform([request])
    if let mask = request.results?.first?.pixelBuffer {
        var img = CIImage(cvPixelBuffer: mask)
        img = img.transformed(by: CGAffineTransform(scaleX: CGFloat(W) / img.extent.width, y: CGFloat(H) / img.extent.height))
        // Soften the edge slightly so the cut-out does not look stencilled.
        img = img.clampedToExtent().applyingGaussianBlur(sigma: 1.2).cropped(to: CGRect(x: 0, y: 0, width: W, height: H))
        buffer.withUnsafeMutableBytes { ptr in
            context.render(img, toBitmap: ptr.baseAddress!, rowBytes: W, bounds: CGRect(x: 0, y: 0, width: W, height: H),
                           format: .L8, colorSpace: nil)
        }
    } else {
        for i in 0..<buffer.count { buffer[i] = 0 }
    }
    out.write(Data(buffer))
    frames += 1
}
FileHandle.standardError.write("matte: \(frames) frames\n".data(using: .utf8)!)
