import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../models/world.dart';
import '../providers/providers.dart';
import '../widgets/common.dart';
import 'author_widgets.dart';
import 'sheet_panel.dart';

/// Create or edit a character: info, design tags (LLM suggestion → editable chips),
/// character sheet, reference images, identity level (+ IP-Adapter settings).
class CharacterEditorScreen extends ConsumerStatefulWidget {
  final String worldId;

  /// null = new character.
  final String? characterId;

  const CharacterEditorScreen({
    super.key,
    required this.worldId,
    this.characterId,
  });

  @override
  ConsumerState<CharacterEditorScreen> createState() =>
      _CharacterEditorScreenState();
}

class _CharacterEditorScreenState extends ConsumerState<CharacterEditorScreen> {
  final _name = TextEditingController();
  final _description = TextEditingController();
  final _personality = TextEditingController();
  final _speech = TextEditingController();
  String? _id;
  String _role = 'npc';
  String _countTag = '';
  List<String> _tags = [];
  List<String> _dropped = [];
  String _tagNotes = '';
  List<String> _refs = [];
  List<String> _refUrls = [];
  String _identity = 'prompt';
  IpAdapterConfig _ip = IpAdapterConfig.defaults;
  bool _loaded = false;
  bool _saving = false;
  bool _generating = false;

  @override
  void initState() {
    super.initState();
    _id = widget.characterId;
    if (_id == null) _loaded = true;
  }

  @override
  void dispose() {
    for (final c in [_name, _description, _personality, _speech]) {
      c.dispose();
    }
    super.dispose();
  }

  void _fill(Character c) {
    _name.text = c.name;
    _description.text = c.description;
    _personality.text = c.personality;
    _speech.text = c.speechStyle;
    _role = c.role;
    _countTag = c.countTag;
    _tags = c.tags;
    _refs = c.referenceImages;
    _refUrls = c.referenceUrls;
    _identity = c.identityLevel;
    _ip = c.ipAdapter ?? IpAdapterConfig.defaults;
    _loaded = true;
  }

  Map<String, dynamic> _fields() => {
    'name': _name.text.trim(),
    'role': _role,
    'count_tag': _countTag,
    'description': _description.text.trim(),
    'personality': _personality.text.trim(),
    'speech_style': _speech.text.trim(),
    'tag_prompt': _tags.join(', '),
    'identity_level': _identity,
    'ip_adapter': _identity == 'ip_adapter' ? _ip.toJson() : null,
  };

  Future<void> _save() async {
    if (_name.text.trim().isEmpty) {
      showSnack(context, 'Postava potřebuje jméno.');
      return;
    }
    setState(() => _saving = true);
    final api = ref.read(apiProvider);
    final fields = _fields();
    final saved = await guarded(context, () async {
      if (_id == null) {
        // ip_adapter is a PATCH-only field; send it after creation.
        final created = await api.createCharacter(
          widget.worldId,
          {...fields}..remove('ip_adapter'),
        );
        if (_identity == 'ip_adapter') {
          return api.updateCharacter(widget.worldId, created.id, {
            'ip_adapter': _ip.toJson(),
          });
        }
        return created;
      }
      return api.updateCharacter(widget.worldId, _id!, fields);
    });
    if (!mounted) return;
    setState(() => _saving = false);
    if (saved == null) return;
    invalidateWorld(ref, widget.worldId);
    setState(() {
      _id = saved.id;
      _fill(saved);
    });
    showSnack(context, 'Uloženo.');
  }

  Future<void> _generateTags() async {
    setState(() => _generating = true);
    final api = ref.read(apiProvider);
    final desc = _description.text.trim();
    final res = await guarded(
      context,
      () => api.suggestCharacterTags(
        widget.worldId,
        _id!,
        description: desc.isEmpty ? null : desc,
      ),
    );
    if (!mounted) return;
    setState(() {
      _generating = false;
      if (res != null) {
        _tags = res.tags;
        _dropped = res.dropped;
        _tagNotes = res.notes;
      }
    });
    if (res != null) {
      showSnack(context, 'Tagy vygenerovány — zkontroluj je a ulož.');
    }
  }

  Future<void> _setRefs(List<String> paths) async {
    final saved = await guarded(
      context,
      () => ref.read(apiProvider).updateCharacter(widget.worldId, _id!, {
        'reference_images': paths,
      }),
    );
    if (saved == null || !mounted) return;
    invalidateWorld(ref, widget.worldId);
    setState(() {
      _refs = saved.referenceImages;
      _refUrls = saved.referenceUrls;
    });
  }

