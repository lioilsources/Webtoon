// Entitlements: product → packs via the catalog, bundles over types (also future packs),
// gamebook / kit, persistence.

import 'package:flutter_test/flutter_test.dart';
import 'package:webtoon/shop/entitlements.dart';

import 'shop_fakes.dart';

Receipt r(String id) => Receipt(
  productId: id,
  receipt: 'rc-$id',
  grantedAt: DateTime.utc(2026, 10, 24),
);

void main() {
  test('nothing owned: only free and bundled packs are unlocked', () {
    final c = testCatalog(extraPacks: [pack('kids', 0, bundled: true)]);
    const e = Entitlements();
    expect(e.unlockedPacks(c), {'superhero-1', 'starter'});
    expect(e.unlocksPack(c, c.pack('kids-1')!), isFalse);
  });

  test('a pack product unlocks exactly that pack', () {
    final c = testCatalog();
    final e = const Entitlements().grant(r('pack_kids_1'));
    expect(e.unlockedPacks(c), {'kids-1', 'superhero-1'});
    expect(e.packsOfProduct(c, 'pack_kids_1').map((p) => p.id), ['kids-1']);
  });

  test(
    'bundle_<type> covers every pack of the type, also packs added after the purchase',
    () {
      final e = const Entitlements().grant(r('bundle_kids'));
      final before = testCatalog(version: 5);
      expect(e.unlockedPacks(before), {'kids-1', 'superhero-1'});
      // A later catalog adds kids-2 and harlequin-2: the old bundle covers kids-2 only.
      final after = testCatalog(
        version: 6,
        extraPacks: [
          pack('kids', 2),
          pack('harlequin', 2, audience: 'adult'),
        ],
      );
      expect(e.unlockedPacks(after), {'kids-1', 'kids-2', 'superhero-1'});
      expect(
        e.bundlesFor(after, after.pack('kids-2')!).single.id,
        'bundle_kids',
      );
      expect(e.packsOfProduct(after, 'bundle_kids').map((p) => p.id), [
        'kids-1',
        'kids-2',
      ]);
    },
  );

  test('bundle_all covers every type, present and future', () {
    final e = const Entitlements().grant(r('bundle_all'));
    final c = testCatalog(
      extraPacks: [pack('spooky', 1), pack('kids', 0, bundled: true)],
    );
    expect(e.unlockedPacks(c), {
      'kids-1',
      'superhero-1',
      'harlequin-1',
      'spooky-1',
      'starter',
    });
    expect(e.packsOfProduct(c, 'bundle_all').map((p) => p.id), [
      'kids-1',
      'superhero-1',
      'harlequin-1',
      'spooky-1',
    ]);
    expect(e.ownsBundle(c.bundle('bundle_all')!), isTrue);
    expect(e.ownsBundle(c.bundle('bundle_kids')!), isFalse);
  });

  test('gamebook and kit: the kit includes the gamebook', () {
    final g = testCatalog().gamebooks.single;
    expect(const Entitlements().unlocksGamebook(g), isFalse);
    final gb = const Entitlements().grant(r('gamebook_drak'));
    expect(gb.unlocksGamebook(g), isTrue);
    expect(gb.unlocksKit(g), isFalse);
    final kit = const Entitlements().grant(r('kit_drak'));
    expect(kit.unlocksGamebook(g), isTrue);
    expect(kit.unlocksKit(g), isTrue);
  });

  test('repository persists receipts', () async {
    final store = MemoryEntitlementStore();
    final repo = EntitlementRepository(store);
    await repo.load();
    await repo.grant(r('pack_kids_1'));
    await repo.grant(r('bundle_all'));
    final again = await EntitlementRepository(store).load();
    expect(again.productIds, {'pack_kids_1', 'bundle_all'});
    expect(again.receipts['bundle_all']!.receipt, 'rc-bundle_all');
    final json = Receipt.fromJson(again.receipts['pack_kids_1']!.toJson());
    expect(json.grantedAt, DateTime.utc(2026, 10, 24));
  });
}
