import 'dart:convert';
import 'dart:io';

import 'package:flutter/foundation.dart';
import 'package:path/path.dart' as p;
import 'package:path_provider/path_provider.dart';

/// アプリ設定の永続化（旧 champ-edge の recog/setting.json 相当の最小版）。
/// 現状はローカル JSON。将来クラウド同期に載せ替え可能。
class AppSettings {
  AppSettings._();
  static final AppSettings instance = AppSettings._();

  // --- ルール（現状シングル＋メガのみ。ダブル/Z/ダイマは P4 で選択不可）---
  /// 対戦ルール（1=シングル固定。2=ダブルは P4）。
  final int rule = 1;

  /// メガシンカをダメージ計算/フォルムに反映（現状は常時 ON・選択可）。
  bool megaEnabled = true;

  // --- 動作モード ---
  /// 類似パーティ自動検索（相手パーティ確定時に自動実行）。既定 OFF。
  bool autoSimilarSearch = false;

  /// 相手選出の自動登録（相手を選ぶと選出にも自動登録）。常時 ON（変更不可）。
  bool get autoRegisterOpponentChoice => true;

  /// 相手の性格変更時に努力値を自動調整。常時 OFF（未実装・変更不可）。
  bool get autoEvOnNatureChange => false;

  bool _loaded = false;

  Future<File> _file() async {
    final dir = await getApplicationDocumentsDirectory();
    return File(p.join(dir.path, 'app_settings.json'));
  }

  /// クラウド復元後などに強制再読込する。
  Future<void> reload() async {
    _loaded = false;
    await load();
  }

  Future<void> load() async {
    if (_loaded) return;
    try {
      final f = await _file();
      if (await f.exists()) {
        final j = jsonDecode(await f.readAsString()) as Map<String, dynamic>;
        megaEnabled = j['megaEnabled'] as bool? ?? true;
        autoSimilarSearch = j['autoSimilarSearch'] as bool? ?? false;
      }
    } catch (e) {
      debugPrint('[AppSettings] load failed: $e');
    }
    _loaded = true;
  }

  Future<void> save() async {
    try {
      final f = await _file();
      await f.writeAsString(jsonEncode({
        'megaEnabled': megaEnabled,
        'autoSimilarSearch': autoSimilarSearch,
      }));
    } catch (e) {
      debugPrint('[AppSettings] save failed: $e');
    }
  }
}
