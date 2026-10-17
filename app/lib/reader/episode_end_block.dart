import 'package:flutter/material.dart';

import '../models/campaign.dart';
import '../models/episode.dart';
import '../models/world.dart';
import '../theme.dart';

/// The player's pick at the end of an episode.
class EndChoice {
  final String? choiceId;
  final String? freeText;
  final String label;
  final DirectorRequest? director;
  const EndChoice({
    this.choiceId,
    this.freeText,
    required this.label,
    this.director,
  });
}

/// End of the latest episode (§6): closed choices as buttons, a free text field, the
/// "director" section when the world permits it, and the credits cost before confirming.
class EpisodeEndBlock extends StatefulWidget {
  final List<Choice> choices;

  /// Credits the next episode costs (1 per panel; the next episode's panel count is not known
  /// yet, so the reader passes the current one as the estimate).
  final int creditsEstimate;
  final World? world;
  final Campaign? campaign;
  final bool submitting;
  final String? error;
  final String heading;
  final Future<void> Function(EndChoice choice) onSubmit;

  const EpisodeEndBlock({
    super.key,
    required this.choices,
    required this.onSubmit,
    this.creditsEstimate = 0,
    this.world,
    this.campaign,
    this.submitting = false,
    this.error,
    this.heading = 'Co udělá dál?',
  });

  @override
  State<EpisodeEndBlock> createState() => _EpisodeEndBlockState();
}

class _EpisodeEndBlockState extends State<EpisodeEndBlock> {
  final _free = TextEditingController();
  final Set<String> _add = {};
  final Set<String> _remove = {};
  String? _location;

  @override
  void dispose() {
    _free.dispose();
    super.dispose();
  }

  DirectorRequest? get _director {
    final d = DirectorRequest(
      addCharacters: _add.toList(),
      removeCharacters: _remove.toList(),
      locationId: _location,
    );
    return d.isEmpty ? null : d;
  }

  String get _cost {
    final n = widget.creditsEstimate;
    if (n <= 0) return '6–8 kreditů';
    return '≈ $n ${_credits(n)}';
  }

  static String _credits(int n) =>
      n == 1 ? 'kredit' : (n >= 2 && n <= 4 ? 'kredity' : 'kreditů');

