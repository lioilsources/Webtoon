import 'package:flutter_test/flutter_test.dart';
import 'package:webtoon/models/campaign.dart';
import 'package:webtoon/models/world.dart';
import 'package:webtoon/packs/pack_store.dart';

void main() {
  test('campaign title follows the reading language', () {
    const c = Campaign(
      id: 'c',
      worldId: 'w',
      title: 'Halloweenská noc',
      titleI18n: {'en': 'Halloween Night'},
    );
    expect(c.titleIn('en'), 'Halloween Night');
    expect(c.titleIn('ja'), 'Halloweenská noc');
    expect(c.titleIn(null), 'Halloweenská noc');
  });

  test(
    'a world synopsis is never shown in a language the reader did not pick',
    () {
      const w = WorldSummary(
        id: 'w',
        title: 'Les',
        synopsis: 'Česky',
        language: 'cs',
        synopsisI18n: {'de': 'Deutsch'},
      );
      expect(w.synopsisIn(null), 'Česky');
      expect(w.synopsisIn('cs'), 'Česky');
      expect(w.synopsisIn('de'), 'Deutsch');
      expect(w.synopsisIn('en'), isNull);
    },
  );

  test('sizes use the decimal mark of the UI language', () {
    const bytes = 44354765; // 42.3 MB
    expect(formatBytes(bytes, 'en'), '42.3 MB');
    expect(formatBytes(bytes, 'ja'), '42.3 MB');
    expect(formatBytes(bytes, 'cs'), '42,3 MB');
    expect(formatBytes(bytes, 'de'), '42,3 MB');
    expect(formatBytes(bytes), '42,3 MB');
  });
}
