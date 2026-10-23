import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'author/create_screen.dart';
import 'providers/providers.dart';
import 'screens/campaigns_screen.dart';
import 'screens/library_screen.dart';
import 'screens/pack_splash.dart';
import 'screens/reader_screen.dart';
import 'screens/settings_screen.dart';
import 'screens/worlds_screen.dart';
import 'theme.dart';

class WebtoonApp extends StatelessWidget {
  const WebtoonApp({super.key});

  @override
  Widget build(BuildContext context) => MaterialApp(
    title: 'Toonfork',
    debugShowCheckedModeBanner: false,
    theme: buildTheme(Brightness.light),
    darkTheme: buildTheme(Brightness.dark),
    themeMode: ThemeMode.system,
    home: const HomeScreen(),
  );
}

/// Two shapes, decided by [WebtoonApi.canEdit]:
/// - **Reader** (offline packs): Knihovna / Nastavení, behind a splash while the starter
///   pack is extracted.
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
      return PackSplash(
        state: boot,
        onRetry: () => ref.read(packBootstrapProvider.notifier).start(),
      );
    }
    return _tabs(
      const [LibraryScreen(), SettingsScreen()],
      const [
        NavigationDestination(
          icon: Icon(Icons.auto_stories_outlined),
          selectedIcon: Icon(Icons.auto_stories),
          label: 'Knihovna',
        ),
        NavigationDestination(
          icon: Icon(Icons.settings_outlined),
          selectedIcon: Icon(Icons.settings),
          label: 'Nastavení',
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
