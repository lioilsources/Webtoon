// StoreGateway: the one seam between the app and App Store / Google Play (in_app_purchase:
// StoreKit / Play Billing). Every product is a non-consumable unlock; content is downloaded
// separately (pack_downloader.dart). `--dart-define=WEBTOON_FAKE_IAP=true` swaps in
// [FakeStoreGateway] (UI tests, simulator runs without a sandbox account).

import 'dart:async';

import 'package:in_app_purchase/in_app_purchase.dart';

/// `WEBTOON_FAKE_IAP=true`: purchases succeed instantly, nothing talks to a store.
const bool kFakeIap = bool.fromEnvironment('WEBTOON_FAKE_IAP');

/// A product as the store describes it (localised title and price string).
class StoreProduct {
  final String id;
  final String title;
  final String description;

  /// Formatted in the user's storefront currency, e.g. "0,99 €" — shown as is.
  final String price;
  final double rawPrice;
  final String currencyCode;

  const StoreProduct({
    required this.id,
    this.title = '',
    this.description = '',
    required this.price,
    this.rawPrice = 0,
    this.currencyCode = 'USD',
  });
}

enum PurchaseState { pending, purchased, restored, failed, cancelled }

/// One update from the store's purchase stream.
class PurchaseEvent {
  final String productId;
  final PurchaseState state;
  final String? purchaseId;

  /// Store receipt (`serverVerificationData`) and its source (app_store / google_play); kept
  /// with the entitlement for the later server-side validation (not implemented yet).
  final String? receipt;
  final String? source;
  final String? transactionDate;
  final String? error;

  const PurchaseEvent({
    required this.productId,
    required this.state,
    this.purchaseId,
    this.receipt,
    this.source,
    this.transactionDate,
    this.error,
  });

  bool get grants =>
      state == PurchaseState.purchased || state == PurchaseState.restored;
}

abstract class StoreGateway {
  Future<bool> isAvailable();

  /// Product details by id; ids the store does not know are missing from the map.
  Future<Map<String, StoreProduct>> queryProducts(Set<String> ids);

  /// Purchase and restore results (broadcast).
  Stream<PurchaseEvent> get purchases;

  /// Starts a non-consumable purchase; the outcome arrives on [purchases].
  Future<void> buy(String productId);

  /// Re-delivers every owned product on [purchases] as [PurchaseState.restored].
  Future<void> restore();

  /// Acknowledges a delivered purchase (after the entitlement is saved). Play refunds
  /// purchases that are not acknowledged within 3 days.
  Future<void> finish(PurchaseEvent event);

  void dispose();
}

/// The real stores via `package:in_app_purchase`.
class InAppPurchaseGateway implements StoreGateway {
  final InAppPurchase _iap;
  final _events = StreamController<PurchaseEvent>.broadcast();
  final _details = <String, ProductDetails>{};
  final _pending = <String, PurchaseDetails>{};
  StreamSubscription<List<PurchaseDetails>>? _sub;

  InAppPurchaseGateway([InAppPurchase? iap])
    : _iap = iap ?? InAppPurchase.instance {
    _sub = _iap.purchaseStream.listen((list) {
      for (final p in list) {
        _pending[_key(p.productID, p.purchaseID)] = p;
        _events.add(_event(p));
      }
    }, onError: (Object e) => _events.addError(e));
  }

  static String _key(String product, String? purchase) =>
      '$product/${purchase ?? ''}';

  static PurchaseEvent _event(PurchaseDetails p) => PurchaseEvent(
    productId: p.productID,
    state: switch (p.status) {
      PurchaseStatus.pending => PurchaseState.pending,
      PurchaseStatus.purchased => PurchaseState.purchased,
      PurchaseStatus.restored => PurchaseState.restored,
      PurchaseStatus.error => PurchaseState.failed,
      PurchaseStatus.canceled => PurchaseState.cancelled,
    },
    purchaseId: p.purchaseID,
    receipt: p.verificationData.serverVerificationData,
    source: p.verificationData.source,
    transactionDate: p.transactionDate,
    error: p.error?.message,
  );

