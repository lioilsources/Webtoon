// The store's state machine: catalog (cache → refresh), product prices from the store,
// entitlements, purchases (gate → buy → receipt → finish → download) and pack downloads.

import 'dart:async';

import 'package:flutter/foundation.dart' show debugPrint;
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../providers/providers.dart';
import 'catalog.dart';
import 'catalog_repository.dart';
import 'entitlements.dart';
import 'pack_downloader.dart';
import 'store_gateway.dart';

/// A one-off message for a snackbar; [id] changes for every new one.
class ShopNotice {
  final int id;
  final String key; // ui_strings key
  final Map<String, Object> args;
  const ShopNotice(this.id, this.key, [this.args = const {}]);
}

class ShopState {
  final Catalog? catalog;
  final bool loading;
  final String? catalogError;
  final Map<String, StoreProduct> products;
  final bool storeAvailable;
  final Entitlements entitlements;
  final Map<String, DownloadProgress> downloads;
  final Map<String, String> downloadErrors;
  final Set<String> buying;
  final ShopNotice? notice;

  const ShopState({
    this.catalog,
    this.loading = true,
    this.catalogError,
    this.products = const {},
    this.storeAvailable = false,
    this.entitlements = const Entitlements(),
    this.downloads = const {},
    this.downloadErrors = const {},
    this.buying = const {},
    this.notice,
  });

  ShopState copyWith({
    Catalog? catalog,
    bool? loading,
    String? catalogError,
    bool clearCatalogError = false,
    Map<String, StoreProduct>? products,
    bool? storeAvailable,
    Entitlements? entitlements,
    Map<String, DownloadProgress>? downloads,
    Map<String, String>? downloadErrors,
    Set<String>? buying,
    ShopNotice? notice,
  }) => ShopState(
    catalog: catalog ?? this.catalog,
    loading: loading ?? this.loading,
    catalogError: clearCatalogError
        ? null
        : (catalogError ?? this.catalogError),
    products: products ?? this.products,
    storeAvailable: storeAvailable ?? this.storeAvailable,
    entitlements: entitlements ?? this.entitlements,
    downloads: downloads ?? this.downloads,
    downloadErrors: downloadErrors ?? this.downloadErrors,
    buying: buying ?? this.buying,
    notice: notice ?? this.notice,
  );

  bool unlocked(CatalogPack p) =>
      catalog != null && entitlements.unlocksPack(catalog!, p);
}

class ShopController extends StateNotifier<ShopState> {
  final StoreGateway gateway;
  final CatalogRepository catalogs;
  final EntitlementRepository entitlementRepo;
  final PackInstaller installer;
  final void Function() onPacksChanged;
  StreamSubscription<PurchaseEvent>? _sub;
  int _notices = 0;

  ShopController({
    required this.gateway,
    required this.catalogs,
    required this.entitlementRepo,
    required this.installer,
    required this.onPacksChanged,
  }) : super(const ShopState());

  /// Entitlements and the cached catalog first (offline works), then the network.
  Future<void> start() async {
    _sub = gateway.purchases.listen(
      _onPurchase,
      onError: (Object e) {
        _notify('store.purchaseFailed', {'error': '$e'});
      },
    );
    final ents = await entitlementRepo.load();
    final cached = await catalogs.loadCached();
    if (!mounted) return;
    state = state.copyWith(
      entitlements: ents,
      catalog: cached,
      loading: cached == null,
    );
    await refresh();
  }

  /// Re-downloads catalog.json (when online) and the product prices.
  Future<void> refresh() async {
    if (!mounted) return;
    state = state.copyWith(
      loading: state.catalog == null,
      clearCatalogError: true,
    );
    try {
      final c = await catalogs.refresh();
      if (!mounted) return;
      state = state.copyWith(catalog: c, loading: false);
    } catch (e) {
      debugPrint('shop: catalog refresh failed: $e');
      if (!mounted) return;
      state = state.copyWith(loading: false, catalogError: '$e');
    }
    await _loadProducts();
  }

  Future<void> _loadProducts() async {
    final c = state.catalog;
    if (c == null) return;
    try {
      final ok = await gateway.isAvailable();
      final products = ok
          ? await gateway.queryProducts(c.productIds)
          : <String, StoreProduct>{};
      if (mounted) {
        state = state.copyWith(products: products, storeAvailable: ok);
      }
    } catch (e) {
      debugPrint('shop: product query failed: $e');
      if (mounted) state = state.copyWith(storeAvailable: false);
    }
  }

  void _notify(String key, [Map<String, Object> args = const {}]) {
    if (mounted) {
      state = state.copyWith(notice: ShopNotice(++_notices, key, args));
    }
  }

  /// Starts a purchase; the caller has shown the parental gate.
  Future<void> buy(String productId) async {
    state = state.copyWith(buying: {...state.buying, productId});
    try {
      await gateway.buy(productId);
    } catch (e) {
      state = state.copyWith(buying: {...state.buying}..remove(productId));
      _notify('store.purchaseFailed', {'error': '$e'});
    }
  }

