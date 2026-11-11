// Video export for Toonfork (iOS + macOS; macOS links this same file): system TTS to a wav file, audio
// decoding to a wav, and an H.264 + AAC mp4 encoder fed with RGBA frames from Dart.
// Channel "toonfork/export"; see lib/toonfork_export.dart for the calls.

import AVFoundation
import Accelerate
#if os(iOS)
import Flutter
#else
import FlutterMacOS
#endif

public class ToonforkExportPlugin: NSObject, FlutterPlugin {
  private let queue = DispatchQueue(label: "toonfork.export")
  private var synth: AVSpeechSynthesizer?
  private var encoder: Mp4Encoder?

  public static func register(with registrar: FlutterPluginRegistrar) {
    #if os(iOS)
    let messenger = registrar.messenger()
    #else
    let messenger = registrar.messenger
    #endif
    let channel = FlutterMethodChannel(name: "toonfork/export", binaryMessenger: messenger)
    registrar.addMethodCallDelegate(ToonforkExportPlugin(), channel: channel)
  }

  public func handle(_ call: FlutterMethodCall, result: @escaping FlutterResult) {
    let a = call.arguments as? [String: Any] ?? [:]
    switch call.method {
    case "voices":
      result(voices(lang: a["lang"] as? String ?? "cs"))
    case "synth":
      synthesize(a, result)
    case "decode":
      let src = a["src"] as? String ?? "", dst = a["dst"] as? String ?? ""
      queue.async {
        let err = decodeToWav(src: src, dst: dst)
        DispatchQueue.main.async { result(err.map { FlutterError(code: "decode", message: $0, details: nil) } ?? dst) }
      }
    case "start":
      queue.async {
        do {
          self.encoder = try Mp4Encoder(path: a["path"] as! String, width: a["width"] as! Int,
                                        height: a["height"] as! Int, fps: a["fps"] as! Int,
                                        audioWav: a["audio"] as? String)
          DispatchQueue.main.async { result(true) }
        } catch {
          DispatchQueue.main.async { result(FlutterError(code: "start", message: "\(error)", details: nil)) }
        }
      }
    case "frame":
      guard let data = a["rgba"] as? FlutterStandardTypedData else { result(FlutterError(code: "frame", message: "no rgba", details: nil)); return }
      queue.async {
        let ok = self.encoder?.append(rgba: data.data) ?? false
        DispatchQueue.main.async { result(ok ? true : FlutterError(code: "frame", message: self.encoder?.error ?? "no encoder", details: nil)) }
      }
    case "finish":
      queue.async {
        guard let enc = self.encoder else { DispatchQueue.main.async { result(FlutterError(code: "finish", message: "no encoder", details: nil)) }; return }
        enc.finish { err in
          self.encoder = nil
          DispatchQueue.main.async { result(err.map { FlutterError(code: "finish", message: $0, details: nil) } ?? enc.path) }
        }
      }
    case "cancel":
      queue.async { self.encoder?.cancel(); self.encoder = nil; DispatchQueue.main.async { result(true) } }
    default:
      result(FlutterMethodNotImplemented)
    }
  }

  // MARK: TTS

