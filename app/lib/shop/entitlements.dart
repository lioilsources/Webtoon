// What the reader owns: store product ids with their receipts, persisted locally. Which packs
// that unlocks is resolved against the catalog every time — a bundle covers every pack of its
// types, including packs added to the catalog after the purchase.
//
// TODO(phase 2): server-side receipt validation (store.ol1n.com: verify the receipt, hand out a
// signed download URL). Today a receipt is only stored, never verified.

import 'dart:convert';

import 'package:shared_preferences/shared_preferences.dart';

import '../models/json.dart';
import 'catalog.dart';

/// One owned product.
class Receipt {
  final String productId;
  final String? purchaseId;
  final String? receipt;
  final String? source;
  final String? transactionDate;
  final DateTime grantedAt;

  const Receipt({
    required this.productId,
    this.purchaseId,
    this.receipt,
    this.source,
    this.transactionDate,
    required this.grantedAt,
  });

  Map<String, dynamic> toJson() => {
    'product_id': productId,
    'purchase_id': ?purchaseId,
    'receipt': ?receipt,
    'source': ?source,
    'transaction_date': ?transactionDate,
    'granted_at': grantedAt.toUtc().toIso8601String(),
  };

  factory Receipt.fromJson(Map<String, dynamic> j) => Receipt(
    productId: str(j['product_id']),
    purchaseId: strOrNull(j['purchase_id']),
    receipt: strOrNull(j['receipt']),
    source: strOrNull(j['source']),
    transactionDate: strOrNull(j['transaction_date']),
    grantedAt: date(j['granted_at']) ?? DateTime.fromMillisecondsSinceEpoch(0),
  );
}

/// Persistence of the receipts and the grandfathered gamebooks; tests use
/// [MemoryEntitlementStore].
abstract class EntitlementStore {
  Future<List<Receipt>> load();
  Future<void> save(List<Receipt> receipts);

  /// Gamebook ids installed while the catalog had them `free` (see [Entitlements.grandfathered]).
  Future<Set<String>> loadGrandfathered();
  Future<void> saveGrandfathered(Set<String> ids);
}

class PrefsEntitlementStore implements EntitlementStore {
  static const _key = 'entitlements_v1';
  static const _grandfatheredKey = 'grandfathered_gamebooks_v1';

  @override
  Future<List<Receipt>> load() async {
    try {
      final raw = (await SharedPreferences.getInstance()).getString(_key);
      if (raw == null) return [];
      return objList(jsonDecode(raw)).map(Receipt.fromJson).toList();
    } catch (_) {
      return [];
    }
  }

  @override
  Future<void> save(List<Receipt> receipts) async {
    try {
      await (await SharedPreferences.getInstance()).setString(
        _key,
        jsonEncode([for (final r in receipts) r.toJson()]),
      );
    } catch (_) {}
  }

  @override
  Future<Set<String>> loadGrandfathered() async {
    try {
      final ids = (await SharedPreferences.getInstance()).getStringList(
        _grandfatheredKey,
      );
      return {...?ids};
    } catch (_) {
      return {};
    }
  }

  @override
  Future<void> saveGrandfathered(Set<String> ids) async {
    try {
      await (await SharedPreferences.getInstance()).setStringList(
        _grandfatheredKey,
        ids.toList()..sort(),
      );
    } catch (_) {}
  }
}

class MemoryEntitlementStore implements EntitlementStore {
  List<Receipt> saved;
  Set<String> grandfathered;
  MemoryEntitlementStore([List<Receipt>? saved, Set<String>? grandfathered])
    : saved = saved ?? [],
      grandfathered = grandfathered ?? {};

  @override
  Future<List<Receipt>> load() async => List.of(saved);

  @override
  Future<void> save(List<Receipt> receipts) async => saved = List.of(receipts);

  @override
  Future<Set<String>> loadGrandfathered() async => {...grandfathered};

  @override
  Future<void> saveGrandfathered(Set<String> ids) async =>
      grandfathered = {...ids};
}

/// Owned product ids → unlocked packs / gamebooks / kits. Immutable; [grant] returns a copy.
class Entitlements {
  final Map<String, Receipt> receipts;

