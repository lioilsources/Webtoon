// Reader profile: one 12+ app, the reader picks Děti / Dospělí on first launch. The Kids profile
// hides everything with audience "adult" (harlequin stories, packs and bundles) in Knihovna and
// Obchod; switching to Adults is behind the parental gate (lib/profile/parental_gate.dart).

import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:shared_preferences/shared_preferences.dart';

enum ReaderProfile { kids, adults }

/// Whether content of [audience] is shown to [profile]. Kids see kids and teen content, adults
/// see everything.
bool audienceVisible(ReaderProfile? profile, String audience) =>
    profile != ReaderProfile.kids || audience != 'adult';

/// Pack types whose audience is adult (rules/base/pack.yaml types); the library uses it for
/// stories whose world says nothing more specific.
const kAdultTypes = {'harlequin'};

/// A story of the library for [profile]: hidden for Kids when its world is adult or its pack
/// type is an adult one.
bool storyVisible(
  ReaderProfile? profile, {
  String? worldAudience,
  String? type,
}) =>
    profile != ReaderProfile.kids ||
    (worldAudience != 'adult' && !kAdultTypes.contains(type));

/// Where the choice is kept; tests use [MemoryProfileStore].
abstract class ProfileStore {
  /// The saved profile, null when the reader never chose (first launch).
  Future<ReaderProfile?> load();
  Future<void> save(ReaderProfile profile);
}

class PrefsProfileStore implements ProfileStore {
  static const _key = 'reader_profile';

  @override
  Future<ReaderProfile?> load() async {
    try {
      final v = (await SharedPreferences.getInstance()).getString(_key);
      return ReaderProfile.values.where((p) => p.name == v).firstOrNull;
    } catch (_) {
      return null;
    }
  }

  @override
  Future<void> save(ReaderProfile profile) async {
    try {
      await (await SharedPreferences.getInstance()).setString(
        _key,
        profile.name,
      );
    } catch (_) {}
  }
}

class MemoryProfileStore implements ProfileStore {
  ReaderProfile? saved;
  MemoryProfileStore([this.saved]);

  @override
  Future<ReaderProfile?> load() async => saved;

  @override
  Future<void> save(ReaderProfile profile) async => saved = profile;
}

final profileStoreProvider = Provider<ProfileStore>(
  (ref) => PrefsProfileStore(),
);

/// `loaded` false until the store answered; `profile` null = never chosen (show the chooser).
class ProfileState {
  final bool loaded;
  final ReaderProfile? profile;
  const ProfileState({this.loaded = false, this.profile});

  bool get isKids => profile == ReaderProfile.kids;
}

class ReaderProfileNotifier extends StateNotifier<ProfileState> {
  final ProfileStore _store;

  ReaderProfileNotifier(this._store) : super(const ProfileState()) {
    _store.load().then((p) {
      if (mounted && !state.loaded) {
        state = ProfileState(loaded: true, profile: p);
      }
    });
  }

  /// The caller has already passed the parental gate when switching to adults.
  Future<void> select(ReaderProfile profile) async {
    state = ProfileState(loaded: true, profile: profile);
    await _store.save(profile);
  }
}

final readerProfileProvider =
    StateNotifierProvider<ReaderProfileNotifier, ProfileState>(
      (ref) => ReaderProfileNotifier(ref.watch(profileStoreProvider)),
    );
