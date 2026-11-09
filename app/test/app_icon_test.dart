import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:webtoon/settings/app_icon.dart';
import 'package:webtoon/settings/app_icons.g.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  const channel = MethodChannel('toonfork/app_icon');

  testWidgets(
    'Ikona aplikace: shows every icon, marks the current one, sets a tapped one',
    (tester) async {
      final calls = <MethodCall>[];
      var current = kAppIcons.first;
      tester.binding.defaultBinaryMessenger.setMockMethodCallHandler(channel, (
        c,
      ) async {
        calls.add(c);
        if (c.method == 'get') return current;
        current = (c.arguments as Map)['key'] as String;
        return true;
      });
      addTearDown(
        () => tester.binding.defaultBinaryMessenger.setMockMethodCallHandler(
          channel,
          null,
        ),
      );
      await tester.pumpWidget(
        const ProviderScope(
          child: MaterialApp(
            home: Scaffold(body: SingleChildScrollView(child: AppIconPicker())),
          ),
        ),
      );
      await tester.pumpAndSettle();
      for (final k in kAppIcons) {
        expect(find.byKey(ValueKey('app-icon-$k')), findsOneWidget);
      }
      final key = kAppIcons[2];
      await tester.tap(find.byKey(ValueKey('app-icon-$key')));
      await tester.pumpAndSettle();
      final set = calls.lastWhere((c) => c.method == 'set');
      expect((set.arguments as Map)['key'], key);
      expect((set.arguments as Map)['keys'], kAppIcons);
      expect(current, key);
      expect(
        find.ancestor(
          of: find.byKey(ValueKey('app-icon-$key')),
          matching: find.byWidgetPredicate(
            (w) => w is Semantics && w.properties.selected == true,
          ),
        ),
        findsOneWidget,
      );
    },
  );
}
