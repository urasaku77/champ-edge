import 'dart:async';
import 'dart:io' show Platform;

import 'package:firebase_auth/firebase_auth.dart';
import 'package:flutter/material.dart';

import '../data/auth_service.dart';
import '../data/invite_service.dart';
import 'home_screen.dart';

/// 起動時の招待制ゲート。
///
/// Google サインイン → 招待コードで利用登録（allowlist）を通過するまで Top 画面に
/// 入れない。登録済みなら以降は（オフラインでもローカル記録フォールバックで）Top を表示。
///
/// 堅牢化：Firebase 初期化失敗・許可確認の接続不能（オフライン新規端末）でも
/// 行き止まりにせず「再試行」を提示し、ロックアウトを防ぐ。
class AuthGate extends StatefulWidget {
  const AuthGate({super.key});

  @override
  State<AuthGate> createState() => _AuthGateState();
}

enum _Phase {
  initializing, // Firebase 初期化中
  initError, // 初期化失敗（再試行）
  signIn, // 未サインイン
  checking, // allowlist 確認中
  unreachable, // 接続不能で確認できない（再試行）
  invite, // 未登録（招待コード入力）
  ready, // 通過（Top）
}

class _AuthGateState extends State<AuthGate> {
  final _auth = AuthService.instance;
  final _invite = InviteService.instance;
  StreamSubscription<User?>? _sub;

  _Phase _phase = _Phase.initializing;
  User? _user;

  @override
  void initState() {
    super.initState();
    _init();
  }

  @override
  void dispose() {
    _sub?.cancel();
    super.dispose();
  }

  Future<void> _init() async {
    setState(() => _phase = _Phase.initializing);
    final ok = await _auth.ensureFirebaseInitialized();
    if (!mounted) return;
    if (!ok) {
      setState(() => _phase = _Phase.initError);
      return;
    }
    _sub ??= _auth.authStateChanges().listen(
          _onAuthChanged,
          onError: (_) {
            if (mounted) setState(() => _phase = _Phase.initError);
          },
        );
  }

  Future<void> _onAuthChanged(User? user) async {
    _user = user;
    if (user == null) {
      if (mounted) setState(() => _phase = _Phase.signIn);
      return;
    }
    await _evaluateAllowed();
  }

  Future<void> _evaluateAllowed() async {
    final u = _user;
    if (u == null) return;
    if (mounted) setState(() => _phase = _Phase.checking);
    final status = await _invite.allowStatus(u.uid);
    if (!mounted) return;
    setState(() {
      switch (status) {
        case AllowStatus.allowed:
          _phase = _Phase.ready;
        case AllowStatus.denied:
          _phase = _Phase.invite;
        case AllowStatus.unknown:
          _phase = _Phase.unreachable;
      }
    });
  }

  @override
  Widget build(BuildContext context) {
    switch (_phase) {
      case _Phase.initializing:
      case _Phase.checking:
        return const _GateScaffold(child: CircularProgressIndicator());
      case _Phase.initError:
        return _GateMessage(
          title: '接続できませんでした',
          message: 'アプリの初期化に失敗しました。ネットワークを確認して再試行してください。',
          actionLabel: '再試行',
          onAction: _init,
        );
      case _Phase.unreachable:
        return _GateMessage(
          title: 'オフラインのようです',
          message: '利用状態を確認できませんでした。初回はオンライン接続が必要です。'
              '接続を確認して再試行してください。',
          actionLabel: '再試行',
          onAction: _evaluateAllowed,
          onSignOut: () => _auth.signOut(),
        );
      case _Phase.signIn:
        return const _SignInGate();
      case _Phase.invite:
        return _InviteGate(
          user: _user!,
          onRegistered: _evaluateAllowed,
          onSignOut: () => _auth.signOut(),
        );
      case _Phase.ready:
        return const HomeScreen();
    }
  }
}

class _GateScaffold extends StatelessWidget {
  final Widget child;
  const _GateScaffold({required this.child});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: SafeArea(
        child: Center(
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 420),
            child: Padding(
              padding: const EdgeInsets.all(24),
              child: child,
            ),
          ),
        ),
      ),
    );
  }
}

/// エラー/オフライン用の汎用メッセージ＋再試行画面。
class _GateMessage extends StatelessWidget {
  final String title;
  final String message;
  final String actionLabel;
  final VoidCallback onAction;
  final VoidCallback? onSignOut;
  const _GateMessage({
    required this.title,
    required this.message,
    required this.actionLabel,
    required this.onAction,
    this.onSignOut,
  });

