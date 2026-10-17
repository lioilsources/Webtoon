/// Push notification when an episode finishes generating (§6 "push notifikace po dokončení").
///
/// TODO(push): implement with FCM/APNs once the backend can send them (it would need a device
/// token endpoint and a hook in worker.maybeFinalize). Until then the reader polls
/// GET /episodes/{id} while the app is open.
abstract class PushNotifications {
  /// Ask for permission and register the device token with the backend.
  Future<void> init();

  /// Notify this device when [episodeId] becomes `ready` or `failed`.
  Future<void> watchEpisode(String episodeId);

  /// Stop notifications for [episodeId] (e.g. the reader saw it finish).
  Future<void> unwatchEpisode(String episodeId);
}

class NoopPushNotifications implements PushNotifications {
  const NoopPushNotifications();

  @override
  Future<void> init() async {}

  @override
  Future<void> watchEpisode(String episodeId) async {}

  @override
  Future<void> unwatchEpisode(String episodeId) async {}
}