  private func voices(lang: String) -> [[String: Any]] {
    let prefix = lang.lowercased().split(separator: "-").first.map(String.init) ?? lang
    return AVSpeechSynthesisVoice.speechVoices()
      .filter { $0.language.lowercased().hasPrefix(prefix) }
      .map { v in
        var g = ""
        if #available(iOS 13.0, macOS 10.15, *) {
          g = v.gender == .male ? "m" : v.gender == .female ? "f" : ""
        }
        return ["id": v.identifier, "name": v.name, "lang": v.language, "gender": g,
                "quality": v.quality == .default ? 0 : (v.quality == .enhanced ? 1 : 2)]
      }
  }

  /// One utterance → wav at `path` (the synthesizer's own format; Dart resamples).
  private func synthesize(_ a: [String: Any], _ result: @escaping FlutterResult) {
    let text = a["text"] as? String ?? "", path = a["path"] as? String ?? ""
    let u = AVSpeechUtterance(string: text)
    if let id = a["voice"] as? String, let v = AVSpeechSynthesisVoice(identifier: id) { u.voice = v }
    else { u.voice = AVSpeechSynthesisVoice(language: a["lang"] as? String ?? "cs-CZ") }
    // Dart rate 1.0 = normal; AVSpeechUtterance's default is 0.5 of 0…1
    u.rate = Float(min(max(AVSpeechUtteranceDefaultSpeechRate * Float(a["rate"] as? Double ?? 1), AVSpeechUtteranceMinimumSpeechRate), AVSpeechUtteranceMaximumSpeechRate))
    u.pitchMultiplier = Float(min(max(a["pitch"] as? Double ?? 1, 0.5), 2))
    let s = AVSpeechSynthesizer()
    synth = s
    var file: AVAudioFile?
    var done = false
    s.write(u) { buffer in
      guard !done else { return }
      guard let pcm = buffer as? AVAudioPCMBuffer else { return }
      if pcm.frameLength == 0 {
        done = true
        file = nil  // closes the file
        DispatchQueue.main.async { result(path) }
        return
      }
      do {
        if file == nil {
          try? FileManager.default.removeItem(atPath: path)
          file = try AVAudioFile(forWriting: URL(fileURLWithPath: path), settings: pcm.format.settings,
                                 commonFormat: pcm.format.commonFormat, interleaved: pcm.format.isInterleaved)
        }
        try file?.write(from: pcm)
      } catch {
        done = true
        DispatchQueue.main.async { result(FlutterError(code: "synth", message: "\(error)", details: nil)) }
      }
    }
  }
}

// MARK: audio decoding

/// Any audio file AVFoundation reads (mp3, m4a, wav) → 48 kHz mono 16-bit wav.
func decodeToWav(src: String, dst: String) -> String? {
  let asset = AVURLAsset(url: URL(fileURLWithPath: src))
  guard let track = asset.tracks(withMediaType: .audio).first else { return "no audio track in \(src)" }
  do {
    let reader = try AVAssetReader(asset: asset)
    let out = AVAssetReaderTrackOutput(track: track, outputSettings: [
      AVFormatIDKey: kAudioFormatLinearPCM, AVSampleRateKey: 48000, AVNumberOfChannelsKey: 1,
      AVLinearPCMBitDepthKey: 16, AVLinearPCMIsFloatKey: false, AVLinearPCMIsBigEndianKey: false,
      AVLinearPCMIsNonInterleaved: false,
    ])
    reader.add(out)
    reader.startReading()
    var pcm = Data()
    while let sb = out.copyNextSampleBuffer(), let bb = CMSampleBufferGetDataBuffer(sb) {
      var len = 0
      var ptr: UnsafeMutablePointer<Int8>?
      CMBlockBufferGetDataPointer(bb, atOffset: 0, lengthAtOffsetOut: nil, totalLengthOut: &len, dataPointerOut: &ptr)
      if let p = ptr { pcm.append(UnsafeBufferPointer(start: p, count: len)) }
    }
    if reader.status == .failed { return "\(reader.error.map { "\($0)" } ?? "read failed")" }
    try wavData(pcm: pcm, rate: 48000).write(to: URL(fileURLWithPath: dst))
    return nil
  } catch {
    return "\(error)"
  }
}

func wavData(pcm: Data, rate: Int) -> Data {
  var d = Data()
  func u32(_ v: UInt32) { var x = v.littleEndian; d.append(Data(bytes: &x, count: 4)) }
  func u16(_ v: UInt16) { var x = v.littleEndian; d.append(Data(bytes: &x, count: 2)) }
  d.append("RIFF".data(using: .ascii)!); u32(UInt32(36 + pcm.count)); d.append("WAVE".data(using: .ascii)!)
  d.append("fmt ".data(using: .ascii)!); u32(16); u16(1); u16(1); u32(UInt32(rate)); u32(UInt32(rate * 2)); u16(2); u16(16)
  d.append("data".data(using: .ascii)!); u32(UInt32(pcm.count)); d.append(pcm)
  return d
}

/// The samples of a 16-bit mono wav (as written by Dart's export: canonical header, chunks walked anyway).
func wavSamples(_ path: String) -> (Data, Int)? {
  guard let d = FileManager.default.contents(atPath: path), d.count > 12 else { return nil }
  var i = 12, rate = 48000
  while i + 8 <= d.count {
    let id = String(data: d[i..<i + 4], encoding: .ascii) ?? ""
    let size = Int(d[i + 4]) | Int(d[i + 5]) << 8 | Int(d[i + 6]) << 16 | Int(d[i + 7]) << 24
    if id == "fmt " { rate = Int(d[i + 12]) | Int(d[i + 13]) << 8 | Int(d[i + 14]) << 16 | Int(d[i + 15]) << 24 }
    if id == "data" { return (d.subdata(in: i + 8..<min(d.count, i + 8 + size)), rate) }
    i += 8 + size + (size & 1)
  }
  return nil
}

