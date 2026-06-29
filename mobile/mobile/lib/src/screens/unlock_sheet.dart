import 'package:flutter/material.dart';

import '../data/entitlement_service.dart';

/// フル機能の解放シート（購入／コード引き換え／復元）。
///
/// 設定画面の控えめな導線から開く。一般ユーザーには目立たせず、コードを持つ人や
/// 購入したい人だけがここから解放する。解放・引き換え・復元はすべて App Store
/// （StoreKit）経由で、自前のコード照合は行わない。
Future<void> showUnlockSheet(BuildContext context) {
  return showModalBottomSheet<void>(
    context: context,
    isScrollControlled: true,
    showDragHandle: true,
    builder: (_) => const _UnlockSheet(),
  );
}

class _UnlockSheet extends StatefulWidget {
  const _UnlockSheet();

  @override
  State<_UnlockSheet> createState() => _UnlockSheetState();
}

class _UnlockSheetState extends State<_UnlockSheet> {
  final _ent = EntitlementService.instance;
  bool _busy = false;
  String? _message;

  @override
  void initState() {
    super.initState();
    _ent.addListener(_onChanged);
  }

  @override
  void dispose() {
    _ent.removeListener(_onChanged);
    super.dispose();
  }

  void _onChanged() {
    if (mounted) setState(() {});
  }

  Future<void> _run(Future<void> Function() action, {String? doneMsg}) async {
    setState(() {
      _busy = true;
      _message = null;
    });
    try {
      await action();
      if (!mounted) return;
      setState(() {
        _busy = false;
        if (doneMsg != null) _message = doneMsg;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _busy = false;
        _message = 'エラー: $e';
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    final unlocked = _ent.unlocked;
    final price = _ent.priceLabel;
    return Padding(
      padding: EdgeInsets.fromLTRB(
          20, 4, 20, MediaQuery.of(context).viewInsets.bottom + 24),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Text(unlocked ? 'フル機能：有効' : 'フル機能',
              textAlign: TextAlign.center,
              style:
                  const TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
          const SizedBox(height: 8),
          Text(
            unlocked
                ? 'すべての機能が利用できます。'
                : 'パーティ管理・対戦記録・分析・スクショ取込・バトルデータ・'
                    'クラウド連携などのフル機能を解放します。',
            textAlign: TextAlign.center,
            style: const TextStyle(fontSize: 12, color: Colors.black54),
          ),
          const SizedBox(height: 20),
          if (_busy)
            const Center(child: CircularProgressIndicator())
          else if (!unlocked) ...[
            if (_ent.storeAvailable) ...[
              FilledButton.icon(
                onPressed: () => _run(_ent.buy),
                icon: const Icon(Icons.lock_open),
                label: Text(price == null ? 'フル機能を購入' : 'フル機能を購入（$price）'),
              ),
              if (_ent.canRedeemCode) ...[
                const SizedBox(height: 10),
                OutlinedButton.icon(
                  onPressed: () => _run(_ent.redeemCode),
                  icon: const Icon(Icons.confirmation_number_outlined),
                  label: const Text('コードを利用'),
                ),
              ],
              const SizedBox(height: 10),
              TextButton.icon(
                onPressed: () => _run(_ent.restore,
                    doneMsg: '購入情報を確認しました（復元対象があれば反映されます）'),
                icon: const Icon(Icons.restore),
                label: const Text('購入を復元'),
              ),
            ] else
              const Text('ただいまストアに接続できません。時間をおいて再度お試しください。',
                  textAlign: TextAlign.center,
                  style: TextStyle(fontSize: 12, color: Colors.black54)),
          ] else
            TextButton.icon(
              onPressed: () => _run(_ent.restore),
              icon: const Icon(Icons.restore),
              label: const Text('購入を復元'),
            ),
          if (_message != null) ...[
            const SizedBox(height: 12),
            Text(_message!,
                textAlign: TextAlign.center,
                style: const TextStyle(fontSize: 12)),
          ],
        ],
      ),
    );
  }
}
