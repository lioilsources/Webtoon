import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../i18n/ui_strings.dart';
import '../profile/parental_gate.dart';
import '../profile/reader_profile.dart';
import '../theme.dart';
import '../widgets/common.dart';

/// First launch: Děti / Dospělí. Adults is behind the parental gate (the phone may be a child's).
class ProfileChooserScreen extends ConsumerWidget {
  const ProfileChooserScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final lang = ref.watch(uiLanguageProvider);
    final scheme = Theme.of(context).colorScheme;
    Widget option(
      ReaderProfile p,
      IconData icon,
      String title,
      String desc,
    ) => Padding(
      padding: const EdgeInsets.only(bottom: 14),
      child: ComicCard(
        key: ValueKey('profile-${p.name}'),
        onTap: () => chooseProfile(context, ref, p),
        child: Row(
          children: [
            Icon(icon, size: 40, color: ComicColors.accent),
            const SizedBox(width: 14),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(title, style: ComicFonts.title().copyWith(fontSize: 22)),
                  Text(desc, style: TextStyle(color: scheme.onSurfaceVariant)),
                ],
              ),
            ),
          ],
        ),
      ),
    );
    return Scaffold(
      key: const ValueKey('profile-chooser'),
      body: SafeArea(
        child: Center(
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 480),
            child: ListView(
              shrinkWrap: true,
              padding: const EdgeInsets.all(24),
              children: [
                Text(
                  tr(lang, 'profile.chooseTitle'),
                  textAlign: TextAlign.center,
                  style: ComicFonts.title().copyWith(fontSize: 30),
                ),
                const SizedBox(height: 6),
                Text(
                  tr(lang, 'profile.chooseSubtitle'),
                  textAlign: TextAlign.center,
                  style: TextStyle(color: scheme.onSurfaceVariant),
                ),
                const SizedBox(height: 24),
                option(
                  ReaderProfile.kids,
                  Icons.child_care_rounded,
                  tr(lang, 'profile.kids'),
                  tr(lang, 'profile.kidsDesc'),
                ),
                option(
                  ReaderProfile.adults,
                  Icons.person_rounded,
                  tr(lang, 'profile.adults'),
                  tr(lang, 'profile.adultsDesc'),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

/// Switches the profile; to Adults only past the parental gate. Returns whether it switched.
Future<bool> chooseProfile(
  BuildContext context,
  WidgetRef ref,
  ReaderProfile profile,
) async {
  final notifier = ref.read(readerProfileProvider.notifier);
  if (profile == ReaderProfile.adults &&
      !await showParentalGate(context, ref)) {
    return false;
  }
  await notifier.select(profile);
  return true;
}
