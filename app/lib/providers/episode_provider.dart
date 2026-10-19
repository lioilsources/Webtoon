import 'dart:async';

import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../api/webtoon_api.dart';
import '../models/episode.dart';
import '../services/push_notifications.dart';
import 'providers.dart';

final episodeProvider = StateNotifierProvider.autoDispose
    .family<EpisodeNotifier, EpisodeState, String>((ref, id) {
      final n = EpisodeNotifier(
        ref.watch(apiProvider),
        id,
        pollInterval: ref.watch(configProvider).pollInterval,
        push: ref.watch(pushNotificationsProvider),
      );
      n.load();
      return n;
    });

class EpisodeState {
  final Episode? episode;
  final bool loading;
  final String? error;

  /// Panels with an edit / regenerate request in flight.
  final Set<int> busyPanels;

  const EpisodeState({
    this.episode,
    this.loading = false,
    this.error,
    this.busyPanels = const {},
  });

  EpisodeState copyWith({
    Episode? episode,
    bool? loading,
    String? error,
    bool clearError = false,
    Set<int>? busyPanels,
  }) => EpisodeState(
    episode: episode ?? this.episode,
    loading: loading ?? this.loading,
    error: clearError ? null : (error ?? this.error),
    busyPanels: busyPanels ?? this.busyPanels,
  );
}

/// Loads one episode and polls it while it is queued/generating or a panel is re-rendering,
/// so panels appear one by one as the worker finishes them.
class EpisodeNotifier extends StateNotifier<EpisodeState> {
  final WebtoonApi _api;
  final String id;
  final Duration pollInterval;
  final PushNotifications push;
  Timer? _timer;
  bool _fetching = false;

  EpisodeNotifier(
    this._api,
    this.id, {
    this.pollInterval = const Duration(seconds: 2),
    this.push = const NoopPushNotifications(),
  }) : super(const EpisodeState(loading: true));

  Future<void> load() => _fetch();

  Future<void> _fetch() async {
    if (_fetching || !mounted) return;
    _fetching = true;
    _timer?.cancel();
    try {
      final ep = await _api.getEpisode(id);
      if (!mounted) return;
      final was = state.episode;
      state = state.copyWith(episode: ep, loading: false, clearError: true);
      if (ep.needsPolling) {
        if (was == null) unawaited(push.watchEpisode(id));
      } else if (was != null && was.needsPolling) {
        unawaited(push.unwatchEpisode(id));
      }
    } on ApiException catch (e) {
      if (!mounted) return;
      state = state.copyWith(loading: false, error: e.message);
    } finally {
      _fetching = false;
    }
    _schedule();
  }

  void _schedule() {
    if (!mounted) return;
    final ep = state.episode;
    // Keep polling while in flight; after an error retry only if we know it was in flight.
    if (ep != null && ep.needsPolling) {
      _timer?.cancel();
      _timer = Timer(pollInterval, _fetch);
    }
  }

  Future<void> refresh() => _fetch();

  /// Edit one bubble's text (no image regeneration). Optimistic; reverts on failure.
  Future<bool> editBubble(int panelIndex, int bubbleIndex, String text) async {
    final ep = state.episode;
    if (ep == null) return false;
    final panel = ep.panels.firstWhere((p) => p.index == panelIndex);
    if (bubbleIndex < 0 || bubbleIndex >= panel.bubbles.length) return false;
    final bubbles = [
      for (var i = 0; i < panel.bubbles.length; i++)
        i == bubbleIndex
            ? panel.bubbles[i].copyWith(text: text)
            : panel.bubbles[i],
    ];
    state = state.copyWith(
      episode: ep.withPanel(panel.copyWith(bubbles: bubbles)),
      busyPanels: {...state.busyPanels, panelIndex},
      clearError: true,
    );
    try {
      final saved = await _api.updateBubbles(id, panelIndex, bubbles);
      if (!mounted) return true;
      state = state.copyWith(
        episode: state.episode!.withPanel(saved),
        busyPanels: {...state.busyPanels}..remove(panelIndex),
      );
      return true;
    } on ApiException catch (e) {
      if (!mounted) return false;
      state = state.copyWith(
        episode: state.episode!.withPanel(panel),
        busyPanels: {...state.busyPanels}..remove(panelIndex),
        error: e.message,
      );
      return false;
    }
  }

  /// Turn a panel's loop on/off, change its motion prompt or length, or re-render it
  /// (`reseed_video`). The backend answers with the panel; polling picks up the finished loop.
  Future<bool> setMotion(int panelIndex, Map<String, dynamic> patch) async {
    final ep = state.episode;
    if (ep == null) return false;
    state = state.copyWith(
      busyPanels: {...state.busyPanels, panelIndex},
      clearError: true,
    );
    try {
      final p = await _api.updatePanelMotion(id, panelIndex, patch);
      if (!mounted) return true;
      state = state.copyWith(
        episode: state.episode!.withPanel(p),
        busyPanels: {...state.busyPanels}..remove(panelIndex),
      );
      _schedule();
      return true;
    } on ApiException catch (e) {
      if (!mounted) return false;
      state = state.copyWith(
        busyPanels: {...state.busyPanels}..remove(panelIndex),
        error: e.message,
      );
      return false;
    }
  }

  /// Re-render a failed (or any finished) panel; polling resumes until it is done.
  Future<bool> regenerate(int panelIndex) async {
    final ep = state.episode;
    if (ep == null) return false;
    state = state.copyWith(
      busyPanels: {...state.busyPanels, panelIndex},
      clearError: true,
    );
    try {
      final p = await _api.regeneratePanel(id, panelIndex);
      if (!mounted) return true;
      state = state.copyWith(
        episode: state.episode!.withPanel(p),
        busyPanels: {...state.busyPanels}..remove(panelIndex),
      );
      _schedule();
      return true;
    } on ApiException catch (e) {
      if (!mounted) return false;
      state = state.copyWith(
        busyPanels: {...state.busyPanels}..remove(panelIndex),
        error: e.message,
      );
      return false;
    }
  }

  @override
  void dispose() {
    _timer?.cancel();
    super.dispose();
  }
}
