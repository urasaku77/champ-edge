import 'package:flutter/material.dart';
import 'package:package_info_plus/package_info_plus.dart';

import '../data/entitlement_service.dart';
import '../data/ref_data.dart';
import 'cloud_account_screen.dart';
import 'unlock_sheet.dart';

/// 設定画面（旧 champ-edge の「アプリ設定」相当の最小版）。
/// ルール（シングル＋メガ固定。ダブル/Z技/ダイマは P4）＋クラウド/参照データ更新。
class SettingsScreen extends StatefulWidget {
  const SettingsScreen({super.key});

  @override
  State<SettingsScreen> createState() => _SettingsScreenState();
}

class _SettingsScreenState extends State<SettingsScreen> {
  final _ent = EntitlementService.instance;
  String _appVersion = '';

  @override
  void initState() {
    super.initState();
    _loadVersion();
    _ent.addListener(_onEntChanged);
  }

  @override
  void dispose() {
    _ent.removeListener(_onEntChanged);
    super.dispose();
  }

  void _onEntChanged() {
    if (mounted) setState(() {});
  }

  Future<void> _loadVersion() async {
    final info = await PackageInfo.fromPlatform();
    if (!mounted) return;
    setState(() => _appVersion = '${info.version} (${info.buildNumber})');
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('設定')),
      body: SafeArea(
        child: ListView(
          children: [
            _sectionHeader('ルール'),
            // シングル＋メガのみ選択可（ダブル/Z技/ダイマは P4）。ラベルなしで一列表示。
            Padding(
              padding: const EdgeInsets.fromLTRB(16, 4, 16, 8),
              child: Wrap(
                spacing: 12,
                runSpacing: 8,
                crossAxisAlignment: WrapCrossAlignment.center,
                children: [
                  SegmentedButton<int>(
                    style: const ButtonStyle(
                        visualDensity: VisualDensity.compact),
                    segments: const [
                      ButtonSegment(value: 1, label: Text('シングル')),
                      ButtonSegment(
                          value: 2,
                          label: Text('ダブル'),
                          enabled: false), // P4
                    ],
                    selected: const {1},
                    onSelectionChanged: (_) {},
                  ),
                  // メガは固定でオン（Z技/ダイマは P4）。現状は常時反映。
                  const FilterChip(
                    label: Text('メガ'),
                    selected: true,
                    onSelected: null,
                  ),
                  const FilterChip(
                    label: Text('Z技'),
                    selected: false,
                    onSelected: null, // P4
                  ),
                  const FilterChip(
                    label: Text('ダイマックス'),
                    selected: false,
                    onSelected: null, // P4
                  ),
                ],
              ),
            ),
            const Divider(height: 1),
            // クラウドアカウントはフル機能（解放済みのみ表示）。
            if (_ent.unlocked)
              ListTile(
                dense: true,
                visualDensity: VisualDensity.compact,
                title: const Text('クラウドアカウント'),
                trailing: const Icon(Icons.chevron_right),
                onTap: () => Navigator.of(context).push(
                  MaterialPageRoute(
                      builder: (_) => const CloudAccountScreen()),
                ),
              ),
            // HOMEデータ更新はバトルデータ（フル機能）に関わるため解放済みのみ。
            if (_ent.unlocked)
              ListTile(
                dense: true,
                visualDensity: VisualDensity.compact,
                title: const Text('HOMEデータを更新'),
                trailing: _refreshing
                    ? const SizedBox(
                        width: 18,
                        height: 18,
                        child: CircularProgressIndicator(strokeWidth: 2))
                    : const Icon(Icons.cloud_download_outlined),
                onTap: _refreshing ? null : _refreshRefData,
              ),
            const Divider(height: 1),
            _sectionHeader('アプリ情報'),
            ListTile(
              dense: true,
              visualDensity: VisualDensity.compact,
              title: const Text('ChampEdge'),
              subtitle: const Text('非公式ファンメイドツール'),
              trailing: Text(
                _appVersion.isEmpty ? '—' : 'バージョン $_appVersion',
                style: const TextStyle(fontSize: 12, color: Colors.black54),
              ),
            ),
            // 控えめなフル機能の導線（解放済みは状態表示）。一般ユーザーには
            // 目立たせず、コードを持つ人・購入したい人だけがここから解放する。
            ListTile(
              dense: true,
              visualDensity: VisualDensity.compact,
              leading: Icon(
                _ent.unlocked ? Icons.verified : Icons.lock_open_outlined,
                size: 18,
                color: _ent.unlocked ? Colors.indigo : Colors.black45,
              ),
              title: Text(_ent.unlocked ? 'フル機能：有効' : 'フル機能 / コードをお持ちの方'),
              trailing: const Icon(Icons.chevron_right, size: 18),
              onTap: () => showUnlockSheet(context),
            ),
          ],
        ),
      ),
    );
  }

  bool _refreshing = false;

  Future<void> _refreshRefData() async {
    setState(() => _refreshing = true);
    await RefData.instance.refreshAll(force: true);
    if (!mounted) return;
    setState(() => _refreshing = false);
    ScaffoldMessenger.of(context).showSnackBar(const SnackBar(
        duration: Duration(milliseconds: 1500),
        content: Text('参照データを更新しました（反映は次回起動時）')));
  }

  Widget _sectionHeader(String label) => Padding(
        padding: const EdgeInsets.fromLTRB(16, 12, 16, 4),
        child: Text(label,
            style: const TextStyle(
                fontSize: 12,
                fontWeight: FontWeight.bold,
                color: Colors.indigo)),
      );
}
