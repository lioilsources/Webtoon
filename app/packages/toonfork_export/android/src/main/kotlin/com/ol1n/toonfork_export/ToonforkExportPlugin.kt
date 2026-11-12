// Video export for Toonfork (Android): system TTS to a wav file, audio decoding to a wav, and an
// H.264 + AAC mp4 encoder (MediaCodec + MediaMuxer) fed with RGBA frames from Dart.
// Channel "toonfork/export"; see lib/toonfork_export.dart for the calls.
package com.ol1n.toonfork_export

import android.content.Context
import android.media.MediaCodec
import android.media.MediaCodecInfo
import android.media.MediaExtractor
import android.media.MediaFormat
import android.media.MediaMuxer
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.speech.tts.TextToSpeech
import android.speech.tts.UtteranceProgressListener
import io.flutter.embedding.engine.plugins.FlutterPlugin
import io.flutter.plugin.common.MethodCall
import io.flutter.plugin.common.MethodChannel
import java.io.File
import java.io.RandomAccessFile
import java.nio.ByteBuffer
import java.nio.ByteOrder
import java.util.Locale
import java.util.concurrent.Executors

class ToonforkExportPlugin : FlutterPlugin, MethodChannel.MethodCallHandler {
    private lateinit var channel: MethodChannel
    private lateinit var context: Context
    private val worker = Executors.newSingleThreadExecutor()
    private val main = Handler(Looper.getMainLooper())
    private var tts: TextToSpeech? = null
    private var ttsReady = false
    private val ttsWaiting = mutableListOf<() -> Unit>()
    private var encoder: Mp4Encoder? = null

    override fun onAttachedToEngine(binding: FlutterPlugin.FlutterPluginBinding) {
        context = binding.applicationContext
        channel = MethodChannel(binding.binaryMessenger, "toonfork/export")
        channel.setMethodCallHandler(this)
    }

    override fun onDetachedFromEngine(binding: FlutterPlugin.FlutterPluginBinding) {
        channel.setMethodCallHandler(null)
        tts?.shutdown()
        encoder?.cancel()
    }

    private fun withTts(block: (TextToSpeech) -> Unit) {
        val t = tts
        if (t != null && ttsReady) { block(t); return }
        ttsWaiting.add { block(tts!!) }
        if (t == null) {
            tts = TextToSpeech(context) { status ->
                main.post {
                    ttsReady = status == TextToSpeech.SUCCESS
                    val w = ttsWaiting.toList(); ttsWaiting.clear()
                    w.forEach { it() }
                }
            }
        }
    }

    private fun bg(result: MethodChannel.Result, block: () -> Any?) {
        worker.execute {
            try {
                val v = block()
                main.post { result.success(v) }
            } catch (e: Exception) {
                main.post { result.error("export", e.message ?: e.toString(), null) }
            }
        }
    }

    override fun onMethodCall(call: MethodCall, result: MethodChannel.Result) {
        when (call.method) {
            "voices" -> withTts { t ->
                if (!ttsReady) { result.success(emptyList<Any>()); return@withTts }
                val lang = (call.argument<String>("lang") ?: "cs").substringBefore('-').lowercase()
                val out = (t.voices ?: emptySet()).filter { it.locale.language.lowercase() == lang && !it.isNetworkConnectionRequired }
                    .map { v ->
                        val n = v.name.lowercase()
                        // Android voices carry no gender; Google's names sometimes say it
                        val g = if ("female" in n) "f" else if ("male" in n) "m" else ""
                        mapOf("id" to v.name, "name" to v.name, "lang" to v.locale.toLanguageTag(), "gender" to g,
                              "quality" to (if (v.quality >= 400) 2 else if (v.quality >= 300) 1 else 0))
                    }
                result.success(out)
            }
            "synth" -> withTts { t ->
                if (!ttsReady) { result.error("synth", "text to speech is not available", null); return@withTts }
                val text = call.argument<String>("text") ?: ""
                val path = call.argument<String>("path")!!
                val lang = call.argument<String>("lang") ?: "cs"
                val voice = call.argument<String>("voice")
                val v = t.voices?.firstOrNull { it.name == voice }
                if (v != null) t.voice = v else t.language = Locale.forLanguageTag(lang)
                t.setSpeechRate((call.argument<Double>("rate") ?: 1.0).toFloat())
                t.setPitch((call.argument<Double>("pitch") ?: 1.0).toFloat())
                val id = "u${System.nanoTime()}"
                t.setOnUtteranceProgressListener(object : UtteranceProgressListener() {
                    override fun onStart(utteranceId: String?) {}
                    override fun onDone(utteranceId: String?) { if (utteranceId == id) main.post { result.success(path) } }
                    @Deprecated("Deprecated in Java")
                    override fun onError(utteranceId: String?) { if (utteranceId == id) main.post { result.error("synth", "TTS failed", null) } }
                    override fun onError(utteranceId: String?, errorCode: Int) { if (utteranceId == id) main.post { result.error("synth", "TTS failed ($errorCode)", null) } }
                })
                if (t.synthesizeToFile(text, Bundle(), File(path), id) != TextToSpeech.SUCCESS) {
                    result.error("synth", "TTS refused the line", null)
                }
            }
            "decode" -> bg(result) {
                val dst = call.argument<String>("dst")!!
                decodeToWav(call.argument<String>("src")!!, dst)
                dst
            }
            "start" -> bg(result) {
                encoder?.cancel()
                encoder = Mp4Encoder(call.argument<String>("path")!!, call.argument<Int>("width")!!,
                    call.argument<Int>("height")!!, call.argument<Int>("fps")!!, call.argument<String>("audio"))
                true
            }
            "frame" -> {
                val rgba = call.argument<ByteArray>("rgba")!!
                bg(result) { (encoder ?: throw IllegalStateException("no encoder")).append(rgba); true }
            }
            "finish" -> bg(result) {
                val e = encoder ?: throw IllegalStateException("no encoder")
                encoder = null
                e.finish()
                e.path
            }
            "cancel" -> bg(result) { encoder?.cancel(); encoder = null; true }
            else -> result.notImplemented()
        }
    }
}

