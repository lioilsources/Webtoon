import 'package:flutter/material.dart';
import 'package:flutter/rendering.dart' show ScrollCacheExtent;
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../i18n/languages.dart';
import '../models/campaign.dart';
import '../models/episode.dart';
import '../providers/episode_provider.dart';
import '../providers/language_provider.dart';
import '../providers/providers.dart';
import '../providers/reader_provider.dart';
import '../reader/episode_end_block.dart';
import '../reader/episode_view.dart';
import '../reader/local_episode_end.dart';
import '../theme.dart';

/// The webtoon reader for one campaign: one vertical scroll of every episode. The view is
/// anchored on the focused episode (default: the latest) — earlier episodes are above it,
/// reachable by scrolling up, and the end-of-episode block with choices sits after the last.
///
/// With an API that cannot edit (the offline pack reader) nothing is generated: under each
/// episode the recorded choice and "Další díl", after the last one "Konec" + another story.
class ReaderScreen extends ConsumerStatefulWidget {
  final String campaignId;

  /// Open on episode 1 instead of the latest (the library).
  final bool startAtFirst;

  const ReaderScreen({
    super.key,
    required this.campaignId,
    this.startAtFirst = false,
  });

  @override
  ConsumerState<ReaderScreen> createState() => _ReaderScreenState();
}

class _ReaderScreenState extends ConsumerState<ReaderScreen> {
  final _scroll = ScrollController();
  String? _anchoredOn;

  @override
  void initState() {
    super.initState();
    if (widget.startAtFirst) {
      ref.read(readerProvider(widget.campaignId).notifier).startAtFirst();
    }
  }

  @override
  void dispose() {
    _scroll.dispose();
    super.dispose();
  }

  ReaderNotifier get _notifier =>
      ref.read(readerProvider(widget.campaignId).notifier);