  Future<void> _confirm(EndChoice c) async {
    final ok = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Vygenerovat další díl?'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              '„${c.label}“',
              style: ComicFonts.ui(700).copyWith(fontSize: 16),
            ),
            if (c.director != null) ...[
              const SizedBox(height: 8),
              Text(
                _directorSummary(c.director!),
                style: TextStyle(
                  color: Theme.of(ctx).colorScheme.onSurfaceVariant,
                  fontSize: 13,
                ),
              ),
            ],
            const SizedBox(height: 14),
            Row(
              children: [
                const Icon(Icons.toll, color: ComicColors.accent),
                const SizedBox(width: 8),
                Text(
                  'Cena: $_cost',
                  key: const ValueKey('confirm-cost'),
                  style: ComicFonts.ui(800),
                ),
              ],
            ),
            const SizedBox(height: 4),
            Text(
              '1 kredit za každý panel dílu.',
              style: TextStyle(
                color: Theme.of(ctx).colorScheme.onSurfaceVariant,
                fontSize: 12,
              ),
            ),
          ],
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx, false),
            child: const Text('Zrušit'),
          ),
          FilledButton(
            key: const ValueKey('confirm-generate'),
            onPressed: () => Navigator.pop(ctx, true),
            child: const Text('Generovat díl'),
          ),
        ],
      ),
    );
    if (ok == true) {
      await widget.onSubmit(c);
      if (mounted && widget.error == null) _free.clear();
    }
  }

  String _directorSummary(DirectorRequest d) {
    final w = widget.world;
    String name(String id) => w?.character(id)?.name ?? id;
    return [
      if (d.addCharacters.isNotEmpty)
        'Přidat: ${d.addCharacters.map(name).join(', ')}',
      if (d.removeCharacters.isNotEmpty)
        'Odebrat: ${d.removeCharacters.map(name).join(', ')}',
      if (d.locationId != null)
        'Lokace: ${w?.location(d.locationId)?.name ?? d.locationId}',
    ].join(' · ');
  }

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    final comic = ComicTheme.of(context);
    final closed = widget.choices.where((c) => !c.isFree).toList();
    final free = widget.choices.where((c) => c.isFree).firstOrNull;
    final busy = widget.submitting;
    final perms = widget.world?.permissions ?? const Permissions();

    return Padding(
      padding: const EdgeInsets.fromLTRB(16, 8, 16, 48),
      child: Container(
        key: const ValueKey('episode-end-block'),
        padding: const EdgeInsets.all(20),
        decoration: comic.card(color: scheme.surface, radius: 22),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Text(
              widget.heading,
              style: ComicFonts.title().copyWith(fontSize: 28, height: 1.1),
            ),
            const SizedBox(height: 4),
            Row(
              children: [
                const Icon(Icons.toll, size: 16, color: ComicColors.accent),
                const SizedBox(width: 6),
                Text(
                  'Další díl: $_cost',
                  key: const ValueKey('credits-cost'),
                  style: ComicFonts.ui(
                    700,
                  ).copyWith(fontSize: 13, color: scheme.onSurfaceVariant),
                ),
              ],
            ),
            const SizedBox(height: 16),
            for (final c in closed) ...[
              _ChoiceButton(
                key: ValueKey('choice-${c.id}'),
                text: c.text,
                enabled: !busy,
                onTap: () => _confirm(
                  EndChoice(choiceId: c.id, label: c.text, director: _director),
                ),
              ),
              const SizedBox(height: 10),
            ],
            if (free != null || widget.choices.isEmpty) ...[
              const SizedBox(height: 4),
              TextField(
                key: const ValueKey('free-text'),
                controller: _free,
                enabled: !busy,
                minLines: 1,
                maxLines: 4,
                maxLength: 500,
                textInputAction: TextInputAction.send,
                decoration: InputDecoration(
                  hintText: free?.text.isNotEmpty == true
                      ? free!.text
                      : 'Nebo napiš, co uděláš…',
                  suffixIcon: IconButton(
                    key: const ValueKey('free-send'),
                    tooltip: 'Odeslat',
                    icon: const Icon(Icons.send_rounded),
                    onPressed: busy ? null : _sendFree,
                  ),
                ),
                onSubmitted: (_) => _sendFree(),
              ),
            ],
            if (perms.allowsDirector && widget.world != null)
              _DirectorSection(
                world: widget.world!,
                campaign: widget.campaign,
                add: _add,
                remove: _remove,
                location: _location,
                enabled: !busy,
                onChanged: (loc) => setState(() => _location = loc),
                onToggle: () => setState(() {}),
              ),
            if (busy) ...[
              const SizedBox(height: 12),
              const LinearProgressIndicator(color: ComicColors.accent),
            ],
            if (widget.error != null) ...[
              const SizedBox(height: 12),
              Text(
                widget.error!,
                key: const ValueKey('submit-error'),
                style: TextStyle(color: scheme.error),
              ),
            ],
          ],
        ),
      ),
    );
  }

  void _sendFree() {
    final t = _free.text.trim();
    if (t.isEmpty || widget.submitting) return;
    _confirm(EndChoice(freeText: t, label: t, director: _director));
  }
}