/** Any audio MediaExtractor reads → 16-bit wav in the decoder's own rate and channels (Dart resamples). */
fun decodeToWav(src: String, dst: String) {
    val ex = MediaExtractor()
    ex.setDataSource(src)
    val track = (0 until ex.trackCount).first { ex.getTrackFormat(it).getString(MediaFormat.KEY_MIME)!!.startsWith("audio/") }
    ex.selectTrack(track)
    val fmt = ex.getTrackFormat(track)
    val dec = MediaCodec.createDecoderByType(fmt.getString(MediaFormat.KEY_MIME)!!)
    dec.configure(fmt, null, null, 0)
    dec.start()
    var rate = fmt.getInteger(MediaFormat.KEY_SAMPLE_RATE)
    var channels = fmt.getInteger(MediaFormat.KEY_CHANNEL_COUNT)
    val pcm = java.io.ByteArrayOutputStream()
    val info = MediaCodec.BufferInfo()
    var inDone = false
    while (true) {
        if (!inDone) {
            val i = dec.dequeueInputBuffer(10_000)
            if (i >= 0) {
                val n = ex.readSampleData(dec.getInputBuffer(i)!!, 0)
                if (n < 0) { dec.queueInputBuffer(i, 0, 0, 0, MediaCodec.BUFFER_FLAG_END_OF_STREAM); inDone = true }
                else { dec.queueInputBuffer(i, 0, n, ex.sampleTime, 0); ex.advance() }
            }
        }
        val o = dec.dequeueOutputBuffer(info, 10_000)
        if (o == MediaCodec.INFO_OUTPUT_FORMAT_CHANGED) {
            rate = dec.outputFormat.getInteger(MediaFormat.KEY_SAMPLE_RATE)
            channels = dec.outputFormat.getInteger(MediaFormat.KEY_CHANNEL_COUNT)
        } else if (o >= 0) {
            val b = dec.getOutputBuffer(o)!!
            val bytes = ByteArray(info.size)
            b.position(info.offset); b.get(bytes)
            pcm.write(bytes)
            dec.releaseOutputBuffer(o, false)
            if (info.flags and MediaCodec.BUFFER_FLAG_END_OF_STREAM != 0) break
        }
    }
    dec.stop(); dec.release(); ex.release()
    writeWav(File(dst), pcm.toByteArray(), rate, channels)
}

fun writeWav(f: File, pcm: ByteArray, rate: Int, channels: Int) {
    val h = ByteBuffer.allocate(44).order(ByteOrder.LITTLE_ENDIAN)
    h.put("RIFF".toByteArray()).putInt(36 + pcm.size).put("WAVE".toByteArray())
    h.put("fmt ".toByteArray()).putInt(16).putShort(1).putShort(channels.toShort()).putInt(rate)
        .putInt(rate * channels * 2).putShort((channels * 2).toShort()).putShort(16)
    h.put("data".toByteArray()).putInt(pcm.size)
    f.outputStream().use { it.write(h.array()); it.write(pcm) }
}

