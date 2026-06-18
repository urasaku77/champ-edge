import 'package:flutter/foundation.dart';
import 'package:path/path.dart';
import 'package:path_provider/path_provider.dart';
import 'package:sqflite/sqflite.dart';

import '../model/battle_record.dart';

/// 対戦記録の書き込み可能 DB（旧 champ-edge database/battle.db の移植）。
///
/// pokemon.db は読み取り専用アセットのため、対戦記録は別途
/// アプリのドキュメント領域に `battle.db` を作成して読み書きする。
class BattleDb {
  BattleDb._();
  static final BattleDb instance = BattleDb._();

  Database? _db;
  bool get isOpen => _db != null;

  static const String _createSql = '''
    CREATE TABLE IF NOT EXISTS battle (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      date INTEGER, rule INTEGER, result INTEGER, favorite INTEGER,
      opponent_tn TEXT, opponent_rate TEXT, battle_memo TEXT,
      player_party_num TEXT, player_party_subnum TEXT,
      player_pokemon1 TEXT, player_pokemon2 TEXT, player_pokemon3 TEXT,
      player_pokemon4 TEXT, player_pokemon5 TEXT, player_pokemon6 TEXT,
      opponent_pokemon1 TEXT, opponent_pokemon2 TEXT, opponent_pokemon3 TEXT,
      opponent_pokemon4 TEXT, opponent_pokemon5 TEXT, opponent_pokemon6 TEXT,
      player_choice1 TEXT, player_choice2 TEXT, player_choice3 TEXT, player_choice4 TEXT,
      opponent_choice1 TEXT, opponent_choice2 TEXT, opponent_choice3 TEXT, opponent_choice4 TEXT
    )
  ''';

  /// 構築記事（類似パーティ検索用。将来はサーバー集約データで投入）。
  static const String _createKouseiSql = '''
    CREATE TABLE IF NOT EXISTS kousei (
      id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT, url TEXT,
      pokemon1 TEXT, pokemon2 TEXT, pokemon3 TEXT,
      pokemon4 TEXT, pokemon5 TEXT, pokemon6 TEXT
    )
  ''';

  Future<bool> open() async {
    if (_db != null) return true;
    try {
      final dir = await getApplicationDocumentsDirectory();
      final path = join(dir.path, 'battle.db');
      _db = await openDatabase(path, version: 1,
          onCreate: (db, _) async => db.execute(_createSql));
      // 既存DBにテーブルが無い場合に備える。
      await _db!.execute(_createSql);
      await _db!.execute(_createKouseiSql);
      // 旧バージョンが入れたサンプル構築記事（プレースホルダ url=example.com）を除去。
      await _db!.delete('kousei', where: "url LIKE '%example.com%'");
      debugPrint('[BattleDb] opened: $path');
      return true;
    } catch (e) {
      debugPrint('[BattleDb] open failed: $e');
      return false;
    }
  }

  /// DB を閉じる（クラウド復元で battle.db を上書きする前に呼ぶ）。
  Future<void> close() async {
    await _db?.close();
    _db = null;
  }

  /// 全記録（直近順）。類似パーティ検索の対戦履歴照合用。
  Future<List<BattleRecord>> allRecords() async {
    if (_db == null) return const [];
    final rows = await _db!.rawQuery('SELECT * FROM battle ORDER BY date DESC');
    return [for (final r in rows) BattleRecord.fromRow(r)];
  }

  /// 構築記事を1件追加（pokemons は6枠、空は '-1'）。
  Future<int> addKousei(String title, String url, List<String> pokemons) async {
    if (_db == null) return -1;
    return _db!.insert('kousei', {
      'title': title,
      'url': url,
      for (var i = 0; i < 6; i++) 'pokemon${i + 1}': pokemons[i],
    });
  }

