import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../api/webtoon_api.dart';
import '../models/world.dart';
import '../providers/providers.dart';
import '../theme.dart';
import '../widgets/common.dart';
import 'campaigns_screen.dart';
import 'reader_screen.dart';

/// World detail: synopsis, tone, rules, playable characters, the user's campaigns here,
/// and "Začít kampaň".
class WorldDetailScreen extends ConsumerWidget {
  final String worldId;
  const WorldDetailScreen({super.key, required this.worldId});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final world = ref.watch(worldProvider(worldId));
    final userId = ref.watch(apiProvider).userId;
    return Scaffold(
      appBar: AppBar(title: Text(world.valueOrNull?.title ?? 'Svět')),
      body: world.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (e, _) => ErrorRetry(
          message: '$e',
          onRetry: () => ref.invalidate(worldProvider(worldId)),
        ),
        data: (w) => _Body(world: w, userId: userId),
      ),
      bottomNavigationBar: world.hasValue
          ? SafeArea(
              child: Padding(
                padding: const EdgeInsets.fromLTRB(16, 8, 16, 12),
                child: FilledButton.icon(
                  key: const ValueKey('start-campaign'),
                  onPressed: () => startCampaign(context, ref, world.value!),
                  icon: const Icon(Icons.play_arrow_rounded),
                  label: const Text('Začít kampaň'),
                ),
              ),
            )
          : null,
    );
  }
}

class _Body extends ConsumerWidget {
  final World world;
  final String userId;
  const _Body({required this.world, required this.userId});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final scheme = Theme.of(context).colorScheme;
    final playable = world.playableFor(userId);
    final campaigns = ref.watch(worldCampaignsProvider(world.id)).valueOrNull;
    return ListView(
      padding: const EdgeInsets.fromLTRB(16, 20, 16, 32),
      children: [
        Text(world.title, style: Theme.of(context).textTheme.headlineMedium),
        const SizedBox(height: 10),
        Wrap(
          spacing: 6,
          runSpacing: 6,
          children: [
            Tag(audienceLabel(world.audience)),
            if (world.tone.isNotEmpty) Tag(world.tone),
          ],
        ),
        const SizedBox(height: 16),
        if (world.synopsis.isNotEmpty)
          Text(
            world.synopsis,
            style: const TextStyle(fontSize: 16, height: 1.45),
          ),
        if (world.rules.isNotEmpty) ...[
          const SizedBox(height: 20),
          Text('Pravidla světa', style: Theme.of(context).textTheme.titleLarge),
          const SizedBox(height: 6),
          for (final r in world.rules)
            Padding(
              padding: const EdgeInsets.only(bottom: 4),
              child: Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text(
                    '✦  ',
                    style: TextStyle(color: ComicColors.accent),
                  ),
                  Expanded(child: Text(r)),
                ],
              ),
            ),
        ],
        const SizedBox(height: 24),
        Text('Hratelné postavy', style: Theme.of(context).textTheme.titleLarge),
        const SizedBox(height: 10),
        if (playable.isEmpty)
          Text(
            'Tento svět nemá hratelné postavy.',
            style: TextStyle(color: scheme.onSurfaceVariant),
          ),
        for (final c in playable)
          Padding(
            padding: const EdgeInsets.only(bottom: 14),
            child: ComicCard(child: CharacterInfo(character: c)),
          ),
        if (campaigns != null && campaigns.isNotEmpty) ...[
          const SizedBox(height: 12),
          Text('Moje kampaně', style: Theme.of(context).textTheme.titleLarge),
          const SizedBox(height: 10),
          for (final c in campaigns)
            Padding(
              padding: const EdgeInsets.only(bottom: 12),
              child: CampaignTile(campaign: c, showWorld: false),
            ),
        ],
      ],
    );
  }
}

