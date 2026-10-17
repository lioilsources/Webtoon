import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../models/world.dart';
import '../providers/providers.dart';
import '../widgets/common.dart';
import 'author_widgets.dart';

/// Create or edit a location: name, description, mood, scenery tags (LLM suggestion →
/// chips) and reference images.
class LocationEditorScreen extends ConsumerStatefulWidget {
  final String worldId;
  final String? locationId; // null = new

  const LocationEditorScreen({
    super.key,
    required this.worldId,
    this.locationId,
  });

  @override
  ConsumerState<LocationEditorScreen> createState() =>
      _LocationEditorScreenState();
}

class _LocationEditorScreenState extends ConsumerState<LocationEditorScreen> {
  final _name = TextEditingController();
  final _description = TextEditingController();
  final _mood = TextEditingController();
  String? _id;
  List<String> _tags = [];
  List<String> _dropped = [];
  List<String> _refs = [];
  List<String> _refUrls = [];
  bool _loaded = false;
  bool _saving = false;
  bool _generating = false;

  @override
  void initState() {
    super.initState();
    _id = widget.locationId;
    if (_id == null) _loaded = true;
  }

  @override
  void dispose() {
    _name.dispose();
    _description.dispose();
    _mood.dispose();
    super.dispose();
  }

  void _fill(Location l) {
    _name.text = l.name;
    _description.text = l.description;
    _mood.text = l.mood;
    _tags = l.tags;
    _refs = l.referenceImages;
    _refUrls = l.referenceUrls;
    _loaded = true;
  }

  Future<void> _save() async {
    if (_name.text.trim().isEmpty) {
      showSnack(context, 'Lokace potřebuje název.');
      return;
    }
    setState(() => _saving = true);
    final api = ref.read(apiProvider);
    final fields = {
      'name': _name.text.trim(),
      'description': _description.text.trim(),
      'mood': _mood.text.trim(),
      'tag_prompt': _tags.join(', '),
    };
    final saved = await guarded(
      context,
      () => _id == null
          ? api.createLocation(widget.worldId, fields)
          : api.updateLocation(widget.worldId, _id!, fields),
    );
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
    final desc = _description.text.trim();
    final res = await guarded(
      context,
      () => ref
          .read(apiProvider)
          .suggestLocationTags(
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
      }
    });
  }

  void _setFrom(Location? l) {
    if (l == null || !mounted) return;
    invalidateWorld(ref, widget.worldId);
    setState(() {
      _refs = l.referenceImages;
      _refUrls = l.referenceUrls;
    });
  }

  Future<void> _delete() async {
    final ok = await confirmDialog(
      context,
      title: 'Smazat lokaci?',
      body: 'Lokace „${_name.text}“ zmizí ze světa.',
    );
    if (!ok || !mounted) return;
    final nav = Navigator.of(context);
    final done = await guarded(context, () async {
      await ref.read(apiProvider).deleteLocation(widget.worldId, _id!);
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
        appBar: AppBar(title: const Text('Lokace')),
        body: world.when(
          loading: () => const Center(child: CircularProgressIndicator()),
          error: (e, _) => ErrorRetry(
            message: '$e',
            onRetry: () => ref.invalidate(worldProvider(widget.worldId)),
          ),
          data: (w) {
            final l = w.location(_id);
            if (l == null) {
              return const EmptyState(
                icon: Icons.wrong_location_outlined,
                title: 'Lokace nenalezena',
              );
            }
            WidgetsBinding.instance.addPostFrameCallback((_) {
              if (mounted && !_loaded) setState(() => _fill(l));
            });
            return const SizedBox.shrink();
          },
        ),
      );
    }
    final exists = _id != null;
    return Scaffold(
      appBar: AppBar(
        title: Text(exists ? _name.text : 'Nová lokace'),
        actions: [
          if (exists)
            IconButton(
              key: const ValueKey('delete-location'),
              tooltip: 'Smazat lokaci',
              onPressed: _delete,
              icon: const Icon(Icons.delete_outline),
            ),
          Padding(
            padding: const EdgeInsets.only(right: 8),
            child: FilledButton(
              key: const ValueKey('save-location'),
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
            key: const ValueKey('loc-name'),
            controller: _name,
            decoration: const InputDecoration(labelText: 'Název'),
          ),
          const SizedBox(height: 12),
          TextField(
            key: const ValueKey('loc-description'),
            controller: _description,
            minLines: 2,
            maxLines: 6,
            decoration: const InputDecoration(labelText: 'Popis'),
          ),
          const SizedBox(height: 12),
          TextField(
            key: const ValueKey('loc-mood'),
            controller: _mood,
            decoration: const InputDecoration(labelText: 'Nálada'),
          ),
          SectionTitle(
            'Scéna (booru tagy)',
            trailing: exists
                ? FilledButton.tonalIcon(
                    key: const ValueKey('generate-loc-tags'),
                    onPressed: _generating ? null : _generateTags,
                    icon: const Icon(Icons.auto_awesome),
                    label: const Text('Vygenerovat tagy'),
                  )
                : null,
          ),
          const Hint('Vkládá se do každého panelu v této lokaci.'),
          TagChipsEditor(
            key: const ValueKey('loc-tags'),
            tags: _tags,
            dropped: _dropped,
            onChanged: (t) => setState(() => _tags = t),
          ),
          if (exists) ...[
            const SectionTitle('Referenční obrázky'),
            ReferenceImagesEditor(
              paths: _refs,
              urls: _refUrls,
              onChanged: (paths) async => _setFrom(
                await guarded(
                  context,
                  () => ref.read(apiProvider).updateLocation(
                    widget.worldId,
                    _id!,
                    {'reference_images': paths},
                  ),
                ),
              ),
              onUpload: (img) async => _setFrom(
                await guarded(
                  context,
                  () => ref
                      .read(apiProvider)
                      .uploadLocationReference(
                        widget.worldId,
                        _id!,
                        img.bytes,
                        img.name,
                      ),
                ),
              ),
            ),
          ],
        ],
      ),
    );
  }
}
