import 'package:flutter/material.dart';
import 'package:flutter/rendering.dart' show ScrollCacheExtent;
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../models/campaign.dart';
import '../models/episode.dart';
import '../providers/episode_provider.dart';
import '../providers/providers.dart';
import '../providers/reader_provider.dart';
import '../reader/episode_end_block.dart';
import '../reader/episode_view.dart';
import '../theme.dart';

/// The webtoon reader for one campaign: one vertical scroll of every episode. The view is
/// anchored on the focused episode (default: the latest) — earlier episodes are above it,
/// reachable by scrolling up, and the end-of-episode block with choices sits after the last.
class ReaderScreen extends ConsumerStatefulWidget {
  final String campaignId;
  const ReaderScreen({super.key, required this.campaignId});

  @override
  ConsumerState<ReaderScreen> createState() => _ReaderScreenState();
}

class _ReaderScreenState extends ConsumerState<ReaderScreen> {
  final _scroll = ScrollController();
  String? _anchoredOn;

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
    final isPlayer = _notifier.isPlayer;
    if (eps.isEmpty) {
      return _Message(
        text: 'Kampaň zatím nemá žádný díl.',
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

    Widget item(int i) => EpisodeView(
      key: ValueKey('episode-${eps[i].id}'),
      episodeId: eps[i].id,
      world: st.world,
      editable: isPlayer,
      nextChosenText: i + 1 < eps.length ? eps[i + 1].chosen?.text : null,
    );

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
            child: isPlayer
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
                title: Text(e.title.isNotEmpty ? e.title : 'Díl ${e.index}'),
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
          choices: source.choices,
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
