import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../data/invite_service.dart';

/// 管理者専用：招待コード発行・招待一覧・ユーザー一覧/無効化。
/// 表示は users.role == 'admin' のユーザーのみ（呼び出し側でガード）。
class AdminScreen extends StatefulWidget {
  const AdminScreen({super.key});

  @override
  State<AdminScreen> createState() => _AdminScreenState();
}

class _AdminScreenState extends State<AdminScreen> {
  final _invite = InviteService.instance;
  final _emailCtrl = TextEditingController();
  final _nameCtrl = TextEditingController();

  bool _loading = true;
  bool _issuing = false;
  String? _error;
  List<UserEntry> _users = const [];
  List<InviteEntry> _invites = const [];

  @override
  void initState() {
    super.initState();
    _load();
  }

  @override
  void dispose() {
    _emailCtrl.dispose();
    _nameCtrl.dispose();
    super.dispose();
  }

  Future<void> _load() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final users = await _invite.listUsers();
      final invites = await _invite.listInvites();
      if (!mounted) return;
      setState(() {
        _users = users;
        _invites = invites;
        _loading = false;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _error = '読み込みに失敗しました: $e';
        _loading = false;
      });
    }
  }

  Future<void> _issue() async {
    final email = _emailCtrl.text.trim();
    final name = _nameCtrl.text.trim();
    if (email.isEmpty || !email.contains('@')) {
      setState(() => _error = '有効な Gmail アドレスを入力してください。');
      return;
    }
    if (name.isEmpty) {
      setState(() => _error = '表示名を入力してください。');
      return;
    }
    setState(() {
      _issuing = true;
      _error = null;
    });
    try {
      final code = await _invite.issueInvite(email, name);
      if (!mounted) return;
      _emailCtrl.clear();
      _nameCtrl.clear();
      await _showCodeDialog(email, code);
      await _load();
    } catch (e) {
      if (!mounted) return;
      setState(() => _error = '発行に失敗しました: $e');
    } finally {
      if (mounted) setState(() => _issuing = false);
    }
  }

  Future<void> _showCodeDialog(String email, String code) async {
    await showDialog<void>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('招待コードを発行しました'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text('宛先: $email'),
            const SizedBox(height: 12),
            SelectableText(
              code,
              style: const TextStyle(
                  fontSize: 28,
                  fontWeight: FontWeight.bold,
                  letterSpacing: 4,
                  fontFamily: 'monospace'),
            ),
            const SizedBox(height: 8),
            const Text('このコードを本人へ直接共有してください（1回限り）。',
                style: TextStyle(fontSize: 12, color: Colors.black54)),
          ],
        ),
        actions: [
          TextButton.icon(
            onPressed: () async {
              await Clipboard.setData(ClipboardData(text: code));
              if (ctx.mounted) {
                ScaffoldMessenger.of(ctx).showSnackBar(
                  const SnackBar(content: Text('コピーしました')),
                );
              }
            },
            icon: const Icon(Icons.copy),
            label: const Text('コピー'),
          ),
          TextButton(
            onPressed: () => Navigator.of(ctx).pop(),
            child: const Text('閉じる'),
          ),
        ],
      ),
    );
  }

  Future<void> _confirmRemoveUser(UserEntry u) async {
    final ok = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('ユーザーを無効化'),
        content: Text('${u.email} を allowlist から削除します。'
            'このユーザーは再度招待コードが必要になります。'),
        actions: [
          TextButton(
              onPressed: () => Navigator.pop(ctx, false),
              child: const Text('キャンセル')),
          FilledButton(
              onPressed: () => Navigator.pop(ctx, true),
              child: const Text('無効化')),
        ],
      ),
    );
    if (ok == true) {
      await _invite.removeUser(u.uid);
      await _load();
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('管理者メニュー'),
        actions: [
          IconButton(
            onPressed: _loading ? null : _load,
            icon: const Icon(Icons.refresh),
            tooltip: '再読み込み',
          ),
        ],
      ),
      body: SafeArea(
        child: _loading
            ? const Center(child: CircularProgressIndicator())
            : ListView(
                padding: const EdgeInsets.all(16),
                children: [
                  if (_error != null) ...[
                    Text(_error!, style: const TextStyle(color: Colors.red)),
                    const SizedBox(height: 12),
                  ],
                  _sectionHeader('招待コードを発行'),
                  Row(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Expanded(
                        child: Column(
                          children: [
                            TextField(
                              controller: _nameCtrl,
                              decoration: const InputDecoration(
                                labelText: '表示名（日本語可）',
                                border: OutlineInputBorder(),
                                isDense: true,
                              ),
                            ),
                            const SizedBox(height: 8),
                            TextField(
                              controller: _emailCtrl,
                              decoration: const InputDecoration(
                                labelText: '招待する人のメール（サインインに使うアドレス）',
                                border: OutlineInputBorder(),
                                isDense: true,
                              ),
                              keyboardType: TextInputType.emailAddress,
                              autocorrect: false,
                              enableSuggestions: false,
                            ),
                          ],
                        ),
                      ),
                      const SizedBox(width: 12),
                      FilledButton(
                        onPressed: _issuing ? null : _issue,
                        child: _issuing
                            ? const SizedBox(
                                width: 18,
                                height: 18,
                                child:
                                    CircularProgressIndicator(strokeWidth: 2))
                            : const Text('発行'),
                      ),
                    ],
                  ),
                  const SizedBox(height: 20),
                  _sectionHeader('招待コード（${_invites.length}）'),
                  if (_invites.isEmpty)
                    const _EmptyHint('発行済みの招待コードはありません'),
                  for (final inv in _invites) _inviteTile(inv),
                  const SizedBox(height: 20),
                  _sectionHeader('登録ユーザー（${_users.length}）'),
                  if (_users.isEmpty) const _EmptyHint('登録ユーザーはいません'),
                  for (final u in _users) _userTile(u),
                ],
              ),
      ),
    );
  }

  Widget _inviteTile(InviteEntry inv) {
    return ListTile(
      dense: true,
      leading: Icon(
        inv.used ? Icons.check_circle : Icons.mail_outline,
        color: inv.used ? Colors.grey : Colors.indigo,
      ),
      title: Text(inv.code,
          style: const TextStyle(
              fontFamily: 'monospace', fontWeight: FontWeight.bold)),
      subtitle: Text('${inv.name.isEmpty ? "(名前なし)" : inv.name}  ・  '
          '${inv.email}  ・  ${inv.used ? "使用済み" : "未使用"}'),
      trailing: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          if (!inv.used)
            IconButton(
              icon: const Icon(Icons.copy, size: 20),
              tooltip: 'コピー',
              onPressed: () async {
                await Clipboard.setData(ClipboardData(text: inv.code));
                if (mounted) {
                  ScaffoldMessenger.of(context).showSnackBar(
                      const SnackBar(content: Text('コピーしました')));
                }
              },
            ),
          IconButton(
            icon: const Icon(Icons.delete_outline, size: 20),
            tooltip: '削除',
            onPressed: () async {
              await _invite.deleteInvite(inv.code);
              await _load();
            },
          ),
        ],
      ),
    );
  }

  Widget _userTile(UserEntry u) {
    return ListTile(
      dense: true,
      leading: Icon(u.isAdmin ? Icons.shield : Icons.person,
          color: u.isAdmin ? Colors.indigo : Colors.black54),
      title: Text(u.name.isEmpty ? '(名前なし)' : u.name),
      subtitle: Text('${u.email}  ・  ${u.role}'),
      trailing: u.isAdmin
          ? const Text('管理者',
              style: TextStyle(fontSize: 12, color: Colors.indigo))
          : IconButton(
              icon: const Icon(Icons.person_remove_outlined, size: 20),
              tooltip: '無効化',
              onPressed: () => _confirmRemoveUser(u),
            ),
    );
  }

  Widget _sectionHeader(String label) => Padding(
        padding: const EdgeInsets.only(bottom: 8),
        child: Text(label,
            style: const TextStyle(
                fontSize: 13,
                fontWeight: FontWeight.bold,
                color: Colors.indigo)),
      );
}

class _EmptyHint extends StatelessWidget {
  final String text;
  const _EmptyHint(this.text);
  @override
  Widget build(BuildContext context) => Padding(
        padding: const EdgeInsets.symmetric(vertical: 8),
        child: Text(text,
            style: const TextStyle(fontSize: 12, color: Colors.black45)),
      );
}