  Future<void> restore() async {
    await gateway.restore();
  }

  Future<void> _onPurchase(PurchaseEvent e) async {
    if (e.state == PurchaseState.pending) return;
    if (mounted) {
      state = state.copyWith(buying: {...state.buying}..remove(e.productId));
    }
    switch (e.state) {
      case PurchaseState.failed:
        _notify('store.purchaseFailed', {'error': e.error ?? '?'});
        await gateway.finish(e);
        return;
      case PurchaseState.cancelled:
        _notify('store.purchaseCancelled');
        await gateway.finish(e);
        return;
      default:
        break;
    }
    final ents = await entitlementRepo.grant(
      Receipt(
        productId: e.productId,
        purchaseId: e.purchaseId,
        receipt: e.receipt,
        source: e.source,
        transactionDate: e.transactionDate,
        grantedAt: DateTime.now(),
      ),
    );
    await gateway.finish(e);
    if (!mounted) return;
    state = state.copyWith(entitlements: ents);
    // A pack bought just now downloads right away; bundles and restores leave it to the reader
    // (a bundle is many packs, a restore may run on a new phone with little space).
    final c = state.catalog;
    if (e.state == PurchaseState.purchased &&
        c != null &&
        !e.productId.startsWith('bundle_')) {
      for (final p in ents.packsOfProduct(c, e.productId)) {
        if (!installer.isInstalled(p)) unawaited(download(p));
      }
    }
  }

  bool isInstalled(CatalogPack p) => installer.isInstalled(p);

  /// Unlocked packs and gamebooks on the device in an older version than the catalog's.
  List<CatalogPack> updates() {
    final c = state.catalog;
    if (c == null) return const [];
    return [
      for (final p in [
        ...c.packs.where((p) => !p.bundled),
        for (final g in c.gamebooks)
          if (g.ready) g.asPack(),
      ])
        if (state.unlocked(p) &&
            installer.hasAnyVersion(p) &&
            !installer.isInstalled(p))
          p,
    ];
  }

  Future<void> download(CatalogPack pack) async {
    final c = state.catalog;
    if (c == null || state.downloads.containsKey(pack.id)) return;
    state = state.copyWith(
      downloads: {
        ...state.downloads,
        pack.id: DownloadProgress(
          packId: pack.id,
          phase: DownloadPhase.downloading,
        ),
      },
      downloadErrors: {...state.downloadErrors}..remove(pack.id),
    );
    try {
      await for (final p in installer.download(c, pack, state.entitlements)) {
        if (!mounted) return;
        state = state.copyWith(downloads: {...state.downloads, pack.id: p});
      }
      if (!mounted) return;
      state = state.copyWith(downloads: {...state.downloads}..remove(pack.id));
      onPacksChanged();
    } catch (e) {
      if (!mounted) return;
      state = state.copyWith(
        downloads: {...state.downloads}..remove(pack.id),
        downloadErrors: {...state.downloadErrors, pack.id: '$e'},
      );
      _notify('store.downloadFailed', {'error': '$e'});
    }
  }

  Future<void> remove(CatalogPack pack) async {
    await installer.remove(pack);
    if (!mounted) return;
    state = state.copyWith(); // re-evaluate isInstalled
    onPacksChanged();
  }

  @override
  void dispose() {
    _sub?.cancel();
    super.dispose();
  }
}

// --- providers -----------------------------------------------------------------------------

/// A store that is never available (platform without IAP, plugin missing in tests).
class UnavailableStoreGateway extends FakeStoreGateway {
  UnavailableStoreGateway() : super(available: false);
}

final storeGatewayProvider = Provider<StoreGateway>((ref) {
  StoreGateway g;
  if (kFakeIap) {
    g = FakeStoreGateway();
  } else {
    try {
      g = InAppPurchaseGateway();
    } catch (e) {
      debugPrint('shop: in_app_purchase unavailable: $e');
      g = UnavailableStoreGateway();
    }
  }
  ref.onDispose(g.dispose);
  return g;
});

final catalogRepositoryProvider = Provider<CatalogRepository>(
  (ref) => CatalogRepository(),
);

final entitlementStoreProvider = Provider<EntitlementStore>(
  (ref) => PrefsEntitlementStore(),
);

final packInstallerProvider = Provider<PackInstaller>(
  (ref) => PackDownloader(ref.watch(packStoreProvider)),
);

/// Bumped after a pack is installed or removed; the library watches it.
final packsRevisionProvider = StateProvider<int>((ref) => 0);

final shopProvider = StateNotifierProvider<ShopController, ShopState>((ref) {
  final c = ShopController(
    gateway: ref.watch(storeGatewayProvider),
    catalogs: ref.watch(catalogRepositoryProvider),
    entitlementRepo: EntitlementRepository(ref.watch(entitlementStoreProvider)),
    installer: ref.watch(packInstallerProvider),
    onPacksChanged: () => ref.read(packsRevisionProvider.notifier).state++,
  );
  c.start();
  return c;
});
