// State of "Your voice": the device token and the voice id (secure storage), the voice's status on the
// server, upload, delete, and fetching lines for the video export.

import 'dart:async';
import 'dart:io';

import 'package:flutter/foundation.dart' show debugPrint;
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';

import '../shop/shop_controller.dart';
import 'voice_api.dart';

/// The consent sentence, versioned; the server keeps it with the time (docs/voice-backend.md).
const kConsentVersion = 'toonfork-cs-1';

String get kPlatform => Platform.isIOS || Platform.isMacOS ? 'ios' : 'android';

class VoiceState {
  final bool loaded;
  final VoiceInfo? voice;
  final bool busy;
  final Object? error;
  const VoiceState({
    this.loaded = false,
    this.voice,
    this.busy = false,
    this.error,
  });

  bool get ready => voice?.status == VoiceStatus.ready;

  VoiceState copyWith({
    bool? loaded,
    VoiceInfo? voice,
    bool clearVoice = false,
    bool? busy,
    Object? error,
    bool clearError = false,
  }) => VoiceState(
    loaded: loaded ?? this.loaded,
    voice: clearVoice ? null : (voice ?? this.voice),
    busy: busy ?? this.busy,
    error: clearError ? null : (error ?? this.error),
  );
}

/// Where the token and the voice id live (tests use a map).
abstract class VoiceSecrets {
  Future<String?> read(String key);
  Future<void> write(String key, String? value);
}

class SecureVoiceSecrets implements VoiceSecrets {
  static const _s = FlutterSecureStorage();
  @override
  Future<String?> read(String key) async {
    try {
      return await _s.read(key: key);
    } catch (_) {
      return null;
    }
  }

  @override
  Future<void> write(String key, String? value) async {
    try {
      value == null
          ? await _s.delete(key: key)
          : await _s.write(key: key, value: value);
    } catch (_) {}
  }
}

class VoiceController extends StateNotifier<VoiceState> {
  final VoiceApi api;
  final VoiceSecrets secrets;
  final String? Function() receipt;
  Timer? _poll;

  VoiceController(this.api, this.secrets, this.receipt)
    : super(const VoiceState()) {
    _load();
  }

  static const _tokenKey = 'voice_device_token', _voiceKey = 'voice_id';

  Future<void> _load() async {
    final id = await secrets.read(_voiceKey);
    if (!mounted) return;
    state = state.copyWith(
      loaded: true,
      voice: id == null ? null : VoiceInfo(id, VoiceStatus.queued),
    );
    if (id != null) await refresh();
  }

  Future<String> _token() async {
    final t = await secrets.read(_tokenKey);
    if (t != null) return t;
    final (_, token) = await api.registerDevice(kPlatform);
    await secrets.write(_tokenKey, token);
    return token;
  }

  /// The voice's status on the server; polls while it is being made.
  Future<void> refresh() async {
    final v = state.voice;
    if (v == null) return;
    try {
      final info = await api.getVoice(await _token(), v.id);
      if (!mounted) return;
      state = state.copyWith(voice: info, clearError: true);
      _schedule(info.status == VoiceStatus.queued);
    } on VoiceApiError catch (e) {
      if (e.status == 404) {
        // deleted on the server (180 days unused, or the device was removed): record again
        await secrets.write(_voiceKey, null);
        if (mounted) state = state.copyWith(clearVoice: true);
      } else if (mounted) {
        state = state.copyWith(error: e);
        _schedule(e.transient);
      }
    }
  }

  void _schedule(bool again) {
    _poll?.cancel();
    if (again) _poll = Timer(const Duration(seconds: 10), refresh);
  }

  Future<void> upload(File sample, String consentText) async {
    final r = receipt();
    if (r == null || r.isEmpty) {
      state = state.copyWith(
        error: const VoiceApiError(402, 'receipt_invalid'),
      );
      return;
    }
    state = state.copyWith(busy: true, clearError: true);
    try {
      final info = await api.createVoice(
        token: await _token(),
        sample: sample,
        consentText: consentText,
        consentVersion: kConsentVersion,
        receipt: r,
        platform: kPlatform,
      );
      await secrets.write(_voiceKey, info.id);
      if (!mounted) return;
      state = state.copyWith(voice: info, busy: false);
      _schedule(info.status == VoiceStatus.queued);
    } catch (e) {
      if (mounted) state = state.copyWith(busy: false, error: e);
    }
  }

  /// Deletes the voice and the device on the server (sample, clone and lines), then here.
  Future<void> delete() async {
    state = state.copyWith(busy: true, clearError: true);
    try {
      final t = await secrets.read(_tokenKey);
      if (t != null) await api.deleteDevice(t);
      await secrets.write(_voiceKey, null);
      await secrets.write(_tokenKey, null);
      _poll?.cancel();
      if (mounted) state = state.copyWith(busy: false, clearVoice: true);
    } catch (e) {
      if (mounted) state = state.copyWith(busy: false, error: e);
    }
  }

  /// The lines (key → text) spoken in the voice, downloaded into [dir]: key → m4a path. Lines the server
  /// could not make are left out (the export reads them with a system voice). Waits for the worker, which
  /// may queue for the GPU; [onProgress] gets done / total.
  Future<Map<String, String>> fetchLines(
    String lang,
    Map<String, String> lines,
    Directory dir, {
    void Function(int done, int total)? onProgress,
    bool Function()? cancelled,
    Duration timeout = const Duration(minutes: 20),
  }) async {
    final v = state.voice;
    if (v == null || v.status != VoiceStatus.ready) {
      throw const VoiceApiError(409, 'voice_not_ready');
    }
    final token = await _token();
    final out = <String, String>{};
    final entries = [
      for (final e in lines.entries)
        if (e.value.trim().isNotEmpty)
          MapEntry(
            e.key,
            e.value.length > VoiceApi.maxChars
                ? e.value.substring(0, VoiceApi.maxChars)
                : e.value,
          ),
    ];
    final deadline = DateTime.now().add(timeout);
    for (var i = 0; i < entries.length; i += VoiceApi.maxLines) {
      final chunk = Map.fromEntries(entries.skip(i).take(VoiceApi.maxLines));
      final jobId = await api.requestLines(token, v.id, lang, chunk);
      VoiceJob job;
      while (true) {
        if (cancelled?.call() ?? false) return out;
        job = await api.getJob(token, jobId);
        onProgress?.call(i + job.done, entries.length);
        if (job.finished) break;
        if (DateTime.now().isAfter(deadline)) {
          debugPrint('voice: job $jobId still ${job.status} after $timeout');
          break;
        }
        await Future<void>.delayed(const Duration(seconds: 3));
      }
      for (final l in job.lines) {
        final path = '${dir.path}/voice_${out.length}.m4a';
        try {
          await api.download(l.url, path);
          out[l.key] = path;
        } catch (e) {
          debugPrint('voice: line ${l.key} not downloaded: $e');
        }
      }
    }
    return out;
  }

  @override
  void dispose() {
    _poll?.cancel();
    super.dispose();
  }
}

final voiceApiProvider = Provider<VoiceApi>((_) => VoiceApi());

final voiceProvider = StateNotifierProvider<VoiceController, VoiceState>((ref) {
  final api = ref.watch(voiceApiProvider);
  return VoiceController(
    api,
    SecureVoiceSecrets(),
    () => ref.read(shopProvider).entitlements.receipts[kVoiceProduct]?.receipt,
  );
});
