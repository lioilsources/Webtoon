import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../api/http_webtoon_api.dart';
import '../api/webtoon_api.dart';
import '../config.dart';
import '../models/author.dart';
import '../models/campaign.dart';
import '../models/world.dart';
import '../services/image_picker.dart';
import '../services/push_notifications.dart';

final configProvider = Provider<AppConfig>(
  (ref) => AppConfig.fromEnvironment(),
);

/// Overridden with a fake in tests.
final apiProvider = Provider<WebtoonApi>(
  (ref) => HttpWebtoonApi(ref.watch(configProvider)),
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
