import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../models/campaign.dart';
import '../models/episode.dart';
import '../providers/providers.dart';
import '../theme.dart';
import '../widgets/common.dart';
import 'reader_screen.dart';

/// The user's campaigns (GET /campaigns), newest activity first.
class CampaignsScreen extends ConsumerWidget {
  const CampaignsScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final campaigns = ref.watch(campaignsProvider);
    return Scaffold(
      appBar: AppBar(title: const Text('Moje kampaně')),
      body: campaigns.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (e, _) => ErrorRetry(
          message: '$e',
          onRetry: () => ref.invalidate(campaignsProvider),
        ),
        data: (list) => RefreshIndicator(
          onRefresh: () => ref.refresh(campaignsProvider.future),
          child: list.isEmpty
              ? ListView(
                  children: const [
                    SizedBox(height: 120),
                    EmptyState(
                      icon: Icons.auto_stories_outlined,
                      title: 'Zatím žádná kampaň',
                      subtitle: 'Vyber si svět a začni svůj příběh.',
                    ),
                  ],
                )
              : ListView.separated(
                  padding: const EdgeInsets.fromLTRB(16, 16, 16, 32),
                  itemCount: list.length,
                  separatorBuilder: (_, _) => const SizedBox(height: 14),
                  itemBuilder: (_, i) => CampaignTile(campaign: list[i]),
                ),
        ),
      ),
    );
  }
}

class CampaignTile extends ConsumerWidget {
  final CampaignSummary campaign;
  final bool showWorld;
  const CampaignTile({
    super.key,
    required this.campaign,
    this.showWorld = true,
  });

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final scheme = Theme.of(context).colorScheme;
    final status = campaign.lastEpisodeStatus.isEmpty
        ? null
        : EpisodeStatus.parse(campaign.lastEpisodeStatus);
    final (label, color) = switch (status) {
      EpisodeStatus.ready => ('Nový díl je hotový', const Color(0xFF2E9E5B)),
      EpisodeStatus.failed => ('Poslední díl selhal', scheme.error),
      EpisodeStatus.queued ||
      EpisodeStatus.generating => ('Generuje se…', ComicColors.accent),
      null => ('Bez dílů', scheme.outline),
    };
    final title = campaign.title.isNotEmpty
        ? campaign.title
        : campaign.worldTitle;
    return ComicCard(
      key: ValueKey('campaign-${campaign.id}'),
      onTap: () async {
        await Navigator.of(context).push(
          MaterialPageRoute<void>(
            builder: (_) => ReaderScreen(campaignId: campaign.id),
          ),
        );
        ref.invalidate(campaignsProvider);
      },
      child: Row(
        children: [
          Container(
            width: 52,
            height: 52,
            alignment: Alignment.center,
            decoration: BoxDecoration(
              color: ComicColors.accent,
              borderRadius: BorderRadius.circular(12),
            ),
            child: Text(
              '${campaign.episodes}',
              style: ComicFonts.title().copyWith(
                fontSize: 24,
                color: Colors.white,
              ),
            ),
          ),
          const SizedBox(width: 14),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(title, style: ComicFonts.title().copyWith(fontSize: 20)),
                if (showWorld &&
                    campaign.worldTitle.isNotEmpty &&
                    campaign.worldTitle != title)
                  Text(
                    campaign.worldTitle,
                    style: TextStyle(color: scheme.onSurfaceVariant),
                  ),
                const SizedBox(height: 4),
                Row(
                  children: [
                    Container(
                      width: 8,
                      height: 8,
                      decoration: BoxDecoration(
                        color: color,
                        shape: BoxShape.circle,
                      ),
                    ),
                    const SizedBox(width: 6),
                    Text(
                      '${_episodes(campaign.episodes)} · $label',
                      style: ComicFonts.ui(700).copyWith(fontSize: 13),
                    ),
                  ],
                ),
              ],
            ),
          ),
          const Icon(Icons.chevron_right_rounded),
        ],
      ),
    );
  }

  static String _episodes(int n) => switch (n) {
    1 => '1 díl',
    2 || 3 || 4 => '$n díly',
    _ => '$n dílů',
  };
}
