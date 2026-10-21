import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'author/create_screen.dart';
import 'providers/providers.dart';
import 'screens/campaigns_screen.dart';
import 'screens/reader_screen.dart';
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

/// Three tabs: worlds, the user's campaigns, and "Tvořit" (the user's own worlds — the
/// author side; one app for both roles).
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
  Widget build(BuildContext context) => Scaffold(
    body: IndexedStack(
      index: _tab,
      children: const [WorldsScreen(), CampaignsScreen(), CreateScreen()],
    ),
    bottomNavigationBar: NavigationBar(
      selectedIndex: _tab,
      onDestinationSelected: (i) => setState(() => _tab = i),
      destinations: const [
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
    ),
  );
}