class CharacterInfo extends StatelessWidget {
  final Character character;
  const CharacterInfo({super.key, required this.character});

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        CircleAvatar(
          radius: 24,
          backgroundColor: ComicColors.accent,
          foregroundColor: Colors.white,
          child: Text(
            character.name.isEmpty ? '?' : character.name.characters.first,
            style: ComicFonts.title().copyWith(
              fontSize: 22,
              color: Colors.white,
            ),
          ),
        ),
        const SizedBox(width: 14),
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                character.name,
                style: ComicFonts.title().copyWith(fontSize: 20),
              ),
              if (character.personality.isNotEmpty)
                Text(
                  character.personality,
                  style: ComicFonts.ui(
                    700,
                  ).copyWith(fontSize: 13, color: ComicColors.accent),
                ),
              if (character.description.isNotEmpty) ...[
                const SizedBox(height: 6),
                Text(
                  character.description,
                  maxLines: 4,
                  overflow: TextOverflow.ellipsis,
                  style: TextStyle(
                    color: scheme.onSurfaceVariant,
                    height: 1.35,
                  ),
                ),
              ],
            ],
          ),
        ),
      ],
    );
  }
}

/// Pick a playable character → POST /campaigns → open the reader on the first episode.
Future<void> startCampaign(
  BuildContext context,
  WidgetRef ref,
  World world,
) async {
  final api = ref.read(apiProvider);
  final playable = world.playableFor(api.userId);
  if (playable.isEmpty) {
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(content: Text('Tento svět nemá hratelnou postavu.')),
    );
    return;
  }
  final picked = await showModalBottomSheet<Character>(
    context: context,
    showDragHandle: true,
    isScrollControlled: true,
    builder: (ctx) => _PickCharacterSheet(world: world, characters: playable),
  );
  if (picked == null || !context.mounted) return;
  final messenger = ScaffoldMessenger.of(context);
  final nav = Navigator.of(context);
  try {
    final created = await api.createCampaign(
      worldId: world.id,
      playerCharacterId: picked.id,
    );
    ref.invalidate(campaignsProvider);
    ref.invalidate(worldCampaignsProvider(world.id));
    await nav.push(
      MaterialPageRoute<void>(
        builder: (_) => ReaderScreen(campaignId: created.campaign.id),
      ),
    );
  } on ApiException catch (e) {
    messenger.showSnackBar(SnackBar(content: Text(e.message)));
  }
}

class _PickCharacterSheet extends StatefulWidget {
  final World world;
  final List<Character> characters;
  const _PickCharacterSheet({required this.world, required this.characters});

  @override
  State<_PickCharacterSheet> createState() => _PickCharacterSheetState();
}

class _PickCharacterSheetState extends State<_PickCharacterSheet> {
  late Character _selected = widget.characters.first;

  @override
  Widget build(BuildContext context) {
    return SafeArea(
      child: Padding(
        padding: const EdgeInsets.fromLTRB(16, 0, 16, 16),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Text(
              'Za koho budeš hrát?',
              style: Theme.of(context).textTheme.headlineSmall,
            ),
            const SizedBox(height: 14),
            Flexible(
              child: ListView(
                shrinkWrap: true,
                children: [
                  for (final c in widget.characters)
                    Padding(
                      padding: const EdgeInsets.only(bottom: 12),
                      child: ComicCard(
                        key: ValueKey('pick-${c.id}'),
                        color: c.id == _selected.id
                            ? ComicColors.accent.withValues(alpha: 0.14)
                            : null,
                        onTap: () => setState(() => _selected = c),
                        child: Row(
                          children: [
                            Expanded(child: CharacterInfo(character: c)),
                            Icon(
                              c.id == _selected.id
                                  ? Icons.radio_button_checked
                                  : Icons.radio_button_off,
                              color: ComicColors.accent,
                            ),
                          ],
                        ),
                      ),
                    ),
                ],
              ),
            ),
            const SizedBox(height: 4),
            Text(
              'První díl se začne generovat hned (≈ 6–8 kreditů, 1 za panel).',
              textAlign: TextAlign.center,
              style: TextStyle(
                color: Theme.of(context).colorScheme.onSurfaceVariant,
                fontSize: 13,
              ),
            ),
            const SizedBox(height: 10),
            FilledButton(
              key: const ValueKey('confirm-start'),
              onPressed: () => Navigator.pop(context, _selected),
              child: Text('Začít jako ${_selected.name}'),
            ),
          ],
        ),
      ),
    );
  }
}
