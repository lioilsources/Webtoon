import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:ol1n_telemetry/ol1n_telemetry.dart';

import '../i18n/ui_strings.dart';
import '../theme.dart';
import 'app_icons.g.dart';

/// The home-screen icon (Nastavení → Ikona aplikace). Native side: iOS alternate icons, Android
/// activity-aliases (tools/app_icons.py); the first key of [kAppIcons] is the main icon.
class AppIconService {
  static const _channel = MethodChannel('toonfork/app_icon');
  const AppIconService();

  Future<String?> current() async {
    try {
      return await _channel.invokeMethod<String>('get', {'keys': kAppIcons});
    } on MissingPluginException {
      return null; // desktop, tests
    } on PlatformException {
      return null;
    }
  }

  Future<bool> set(String key) async {
    try {
      return await _channel.invokeMethod<bool>('set', {
            'key': key,
            'keys': kAppIcons,
          }) ??
          false;
    } on MissingPluginException {
      return false;
    } on PlatformException {
      return false;
    }
  }
}

final appIconServiceProvider = Provider<AppIconService>(
  (_) => const AppIconService(),
);

class AppIconPicker extends ConsumerStatefulWidget {
  const AppIconPicker({super.key});

  @override
  ConsumerState<AppIconPicker> createState() => _AppIconPickerState();
}

class _AppIconPickerState extends ConsumerState<AppIconPicker> {
  String? _current;

  @override
  void initState() {
    super.initState();
    ref.read(appIconServiceProvider).current().then((k) {
      if (mounted) setState(() => _current = k ?? kAppIcons.first);
    });
  }

  Future<void> _pick(String key) async {
    Telemetry.feature('app_icon');
    final ok = await ref.read(appIconServiceProvider).set(key);
    if (ok && mounted) setState(() => _current = key);
  }

  @override
  Widget build(BuildContext context) {
    final ui = ref.watch(uiLanguageProvider);
    final scheme = Theme.of(context).colorScheme;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          tr(ui, 'settings.appIcon'),
          style: Theme.of(context).textTheme.titleLarge,
        ),
        const SizedBox(height: 4),
        Text(
          tr(ui, 'settings.appIconHint'),
          style: TextStyle(color: scheme.onSurfaceVariant, fontSize: 13),
        ),
        const SizedBox(height: 12),
        Wrap(
          spacing: 12,
          runSpacing: 12,
          children: [
            for (final k in kAppIcons)
              Semantics(
                button: true,
                selected: _current == k,
                child: InkWell(
                  key: ValueKey('app-icon-$k'),
                  borderRadius: BorderRadius.circular(18),
                  onTap: () => _pick(k),
                  child: AnimatedContainer(
                    duration: const Duration(milliseconds: 150),
                    padding: const EdgeInsets.all(3),
                    decoration: BoxDecoration(
                      borderRadius: BorderRadius.circular(18),
                      border: Border.all(
                        width: 3,
                        color: _current == k
                            ? ComicColors.accent
                            : Colors.transparent,
                      ),
                    ),
                    child: ClipRRect(
                      borderRadius: BorderRadius.circular(14),
                      child: Image.asset(
                        'assets/icon/thumbs/$k.png',
                        width: 64,
                        height: 64,
                      ),
                    ),
                  ),
                ),
              ),
          ],
        ),
      ],
    );
  }
}
