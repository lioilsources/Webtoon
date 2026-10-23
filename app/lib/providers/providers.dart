import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../api/http_webtoon_api.dart';
import '../api/local_webtoon_api.dart';
import '../api/webtoon_api.dart';
import '../config.dart';
import '../models/author.dart';
import '../models/campaign.dart';
import '../models/world.dart';
import '../packs/pack_bootstrap.dart';
import '../packs/pack_store.dart';
import '../services/image_picker.dart';
import '../services/push_notifications.dart';

final configProvider = Provider<AppConfig>(
  (ref) => AppConfig.fromEnvironment(),
);

/// Installed content packs (reader mode). Tests override it with a store on a temp dir.
final packStoreProvider = Provider<PackStore>((ref) => PackStore());

/// Starter extraction + pack loading on start-up (reader mode); the home screen shows a
/// splash until it is ready. Tests override it with `PackBootstrap.ready(store)`.
final packBootstrapProvider =
    StateNotifierProvider<PackBootstrap, PackBootstrapState>(
      (ref) => PackBootstrap(ref.watch(packStoreProvider))..start(),
    );

/// Reader builds read packs offline; `--dart-define=WEBTOON_STUDIO=true` talks to the Go
/// backend (`WEBTOON_API`, `WEBTOON_USER`) as before. Overridden with a fake in tests —
/// the UI then follows [WebtoonApi.canEdit], not the build flag.
final apiProvider = Provider<WebtoonApi>(
  (ref) => kStudioBuild
      ? HttpWebtoonApi(ref.watch(configProvider))
      : LocalWebtoonApi(ref.watch(packStoreProvider)),
);

final pushNotificationsProvider = Provider<PushNotifications>(
  (ref) => const NoopPushNotifications(),
);

final worldsProvider = FutureProvider.autoDispose<List<WorldSummary>>(
  (ref) => ref.watch(apiProvider).listWorlds(),
);

final worldProvider = FutureProvider.autoDispose.family<World, String>(
  (ref, id) => ref.watch(apiProvider).getWorld(id),
);

final campaignsProvider = FutureProvider.autoDispose<List<CampaignSummary>>(
  (ref) => ref.watch(apiProvider).listCampaigns(),
);

final worldCampaignsProvider = FutureProvider.autoDispose
    .family<List<CampaignSummary>, String>(
      (ref, worldId) => ref.watch(apiProvider).listCampaigns(worldId: worldId),
    );

/// The caller's own worlds (tab "Tvořit").
final myWorldsProvider = FutureProvider.autoDispose<List<WorldSummary>>(
  (ref) => ref.watch(apiProvider).listMyWorlds(),
);

final stylePresetsProvider = FutureProvider.autoDispose<List<StylePreset>>(
  (ref) => ref.watch(apiProvider).listStylePresets(),
);

final worldStatsProvider = FutureProvider.autoDispose
    .family<WorldStats, String>(
      (ref, worldId) => ref.watch(apiProvider).getWorldStats(worldId),
    );

/// File dialog for reference images; tests override it.
final imagePickerProvider = Provider<ImagePickerFn>((ref) => pickImageFile);

/// Everything that shows a world must be refreshed after an author edit.
void invalidateWorld(WidgetRef ref, String worldId) {
  ref.invalidate(worldProvider(worldId));
  ref.invalidate(myWorldsProvider);
  ref.invalidate(worldsProvider);
}
