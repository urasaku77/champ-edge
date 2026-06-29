import 'dart:io' show Platform;

import 'package:firebase_auth/firebase_auth.dart';
import 'package:flutter/material.dart';

import '../data/auth_service.dart';
import '../data/drive_sync.dart';
import '../data/sync_service.dart';
import 'home_screen.dart';

/// クラウドアカウント画面（フル機能側）。
///
/// サインイン（Google / Apple）して、対戦記録・パーティ・設定を本人の Google
/// ドライブへバックアップ／復元する。フル機能解放済みのユーザーのみがここへ到達する
/// （設定画面側で entitlement によりゲートしている）。利用に招待コードや allowlist は
/// 不要で、サインインのみで使える。
class CloudAccountScreen extends StatefulWidget {
  const CloudAccountScreen({super.key});

  @override
  State<CloudAccountScreen> createState() => _CloudAccountScreenState();
}

class _CloudAccountScreenState extends State<CloudAccountScreen> {
  final _auth = AuthService.instance;

  bool _initializing = true; // Firebase 初期化中
  bool _initFailed = false;
  User? _user;
  bool _busy = false;
  bool _syncBusy = false;
  DateTime? _lastBackup;
  String? _error;

  @override
  void initState() {
    super.initState();
    _init();
  }

  Future<void> _init() async {
    setState(() {
      _initializing = true;
      _initFailed = false;
    });
    // クラウド機能を開いたときに初めて Firebase を初期化（遅延初期化）。
    final ok = await _auth.ensureFirebaseInitialized();
    if (!mounted) return;
    if (!ok) {
      setState(() {
        _initializing = false;
        _initFailed = true;
      });
      return;
    }
    setState(() {
      _user = _auth.currentUser;
      _initializing = false;
    });
  }

  Future<void> _signIn(Future<User?> Function() action) async {
    setState(() {
      _busy = true;
      _error = null;
    });
    try {
      final u = await action();
      if (!mounted) return;
      setState(() {
        if (u != null) _user = u;
        _busy = false;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _error = 'サインインに失敗しました: $e';
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
        // 画面スタックを破棄して Top から作り直し、復元データを即反映。
        Navigator.of(context).pushAndRemoveUntil(
          MaterialPageRoute(builder: (_) => const HomeScreen()),
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
    if (_initializing) {
      return const Center(child: CircularProgressIndicator());
    }
    if (_initFailed) {
      return Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text('クラウドへの接続に失敗しました。ネットワークを確認して再試行してください。'),
          const SizedBox(height: 16),
          FilledButton.icon(
            onPressed: _init,
            icon: const Icon(Icons.refresh),
            label: const Text('再試行'),
          ),
        ],
      );
    }
    return _user == null ? _signedOutView() : _allowedView();
  }

  Widget _signedOutView() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Text(
          'クラウド連携は任意です。サインインすると、対戦記録・パーティ・設定を本人の'
          ' Google ドライブへバックアップ／復元できます（機種変更の引き継ぎ用）。',
        ),
        const SizedBox(height: 20),
        if (_busy)
          const Center(child: CircularProgressIndicator())
        else ...[
          FilledButton.icon(
            onPressed: () => _signIn(_auth.signInWithGoogle),
            icon: const Icon(Icons.login),
            label: const Text('Google でサインイン'),
          ),
          if (Platform.isIOS) ...[
            const SizedBox(height: 12),
            FilledButton.icon(
              style: FilledButton.styleFrom(
                  backgroundColor: Colors.black, foregroundColor: Colors.white),
              onPressed: () => _signIn(_auth.signInWithApple),
              icon: const Icon(Icons.apple),
              label: const Text('Apple でサインイン'),
            ),
          ],
        ],
      ],
    );
  }

  Widget _allowedView() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        // アカウント情報＋サインアウト。
        Row(
          children: [
            const Icon(Icons.verified_user, color: Colors.indigo, size: 20),
            const SizedBox(width: 8),
            Expanded(
              child: Text(_user!.email ?? _user!.uid,
                  style: const TextStyle(fontSize: 12, color: Colors.black54)),
            ),
            const SizedBox(width: 8),
            OutlinedButton.icon(
              onPressed: _busy ? null : _signOut,
              icon: const Icon(Icons.logout, size: 18),
              label: const Text('サインアウト'),
              style:
                  OutlinedButton.styleFrom(visualDensity: VisualDensity.compact),
            ),
          ],
        ),
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