  Future<void> _reloadRefs() async {
    invalidateWorld(ref, widget.worldId);
    final w = await guarded(
      context,
      () => ref.read(apiProvider).getWorld(widget.worldId),
    );
    final c = w?.character(_id);
    if (c == null || !mounted) return;
    setState(() {
      _refs = c.referenceImages;
      _refUrls = c.referenceUrls;
    });
  }

  Future<void> _delete() async {
    final ok = await confirmDialog(
      context,
      title: 'Smazat postavu?',
      body: 'Postava „${_name.text}“ zmizí ze světa.',
    );
    if (!ok || !mounted) return;
    final nav = Navigator.of(context);
    final done = await guarded(context, () async {
      await ref.read(apiProvider).deleteCharacter(widget.worldId, _id!);
      return true;
    });
    if (done == true) {
      invalidateWorld(ref, widget.worldId);
      nav.pop();
    }
  }

  @override
  Widget build(BuildContext context) {
    if (!_loaded) {
      final world = ref.watch(worldProvider(widget.worldId));
      return Scaffold(
        appBar: AppBar(title: const Text('Postava')),
        body: world.when(
          loading: () => const Center(child: CircularProgressIndicator()),
          error: (e, _) => ErrorRetry(
            message: '$e',
            onRetry: () => ref.invalidate(worldProvider(widget.worldId)),
          ),
          data: (w) {
            final c = w.character(_id);
            if (c == null) {
              return const EmptyState(
                icon: Icons.person_off_outlined,
                title: 'Postava nenalezena',
              );
            }
            WidgetsBinding.instance.addPostFrameCallback((_) {
              if (mounted && !_loaded) setState(() => _fill(c));
            });
            return const SizedBox.shrink();
          },
        ),
      );
    }
    final exists = _id != null;
    return Scaffold(
      appBar: AppBar(
        title: Text(exists ? _name.text : 'Nová postava'),
        actions: [
          if (exists)
            IconButton(
              key: const ValueKey('delete-character'),
              tooltip: 'Smazat postavu',
              onPressed: _delete,
              icon: const Icon(Icons.delete_outline),
            ),
          Padding(
            padding: const EdgeInsets.only(right: 8),
            child: FilledButton(
              key: const ValueKey('save-character'),
              onPressed: _saving ? null : _save,
              child: const Text('Uložit'),
            ),
          ),
        ],
      ),
      body: ListView(
        padding: const EdgeInsets.fromLTRB(16, 4, 16, 40),
        children: [
          const SectionTitle('Základ'),
          TextField(
            key: const ValueKey('char-name'),
            controller: _name,
            decoration: const InputDecoration(labelText: 'Jméno'),
          ),
          const SizedBox(height: 12),
          Wrap(
            spacing: 12,
            runSpacing: 8,
            crossAxisAlignment: WrapCrossAlignment.center,
            children: [
              SegmentedButton<String>(
                key: const ValueKey('char-role'),
                segments: [
                  const ButtonSegment(value: 'npc', label: Text('NPC')),
                  const ButtonSegment(
                    value: 'playable',
                    label: Text('Hratelná'),
                  ),
                  if (_role == 'player_created')
                    const ButtonSegment(
                      value: 'player_created',
                      label: Text('Od hráče'),
                    ),
                ],
                selected: {_role},
                onSelectionChanged: (s) => setState(() => _role = s.first),
              ),
              SegmentedButton<String>(
                key: const ValueKey('char-count'),
                segments: const [
                  ButtonSegment(value: '1girl', label: Text('Dívka')),
                  ButtonSegment(value: '1boy', label: Text('Chlapec')),
                  ButtonSegment(value: '', label: Text('Jiné')),
                ],
                selected: {_countTag},
                onSelectionChanged: (s) => setState(() => _countTag = s.first),
              ),
            ],
          ),
          const SizedBox(height: 12),
          TextField(
            key: const ValueKey('char-description'),
            controller: _description,
            minLines: 2,
            maxLines: 6,
            decoration: const InputDecoration(
              labelText: 'Popis vzhledu',
              hintText: 'vlasy, oči, oblečení kus po kuse, doplňky…',
            ),
          ),
          const SizedBox(height: 12),
          TextField(
            key: const ValueKey('char-personality'),
            controller: _personality,
            decoration: const InputDecoration(labelText: 'Povaha'),
          ),
          const SizedBox(height: 12),
          TextField(
            key: const ValueKey('char-speech'),
            controller: _speech,
            decoration: const InputDecoration(labelText: 'Styl řeči'),
          ),
          SectionTitle(
            'Design (booru tagy)',
            trailing: exists
                ? FilledButton.tonalIcon(
                    key: const ValueKey('generate-tags'),
                    onPressed: _generating ? null : _generateTags,
                    icon: _generating
                        ? const SizedBox.square(
                            dimension: 16,
                            child: CircularProgressIndicator(strokeWidth: 2),
                          )
                        : const Icon(Icons.auto_awesome),
                    label: const Text('Vygenerovat tagy'),
                  )
                : null,
          ),
          const Hint(
            'Pevný popis designu, vkládá se do každého panelu s postavou. '
            'LLM ho navrhne z popisu, ty ho dolaď.',
          ),
          if (_tagNotes.isNotEmpty) Hint('Poznámka LLM: $_tagNotes'),
          TagChipsEditor(
            key: const ValueKey('char-tags'),
            tags: _tags,
            dropped: _dropped,
            onChanged: (t) => setState(() => _tags = t),
          ),
          const SectionTitle('Identita'),
          SegmentedButton<String>(
            key: const ValueKey('identity-level'),
            segments: const [
              ButtonSegment(value: 'prompt', label: Text('Jen tagy')),
              ButtonSegment(value: 'ip_adapter', label: Text('IP-Adapter')),
              ButtonSegment(value: 'lora', label: Text('LoRA')),
            ],
            selected: {_identity},
            onSelectionChanged: (s) => setState(() => _identity = s.first),
          ),
          const SizedBox(height: 8),
          Hint(switch (_identity) {
            'ip_adapter' =>
              'Obličej drží i první referenční obrázek (IP-Adapter). '
                  'Výřez obličeje + váha 0,3–0,4 obrázek „nepřepálí“.',
            'lora' => 'LoRA per postava přijde v M4 (premium).',
            _ => 'Výchozí: postavu drží jen tagy (výsledek M0).',
          }),
          if (_identity == 'ip_adapter')
            _IpAdapterFields(
              config: _ip,
              onChanged: (c) => setState(() => _ip = c),
            ),
          if (exists) ...[
            const SectionTitle('Character sheet'),
            SheetPanel(
              worldId: widget.worldId,
              characterId: _id!,
              onReady: _reloadRefs,
            ),
            const SectionTitle('Referenční obrázky'),
            ReferenceImagesEditor(
              paths: _refs,
              urls: _refUrls,
              onChanged: _setRefs,
              onUpload: (img) async {
                final saved = await guarded(
                  context,
                  () => ref
                      .read(apiProvider)
                      .uploadCharacterReference(
                        widget.worldId,
                        _id!,
                        img.bytes,
                        img.name,
                      ),
                );
                if (saved == null || !mounted) return;
                invalidateWorld(ref, widget.worldId);
                setState(() {
                  _refs = saved.referenceImages;
                  _refUrls = saved.referenceUrls;
                });
              },
            ),
          ] else ...[
            const SizedBox(height: 20),
            const Hint(
              'Generování tagů, character sheet a reference půjdou po prvním uložení.',
            ),
          ],
        ],
      ),
    );
  }
}

