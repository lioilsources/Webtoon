import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../models/author.dart';
import '../models/world.dart';
import '../providers/providers.dart';
import '../screens/world_detail_screen.dart';
import '../theme.dart';
import '../widgets/common.dart';
import 'author_widgets.dart';
import 'character_editor_screen.dart';
import 'dashboard_view.dart';
import 'location_editor_screen.dart';

/// The author's world editor: Základ (info, style, permissions), Lore & kánon (rules,
/// factions, canon nodes, constraints), Postavy, Lokace, Přehled (dashboard).
/// "Uložit" PATCHes the world fields; characters and locations save in their own editors.
class WorldEditorScreen extends ConsumerStatefulWidget {
  final String worldId;
  const WorldEditorScreen({super.key, required this.worldId});

  @override
  ConsumerState<WorldEditorScreen> createState() => _WorldEditorScreenState();
}

class _NodeItem {
  static int _seq = 0;
  final int uid = _seq++;
  final String id;
  final TextEditingController text;
  final bool fresh; // added by the author in this session: focus its field
  _NodeItem(this.id, String t, {this.fresh = false})
    : text = TextEditingController(text: t);
}

class _WorldEditorScreenState extends ConsumerState<WorldEditorScreen> {
  final _title = TextEditingController();
  final _synopsis = TextEditingController();
  final _tone = TextEditingController();
  final _language = TextEditingController();
  final _maxEpisodes = TextEditingController();
  String _audience = 'teen';
  String _visibility = 'private';
  String _styleId = '';
  bool _canAdd = false, _canCreate = false, _canChangeLoc = false;
  Set<String> _allowed = {};
  Map<String, dynamic> _bible = {};
  final List<TextEditingController> _rules = [];
  final List<TextEditingController> _factions = [];
  final List<_NodeItem> _nodes = [];
  final List<TextEditingController> _constraints = [];
  bool _initialized = false;
  bool _saving = false;

  @override
  void dispose() {
    for (final c in [_title, _synopsis, _tone, _language, _maxEpisodes]) {
      c.dispose();
    }
    for (final c in [..._rules, ..._factions, ..._constraints]) {
      c.dispose();
    }
    for (final n in _nodes) {
      n.text.dispose();
    }
    super.dispose();
  }

  void _fill(World w) {
    _title.text = w.title;
    _synopsis.text = w.synopsis;
    _tone.text = w.tone;
    _language.text = w.language;
    _audience = w.audience;
    _visibility = w.visibility;
    _styleId = w.styleId;
    final p = w.permissions;
    _canAdd = p.canAddCharacters;
    _canCreate = p.canCreateCharacter;
    _canChangeLoc = p.canChangeLocation;
    _allowed = p.allowedLocations.toSet();
    _maxEpisodes.text = p.maxEpisodes == 0 ? '' : '${p.maxEpisodes}';
    _bible = Map.of(w.bible);
    _rules
      ..clear()
      ..addAll(w.rules.map((r) => TextEditingController(text: r)));
    _factions
      ..clear()
      ..addAll(w.factions.map((f) => TextEditingController(text: f)));
    _nodes
      ..clear()
      ..addAll(w.canonNodes.map((n) => _NodeItem(n.id, n.text)));
    _constraints
      ..clear()
      ..addAll(w.constraints.map((c) => TextEditingController(text: c)));
    _initialized = true;
  }

  List<String> _texts(List<TextEditingController> cs) =>
      cs.map((c) => c.text.trim()).where((t) => t.isNotEmpty).toList();

  Map<String, dynamic> _patch() => {
    'title': _title.text.trim(),
    'synopsis': _synopsis.text.trim(),
    'tone': _tone.text.trim(),
    'audience': _audience,
    'language': _language.text.trim().isEmpty ? 'cs' : _language.text.trim(),
    'visibility': _visibility,
    'style_id': _styleId,
    'bible': {
      ..._bible,
      'rules': _texts(_rules),
      'factions': _texts(_factions),
    },
    'canon': {
      'nodes': [
        for (final n in _nodes)
          if (n.text.text.trim().isNotEmpty)
            CanonNode(id: n.id, text: n.text.text.trim()).toJson(),
      ],
      'constraints': _texts(_constraints),
    },
    'permissions': Permissions(
      canAddCharacters: _canAdd,
      canCreateCharacter: _canCreate,
      canChangeLocation: _canChangeLoc,
      allowedLocations: _allowed.toList()..sort(),
      maxEpisodes: int.tryParse(_maxEpisodes.text.trim()) ?? 0,
    ).toJson(),
  };

