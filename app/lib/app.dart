import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'author/create_screen.dart';
import 'packs/pack_bootstrap.dart';
import 'i18n/ui_strings.dart';
import 'profile/reader_profile.dart';
import 'providers/providers.dart';
import 'screens/campaigns_screen.dart';
import 'screens/library_screen.dart';
import 'screens/pack_splash.dart';
import 'screens/profile_chooser_screen.dart';
import 'screens/reader_screen.dart';
import 'screens/settings_screen.dart';
import 'screens/store_screen.dart';
import 'screens/worlds_screen.dart';
import 'telemetry/telemetry_setup.dart';
import 'theme.dart';

class WebtoonApp extends StatefulWidget {
  const WebtoonApp({super.key});

  @override
  State<WebtoonApp> createState() => _WebtoonAppState();
}

class _WebtoonAppState extends State<WebtoonApp> {
  // Anonymous statistics: screens by route name (no-op unless measuring, docs/telemetry.md).
  final _screens = ToonforkScreenObserver();

  @override
  Widget build(BuildContext context) => MaterialApp(
    title: 'Toonfork',
    debugShowCheckedModeBanner: false,
    theme: buildTheme(Brightness.light),
    darkTheme: buildTheme(Brightness.dark),
    themeMode: ThemeMode.system,
    navigatorObservers: [_screens],
    home: const HomeScreen(),
  );
}

/// Two shapes, decided by [WebtoonApi.canEdit]:
/// - **Reader** (offline packs): Knihovna / Obchod / Nastavení, behind a splash while the
///   starter pack is extracted, and the Děti / Dospělí chooser on first launch.
/// - **Studio** (Go backend): Světy / Kampaně / Tvořit — the reader plus the author side.
class HomeScreen extends ConsumerStatefulWidget {
  const HomeScreen({super.key});

  @override
  ConsumerState<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends ConsumerState<HomeScreen> {
  int _tab = 0;

  @override
  void initState() {
    super.initState();
    final open = ref.read(configProvider).openCampaign;
    if (open != null) {
      WidgetsBinding.instance.addPostFrameCallback((_) {
        if (!mounted) return;
        Navigator.of(context).push(
          MaterialPageRoute<void>(
            builder: (_) => ReaderScreen(campaignId: open),
          ),
        );
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    if (ref.watch(apiProvider).canEdit) return _studio();
    final boot = ref.watch(packBootstrapProvider);
    if (!boot.isReady) {
      reportHomeScreen(context, 'splash');
      return PackSplash(
        state: boot,
        onRetry: () => ref.read(packBootstrapProvider.notifier).start(),
      );
    }
    final profile = ref.watch(readerProfileProvider);
    if (!profile.loaded) {
      reportHomeScreen(context, 'splash');
      return PackSplash(state: const PackBootstrapState(), onRetry: () {});
    }
    if (profile.profile == null) {
      reportHomeScreen(context, 'profile_chooser');
      return const ProfileChooserScreen();
    }
    reportHomeScreen(
      context,
      const ['library', 'store', 'settings'][_tab.clamp(0, 2)],
    );
    final lang = ref.watch(uiLanguageProvider);
    return _tabs(
      const [LibraryScreen(), StoreScreen(), SettingsScreen()],
      [
        NavigationDestination(
          icon: const Icon(Icons.auto_stories_outlined),
          selectedIcon: const Icon(Icons.auto_stories),
          label: tr(lang, 'tab.library'),
        ),
        NavigationDestination(
          key: const ValueKey('tab-store'),
          icon: const Icon(Icons.storefront_outlined),
          selectedIcon: const Icon(Icons.storefront),
          label: tr(lang, 'tab.store'),
        ),
        NavigationDestination(
          icon: const Icon(Icons.settings_outlined),
          selectedIcon: const Icon(Icons.settings),
          label: tr(lang, 'tab.settings'),
        ),
      ],
    );
  }

  Widget _studio() => _tabs(
    const [WorldsScreen(), CampaignsScreen(), CreateScreen()],
    const [
      NavigationDestination(
        icon: Icon(Icons.public_outlined),
        selectedIcon: Icon(Icons.public),
        label: 'Světy',
      ),
      NavigationDestination(
        icon: Icon(Icons.auto_stories_outlined),
        selectedIcon: Icon(Icons.auto_stories),
        label: 'Kampaně',
      ),
      NavigationDestination(
        icon: Icon(Icons.brush_outlined),
        selectedIcon: Icon(Icons.brush),
        label: 'Tvořit',
      ),
    ],
  );

  Widget _tabs(List<Widget> screens, List<NavigationDestination> dests) {
    final tab = _tab.clamp(0, screens.length - 1);
    return Scaffold(
      body: IndexedStack(index: tab, children: screens),
      bottomNavigationBar: NavigationBar(
        selectedIndex: tab,
        onDestinationSelected: (i) => setState(() => _tab = i),
        destinations: dests,
      ),
    );
  }
}