  @override
  Widget build(BuildContext context) {
    return _GateScaffold(
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          const Icon(Icons.cloud_off, size: 40, color: Colors.black45),
          const SizedBox(height: 12),
          Text(title,
              textAlign: TextAlign.center,
              style:
                  const TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
          const SizedBox(height: 8),
          Text(message, textAlign: TextAlign.center),
          const SizedBox(height: 20),
          FilledButton.icon(
            onPressed: onAction,
            icon: const Icon(Icons.refresh),
            label: Text(actionLabel),
          ),
          if (onSignOut != null) ...[
            const SizedBox(height: 8),
            TextButton(
              onPressed: onSignOut,
              child: const Text('別のアカウントでサインイン'),
            ),
          ],
        ],
      ),
    );
  }
}

class _SignInGate extends StatefulWidget {
  const _SignInGate();

  @override
  State<_SignInGate> createState() => _SignInGateState();
}

class _SignInGateState extends State<_SignInGate> {
  bool _busy = false;
  String? _error;

  Future<void> _run(Future<User?> Function() action) async {
    setState(() {
      _busy = true;
      _error = null;
    });
    try {
      final u = await action();
      if (!mounted) return;
      // 成功時は authStateChanges がゲートを次フェーズへ進める。
      if (u == null) setState(() => _busy = false); // キャンセル
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _error = 'サインインに失敗しました: $e';
        _busy = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return _GateScaffold(
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          const Text('ChampEdge',
              style: TextStyle(fontSize: 26, fontWeight: FontWeight.bold)),
          const SizedBox(height: 8),
          const Text('招待制アプリです。続けるにはサインインしてください。',
              textAlign: TextAlign.center),
          const SizedBox(height: 28),
          if (_busy)
            const CircularProgressIndicator()
          else ...[
            // 全プラットフォームで Google を推奨（Drive 連携を見据え）。
            FilledButton.icon(
              onPressed: () => _run(AuthService.instance.signInWithGoogle),
              icon: const Icon(Icons.login),
              label: const Text('Google でサインイン'),
            ),
            // iOS は App Store 4.8 対応で Apple も併記（希望者・審査用）。
            if (Platform.isIOS) ...[
              const SizedBox(height: 12),
              FilledButton.icon(
                style: FilledButton.styleFrom(
                    backgroundColor: Colors.black,
                    foregroundColor: Colors.white),
                onPressed: () => _run(AuthService.instance.signInWithApple),
                icon: const Icon(Icons.apple),
                label: const Text('Apple でサインイン'),
              ),
            ],
          ],
          if (_error != null) ...[
            const SizedBox(height: 16),
            Text(_error!,
                textAlign: TextAlign.center,
                style: const TextStyle(color: Colors.red)),
          ],
        ],
      ),
    );
  }
}

class _InviteGate extends StatefulWidget {
  final User user;
  final Future<void> Function() onRegistered;
  final VoidCallback onSignOut;
  const _InviteGate({
    required this.user,
    required this.onRegistered,
    required this.onSignOut,
  });

  @override
  State<_InviteGate> createState() => _InviteGateState();
}

class _InviteGateState extends State<_InviteGate> {
  final _codeCtrl = TextEditingController();
  bool _busy = false;
  String? _error;

  @override
  void dispose() {
    _codeCtrl.dispose();
    super.dispose();
  }

  Future<void> _redeem() async {
    setState(() {
      _busy = true;
      _error = null;
    });
    final res = await InviteService.instance.redeem(_codeCtrl.text, widget.user);
    if (!mounted) return;
    if (res.ok) {
      await widget.onRegistered();
    } else {
      setState(() {
        _error = res.message;
        _busy = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return _GateScaffold(
      child: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          const Text('招待コードの入力',
              textAlign: TextAlign.center,
              style: TextStyle(fontSize: 20, fontWeight: FontWeight.bold)),
          const SizedBox(height: 8),
          Text('サインイン中: ${widget.user.email ?? widget.user.uid}',
              textAlign: TextAlign.center,
              style: const TextStyle(fontSize: 12, color: Colors.black54)),
          const SizedBox(height: 20),
          TextField(
            controller: _codeCtrl,
            decoration: const InputDecoration(
              labelText: '招待コード',
              border: OutlineInputBorder(),
            ),
            autocorrect: false,
            enableSuggestions: false,
            textInputAction: TextInputAction.done,
            onSubmitted: (_) => _busy ? null : _redeem(),
          ),
          const SizedBox(height: 16),
          if (_busy)
            const Center(child: CircularProgressIndicator())
          else
            FilledButton(
              onPressed: _redeem,
              child: const Text('登録'),
            ),
          if (_error != null) ...[
            const SizedBox(height: 16),
            Text(_error!,
                textAlign: TextAlign.center,
                style: const TextStyle(color: Colors.red)),
          ],
          const SizedBox(height: 8),
          TextButton(
            onPressed: _busy ? null : widget.onSignOut,
            child: const Text('別のアカウントでサインイン'),
          ),
        ],
      ),
    );
  }
}