  /// Gamebook ids the reader installed while the catalog had them `free`: they stay unlocked
  /// (book and kit) after a later catalog makes them paid.
  final Set<String> grandfathered;

  const Entitlements([this.receipts = const {}, this.grandfathered = const {}]);

  Set<String> get productIds => receipts.keys.toSet();

  bool ownsProduct(String id) => receipts.containsKey(id);

  Entitlements grant(Receipt r) =>
      Entitlements({...receipts, r.productId: r}, grandfathered);

  Entitlements withGrandfathered(Iterable<String> ids) =>
      Entitlements(receipts, {...grandfathered, ...ids});

  bool _grandfatheredPack(CatalogPack pack) =>
      pack.gamebook &&
      pack.id.startsWith(CatalogGamebook.packPrefix) &&
      grandfathered.contains(
        pack.id.substring(CatalogGamebook.packPrefix.length),
      );

  /// Free packs need no purchase; paid ones need their product or a bundle over their type.
  bool unlocksPack(Catalog catalog, CatalogPack pack) {
    if (pack.free || pack.bundled) return true;
    if (pack.productId != null && ownsProduct(pack.productId!)) return true;
    if (pack.gamebook) {
      return _grandfatheredPack(pack) ||
          (pack.kitProductId != null && ownsProduct(pack.kitProductId!));
    }
    return bundlesFor(catalog, pack).isNotEmpty;
  }

  /// Owned bundles that cover [pack] (also packs that were not in the catalog at purchase).
  List<CatalogBundle> bundlesFor(Catalog catalog, CatalogPack pack) => [
    for (final b in catalog.bundles)
      if (ownsProduct(b.productId) && b.covers.coversType(pack.type)) b,
  ];

  /// Every unlocked pack id of the catalog.
  Set<String> unlockedPacks(Catalog catalog) => {
    for (final p in catalog.packs)
      if (unlocksPack(catalog, p)) p.id,
  };

  /// A bundle is "owned" when bought; the store shows it as purchased.
  bool ownsBundle(CatalogBundle b) => ownsProduct(b.productId);

  /// `gamebook_<id>` or `kit_<id>` (the kit includes the gamebook).
  bool unlocksGamebook(CatalogGamebook g) =>
      g.free ||
      grandfathered.contains(g.id) ||
      ownsProduct(g.productId) ||
      (g.kitProductId != null && ownsProduct(g.kitProductId!));

  bool unlocksKit(CatalogGamebook g) =>
      g.free ||
      grandfathered.contains(g.id) ||
      (g.kitProductId != null && ownsProduct(g.kitProductId!));

  /// Packs a product unlocks in [catalog] (for "download after purchase"); a gamebook product
  /// shared by several gamebooks returns all of them.
  List<CatalogPack> packsOfProduct(Catalog catalog, String productId) {
    final bundle = catalog.bundles.where((b) => b.productId == productId);
    if (bundle.isNotEmpty) {
      return [
        for (final p in catalog.packs)
          if (!p.bundled && bundle.first.covers.coversType(p.type)) p,
      ];
    }
    return [
      for (final p in catalog.packs)
        if (p.productId == productId) p,
      for (final g in catalog.gamebooks)
        if (g.ready &&
            (g.productId == productId || g.kitProductId == productId))
          g.asPack(),
    ];
  }
}

/// Loads, grants and saves; the shop controller owns one.
class EntitlementRepository {
  final EntitlementStore store;
  Entitlements _current = const Entitlements();

  EntitlementRepository(this.store);

  Entitlements get current => _current;

  Future<Entitlements> load() async {
    _current = Entitlements({
      for (final r in await store.load()) r.productId: r,
    }, await store.loadGrandfathered());
    return _current;
  }

  /// Adds gamebook ids to the grandfathered set; saves only when something is new.
  Future<Entitlements> grandfather(Iterable<String> ids) async {
    final fresh = [
      for (final id in ids)
        if (!_current.grandfathered.contains(id)) id,
    ];
    if (fresh.isEmpty) return _current;
    _current = _current.withGrandfathered(fresh);
    await store.saveGrandfathered(_current.grandfathered);
    return _current;
  }

  Future<Entitlements> grant(Receipt r) async {
    _current = _current.grant(r);
    await store.save(_current.receipts.values.toList());
    return _current;
  }
}