  Future<void> _save() async {
    if (_title.text.trim().isEmpty) {
      showSnack(context, 'Svět potřebuje název.');
      return;
    }
    setState(() => _saving = true);
    final saved = await guarded(
      context,
      () => ref.read(apiProvider).updateWorld(widget.worldId, _patch()),
    );
    if (!mounted) return;
    setState(() {
      _saving = false;
      if (saved != null) _fill(saved);
    });
    if (saved != null) {
      invalidateWorld(ref, widget.worldId);
      showSnack(context, 'Svět uložen.');
    }
  }

  void _moveNode(int from, int to) {
    setState(() {
      final n = _nodes.removeAt(from);
      _nodes.insert(to.clamp(0, _nodes.length), n);
    });
  }

  @override
  Widget build(BuildContext context) {
    final world = ref.watch(worldProvider(widget.worldId));
    final w = world.valueOrNull;
    if (w != null && !_initialized) _fill(w);
    return DefaultTabController(
      length: 5,
      child: Scaffold(
        appBar: AppBar(
          title: Text(w?.title ?? 'Editor světa'),
          actions: [
            if (w != null)
              IconButton(
                key: const ValueKey('play-own'),
                tooltip: 'Zahraj si vlastní svět',
                onPressed: () => startCampaign(context, ref, w),
                icon: const Icon(Icons.play_circle_outline),
              ),
            Padding(
              padding: const EdgeInsets.only(right: 8),
              child: FilledButton(
                key: const ValueKey('save-world'),
                onPressed: w == null || _saving ? null : _save,
                child: const Text('Uložit'),
              ),
            ),
          ],
          bottom: const TabBar(
            isScrollable: true,
            tabAlignment: TabAlignment.start,
            tabs: [
              Tab(text: 'Základ'),
              Tab(text: 'Lore & kánon'),
              Tab(text: 'Postavy'),
              Tab(text: 'Lokace'),
              Tab(text: 'Přehled'),
            ],
          ),
        ),
        body: w == null
            ? world.hasError
                  ? ErrorRetry(
                      message: '${world.error}',
                      onRetry: () =>
                          ref.invalidate(worldProvider(widget.worldId)),
                    )
                  : const Center(child: CircularProgressIndicator())
            : TabBarView(
                children: [
                  _basics(w),
                  _lore(),
                  _CharacterList(world: w),
                  _LocationList(world: w),
                  WorldDashboard(
                    world: w,
                    onPlay: () => startCampaign(context, ref, w),
                  ),
                ],
              ),
      ),
    );
  }