class _IpAdapterFields extends StatelessWidget {
  final IpAdapterConfig config;
  final ValueChanged<IpAdapterConfig> onChanged;
  const _IpAdapterFields({required this.config, required this.onChanged});

  @override
  Widget build(BuildContext context) {
    final presets = {...IpAdapterConfig.presets, config.preset}.toList();
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        DropdownButtonFormField<String>(
          key: const ValueKey('ip-preset'),
          initialValue: config.preset,
          decoration: const InputDecoration(labelText: 'IP-Adapter preset'),
          items: [
            for (final p in presets) DropdownMenuItem(value: p, child: Text(p)),
          ],
          onChanged: (v) => onChanged(config.copyWith(preset: v)),
        ),
        const SizedBox(height: 8),
        Text('Váha: ${config.weight.toStringAsFixed(2)}'),
        Slider(
          key: const ValueKey('ip-weight'),
          value: config.weight.clamp(0, 1.5),
          max: 1.5,
          divisions: 30,
          label: config.weight.toStringAsFixed(2),
          onChanged: (v) => onChanged(config.copyWith(weight: v)),
        ),
        Text('Konec působení (end_at): ${config.endAt.toStringAsFixed(2)}'),
        Slider(
          key: const ValueKey('ip-end'),
          value: config.endAt.clamp(0, 1),
          divisions: 20,
          label: config.endAt.toStringAsFixed(2),
          onChanged: (v) => onChanged(config.copyWith(endAt: v)),
        ),
      ],
    );
  }
}