/** (16-bit samples, rate) of a mono 16-bit wav, as written by Dart's export. */
fun readWav(path: String): Pair<ByteArray, Int> {
    val raf = RandomAccessFile(path, "r")
    val all = ByteArray(raf.length().toInt()); raf.readFully(all); raf.close()
    val b = ByteBuffer.wrap(all).order(ByteOrder.LITTLE_ENDIAN)
    var i = 12; var rate = 48000
    while (i + 8 <= all.size) {
        val id = String(all, i, 4); val size = b.getInt(i + 4)
        if (id == "fmt ") rate = b.getInt(i + 12)
        if (id == "data") return Pair(all.copyOfRange(i + 8, minOf(all.size, i + 8 + size)), rate)
        i += 8 + size + (size and 1)
    }
    throw IllegalArgumentException("no data chunk in $path")
}

class Mp4Encoder(val path: String, private val width: Int, private val height: Int, private val fps: Int, audioWav: String?) {
    private val muxer: MediaMuxer
    private val video: MediaCodec
    private val audio: MediaCodec?
    private var pcm = ByteArray(0)
    private var rate = 48000
    private var audioPos = 0 // samples
    private var audioInDone = false
    private var videoTrack = -1
    private var audioTrack = -1
    private var started = false
    private val pending = mutableListOf<Triple<Int, ByteArray, MediaCodec.BufferInfo>>() // before the muxer starts
    private var frame = 0
    private val info = MediaCodec.BufferInfo()
    private val yuv = ByteArray(width * height * 3 / 2)

    init {
        File(path).delete()
        muxer = MediaMuxer(path, MediaMuxer.OutputFormat.MUXER_OUTPUT_MPEG_4)
        val vf = MediaFormat.createVideoFormat(MediaFormat.MIMETYPE_VIDEO_AVC, width, height)
        vf.setInteger(MediaFormat.KEY_COLOR_FORMAT, MediaCodecInfo.CodecCapabilities.COLOR_FormatYUV420Flexible)
        vf.setInteger(MediaFormat.KEY_BIT_RATE, width * height * 7)
        vf.setInteger(MediaFormat.KEY_FRAME_RATE, fps)
        vf.setInteger(MediaFormat.KEY_I_FRAME_INTERVAL, 2)
        video = MediaCodec.createEncoderByType(MediaFormat.MIMETYPE_VIDEO_AVC)
        video.configure(vf, null, null, MediaCodec.CONFIGURE_FLAG_ENCODE)
        video.start()
        if (audioWav != null) {
            val (s, r) = readWav(audioWav)
            pcm = s; rate = r
            val af = MediaFormat.createAudioFormat(MediaFormat.MIMETYPE_AUDIO_AAC, r, 1)
            af.setInteger(MediaFormat.KEY_AAC_PROFILE, MediaCodecInfo.CodecProfileLevel.AACObjectLC)
            af.setInteger(MediaFormat.KEY_BIT_RATE, 128_000)
            af.setInteger(MediaFormat.KEY_MAX_INPUT_SIZE, 16384)
            audio = MediaCodec.createEncoderByType(MediaFormat.MIMETYPE_AUDIO_AAC)
            audio.configure(af, null, null, MediaCodec.CONFIGURE_FLAG_ENCODE)
            audio.start()
        } else {
            audio = null
        }
    }

    /** RGBA → the codec's YUV 4:2:0 planes (BT.601, limited range). */
    private fun fill(img: android.media.Image, rgba: ByteArray) {
        val y = img.planes[0]; val u = img.planes[1]; val v = img.planes[2]
        val yb = y.buffer; val ub = u.buffer; val vb = v.buffer
        for (row in 0 until height) {
            var p = row * width * 4
            var yo = row * y.rowStride
            for (col in 0 until width) {
                val r = rgba[p].toInt() and 255; val g = rgba[p + 1].toInt() and 255; val b = rgba[p + 2].toInt() and 255
                yb.put(yo, (((66 * r + 129 * g + 25 * b + 128) shr 8) + 16).toByte())
                if (row % 2 == 0 && col % 2 == 0) {
                    val cu = (((-38 * r - 74 * g + 112 * b + 128) shr 8) + 128).toByte()
                    val cv = (((112 * r - 94 * g - 18 * b + 128) shr 8) + 128).toByte()
                    ub.put((row / 2) * u.rowStride + (col / 2) * u.pixelStride, cu)
                    vb.put((row / 2) * v.rowStride + (col / 2) * v.pixelStride, cv)
                }
                p += 4; yo += y.pixelStride
            }
        }
    }