  /// 全構築記事。返り値は (title, url, 6体pid)。
  Future<List<({String title, String url, List<String> pokemons})>>
      allKousei() async {
    if (_db == null) return const [];
    final rows = await _db!.rawQuery('SELECT * FROM kousei ORDER BY id DESC');
    return [
      for (final r in rows)
        (
          title: (r['title'] as String?) ?? '',
          url: (r['url'] as String?) ?? '',
          pokemons: [
            for (var i = 1; i <= 6; i++) (r['pokemon$i'] as String?) ?? '-1'
          ],
        ),
    ];
  }

  Future<int> register(BattleRecord b) async {
    if (_db == null) return -1;
    return _db!.insert('battle', b.toColumns());
  }

  Future<void> updateFull(int id, BattleRecord b) async {
    if (_db == null) return;
    await _db!.update('battle', b.toColumns(), where: 'id = ?', whereArgs: [id]);
  }

  Future<void> deleteById(int id) async {
    if (_db == null) return;
    await _db!.delete('battle', where: 'id = ?', whereArgs: [id]);
  }

  /// 期間・ルール・パーティ番号・相手伝説(KP)・キーワードで絞り込み、日時降順で返す。
  Future<List<BattleRecord>> query({
    required int fromDate,
    required int toDate,
    int rule = 1,
    String partyNum = '',
    String partySubnum = '',
    String regendNum = '0',
    String keyword = '',
    bool favoriteOnly = false,
    bool ascending = false,
  }) async {
    if (_db == null) return const [];
    final (where, params) = _baseWhere(
        fromDate, toDate, rule, partyNum, partySubnum, regendNum, keyword,
        favoriteOnly: favoriteOnly);
    final rows = await _db!.rawQuery(
      'SELECT * FROM battle WHERE $where ORDER BY date ${ascending ? 'ASC' : 'DESC'}',
      params,
    );
    return [for (final r in rows) BattleRecord.fromRow(r)];
  }

  /// 範囲削除（履歴画面の「この範囲を全削除」）。
  Future<void> deleteByQuery({
    required int fromDate,
    required int toDate,
    int rule = 1,
    String partyNum = '',
    String partySubnum = '',
    String regendNum = '0',
    String keyword = '',
    bool favoriteOnly = false,
  }) async {
    if (_db == null) return;
    final (where, params) = _baseWhere(
        fromDate, toDate, rule, partyNum, partySubnum, regendNum, keyword,
        favoriteOnly: favoriteOnly);
    await _db!.rawDelete('DELETE FROM battle WHERE $where', params);
  }

  /// 共通 WHERE 句（旧 _build_base_where 相当）。
  (String, List<Object?>) _baseWhere(int fromDate, int toDate, int rule,
      String partyNum, String partySubnum, String regendNum, String keyword,
      {bool favoriteOnly = false}) {
    final parts = <String>['date >= ?', 'date <= ?', 'rule = ?'];
    final params = <Object?>[fromDate, toDate, rule];
    if (partyNum.isNotEmpty && partyNum != '0') {
      parts.add('player_party_num = ?');
      params.add(partyNum);
    }
    if (partySubnum.isNotEmpty && partySubnum != '0') {
      parts.add('player_party_subnum = ?');
      params.add(partySubnum);
    }
    if (regendNum != '0' && regendNum.isNotEmpty) {
      parts.add('(${[for (var i = 1; i <= 6; i++) 'opponent_pokemon$i = ?'].join(' OR ')})');
      params.addAll([for (var i = 0; i < 6; i++) regendNum]);
    }
    if (favoriteOnly) parts.add('favorite = 1');
    if (keyword.isNotEmpty) {
      parts.add('(opponent_tn LIKE ? OR battle_memo LIKE ?)');
      params..add('%$keyword%')..add('%$keyword%');
    }
    return (parts.join(' AND '), params);
  }

  /// 直近の記録日時（epoch 秒）。無ければ null。
  Future<int?> recentDate() async {
    if (_db == null) return null;
    final r = await _db!.rawQuery('SELECT MAX(date) AS m FROM battle');
    return r.first['m'] as int?;
  }

  Future<int> totalCount() async {
    if (_db == null) return 0;
    final r = await _db!.rawQuery('SELECT COUNT(*) AS c FROM battle');
    return (r.first['c'] as int?) ?? 0;
  }
}