  Widget _basics(World w) {
    final presets = ref.watch(stylePresetsProvider);
    return ListView(
      key: const ValueKey('tab-basics'),
      padding: const EdgeInsets.fromLTRB(16, 4, 16, 40),
      children: [
        const SectionTitle('Svět'),
        TextField(
          key: const ValueKey('world-title'),
          controller: _title,
          decoration: const InputDecoration(labelText: 'Název'),
        ),
        const SizedBox(height: 12),
        TextField(
          key: const ValueKey('world-synopsis'),
          controller: _synopsis,
          minLines: 2,
          maxLines: 6,
          decoration: const InputDecoration(labelText: 'Synopse'),
        ),
        const SizedBox(height: 12),
        TextField(
          key: const ValueKey('world-tone'),
          controller: _tone,
          decoration: const InputDecoration(
            labelText: 'Tón',
            hintText: 'dobrodružný, hřejivý, lehce tajemný',
          ),
        ),
        const SizedBox(height: 12),
        TextField(
          key: const ValueKey('world-language'),
          controller: _language,
          decoration: const InputDecoration(
            labelText: 'Jazyk textů (kód)',
            hintText: 'cs',
          ),
        ),
        const SizedBox(height: 16),
        Text('Publikum', style: ComicFonts.ui(800)),
        const SizedBox(height: 6),
        SegmentedButton<String>(
          key: const ValueKey('world-audience'),
          segments: [
            for (final a in const ['kids', 'teen', 'adult'])
              ButtonSegment(value: a, label: Text(audienceLabel(a))),
          ],
          selected: {_audience},
          onSelectionChanged: (s) => setState(() => _audience = s.first),
        ),
        const SizedBox(height: 16),
        Text('Viditelnost', style: ComicFonts.ui(800)),
        const SizedBox(height: 6),
        SegmentedButton<String>(
          key: const ValueKey('world-visibility'),
          segments: [
            for (final v in const ['private', 'unlisted', 'public'])
              ButtonSegment(value: v, label: Text(visibilityLabel(v))),
          ],
          selected: {_visibility},
          onSelectionChanged: (s) => setState(() => _visibility = s.first),
        ),
        const SectionTitle('Výtvarný styl'),
        const Hint('Styl je zamčený pro celý svět (artist tagy + sampler).'),
        presets.when(
          loading: () => const LinearProgressIndicator(),
          error: (e, _) => ErrorRetry(
            message: '$e',
            onRetry: () => ref.invalidate(stylePresetsProvider),
          ),
          data: (list) => StylePresetPicker(
            presets: list,
            selected: _styleId,
            onSelected: (id) => setState(() => _styleId = id),
          ),
        ),
        const SectionTitle('Co hráč smí'),
        SwitchListTile(
          key: const ValueKey('perm-add'),
          contentPadding: EdgeInsets.zero,
          title: const Text('Přidávat / odebírat postavy (režie)'),
          value: _canAdd,
          onChanged: (v) => setState(() => _canAdd = v),
        ),
        SwitchListTile(
          key: const ValueKey('perm-create'),
          contentPadding: EdgeInsets.zero,
          title: const Text('Vytvořit si vlastní postavu'),
          value: _canCreate,
          onChanged: (v) => setState(() => _canCreate = v),
        ),
        SwitchListTile(
          key: const ValueKey('perm-location'),
          contentPadding: EdgeInsets.zero,
          title: const Text('Měnit lokaci (režie)'),
          value: _canChangeLoc,
          onChanged: (v) => setState(() => _canChangeLoc = v),
        ),
        const SizedBox(height: 8),
        Text('Povolené lokace', style: ComicFonts.ui(800)),
        const Hint('Nic nevybráno = všechny lokace.'),
        Wrap(
          spacing: 6,
          runSpacing: 6,
          children: [
            for (final l in w.locations)
              FilterChip(
                key: ValueKey('allowed-${l.id}'),
                label: Text(l.name),
                selected: _allowed.contains(l.id),
                onSelected: (on) => setState(
                  () => on ? _allowed.add(l.id) : _allowed.remove(l.id),
                ),
              ),
          ],
        ),
        const SizedBox(height: 14),
        TextField(
          key: const ValueKey('perm-max-episodes'),
          controller: _maxEpisodes,
          keyboardType: TextInputType.number,
          decoration: const InputDecoration(
            labelText: 'Max. dílů na kampaň',
            hintText: 'prázdné = bez omezení',
          ),
        ),
      ],
    );
  }

