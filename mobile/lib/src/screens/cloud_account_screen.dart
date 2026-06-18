import 'package:firebase_auth/firebase_auth.dart';
import 'package:flutter/material.dart';

import '../data/auth_service.dart';
import '../data/drive_sync.dart';
import '../data/invite_service.dart';
import '../data/sync_service.dart';
import 'admin_screen.dart';
import 'auth_gate.dart';

/// クラウドアカウント画面（アカウント情報・サインアウト・管理者メニュー入口）。
///
/// 起動ゲート（AuthGate）通過後にここへ来るため通常は登録済み状態を表示する。
/// 管理者（users.role == 'admin'）にのみ管理者メニューを表示する。
class CloudAccountScreen extends StatefulWidget {
  const CloudAccountScreen({super.key});

  @override
  State<CloudAccountScreen> createState() => _CloudAccountScreenState();
}

class _CloudAccountScreenState extends State<CloudAccountScreen> {
  final _auth = AuthService.instance;
  final _invite = InviteService.instance;
  final _codeCtrl = TextEditingController();

  User? _user;
  bool? _allowed; // null=未判定
  bool _isAdmin = false;
  String _myName = '';
  bool _busy = false;
  bool _syncBusy = false;
  DateTime? _lastBackup;
  String? _error;

  @override
  void initState() {
    super.initState();
    _user = _auth.currentUser;
    if (_user != null) _checkAllowed();
  }

  @override
  void dispose() {
    _codeCtrl.dispose();
    super.dispose();
  }

  Future<void> _checkAllowed() async {
    final u = _user;
    if (u == null) return;
    setState(() => _busy = true);
    final status = await _invite.allowStatus(u.uid);
    final entry =
        status == AllowStatus.allowed ? await _invite.getUser(u.uid) : null;
    if (!mounted) return;
    setState(() {
      _allowed = status == AllowStatus.allowed;
      _isAdmin = entry?.isAdmin ?? false;
      _myName = entry?.name ?? '';
      if (status == AllowStatus.unknown) {
        _error = '利用状態を確認できませんでした（オフラインの可能性）。';
      }
      _busy = false;
    });
  }