  void _jumpToFocusIfChanged(String focusId) {
    if (_anchoredOn == focusId) return;
    final first = _anchoredOn == null;
    _anchoredOn = focusId;
    if (first) return;
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (_scroll.hasClients) _scroll.jumpTo(0);
    });
  }

  @override
  Widget build(BuildContext context) {
    final st = ref.watch(readerProvider(widget.campaignId));
    final comic = ComicTheme.of(context);
    final campaign = st.campaign;
    final title = campaign?.title.isNotEmpty == true
        ? campaign!.title
        : (st.world?.title ?? 'Čtečka');

    return Scaffold(
      backgroundColor: comic.readerBackground,
      appBar: AppBar(
        title: Text(title),
        actions: [
          if (st.episodes.isNotEmpty)
            _LanguageMenu(
              focus: ref
                  .watch(episodeProvider(st.episodes[st.focusIndex].id))
                  .episode,
            ),
          if (st.episodes.isNotEmpty)
            IconButton(
              key: const ValueKey('history-button'),
              tooltip: 'Historie dílů',
              icon: const Icon(Icons.format_list_numbered_rounded),
              onPressed: () => _showHistory(context, st),
            ),
        ],
      ),
      body: _body(context, st),
    );
  }

  Widget _body(BuildContext context, ReaderState st) {
    if (st.campaign == null) {
      if (st.error != null) {
        return _Message(
          text: st.error!,
          action: OutlinedButton(
            onPressed: _notifier.load,
            child: const Text('Zkusit znovu'),
          ),
        );
      }
      return const Center(child: CircularProgressIndicator());
    }
    final eps = st.episodes;
    final canEdit = ref.watch(apiProvider).canEdit;
    final isPlayer = _notifier.isPlayer && canEdit;
    final local = !canEdit;
    if (eps.isEmpty) {
      return _Message(
        text: local ? 'Příběh nemá žádný díl.' : 'Kampaň zatím nemá žádný díl.',
        action: isPlayer
            ? FilledButton(
                onPressed: st.submitting
                    ? null
                    : () => _notifier.continueWith(),
                child: const Text('Vygenerovat první díl'),
              )
            : null,
      );
    }

    final f = st.focusIndex;
    _jumpToFocusIfChanged(eps[f].id);
    final last = eps.last;

    // Refresh the campaign's episode list when the latest episode finishes.
    ref.listen(episodeProvider(last.id), (prev, next) {
      if (prev?.episode?.needsPolling == true &&
          next.episode?.needsPolling == false) {
        _notifier.refreshCampaign();
      }
    });

    final lang = ref.watch(readerLanguageProvider);
    Widget item(int i) {
      final next = i + 1 < eps.length ? eps[i + 1] : null;
      return EpisodeView(
        key: ValueKey('episode-${eps[i].id}'),
        episodeId: eps[i].id,
        world: st.world,
        editable: isPlayer,
        nextChosenText: local ? null : next?.chosen?.text,
        footer: local && next != null
            ? (ep) => LocalEpisodeEnd(
                choices: [
                  for (final c in ep.choices)
                    c.localized(ep.displayLanguage(lang)),
                ],
                chosen: next.chosen,
                onNext: () => _notifier.focus(next.id),
              )
            : null,
      );
    }

    final centerKey = ValueKey('center-${eps[f].id}');
    return RefreshIndicator(
      onRefresh: () async {
        await _notifier.refreshCampaign();
        ref.invalidate(episodeProvider(last.id));
      },
      child: CustomScrollView(
        key: const ValueKey('reader-scroll'),
        controller: _scroll,
        center: centerKey,
        scrollCacheExtent: const ScrollCacheExtent.pixels(1600),
        slivers: [
          SliverList.builder(
            itemCount: f,
            itemBuilder: (_, i) => item(f - 1 - i),
          ),
          SliverToBoxAdapter(key: centerKey, child: item(f)),
          SliverList.builder(
            itemCount: eps.length - 1 - f,
            itemBuilder: (_, i) => item(f + 1 + i),
          ),
          SliverToBoxAdapter(
            child: local
                ? _LocalEnd(campaign: st.campaign!)
                : isPlayer
                ? _EndOfCampaign(st: st, notifier: _notifier)
                : null,
          ),
        ],
      ),
    );
  }

  void _showHistory(BuildContext context, ReaderState st) {
    showModalBottomSheet<void>(
      context: context,
      showDragHandle: true,
      builder: (ctx) => SafeArea(
        child: ListView(
          shrinkWrap: true,
          children: [
            Padding(
              padding: const EdgeInsets.fromLTRB(20, 0, 20, 8),
              child: Text(
                'Historie dílů',
                style: Theme.of(ctx).textTheme.headlineSmall,
              ),
            ),
            for (final e in st.episodes.reversed)
              ListTile(
                key: ValueKey('history-${e.id}'),
                leading: CircleAvatar(
                  backgroundColor: ComicColors.accent,
                  foregroundColor: Colors.white,
                  child: Text('${e.index}'),
                ),
                title: Text(
                  e.title.isNotEmpty
                      ? e.titleIn(ref.read(readerLanguageProvider))
                      : 'Díl ${e.index}',
                ),
                subtitle: Text(
                  [
                    episodeStatusLabel(e.status, e.panelsReady, e.panelsTotal),
                    if (e.chosen?.text.isNotEmpty == true)
                      '„${e.chosen!.text}“',
                  ].join(' · '),
                  maxLines: 2,
                  overflow: TextOverflow.ellipsis,
                ),
                selected: e.id == st.episodes[st.focusIndex].id,
                onTap: () {
                  Navigator.pop(ctx);
                  _notifier.focus(e.id);
                },
              ),
          ],
        ),
      ),
    );
  }
}

String episodeStatusLabel(EpisodeStatus s, int ready, int total) => switch (s) {
  EpisodeStatus.queued => 'Ve frontě',
  EpisodeStatus.generating =>
    total > 0 ? 'Kreslí se $ready/$total' : 'Píše se scénář',
  EpisodeStatus.ready => 'Hotovo',
  EpisodeStatus.failed => 'Selhalo',
};

/// What follows the last episode: the choices (ready), nothing (still generating), or — when
/// the last attempt failed — the previous ready episode's choices again.
class _EndOfCampaign extends ConsumerWidget {
  final ReaderState st;
  final ReaderNotifier notifier;
  const _EndOfCampaign({required this.st, required this.notifier});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final eps = st.episodes;
    final last = ref.watch(episodeProvider(eps.last.id)).episode;
    if (last == null || last.status.inProgress) {
      return const SizedBox(height: 120);
    }
    Episode? source;
    var heading = 'Co udělá dál?';
    if (last.status == EpisodeStatus.ready) {
      source = last;
    } else if (last.status == EpisodeStatus.failed) {
      heading = 'Zkus to jinak';
      final prevReady = eps
          .sublist(0, eps.length - 1)
          .lastWhere(
            (e) => e.status == EpisodeStatus.ready,
            orElse: () => const EpisodeSummary(id: '', index: 0),
          );
      if (prevReady.id.isNotEmpty) {
        source = ref.watch(episodeProvider(prevReady.id)).episode;
        if (source == null) return const SizedBox(height: 120);
      } else {
        return Padding(
          padding: const EdgeInsets.fromLTRB(16, 8, 16, 48),
          child: Center(
            child: FilledButton.icon(
              key: const ValueKey('restart-campaign'),
              onPressed: st.submitting ? null : () => notifier.continueWith(),
              icon: const Icon(Icons.refresh),
              label: const Text('Začít díl znovu'),
            ),
          ),
        );
      }
    } else {
      return const SizedBox(height: 120);
    }

