import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'app.dart';
import 'config.dart';
import 'profile/reader_profile.dart';
import 'telemetry/telemetry_setup.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  final container = ProviderContainer();
  // The reader only: a Studio build measures nothing. Kids (or no profile yet) starts
  // suspended, so not even the launch is recorded for a child.
  if (!kStudioBuild) {
    final profile = await PrefsProfileStore().load();
    await startTelemetry(container, adults: profile == ReaderProfile.adults);
  }
  runApp(
    UncontrolledProviderScope(container: container, child: const WebtoonApp()),
  );
}