  @override
  Future<bool> isAvailable() => _iap.isAvailable();

  @override
  Future<Map<String, StoreProduct>> queryProducts(Set<String> ids) async {
    if (ids.isEmpty) return {};
    final res = await _iap.queryProductDetails(ids);
    for (final d in res.productDetails) {
      _details[d.id] = d;
    }
    return {
      for (final d in res.productDetails)
        d.id: StoreProduct(
          id: d.id,
          title: d.title,
          description: d.description,
          price: d.price,
          rawPrice: d.rawPrice,
          currencyCode: d.currencyCode,
        ),
    };
  }

  @override
  Stream<PurchaseEvent> get purchases => _events.stream;

  @override
  Future<void> buy(String productId) async {
    var d = _details[productId];
    if (d == null) {
      await queryProducts({productId});
      d = _details[productId];
    }
    if (d == null) throw StateError('Produkt $productId obchod nezná.');
    await _iap.buyNonConsumable(
      purchaseParam: PurchaseParam(productDetails: d),
    );
  }

  @override
  Future<void> restore() => _iap.restorePurchases();

  @override
  Future<void> finish(PurchaseEvent event) async {
    final p = _pending.remove(_key(event.productId, event.purchaseId));
    if (p != null && p.pendingCompletePurchase) await _iap.completePurchase(p);
  }

  @override
  void dispose() {
    _sub?.cancel();
    _events.close();
  }
}

/// Store stand-in: every known product can be bought, prices by product kind (USD tiers of
/// docs/store-products.md). [nextResult] lets a test make the next purchase fail or cancel.
class FakeStoreGateway implements StoreGateway {
  final _events = StreamController<PurchaseEvent>.broadcast();

  /// Products owned "on the store account" (re-delivered by [restore]).
  final Set<String> owned;
  final bool available;
  PurchaseState nextResult = PurchaseState.purchased;
  final List<String> bought = [];
  final List<String> finished = [];
  int restoreCalls = 0;

  FakeStoreGateway({Set<String>? owned, this.available = true})
    : owned = owned ?? {};

  static String priceFor(String id) {
    if (id == 'bundle_all') return r'$6.99';
    if (id.startsWith('bundle_')) return r'$2.99';
    if (id.startsWith('kit_')) return r'$3.99';
    if (id.startsWith('gamebook_')) return r'$1.99';
    return r'$0.99';
  }

  @override
  Future<bool> isAvailable() async => available;

  @override
  Future<Map<String, StoreProduct>> queryProducts(Set<String> ids) async => {
    if (available)
      for (final id in ids)
        id: StoreProduct(id: id, title: id, price: priceFor(id)),
  };

  @override
  Stream<PurchaseEvent> get purchases => _events.stream;

  @override
  Future<void> buy(String productId) async {
    bought.add(productId);
    final result = nextResult;
    nextResult = PurchaseState.purchased;
    scheduleMicrotask(() {
      if (result == PurchaseState.purchased) owned.add(productId);
      _events.add(
        PurchaseEvent(
          productId: productId,
          state: result,
          purchaseId: 'fake-${bought.length}',
          receipt: 'fake-receipt-$productId',
          source: 'fake',
          error: result == PurchaseState.failed ? 'fake failure' : null,
        ),
      );
    });
  }

  @override
  Future<void> restore() async {
    restoreCalls++;
    final ids = owned.toList();
    scheduleMicrotask(() {
      for (final id in ids) {
        _events.add(
          PurchaseEvent(
            productId: id,
            state: PurchaseState.restored,
            purchaseId: 'fake-restore-$id',
            receipt: 'fake-receipt-$id',
            source: 'fake',
          ),
        );
      }
    });
  }

  @override
  Future<void> finish(PurchaseEvent event) async =>
      finished.add(event.productId);

  @override
  void dispose() => _events.close();
}