    private fun write(track: Int, buf: ByteBuffer, i: MediaCodec.BufferInfo) {
        if (i.size == 0 || i.flags and MediaCodec.BUFFER_FLAG_CODEC_CONFIG != 0) return
        if (!started) {
            val bytes = ByteArray(i.size); buf.position(i.offset); buf.get(bytes)
            val copy = MediaCodec.BufferInfo(); copy.set(0, i.size, i.presentationTimeUs, i.flags)
            pending.add(Triple(track, bytes, copy)); return
        }
        buf.position(i.offset); buf.limit(i.offset + i.size)
        muxer.writeSampleData(if (track == 0) videoTrack else audioTrack, buf, i)
    }

    private fun maybeStart() {
        if (started || videoTrack < 0 || (audio != null && audioTrack < 0)) return
        muxer.start(); started = true
        for ((t, bytes, i) in pending) muxer.writeSampleData(if (t == 0) videoTrack else audioTrack, ByteBuffer.wrap(bytes), i)
        pending.clear()
    }

    /** Drains a codec; returns true at end of stream. */
    private fun drain(codec: MediaCodec, track: Int, untilEos: Boolean): Boolean {
        while (true) {
            val o = codec.dequeueOutputBuffer(info, if (untilEos) 10_000 else 0)
            when {
                o == MediaCodec.INFO_TRY_AGAIN_LATER -> if (!untilEos) return false
                o == MediaCodec.INFO_OUTPUT_FORMAT_CHANGED -> {
                    if (track == 0) videoTrack = muxer.addTrack(codec.outputFormat) else audioTrack = muxer.addTrack(codec.outputFormat)
                    maybeStart()
                }
                o >= 0 -> {
                    write(track, codec.getOutputBuffer(o)!!, info)
                    codec.releaseOutputBuffer(o, false)
                    if (info.flags and MediaCodec.BUFFER_FLAG_END_OF_STREAM != 0) return true
                }
            }
        }
    }

    private fun feedAudio(untilSeconds: Double, eos: Boolean) {
        val a = audio ?: return
        val total = pcm.size / 2
        val target = minOf(total, (untilSeconds * rate).toInt())
        while (!audioInDone) {
            if (audioPos >= target && !(eos && audioPos >= total)) break
            val i = a.dequeueInputBuffer(if (eos) 10_000 else 0)
            if (i < 0) { drain(a, 1, false); if (!eos) break else continue }
            val buf = a.getInputBuffer(i)!!
            val pts = audioPos.toLong() * 1_000_000 / rate
            if (audioPos >= total) {
                a.queueInputBuffer(i, 0, 0, pts, MediaCodec.BUFFER_FLAG_END_OF_STREAM); audioInDone = true; break
            }
            val n = minOf(buf.capacity() / 2, 2048, maxOf(target, if (eos) total else 0) - audioPos)
            buf.clear(); buf.put(pcm, audioPos * 2, n * 2)
            a.queueInputBuffer(i, 0, n * 2, pts, 0)
            audioPos += n
        }
        drain(a, 1, false)
    }

    fun append(rgba: ByteArray) {
        require(rgba.size == width * height * 4) { "frame is ${rgba.size} bytes, want ${width * height * 4}" }
        var i: Int
        while (true) {
            i = video.dequeueInputBuffer(10_000)
            if (i >= 0) break
            drain(video, 0, false)
        }
        val img = video.getInputImage(i)!!
        fill(img, rgba)
        video.queueInputBuffer(i, 0, width * height * 3 / 2, frame.toLong() * 1_000_000 / fps, 0)
        frame++
        drain(video, 0, false)
        feedAudio(frame.toDouble() / fps + 0.5, false)
    }

    fun finish() {
        val end = frame.toDouble() / fps
        if (audio != null) {
            pcm = pcm.copyOf(minOf(pcm.size, (end * rate).toInt() * 2))
            feedAudio(end, true)
        }
        var i: Int
        while (true) { i = video.dequeueInputBuffer(10_000); if (i >= 0) break; drain(video, 0, false) }
        video.queueInputBuffer(i, 0, 0, frame.toLong() * 1_000_000 / fps, MediaCodec.BUFFER_FLAG_END_OF_STREAM)
        drain(video, 0, true)
        audio?.let { drain(it, 1, true) }
        video.stop(); video.release()
        audio?.stop(); audio?.release()
        if (started) muxer.stop()
        muxer.release()
    }

    fun cancel() {
        try { video.stop() } catch (_: Exception) {}
        video.release()
        try { audio?.stop() } catch (_: Exception) {}
        audio?.release()
        try { muxer.release() } catch (_: Exception) {}
        File(path).delete()
    }
}