    final max = st.world?.permissions.maxEpisodes ?? 0;
    if (max > 0 &&
        eps.last.index >= max &&
        last.status == EpisodeStatus.ready) {
      return const _Message(
        text: 'Konec. Kampaň dosáhla posledního dílu tohoto světa.',
      );
    }
    return Center(
      child: ConstrainedBox(
        constraints: const BoxConstraints(maxWidth: kStripMaxWidth),
        child: EpisodeEndBlock(
          key: ValueKey('end-${source.id}'),
          choices: [
            for (final c in source.choices)
              c.localized(
                source.displayLanguage(ref.watch(readerLanguageProvider)),
              ),
          ],
          creditsEstimate: source.creditsCost > 0
              ? source.creditsCost
              : source.panelsTotal,
          world: st.world,
          campaign: st.campaign,
          submitting: st.submitting,
          error: st.submitError,
          heading: heading,
          onSubmit: (c) async {
            final id = await notifier.continueWith(
              choiceId: c.choiceId,
              freeText: c.freeText,
              director: c.director,
            );
            if (id != null) {
              // A new campaign entry exists now; the list screen should show it.
              ref.invalidate(campaignsProvider);
            }
          },
        ),
      ),
    );
  }
}

/// Offline reader, after the last episode: "Konec" + another story (same world first).
class _LocalEnd extends ConsumerWidget {
  final Campaign campaign;
  const _LocalEnd({required this.campaign});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final all = ref.watch(campaignsProvider).valueOrNull ?? const [];
    final others = all.where((c) => c.id != campaign.id).toList();
    final suggestion = others.isEmpty
        ? null
        : others.firstWhere(
            (c) => c.worldId == campaign.worldId,
            orElse: () => others.first,
          );
    return Center(
      child: ConstrainedBox(
        constraints: const BoxConstraints(maxWidth: kStripMaxWidth),
        child: LocalStoryEnd(
          suggestion: suggestion,
          onOpen: (s) => Navigator.of(context).pushReplacement(
            MaterialPageRoute<void>(
              builder: (_) =>
                  ReaderScreen(campaignId: s.id, startAtFirst: true),
            ),
          ),
        ),
      ),
    );
  }
}

class _Message extends StatelessWidget {
  final String text;
  final Widget? action;
  const _Message({required this.text, this.action});

  @override
  Widget build(BuildContext context) => Center(
    child: Padding(
      padding: const EdgeInsets.all(32),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Text(
            text,
            textAlign: TextAlign.center,
            style: ComicFonts.title().copyWith(fontSize: 20),
          ),
          if (action != null) ...[const SizedBox(height: 16), action!],
        ],
      ),
    ),
  );
}

/// Language picker like Lexify's: "Originál" first, then every reader language by its own
/// name. Languages the focused episode is not (fully) translated into are disabled; episodes
/// without the chosen language fall back to their original on their own.
class _LanguageMenu extends ConsumerWidget {
  final Episode? focus;
  const _LanguageMenu({required this.focus});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final current = ref.watch(readerLanguageProvider);
    final source = focus?.sourceLanguage ?? 'cs';
    final available = focus?.languages ?? const <String>[];
    final shown = focus?.displayLanguage(current);
    PopupMenuItem<String> item(String value, String label, bool enabled) =>
        CheckedPopupMenuItem<String>(
          key: ValueKey('lang-$value'),
          value: value,
          enabled: enabled,
          checked: value == (current ?? ''),
          child: Text('${langFlag(value.isEmpty ? source : value)}  $label'),
        );
    return PopupMenuButton<String>(
      key: const ValueKey('language-button'),
      tooltip: 'Jazyk bublin',
      icon: shown == null
          ? const Icon(Icons.translate_rounded)
          : Text(
              '${langFlag(shown)} ${shown.toUpperCase()}',
              style: ComicFonts.ui(900).copyWith(fontSize: 13),
            ),
      onSelected: (v) => ref
          .read(readerLanguageProvider.notifier)
          .select(v.isEmpty ? null : v),
      itemBuilder: (_) => [
        item('', 'Originál (${langDisplayName(source)})', true),
        const PopupMenuDivider(),
        for (final l in kReaderLanguages)
          if (l != source) item(l, langDisplayName(l), available.contains(l)),
      ],
    );
  }
}
