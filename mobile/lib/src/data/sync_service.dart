import 'dart:convert';
import 'dart:io';

import 'package:path/path.dart' as p;
import 'package:path_provider/path_provider.dart';

import 'app_settings.dart';
import 'battle_db.dart';
import 'drive_sync.dart';

/// 端末のユーザーデータ（対戦記録・パーティ/ボックス・設定）を1つのスナップショット
/// JSON にまとめ、本人の Google Drive（appDataFolder）へバックアップ/復元する。
///
/// 方針：基本はローカル保存。これは任意の「バックアップ／機種変更引き継ぎ」機能。
/// 対象ファイル（Documents 配下の相対パス）：
///   - app_settings.json（設定）
///   - battle.db（対戦記録・構築記事）
///   - parties/**（保存パーティ・ボックス・使用中・直近・メタ）
/// 参照データ（pokemon.db・ref_cache）や認証キャッシュは対象外。
class SyncService {
  SyncService._();
  static final SyncService instance = SyncService._();

  static const _topLevelTargets = ['app_settings.json', 'battle.db'];
  static const _dirTargets = ['parties'];

  Future<Directory> _docs() => getApplicationDocumentsDirectory();

  /// 現在の端末データからスナップショット JSON を生成。
  Future<String> buildSnapshot() async {
    final dir = await _docs();
    final files = <String, String>{};
    for (final rel in _topLevelTargets) {
      final f = File(p.join(dir.path, rel));
      if (await f.exists()) files[rel] = base64Encode(await f.readAsBytes());
    }
    for (final sub in _dirTargets) {
      final d = Directory(p.join(dir.path, sub));
      if (!await d.exists()) continue;
      await for (final e in d.list(recursive: true, followLinks: false)) {
        if (e is File) {
          final rel = p.relative(e.path, from: dir.path);
          files[rel] = base64Encode(await e.readAsBytes());
        }
      }
    }
    return jsonEncode({
      'version': 1,
      'updatedAt': DateTime.now().toIso8601String(),
      'files': files,
    });
  }

  /// スナップショット JSON を端末へ適用（上書き復元）。
  /// battle.db は閉じてから上書きし、再オープン。設定も再読込する。
  Future<void> applySnapshot(String json) async {
    final m = jsonDecode(json) as Map<String, dynamic>;
    final files = (m['files'] as Map).cast<String, dynamic>();
    final dir = await _docs();

    await BattleDb.instance.close();
    for (final entry in files.entries) {
      final f = File(p.join(dir.path, entry.key));
      await f.parent.create(recursive: true);
      await f.writeAsBytes(base64Decode(entry.value as String));
    }
    await BattleDb.instance.open();
    await AppSettings.instance.reload();
  }

  /// 端末データを Drive へバックアップ。
  Future<void> backupToDrive() async {
    final snapshot = await buildSnapshot();
    await DriveSync.instance.upload(snapshot);
  }

  /// Drive から復元（バックアップが無ければ false）。
  Future<bool> restoreFromDrive() async {
    final json = await DriveSync.instance.download();
    if (json == null) return false;
    await applySnapshot(json);
    return true;
  }
}