  Future<void> _signIn() async {
    setState(() {
      _busy = true;
      _error = null;
    });
    try {
      final u = await _auth.signInWithGoogle();
      if (!mounted) return;
      if (u == null) {
        setState(() => _busy = false); // キャンセル
        return;
      }
      setState(() => _user = u);
      await _checkAllowed();
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _error = 'サインインに失敗しました: $e';
        _busy = false;
      });
    }
  }

  Future<void> _redeem() async {
    final u = _user;
    if (u == null) return;
    setState(() {
      _busy = true;
      _error = null;
    });
    final res = await _invite.redeem(_codeCtrl.text, u);
    if (!mounted) return;
    if (res.ok) {
      setState(() {
        _allowed = true;
        _busy = false;
      });
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('利用登録が完了しました')),
      );
    } else {
      setState(() {
        _error = res.message;
        _busy = false;
      });
    }
  }

  Future<void> _signOut() async {
    setState(() => _busy = true);
    await _auth.signOut();
    if (!mounted) return;
    setState(() {
      _user = null;
      _allowed = null;
      _codeCtrl.clear();
      _busy = false;
      _error = null;
    });
  }

  Future<void> _backup() async {
    setState(() {
      _syncBusy = true;
      _error = null;
    });
    try {
      await SyncService.instance.backupToDrive();
      final t = await DriveSync.instance.lastBackupTime();
      if (!mounted) return;
      setState(() => _lastBackup = t ?? DateTime.now());
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('クラウドにバックアップしました')),
      );
    } catch (e) {
      if (!mounted) return;
      setState(() => _error = 'バックアップに失敗しました: $e');
    } finally {
      if (mounted) setState(() => _syncBusy = false);
    }
  }

  Future<void> _restore() async {
    final ok = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('クラウドから復元'),
        content: const Text('この端末の対戦記録・パーティ・設定を、クラウドの'
            'バックアップで上書きします。よろしいですか？'),
        actions: [
          TextButton(
              onPressed: () => Navigator.pop(ctx, false),
              child: const Text('キャンセル')),
          FilledButton(
              onPressed: () => Navigator.pop(ctx, true),
              child: const Text('復元')),
        ],
      ),
    );
    if (ok != true) return;
    setState(() {
      _syncBusy = true;
      _error = null;
    });
    try {
      final found = await SyncService.instance.restoreFromDrive();
      if (!mounted) return;
      if (found) {
        // 画面スタックを破棄してゲート（→Top）から作り直し、復元データを即反映。
        Navigator.of(context).pushAndRemoveUntil(
          MaterialPageRoute(builder: (_) => const AuthGate()),
          (route) => false,
        );
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('クラウドから復元しました')),
        );
        return;
      }
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('クラウドにバックアップが見つかりませんでした')),
      );
    } catch (e) {
      if (!mounted) return;
      setState(() => _error = '復元に失敗しました: $e');
    } finally {
      if (mounted) setState(() => _syncBusy = false);
    }
  }

  String _fmt(DateTime t) {
    final l = t.toLocal();
    String two(int v) => v.toString().padLeft(2, '0');
    return '${l.year}/${two(l.month)}/${two(l.day)} ${two(l.hour)}:${two(l.minute)}';
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('クラウドアカウント')),
      body: SafeArea(
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(20),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              _body(),
              if (_error != null) ...[
                const SizedBox(height: 16),
                Text(_error!, style: const TextStyle(color: Colors.red)),
              ],
            ],
          ),
        ),
      ),
    );
  }

  Widget _body() {
    if (_busy && _user == null) {
      return const Center(child: CircularProgressIndicator());
    }
    if (_user == null) return _signedOutView();
    if (_allowed == null || (_busy && _allowed == null)) {
      return const Center(child: CircularProgressIndicator());
    }
    return _allowed == true ? _allowedView() : _inviteView();
  }

  Widget _signedOutView() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Text(
          'クラウド連携は任意です。サインインしなくても、計算・パーティ編集・'
          '対戦記録などアプリの全機能はこの端末でそのまま使えます。',
        ),
        const SizedBox(height: 20),
        FilledButton.icon(
          onPressed: _busy ? null : _signIn,
          icon: const Icon(Icons.login),
          label: const Text('Google でサインイン'),
        ),
        const SizedBox(height: 12),
        const Text(
          '※ 利用には招待コードが必要です（招待制）。',
          style: TextStyle(fontSize: 12, color: Colors.black54),
        ),
      ],
    );
  }

  Widget _inviteView() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text('サインイン済み: ${_user!.email ?? _user!.uid}'),
        const SizedBox(height: 16),
        const Text('招待コードを入力して利用登録してください。'),
        const SizedBox(height: 12),
        TextField(
          controller: _codeCtrl,
          decoration: const InputDecoration(
            labelText: '招待コード',
            border: OutlineInputBorder(),
          ),
          autocorrect: false,
          enableSuggestions: false,
        ),
        const SizedBox(height: 16),
        Row(
          children: [
            FilledButton(
              onPressed: _busy ? null : _redeem,
              child: _busy
                  ? const SizedBox(
                      width: 18,
                      height: 18,
                      child: CircularProgressIndicator(strokeWidth: 2))
                  : const Text('登録'),
            ),
            const SizedBox(width: 12),
            TextButton(
              onPressed: _busy ? null : _signOut,
              child: const Text('サインアウト'),
            ),
          ],
        ),
      ],
    );
  }

  Widget _allowedView() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        // アカウント情報＋サインアウト（上部・スクロール不要）。
        Row(
          children: [
            const Icon(Icons.verified_user, color: Colors.indigo, size: 20),
            const SizedBox(width: 8),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  if (_myName.isNotEmpty)
                    Text(_myName,
                        style: const TextStyle(fontWeight: FontWeight.bold)),
                  Text(_user!.email ?? _user!.uid,
                      style:
                          const TextStyle(fontSize: 12, color: Colors.black54)),
                ],
              ),
            ),
            const SizedBox(width: 8),
            OutlinedButton.icon(
              onPressed: _busy ? null : _signOut,
              icon: const Icon(Icons.logout, size: 18),
              label: const Text('サインアウト'),
              style: OutlinedButton.styleFrom(
                  visualDensity: VisualDensity.compact),
            ),
          ],
        ),
        // 管理者メニュー（管理者のみ・サインアウトの直下＝上部に配置）。
        if (_isAdmin) ...[
          const SizedBox(height: 12),
          FilledButton.tonalIcon(
            onPressed: () => Navigator.of(context).push(
              MaterialPageRoute(builder: (_) => const AdminScreen()),
            ),
            icon: const Icon(Icons.admin_panel_settings),
            label: const Text('管理者メニュー'),
          ),
        ],
        const Divider(height: 28),
        const Text('クラウドバックアップ（任意）',
            style: TextStyle(fontSize: 13, fontWeight: FontWeight.bold)),
        const SizedBox(height: 4),
        const Text(
          '対戦記録・パーティ・設定を本人の Google ドライブへ保存／復元（機種変更の引き継ぎ用）。',
          style: TextStyle(fontSize: 12, color: Colors.black54),
        ),
        if (_lastBackup != null)
          Padding(
            padding: const EdgeInsets.only(top: 6),
            child: Text('最終バックアップ: ${_fmt(_lastBackup!)}',
                style: const TextStyle(fontSize: 12, color: Colors.black45)),
          ),
        const SizedBox(height: 10),
        Row(
          children: [
            FilledButton.icon(
              onPressed: _syncBusy ? null : _backup,
              icon: const Icon(Icons.backup_outlined),
              label: const Text('バックアップ'),
            ),
            const SizedBox(width: 12),
            OutlinedButton.icon(
              onPressed: _syncBusy ? null : _restore,
              icon: const Icon(Icons.restore),
              label: const Text('復元'),
            ),
            if (_syncBusy) ...[
              const SizedBox(width: 12),
              const SizedBox(
                  width: 18,
                  height: 18,
                  child: CircularProgressIndicator(strokeWidth: 2)),
            ],
          ],
        ),
      ],
    );
  }
}