// MARK: encoder

final class Mp4Encoder {
  let path: String
  private let writer: AVAssetWriter
  private let video: AVAssetWriterInput
  private let adaptor: AVAssetWriterInputPixelBufferAdaptor
  private let audio: AVAssetWriterInput?
  private let width: Int, height: Int, fps: Int
  private var frame = 0
  private var pcm = Data(), rate = 48000, audioPos = 0  // audioPos in samples
  private var audioFormat: CMAudioFormatDescription?
  private var audioFinished = false
  var error: String?

  init(path: String, width: Int, height: Int, fps: Int, audioWav: String?) throws {
    self.path = path
    self.width = width
    self.height = height
    self.fps = fps
    try? FileManager.default.removeItem(atPath: path)
    writer = try AVAssetWriter(outputURL: URL(fileURLWithPath: path), fileType: .mp4)
    writer.shouldOptimizeForNetworkUse = true
    video = AVAssetWriterInput(mediaType: .video, outputSettings: [
      AVVideoCodecKey: AVVideoCodecType.h264, AVVideoWidthKey: width, AVVideoHeightKey: height,
      AVVideoCompressionPropertiesKey: [AVVideoAverageBitRateKey: width * height * 7, AVVideoMaxKeyFrameIntervalKey: fps * 2,
                                        AVVideoProfileLevelKey: AVVideoProfileLevelH264HighAutoLevel],
    ])
    video.expectsMediaDataInRealTime = false
    adaptor = AVAssetWriterInputPixelBufferAdaptor(assetWriterInput: video, sourcePixelBufferAttributes: [
      kCVPixelBufferPixelFormatTypeKey as String: kCVPixelFormatType_32BGRA,
      kCVPixelBufferWidthKey as String: width, kCVPixelBufferHeightKey as String: height,
    ])
    writer.add(video)
    if let wav = audioWav, let (samples, r) = wavSamples(wav) {
      pcm = samples
      rate = r
      let a = AVAssetWriterInput(mediaType: .audio, outputSettings: [
        AVFormatIDKey: kAudioFormatMPEG4AAC, AVSampleRateKey: r, AVNumberOfChannelsKey: 1, AVEncoderBitRateKey: 128_000,
      ])
      a.expectsMediaDataInRealTime = false
      writer.add(a)
      audio = a
      var asbd = AudioStreamBasicDescription(mSampleRate: Float64(r), mFormatID: kAudioFormatLinearPCM,
                                             mFormatFlags: kLinearPCMFormatFlagIsSignedInteger | kLinearPCMFormatFlagIsPacked,
                                             mBytesPerPacket: 2, mFramesPerPacket: 1, mBytesPerFrame: 2,
                                             mChannelsPerFrame: 1, mBitsPerChannel: 16, mReserved: 0)
      CMAudioFormatDescriptionCreate(allocator: nil, asbd: &asbd, layoutSize: 0, layout: nil, magicCookieSize: 0,
                                     magicCookie: nil, extensions: nil, formatDescriptionOut: &audioFormat)
    } else {
      audio = nil
    }
    guard writer.startWriting() else { throw NSError(domain: "export", code: 1, userInfo: [NSLocalizedDescriptionKey: "\(writer.error.map { "\($0)" } ?? "startWriting failed")"]) }
    writer.startSession(atSourceTime: .zero)
  }

