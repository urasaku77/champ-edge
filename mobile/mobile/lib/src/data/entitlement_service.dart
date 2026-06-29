import 'dart:async';
import 'dart:io' show Platform;

import 'package:flutter/foundation.dart';
import 'package:in_app_purchase/in_app_purchase.dart';
import 'package:in_app_purchase_storekit/in_app_purchase_storekit.dart';

import 'app_settings.dart';

/// フル機能の解放状態（entitlement）を管理する。
///
/// App Store の In-App Purchase（非消費型 1 商品）＋プロモコードで解放する。
/// 自前の招待コード（旧 InviteService）に代わり、解放は購入／復元／App Store の
/// コード引き換え（StoreKit の `presentCodeRedemptionSheet`）でのみ行う。
///
/// 解放状態はローカル（[AppSettings.unlocked]）に永続化し、オフラインでも維持する。
/// 機種変更・再インストール時は「購入を復元」で再付与する。
class EntitlementService extends ChangeNotifier {
  EntitlementService._();
  static final EntitlementService instance = EntitlementService._();

  /// 非消費型 IAP の商品 ID（App Store Connect で同 ID を作成する）。
  /// バンドル ID（io.github.urasaku77.champedge）に揃える。
  static const String productId = 'io.github.urasaku77.champedge.full_unlock';

  final InAppPurchase _iap = InAppPurchase.instance;
  StreamSubscription<List<PurchaseDetails>>? _sub;

  bool _unlocked = false;

  /// フル機能が解放済みか。UI はこれを参照し、未解放なら有料 UI を描画しない。
  bool get unlocked => _unlocked;

  bool _available = false;

  /// ストアに接続できるか（購入・復元の可否）。
  bool get storeAvailable => _available;

  ProductDetails? _product;

  /// 価格表示（例 "¥160"）。未取得なら null。
  String? get priceLabel => _product?.price;

  /// iOS のみ App Store のコード引き換えに対応。
  bool get canRedeemCode => Platform.isIOS;

  bool _initialized = false;

  /// 起動時に一度呼ぶ。永続フラグを反映 → ストア初期化 → 購入ストリーム購読。
  Future<void> init() async {
    if (_initialized) return;
    _initialized = true;

    // まず永続フラグを反映（ストア接続前でも解放状態を即時に確定）。
    await AppSettings.instance.load();
    if (AppSettings.instance.unlocked && !_unlocked) {
      _unlocked = true;
      notifyListeners();
    }

    try {
      _available = await _iap.isAvailable();
    } catch (e) {
      debugPrint('[Entitlement] isAvailable failed: $e');
      _available = false;
    }
    if (!_available) return;

    _sub = _iap.purchaseStream.listen(
      _onPurchases,
      onError: (e) => debugPrint('[Entitlement] purchaseStream error: $e'),
    );
    await _loadProduct();
  }

  Future<void> _loadProduct() async {
    try {
      final resp = await _iap.queryProductDetails(<String>{productId});
      if (resp.productDetails.isNotEmpty) {
        _product = resp.productDetails.first;
        notifyListeners();
      } else {
        debugPrint('[Entitlement] product not found: ${resp.notFoundIDs}');
      }
    } catch (e) {
      debugPrint('[Entitlement] queryProductDetails failed: $e');
    }
  }

  Future<void> _onPurchases(List<PurchaseDetails> purchases) async {
    for (final p in purchases) {
      if (p.productID != productId) {
        // 想定外の保留トランザクションは完了させてキューを詰まらせない。
        if (p.pendingCompletePurchase) await _iap.completePurchase(p);
        continue;
      }
      switch (p.status) {
        case PurchaseStatus.purchased:
        case PurchaseStatus.restored:
          await _grant();
        case PurchaseStatus.error:
          debugPrint('[Entitlement] purchase error: ${p.error}');
        case PurchaseStatus.canceled:
        case PurchaseStatus.pending:
          break;
      }
      if (p.pendingCompletePurchase) {
        await _iap.completePurchase(p);
      }
    }
  }

  Future<void> _grant() async {
    if (_unlocked) return;
    _unlocked = true;
    AppSettings.instance.unlocked = true;
    await AppSettings.instance.save();
    notifyListeners();
  }

  /// 購入（非消費型）。開始できたら true（解放は purchaseStream 経由で確定）。
  Future<bool> buy() async {
    if (!_available) return false;
    if (_product == null) await _loadProduct();
    final pd = _product;
    if (pd == null) return false;
    return _iap.buyNonConsumable(
        purchaseParam: PurchaseParam(productDetails: pd));
  }

  /// 購入を復元（機種変更・再インストール時）。結果は purchaseStream 経由。
  Future<void> restore() async {
    if (!_available) return;
    await _iap.restorePurchases();
  }

  /// iOS: App Store のコード引き換えシートを表示（プロモコード入力）。
  /// 引き換え成功時の解放は purchaseStream 経由で確定する。
  Future<void> redeemCode() async {
    if (!Platform.isIOS) return;
    final addition =
        _iap.getPlatformAddition<InAppPurchaseStoreKitPlatformAddition>();
    await addition.presentCodeRedemptionSheet();
  }

  @override
  void dispose() {
    _sub?.cancel();
    super.dispose();
  }
}