  Widget _lore() => ListView(
    key: const ValueKey('tab-lore'),
    padding: const EdgeInsets.fromLTRB(16, 4, 16, 40),
    children: [
      const SectionTitle('Pravidla světa'),
      const Hint('LLM je drží a kontroluje každý díl.'),
      StringListEditor(
        keyPrefix: 'rule',
        controllers: _rules,
        hint: 'např. Kurýři nikdy neotevírají cizí dopisy.',
        addLabel: 'Přidat pravidlo',
        onAdd: () => setState(() => _rules.add(TextEditingController())),
        onRemove: (i) => setState(() => _rules.removeAt(i).dispose()),
      ),
      const SectionTitle('Frakce'),
      StringListEditor(
        keyPrefix: 'faction',
        controllers: _factions,
        hint: 'např. Poštovní cech',
        addLabel: 'Přidat frakci',
        onAdd: () => setState(() => _factions.add(TextEditingController())),
        onRemove: (i) => setState(() => _factions.removeAt(i).dispose()),
      ),
      const SectionTitle('Kánon'),
      const Hint(
        'Události, kterými musí každá kampaň projít, v tomto pořadí. '
        'Přetažením nebo šipkami změníš pořadí.',
      ),
      ReorderableListView(
        key: const ValueKey('canon-list'),
        shrinkWrap: true,
        physics: const NeverScrollableScrollPhysics(),
        buildDefaultDragHandles: false,
        onReorderItem: _moveNode,
        children: [
          for (var i = 0; i < _nodes.length; i++)
            Padding(
              key: ValueKey('canon-node-${_nodes[i].uid}'),
              padding: const EdgeInsets.only(bottom: 8),
              child: Row(
                children: [
                  ReorderableDragStartListener(
                    index: i,
                    child: const Padding(
                      padding: EdgeInsets.all(6),
                      child: Icon(Icons.drag_indicator),
                    ),
                  ),
                  CircleAvatar(
                    radius: 13,
                    backgroundColor: ComicColors.accent,
                    child: Text(
                      '${i + 1}',
                      style: ComicFonts.ui(
                        800,
                      ).copyWith(color: Colors.white, fontSize: 12),
                    ),
                  ),
                  const SizedBox(width: 8),
                  Expanded(
                    child: TextField(
                      key: ValueKey('canon-text-$i'),
                      controller: _nodes[i].text,
                      autofocus: _nodes[i].fresh,
                      minLines: 1,
                      maxLines: 3,
                      decoration: const InputDecoration(isDense: true),
                    ),
                  ),
                  IconButton(
                    key: ValueKey('canon-up-$i'),
                    tooltip: 'Výš',
                    onPressed: i == 0 ? null : () => _moveNode(i, i - 1),
                    icon: const Icon(Icons.arrow_upward),
                  ),
                  IconButton(
                    key: ValueKey('canon-down-$i'),
                    tooltip: 'Níž',
                    onPressed: i == _nodes.length - 1
                        ? null
                        : () => _moveNode(i, i + 1),
                    icon: const Icon(Icons.arrow_downward),
                  ),
                  IconButton(
                    key: ValueKey('canon-remove-$i'),
                    tooltip: 'Odebrat',
                    onPressed: () => setState(() => _nodes.removeAt(i)),
                    icon: const Icon(Icons.delete_outline),
                  ),
                ],
              ),
            ),
        ],
      ),
      TextButton.icon(
        key: const ValueKey('canon-add'),
        onPressed: () =>
            setState(() => _nodes.add(_NodeItem('', '', fresh: true))),
        icon: const Icon(Icons.add),
        label: const Text('Přidat kanonický uzel'),
      ),
      const SectionTitle('Mantinely'),
      const Hint('Volný text: co se ve světě nesmí stát.'),
      StringListEditor(
        keyPrefix: 'constraint',
        controllers: _constraints,
        hint: 'např. Vesna nikdy nezradí kurýry.',
        addLabel: 'Přidat mantinel',
        onAdd: () => setState(() => _constraints.add(TextEditingController())),
        onRemove: (i) => setState(() => _constraints.removeAt(i).dispose()),
      ),
    ],
  );
}

/// Curated style presets (GET /style_presets) as selectable cards.
class StylePresetPicker extends ConsumerWidget {
  final List<StylePreset> presets;
  final String selected;
  final ValueChanged<String> onSelected;
  const StylePresetPicker({
    super.key,
    required this.presets,
    required this.selected,
    required this.onSelected,
  });

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final api = ref.watch(apiProvider);
    return Column(
      children: [
        for (final p in presets)
          Padding(
            padding: const EdgeInsets.only(bottom: 10),
            child: ComicCard(
              key: ValueKey('preset-${p.id}'),
              padding: const EdgeInsets.all(12),
              color: p.id == selected
                  ? ComicColors.accent.withValues(alpha: 0.14)
                  : null,
              onTap: () => onSelected(p.id),
              child: Row(
                children: [
                  if (p.previewUrl != null) ...[
                    ClipRRect(
                      borderRadius: BorderRadius.circular(8),
                      child: Image(
                        image: api.panelImage(p.previewUrl!),
                        width: 56,
                        height: 76,
                        fit: BoxFit.cover,
                        errorBuilder: (_, _, _) =>
                            const SizedBox(width: 56, height: 76),
                      ),
                    ),
                    const SizedBox(width: 12),
                  ],
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(p.id, style: ComicFonts.title()),
                        if (p.summary.isNotEmpty)
                          Text(p.summary, style: const TextStyle(fontSize: 13)),
                        Text(
                          '${p.checkpoint} · ${p.sampler} · ${p.steps} kroků · CFG ${p.cfg}',
                          style: TextStyle(
                            fontSize: 11,
                            color: Theme.of(
                              context,
                            ).colorScheme.onSurfaceVariant,
                          ),
                        ),
                      ],
                    ),
                  ),
                  Icon(
                    p.id == selected
                        ? Icons.radio_button_checked
                        : Icons.radio_button_off,
                    color: ComicColors.accent,
                  ),
                ],
              ),
            ),
          ),
      ],
    );
  }
}

