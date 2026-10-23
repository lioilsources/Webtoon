import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../api/webtoon_api.dart';
import '../models/campaign.dart';
import '../models/world.dart';
import 'providers.dart';

final readerProvider = StateNotifierProvider.autoDispose
    .family<ReaderNotifier, ReaderState, String>((ref, campaignId) {
      final n = ReaderNotifier(ref.watch(apiProvider), campaignId);
      n.load();
      return n;
    });

class ReaderState {
  final Campaign? campaign;
  final World? world;
  final bool loading;
  final String? error;

  /// Episode the scroll view is anchored on (null = the latest one).
  final String? focusEpisodeId;

  /// POST /campaigns/{id}/episodes in flight.
  final bool submitting;
  final String? submitError;

  const ReaderState({
    this.campaign,
    this.world,
    this.loading = false,
    this.error,
    this.focusEpisodeId,
    this.submitting = false,
    this.submitError,
  });

  List<EpisodeSummary> get episodes => campaign?.episodes ?? const [];

  int get focusIndex {
    final eps = episodes;
    if (eps.isEmpty) return 0;
    final i = eps.indexWhere((e) => e.id == focusEpisodeId);
    return i < 0 ? eps.length - 1 : i;
  }

  ReaderState copyWith({
    Campaign? campaign,
    World? world,
    bool? loading,
    String? error,
    bool clearError = false,
    String? focusEpisodeId,
    bool? submitting,
    String? submitError,
    bool clearSubmitError = false,
  }) => ReaderState(
    campaign: campaign ?? this.campaign,
    world: world ?? this.world,
    loading: loading ?? this.loading,
    error: clearError ? null : (error ?? this.error),
    focusEpisodeId: focusEpisodeId ?? this.focusEpisodeId,
    submitting: submitting ?? this.submitting,
    submitError: clearSubmitError ? null : (submitError ?? this.submitError),
  );
}

/// Campaign + world for the reader, the episode the view is focused on, and continuing
/// the story (POST /campaigns/{id}/episodes) — after which the reader follows the new episode.
class ReaderNotifier extends StateNotifier<ReaderState> {
  final WebtoonApi _api;
  final String campaignId;

  bool _startAtFirst = false;

  ReaderNotifier(this._api, this.campaignId)
    : super(const ReaderState(loading: true));

  /// Open on the first episode instead of the latest (the library opens stories from the
  /// start). Applies now when the campaign is loaded, otherwise when it arrives.
  void startAtFirst() {
    final eps = state.episodes;
    if (eps.isNotEmpty) {
      state = state.copyWith(focusEpisodeId: eps.first.id);
    } else {
      _startAtFirst = true;
    }
  }

  Future<void> load() async {
    state = state.copyWith(loading: true, clearError: true);
    try {
      final c = await _api.getCampaign(campaignId);
      final w = state.world?.id == c.worldId
          ? state.world!
          : await _api.getWorld(c.worldId);
      if (!mounted) return;
      final first = _startAtFirst && c.episodes.isNotEmpty
          ? c.episodes.first.id
          : null;
      _startAtFirst = false;
      state = state.copyWith(
        campaign: c,
        world: w,
        loading: false,
        focusEpisodeId: first,
      );
    } on ApiException catch (e) {
      if (!mounted) return;
      state = state.copyWith(loading: false, error: e.message);
    }
  }

  Future<void> refreshCampaign() async {
    try {
      final c = await _api.getCampaign(campaignId);
      if (mounted) state = state.copyWith(campaign: c);
    } on ApiException catch (_) {
      // keep the old list; the episode views show their own errors
    }
  }

  void focus(String episodeId) =>
      state = state.copyWith(focusEpisodeId: episodeId);

  bool get isPlayer => state.campaign?.playerId == _api.userId;

  /// Continue with a closed choice, free text, or (after a failed first episode) neither.
  /// Returns the new episode id, or null on error (see [ReaderState.submitError]).
  Future<String?> continueWith({
    String? choiceId,
    String? freeText,
    DirectorRequest? director,
  }) async {
    if (state.submitting) return null;
    state = state.copyWith(submitting: true, clearSubmitError: true);
    try {
      final id = await _api.continueCampaign(
        campaignId,
        choiceId: choiceId,
        freeText: freeText,
        director: director,
      );
      final c = await _api.getCampaign(campaignId);
      if (!mounted) return id;
      state = state.copyWith(
        campaign: c,
        focusEpisodeId: id,
        submitting: false,
      );
      return id;
    } on ApiException catch (e) {
      if (!mounted) return null;
      state = state.copyWith(submitting: false, submitError: e.message);
      return null;
    }
  }
}