  /// Audio up to `seconds` (the writer interleaves, so it is fed alongside the video).
  private func feedAudio(until seconds: Double) {
    guard let a = audio, let fmt = audioFormat, !audioFinished else { return }
    defer {
      // the writer interleaves: an input that has no more data must say so, or the video input stalls
      if audioPos >= pcm.count / 2 { a.markAsFinished(); audioFinished = true }
    }
    let target = min(pcm.count / 2, Int(seconds * Double(rate)))
    while audioPos < target && a.isReadyForMoreMediaData {
      let n = min(4096, target - audioPos)
      let bytes = pcm.subdata(in: audioPos * 2..<(audioPos + n) * 2)
      var block: CMBlockBuffer?
      CMBlockBufferCreateWithMemoryBlock(allocator: nil, memoryBlock: nil, blockLength: bytes.count, blockAllocator: nil,
                                         customBlockSource: nil, offsetToData: 0, dataLength: bytes.count, flags: 0, blockBufferOut: &block)
      guard let b = block else { return }
      _ = bytes.withUnsafeBytes { CMBlockBufferReplaceDataBytes(with: $0.baseAddress!, blockBuffer: b, offsetIntoDestination: 0, dataLength: bytes.count) }
      var sb: CMSampleBuffer?
      CMAudioSampleBufferCreateReadyWithPacketDescriptions(allocator: nil, dataBuffer: b, formatDescription: fmt, sampleCount: n,
                                                           presentationTimeStamp: CMTime(value: CMTimeValue(audioPos), timescale: CMTimeScale(rate)),
                                                           packetDescriptions: nil, sampleBufferOut: &sb)
      guard let s = sb, a.append(s) else { return }
      audioPos += n
    }
  }

  private func waitForVideo() -> Bool {
    var spins = 0
    while !video.isReadyForMoreMediaData {
      if writer.status != .writing { return false }
      feedAudio(until: Double(frame) / Double(fps) + 1.0)
      usleep(2000)
      spins += 1
      if spins > 15000 {  // 30 s
        error = "encoder stalled at frame \(frame), audio \(audioPos)/\(pcm.count / 2) samples, audio ready \(audio?.isReadyForMoreMediaData ?? false), status \(writer.status.rawValue)"
        return false
      }
    }
    return true
  }

  func append(rgba: Data) -> Bool {
    guard rgba.count == width * height * 4 else { error = "frame is \(rgba.count) bytes, want \(width * height * 4)"; return false }
    guard waitForVideo(), let pool = adaptor.pixelBufferPool else { error = error ?? "\(writer.error.map { "\($0)" } ?? "writer not ready")"; return false }
    var pbOut: CVPixelBuffer?
    CVPixelBufferPoolCreatePixelBuffer(nil, pool, &pbOut)
    guard let pb = pbOut else { error = "no pixel buffer"; return false }
    CVPixelBufferLockBaseAddress(pb, [])
    rgba.withUnsafeBytes { src in
      var s = vImage_Buffer(data: UnsafeMutableRawPointer(mutating: src.baseAddress!), height: vImagePixelCount(height),
                            width: vImagePixelCount(width), rowBytes: width * 4)
      var d = vImage_Buffer(data: CVPixelBufferGetBaseAddress(pb), height: vImagePixelCount(height),
                            width: vImagePixelCount(width), rowBytes: CVPixelBufferGetBytesPerRow(pb))
      let map: [UInt8] = [2, 1, 0, 3]  // RGBA → BGRA
      vImagePermuteChannels_ARGB8888(&s, &d, map, vImage_Flags(kvImageNoFlags))
    }
    CVPixelBufferUnlockBaseAddress(pb, [])
    guard adaptor.append(pb, withPresentationTime: CMTime(value: CMTimeValue(frame), timescale: CMTimeScale(fps))) else {
      error = "\(writer.error.map { "\($0)" } ?? "append failed")"; return false
    }
    frame += 1
    feedAudio(until: Double(frame) / Double(fps) + 0.5)
    return true
  }

  func finish(_ done: @escaping (String?) -> Void) {
    video.markAsFinished()
    let end = Double(frame) / Double(fps)
    if let a = audio, !audioFinished {
      pcm = pcm.prefix(min(pcm.count, Int(end * Double(rate)) * 2))  // no sound after the last frame
      var spins = 0
      while !audioFinished && writer.status == .writing && spins < 15000 {
        feedAudio(until: end + 1)
        if !audioFinished && !a.isReadyForMoreMediaData { usleep(2000); spins += 1 }
      }
      if !audioFinished { a.markAsFinished(); audioFinished = true }
    }
    writer.endSession(atSourceTime: CMTime(value: CMTimeValue(frame), timescale: CMTimeScale(fps)))
    writer.finishWriting {
      done(self.writer.status == .completed ? nil : "\(self.writer.error.map { "\($0)" } ?? "finish failed")")
    }
  }

  func cancel() {
    writer.cancelWriting()
    try? FileManager.default.removeItem(atPath: path)
  }
}