class _CharacterList extends StatelessWidget {
  final World world;
  const _CharacterList({required this.world});

  void _open(BuildContext context, [String? id]) => Navigator.of(context).push(
    MaterialPageRoute<void>(
      builder: (_) => CharacterEditorScreen(worldId: world.id, characterId: id),
    ),
  );

  @override
  Widget build(BuildContext context) => ListView(
    key: const ValueKey('tab-characters'),
    padding: const EdgeInsets.fromLTRB(16, 16, 16, 40),
    children: [
      for (final c in world.characters)
        Padding(
          padding: const EdgeInsets.only(bottom: 12),
          child: ComicCard(
            key: ValueKey('edit-character-${c.id}'),
            onTap: () => _open(context, c.id),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                CharacterInfo(character: c),
                const SizedBox(height: 8),
                Wrap(
                  spacing: 6,
                  runSpacing: 6,
                  children: [
                    Tag(roleLabel(c.role)),
                    Tag(identityLabel(c.identityLevel)),
                    Tag(c.tags.isEmpty ? 'bez tagů' : '${c.tags.length} tagů'),
                    if (c.referenceImages.isNotEmpty)
                      Tag('${c.referenceImages.length} ref.'),
                  ],
                ),
              ],
            ),
          ),
        ),
      if (world.characters.isEmpty) const Hint('Svět zatím nemá postavy.'),
      const SizedBox(height: 8),
      OutlinedButton.icon(
        key: const ValueKey('new-character'),
        onPressed: () => _open(context),
        icon: const Icon(Icons.person_add_alt),
        label: const Text('Nová postava'),
      ),
    ],
  );
}

class _LocationList extends StatelessWidget {
  final World world;
  const _LocationList({required this.world});

  void _open(BuildContext context, [String? id]) => Navigator.of(context).push(
    MaterialPageRoute<void>(
      builder: (_) => LocationEditorScreen(worldId: world.id, locationId: id),
    ),
  );

  @override
  Widget build(BuildContext context) => ListView(
    key: const ValueKey('tab-locations'),
    padding: const EdgeInsets.fromLTRB(16, 16, 16, 40),
    children: [
      for (final l in world.locations)
        Padding(
          padding: const EdgeInsets.only(bottom: 12),
          child: ComicCard(
            key: ValueKey('edit-location-${l.id}'),
            onTap: () => _open(context, l.id),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(l.name, style: ComicFonts.title().copyWith(fontSize: 20)),
                if (l.description.isNotEmpty)
                  Text(
                    l.description,
                    maxLines: 2,
                    overflow: TextOverflow.ellipsis,
                  ),
                const SizedBox(height: 6),
                Wrap(
                  spacing: 6,
                  children: [
                    if (l.mood.isNotEmpty) Tag(l.mood),
                    Tag(l.tags.isEmpty ? 'bez tagů' : '${l.tags.length} tagů'),
                  ],
                ),
              ],
            ),
          ),
        ),
      if (world.locations.isEmpty) const Hint('Svět zatím nemá lokace.'),
      const SizedBox(height: 8),
      OutlinedButton.icon(
        key: const ValueKey('new-location'),
        onPressed: () => _open(context),
        icon: const Icon(Icons.add_location_alt_outlined),
        label: const Text('Nová lokace'),
      ),
    ],
  );
}
