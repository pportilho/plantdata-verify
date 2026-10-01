import Foundation
import Vision
import AppKit

// One token per word or number, each with its own box (boundingBox(for:)), so a table
// cell keeps its position even when Vision reads several cells as one line.
// Usage: ocr_tokens <image.png> > tokens.json      (pixels, origin top-left)
let args = CommandLine.arguments
guard args.count > 1, let img = NSImage(contentsOfFile: args[1]),
      let cg = img.cgImage(forProposedRect: nil, context: nil, hints: nil) else {
    FileHandle.standardError.write("error: cannot read image\n".data(using: .utf8)!)
    exit(1)
}
let W = Double(cg.width), H = Double(cg.height)
let request = VNRecognizeTextRequest()
request.recognitionLevel = .accurate
request.usesLanguageCorrection = false
request.recognitionLanguages = ["en-US"]
try? VNImageRequestHandler(cgImage: cg, options: [:]).perform([request])

var tokens: [[String: Any]] = []
let separators = CharacterSet(charactersIn: " |\t")
var lineID = 0
for observation in (request.results ?? []) {
    lineID += 1
    guard let candidate = observation.topCandidates(1).first else { continue }
    let s = candidate.string
    let line = observation.boundingBox
    var i = s.startIndex
    while i < s.endIndex {
        while i < s.endIndex, s[i].unicodeScalars.allSatisfy({ separators.contains($0) }) { i = s.index(after: i) }
        guard i < s.endIndex else { break }
        var j = i
        while j < s.endIndex, !s[j].unicodeScalars.allSatisfy({ separators.contains($0) }) { j = s.index(after: j) }
        if let wordBox = try? candidate.boundingBox(for: i..<j) {
            let b = wordBox.boundingBox
            tokens.append(["text": String(s[i..<j]), "conf": Double(candidate.confidence),
                           "x0": b.minX * W, "x1": b.maxX * W,
                           "y0": (1 - b.maxY) * H, "y1": (1 - b.minY) * H,
                           "parent": lineID, "offset": s.distance(from: s.startIndex, to: i),
                           "parent_x0": line.minX * W, "parent_x1": line.maxX * W,
                           "parent_len": s.count])
        }
        i = j
    }
}
let json = try! JSONSerialization.data(withJSONObject: ["width": W, "height": H, "tokens": tokens])
FileHandle.standardOutput.write(json)
