import 'package:flutter/foundation.dart' show debugPrint;
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'pack_store.dart';

enum PackPhase { loading, extracting, ready, error }

class PackBootstrapState {
  final PackPhase phase;
  final int done;
  final int total;
  final String? error;

  const PackBootstrapState({
    this.phase = PackPhase.loading,
    this.done = 0,
    this.total = 0,
    this.error,
  });

  static const ready = PackBootstrapState(phase: PackPhase.ready);

  bool get isReady => phase == PackPhase.ready;

  /// 0..1 while extracting, null when the count is not known yet.
  double? get progress =>
      phase == PackPhase.extracting && total > 0 ? done / total : null;
}

/// Reader start-up: load the installed packs and extract the bundled starter when it is
/// missing or newer. The home screen shows a splash until [PackBootstrapState.isReady].
class PackBootstrap extends StateNotifier<PackBootstrapState> {
  final PackStore store;

  PackBootstrap(this.store, {PackBootstrapState? initial})
    : super(initial ?? const PackBootstrapState());

  /// Already loaded store (tests).
  PackBootstrap.ready(this.store) : super(PackBootstrapState.ready);

  Future<void> start() => _run(force: false);

  /// "Obnovit starter": re-extract the bundled starter over the installed one.
  Future<void> reinstallStarter() => _run(force: true);

  Future<void> _run({required bool force}) async {
    state = const PackBootstrapState();
    try {
      final installed = await store.ensureStarter(
        force: force,
        onProgress: (done, total) {
          if (!mounted) return;
          state = PackBootstrapState(
            phase: PackPhase.extracting,
            done: done,
            total: total,
          );
        },
      );
      debugPrint(
        'packs: ${installed ? 'starter extracted' : 'starter up to date'}, '
        '${store.packs.length} pack(s), ${store.stories.length} stories '
        'in ${(await store.rootDir()).path}',
      );
      if (mounted) state = PackBootstrapState.ready;
    } catch (e, st) {
      debugPrint('packs: bootstrap failed: $e\n$st');
      if (mounted) {
        state = PackBootstrapState(phase: PackPhase.error, error: '$e');
      }
    }
  }
}