class _ChoiceButton extends StatelessWidget {
  final String text;
  final bool enabled;
  final VoidCallback onTap;
  const _ChoiceButton({
    super.key,
    required this.text,
    required this.enabled,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    final comic = ComicTheme.of(context);
    final scheme = Theme.of(context).colorScheme;
    return Material(
      color: Colors.transparent,
      child: InkWell(
        onTap: enabled ? onTap : null,
        borderRadius: BorderRadius.circular(16),
        child: Ink(
          padding: const EdgeInsets.symmetric(horizontal: 18, vertical: 16),
          decoration: BoxDecoration(
            color: enabled
                ? ComicColors.accent.withValues(alpha: 0.10)
                : scheme.surfaceContainerHighest,
            borderRadius: BorderRadius.circular(16),
            border: Border.all(color: ComicColors.accent, width: 2.5),
            boxShadow: [
              BoxShadow(color: comic.shadow, offset: const Offset(3, 3)),
            ],
          ),
          child: Row(
            children: [
              Expanded(
                child: Text(
                  text,
                  style: ComicFonts.ui(800).copyWith(fontSize: 16),
                ),
              ),
              const Icon(
                Icons.arrow_forward_rounded,
                color: ComicColors.accent,
              ),
            ],
          ),
        ),
      ),
    );
  }
}

/// "Režie": add/remove characters and change the location, within world.permissions.
class _DirectorSection extends StatelessWidget {
  final World world;
  final Campaign? campaign;
  final Set<String> add;
  final Set<String> remove;
  final String? location;
  final bool enabled;
  final ValueChanged<String?> onChanged;
  final VoidCallback onToggle;

  const _DirectorSection({
    required this.world,
    required this.campaign,
    required this.add,
    required this.remove,
    required this.location,
    required this.enabled,
    required this.onChanged,
    required this.onToggle,
  });

  @override
  Widget build(BuildContext context) {
    final p = world.permissions;
    final present = campaign?.stateCharacterIds.toSet() ?? <String>{};
    final current = campaign?.currentLocation;
    final label = ComicFonts.ui(800).copyWith(fontSize: 13);
    return Padding(
      padding: const EdgeInsets.only(top: 8),
      child: Theme(
        data: Theme.of(context).copyWith(dividerColor: Colors.transparent),
        // Own Material so the tile's ink isn't hidden by the decorated card.
        child: Material(
          type: MaterialType.transparency,
          child: ExpansionTile(
            key: const ValueKey('director-section'),
            tilePadding: EdgeInsets.zero,
            leading: const Icon(
              Icons.movie_filter_outlined,
              color: ComicColors.accent,
            ),
            title: Text(
              'Režie',
              style: ComicFonts.title().copyWith(fontSize: 19),
            ),
            subtitle: const Text('Volitelné úpravy dalšího dílu'),
            childrenPadding: const EdgeInsets.only(bottom: 8),
            expandedCrossAxisAlignment: CrossAxisAlignment.start,
            children: [
              if (p.canAddCharacters) ...[
                Text('Postavy', style: label),
                const SizedBox(height: 6),
                Wrap(
                  spacing: 8,
                  runSpacing: 6,
                  children: [
                    for (final c in world.characters)
                      if (present.contains(c.id))
                        FilterChip(
                          label: Text('Odebrat ${c.name}'),
                          selected: remove.contains(c.id),
                          onSelected: enabled
                              ? (v) {
                                  v ? remove.add(c.id) : remove.remove(c.id);
                                  onToggle();
                                }
                              : null,
                        )
                      else
                        FilterChip(
                          label: Text('Přidat ${c.name}'),
                          selected: add.contains(c.id),
                          onSelected: enabled
                              ? (v) {
                                  v ? add.add(c.id) : add.remove(c.id);
                                  onToggle();
                                }
                              : null,
                        ),
                  ],
                ),
                const SizedBox(height: 12),
              ],
              if (p.canChangeLocation) ...[
                Text('Lokace', style: label),
                const SizedBox(height: 6),
                Wrap(
                  spacing: 8,
                  runSpacing: 6,
                  children: [
                    for (final l in world.allowedLocations)
                      ChoiceChip(
                        key: ValueKey('location-${l.id}'),
                        label: Text(
                          l.id == current ? '${l.name} (teď)' : l.name,
                        ),
                        selected: location == l.id,
                        onSelected: enabled
                            ? (v) => onChanged(v ? l.id : null)
                            : null,
                      ),
                  ],
                ),
              ],
            ],
          ),
        ),
      ),
    );
  }
}
