import 'dart:io';

import 'package:flutter/foundation.dart';
import 'package:flutter/services.dart';
import 'package:path/path.dart';
import 'package:path_provider/path_provider.dart';
import 'package:sqflite/sqflite.dart';

import '../model/battle_pokemon.dart';
import '../service/damage_engine.dart';
import 'available_pokemon.dart';
import 'form_data.dart';

/// パーティ選択から除外するポケモン（旧 exception.remove_pokemon_name_from_party）。
const Set<String> _excludedFromParty = {
  'ヒヒダルマ(ダルマ)',
  'ヒヒダルマ(ダルマ・ガラル)',
  'ジガルデ(パーフェクト)',
  'ヨワシ(群れ)',
  'メロエッタ(ステップ)',
  'ギルガルド(ブレード)',
  'イルカマン(マイティ)',
  'テラパゴス(テラスタル)',
  'テラパゴス(ステラ)',
  'サトシゲッコウガ',
};

/// `pokemon.db`（旧 champ-edge の SQLite）への読み取りアクセス層。
///
/// asset の DB を書き込み可能領域へコピーして readOnly で開く。
/// 技（waza_data）・持ち物（item_data）・ポケモン（pokemon_data）を参照する。
class PokeDb {
  PokeDb._();
  static final PokeDb instance = PokeDb._();

  static const String _assetPath = 'assets/data/pokemon.db';
  static const String _dbFileName = 'pokemon.db';

  Database? _db;
  bool get isOpen => _db != null;

  /// ひらがな→カタカナ（DB のポケモン名はカタカナのため、検索入力を変換する）。
  static String _toKatakana(String s) {
    final buf = StringBuffer();
    for (final r in s.runes) {
      // ひらがな U+3041–U+3096 → カタカナ (+0x60)
      buf.writeCharCode((r >= 0x3041 && r <= 0x3096) ? r + 0x60 : r);
    }
    return buf.toString();
  }

  /// カタカナ→ひらがな（DB の技名はひらがなのため、検索入力を変換する）。
  static String _toHiragana(String s) {
    final buf = StringBuffer();
    for (final r in s.runes) {
      // カタカナ U+30A1–U+30F6 → ひらがな (-0x60)
      buf.writeCharCode((r >= 0x30A1 && r <= 0x30F6) ? r - 0x60 : r);
    }
    return buf.toString();
  }

  /// DB を開く。成功可否を返す（プラグイン未統合などで失敗したら false）。
  Future<bool> open() async {
    if (_db != null) return true;
    try {
      final dir = await getApplicationDocumentsDirectory();
      final dbFile = File(join(dir.path, _dbFileName));
      // バンドル(アセット)の DB を端末へコピーする。pokemon.db は参照専用データ
      // （ポケモン/技/特性/道具）でユーザーデータを含まないため、アプリ更新で
      // 同梱 DB が変わったら端末側を上書き更新する。旧実装は「ファイルが無い時
      // だけコピー」で、初回起動時の DB が更新されず新ポケモン・新メガ（例:
      // メガメタグロス 0376-11）が反映されなかった。
      //
      // 更新判定は「アセットの実バイト長」を別マーカーファイル(.len)へ記録して比較する。
      // コピー済み DB ファイルのサイズではなく **アセット側の実長(data.lengthInBytes)** を
      // 基準にするのが要点。`data.buffer.asUint8List()` の長さは基盤バッファ長で実アセット
      // 長と一致しないことがあり、それで比較すると更新を取りこぼす（build15 で再コピーが
      // 走らなかった原因）。マーカーが無い既存ユーザーは必ず再コピーされる。
      final data = await rootBundle.load(_assetPath);
      final assetLen = data.lengthInBytes;
      final lenFile = File('${dbFile.path}.len');
      int? installedLen;
      if (await lenFile.exists()) {
        installedLen = int.tryParse((await lenFile.readAsString()).trim());
      }
      final needsCopy = !await dbFile.exists() || installedLen != assetLen;
      if (needsCopy) {
        // 旧 DB を開いたままにしないよう、コピー前に念のため閉じておく。
        await _db?.close();
        _db = null;
        // バッファ全体ではなくアセットの実バイト範囲だけを書き出す。
        final bytes =
            data.buffer.asUint8List(data.offsetInBytes, data.lengthInBytes);
        await dbFile.writeAsBytes(bytes, flush: true);
        await lenFile.writeAsString('$assetLen');
        debugPrint('[PokeDb] bundled DB copied ($assetLen bytes)');
      }
      _db = await openDatabase(dbFile.path, readOnly: true);
      debugPrint('[PokeDb] opened: ${dbFile.path}');
      return true;
    } catch (e) {
      debugPrint('[PokeDb] open failed: $e');
      return false;
    }
  }

  /// ポケモン総数（疎通確認用）。
  Future<int> pokemonCount() async {
    final r = await _db!.rawQuery('SELECT COUNT(*) AS c FROM pokemon_data');
    return (r.first['c'] as int?) ?? 0;
  }

  /// 技を名前の部分一致で検索（waza_data）。技名はひらがな格納のため、
  /// 生入力とカタカナ→ひらがな変換の両方でマッチさせる（例: みずびたし／ミズビタシ）。
  Future<List<BattleMove>> searchMoves(String query, {int limit = 60}) async {
    if (_db == null) return const [];
    final rows = await _db!.rawQuery(
      'SELECT name, type, category, power FROM waza_data '
      'WHERE name LIKE ? OR name LIKE ? ORDER BY power DESC, name LIMIT ?',
      ['%$query%', '%${_toHiragana(query)}%', limit],
    );
    return rows.map(_rowToMove).toList();
  }

  /// 技を完全名で取得。
  Future<BattleMove?> moveByName(String name) async {
    if (_db == null) return null;
    final rows = await _db!.rawQuery(
      'SELECT name, type, category, power FROM waza_data WHERE name = ? LIMIT 1',
      [name],
    );
    if (rows.isEmpty) return null;
    return _rowToMove(rows.first);
  }

  BattleMove _rowToMove(Map<String, Object?> r) => BattleMove(
        name: r['name'] as String,
        type: PokeType.fromJp((r['type'] as String?) ?? 'なし'),
        category: MoveCategory.fromJp((r['category'] as String?) ?? '変化'),
        power: (r['power'] as int?) ?? 0,
      );

  /// 技の詳細（waza_data 全列：type/category/power/hit/pp/is_touch/is_guard/
  /// target/description）。無ければ null。
  Future<Map<String, Object?>?> moveDetail(String name) async {
    if (_db == null) return null;
    final rows = await _db!.rawQuery(
      'SELECT * FROM waza_data WHERE name = ? LIMIT 1',
      [name],
    );
    return rows.isEmpty ? null : rows.first;
  }

  /// 持ち物名一覧（item_data）。先頭に「なし」を付ける。
  Future<List<String>> itemNames() async {
    if (_db == null) return const ['なし'];
    final rows =
        await _db!.rawQuery('SELECT item_name FROM item_data ORDER BY item_id');
    return ['なし', ...rows.map((r) => r['item_name'] as String)];
  }

  /// 自パーティOCRの照合辞書用。画像のある通常フォーム（メガ除く）の (name, pid)。
  /// 能力タブ写真から読んだ名前をこの一覧へ曖昧一致させて pid を確定する。
  Future<List<({String name, String pid})>> allPokemonNamesWithPid() async {
    if (_db == null) return const [];
    final rows = await _db!.rawQuery(
      "SELECT no, form, name FROM pokemon_data "
      "WHERE (name NOT LIKE 'メガ%' OR name = 'メガニウム') ORDER BY no, form",
    );
    final out = <({String name, String pid})>[];
    for (final r in rows) {
      final pid = '${(r['no'] as int).toString().padLeft(4, '0')}-${r['form']}';
      if (!availablePokemonPids.contains(pid)) continue;
      out.add((name: r['name'] as String, pid: pid));
    }
    return out;
  }

  /// 全特性名（重複排除）。OCRの特性曖昧一致用。
  Future<List<String>> allAbilityNames() async {
    if (_db == null) return const [];
    final rows = await _db!
        .rawQuery('SELECT ability_name FROM ability_data ORDER BY ability_id');
    return [for (final r in rows) (r['ability_name'] as String).trim()]
        .where((s) => s.isNotEmpty)
        .toList();
  }

  /// 全技名。OCRの技曖昧一致用。
  Future<List<String>> allWazaNames() async {
    if (_db == null) return const [];
    final rows = await _db!.rawQuery('SELECT name FROM waza_data');
    return [for (final r in rows) r['name'] as String];
  }

  /// pid → 種族値 [H,A,B,C,D,S]。自パOCRの努力値逆算（実数値→EV）に使う。
  Future<Map<String, List<int>>> allBaseStats() async {
    if (_db == null) return const {};
    final rows =
        await _db!.rawQuery('SELECT no, form, H, A, B, C, D, S FROM pokemon_data');
    final m = <String, List<int>>{};
    for (final r in rows) {
      final pid = '${(r['no'] as int).toString().padLeft(4, '0')}-${r['form']}';
      m[pid] = [
        r['H'] as int, r['A'] as int, r['B'] as int,
        r['C'] as int, r['D'] as int, r['S'] as int,
      ];
    }
    return m;
  }

  /// ポケモンを名前の部分一致で検索（pokemon_data）。(name, pid) を返す。
  ///
  /// 旧アプリと同様にメガシンカ（name LIKE 'メガ%'、メガニウム除く）と除外リストを外し、
  /// さらに**画像があるポケモンのみ**に限定する。
  ///
  /// 同名で複数フォルムが画像つきで存在する場合（例: ガラルヤドラン 80-1/80-2、
  /// ビビヨン 666-0/666-18）は**1件に集約**する。残すのは「フォーム番号が大きい方」＝
  /// バトルDB(ランキング/構築記事)が使うフォルム。類似パーティ照合は pid 直接比較なので、
  /// バトルDB側に揃えておくと一致が保たれる。
  Future<List<({String name, String pid})>> searchPokemon(String query,
      {int limit = 400, bool includeMega = false}) async {
    if (_db == null) return const [];
    // 対戦記録などメガ込みで選びたい場合は includeMega=true でメガ除外を外す。
    final megaClause =
        includeMega ? '' : "AND (name NOT LIKE 'メガ%' OR name = 'メガニウム') ";
    final rows = await _db!.rawQuery(
      "SELECT no, form, name FROM pokemon_data "
      "WHERE name LIKE ? $megaClause"
      "ORDER BY no, form",
      ['%${_toKatakana(query)}%'],
    );
    // name → 採用エントリ（同名はフォーム番号が大きい方を残す）。
    final byName = <String, ({String name, String pid, int no, int form})>{};
    for (final r in rows) {
      final name = r['name'] as String;
      final no = r['no'] as int;
      final form = r['form'] as int;
      final pid = '${no.toString().padLeft(4, '0')}-$form';
      if (_excludedFromParty.contains(name)) continue;
      if (!availablePokemonPids.contains(pid)) continue; // 画像があるもののみ
      final prev = byName[name];
      if (prev == null || form > prev.form) {
        byName[name] = (name: name, pid: pid, no: no, form: form);
      }
    }
    final entries = byName.values.toList()
      ..sort((a, b) => a.no != b.no ? a.no.compareTo(b.no) : a.form.compareTo(b.form));
    return [
      for (final e in entries.take(limit)) (name: e.name, pid: e.pid)
    ];
  }

  /// pid から BattlePokemon を構築（種族値・タイプ・特性・体重を DB から）。
  /// 性格まじめ・持ち物なし・努力値0・技は空スロット4つの初期状態で返す。
  Future<BattlePokemon?> buildPokemon(String pid) async {
    if (_db == null) return null;
    final parts = pid.split('-');
    final rows = await _db!.rawQuery(
      'SELECT name, H, A, B, C, D, S, type1, type2, ability1, ability2, '
      'ability3, weight FROM pokemon_data WHERE no = ? AND form = ? LIMIT 1',
      [int.parse(parts[0]), int.parse(parts[1])],
    );
    if (rows.isEmpty) return null;
    final r = rows.first;
    final abilities = [
      for (final k in ['ability1', 'ability2', 'ability3'])
        if ((r[k] as String?)?.trim().isNotEmpty ?? false) r[k] as String,
    ];
    final t2 = (r['type2'] as String?)?.trim() ?? '';
    return BattlePokemon(
      name: r['name'] as String,
      pid: pid,
      baseStats: [
        r['H'] as int,
        r['A'] as int,
        r['B'] as int,
        r['C'] as int,
        r['D'] as int,
        r['S'] as int,
      ],
      type1: PokeType.fromJp(r['type1'] as String),
      type2: t2.isEmpty ? PokeType.none : PokeType.fromJp(t2),
      abilityOptions: abilities.isEmpty ? const ['—'] : abilities,
      nature: 'まじめ',
      item: 'なし',
      weight: (r['weight'] as num?)?.toDouble() ?? 0.0,
      moves: List.generate(4, (_) => emptyMove()),
    );
  }

  /// 重さ（kg）。既存保存パーティ（weight 未保存）の補完用。
  Future<double?> weightOf(String pid) async {
    if (_db == null) return null;
    final parts = pid.split('-');
    final rows = await _db!.rawQuery(
      'SELECT weight FROM pokemon_data WHERE no = ? AND form = ? LIMIT 1',
      [int.parse(parts[0]), int.parse(parts[1])],
    );
    if (rows.isEmpty) return null;
    return (rows.first['weight'] as num?)?.toDouble();
  }

  /// 図鑑番号 no のメガシンカフォーム番号（10-19）を昇順で返す。
  Future<List<int>> megaFormsOf(int no) async {
    if (_db == null) return const [];
    final rows = await _db!.rawQuery(
      'SELECT form FROM pokemon_data WHERE no = ? AND form >= 10 AND form <= 19 '
      'ORDER BY form',
      [no],
    );
    return [for (final r in rows) r['form'] as int];
  }

  /// ベース pid（例 0445-0）のメガフォーム pid 一覧（画像があるもののみ）。
  Future<List<String>> megaPidsOf(String basePid) async {
    final no = int.tryParse(basePid.split('-').first) ?? 0;
    final forms = await megaFormsOf(no);
    final s = no.toString().padLeft(4, '0');
    return [
      for (final f in forms)
        if (availablePokemonPids.contains('$s-$f')) '$s-$f'
    ];
  }

  /// フォルム切替（メガシンカ含む）。**PC版 changeble_form_in_battle に定義された
  /// ポケモンのみ**変化する（地方フォルム＝ガラル/ヒスイ等やアルセウスのタイプ違いは
  /// バトル中に変わらないので対象外＝タップしても何も起きない）。種族値・タイプ・特性・
  /// 名前・画像を更新する（技・努力値・性格・持ち物・ランク等は維持）。
  Future<bool> formChange(BattlePokemon p) async {
    if (_db == null) return false;
    final no = p.dexNo;
    if (!kChangeableFormNos.contains(no)) return false;
    // バトル中フォルムチェンジ（ヒヒダルマ等の専用遷移）を優先、無ければメガ循環。
    int? next = nextBattleForm(no, p.formNo);
    if (next == null) {
      // メガ循環: 基本 → 11 → 12 → 基本。
      final megaForms = await megaFormsOf(no);
      if (megaForms.isEmpty) return false;
      if (!megaForms.contains(p.formNo)) {
        next = megaForms.first;
      } else {
        final idx = megaForms.indexOf(p.formNo);
        next = (idx + 1 < megaForms.length) ? megaForms[idx + 1] : p.baseForm;
      }
    }
    final rows = await _db!.rawQuery(
      'SELECT name, H, A, B, C, D, S, type1, type2, ability1, ability2, '
      'ability3, weight FROM pokemon_data WHERE no = ? AND form = ? LIMIT 1',
      [p.dexNo, next],
    );
    if (rows.isEmpty) return false;
    final r = rows.first;
    final abilities = [
      for (final k in ['ability1', 'ability2', 'ability3'])
        if ((r[k] as String?)?.trim().isNotEmpty ?? false) r[k] as String,
    ];
    final t2 = (r['type2'] as String?)?.trim() ?? '';
    p.name = r['name'] as String;
    p.pid = '${p.dexNo.toString().padLeft(4, '0')}-$next';
    p.baseStats = [
      r['H'] as int, r['A'] as int, r['B'] as int,
      r['C'] as int, r['D'] as int, r['S'] as int,
    ];
    p.type1 = PokeType.fromJp(r['type1'] as String);
    p.type2 = t2.isEmpty ? PokeType.none : PokeType.fromJp(t2);
    p.abilityOptions = abilities.isEmpty ? const ['—'] : abilities;
    p.ability = p.abilityOptions.first;
    p.weight = (r['weight'] as num?)?.toDouble() ?? 0.0;
    return true;
  }

  /// 特性の効果説明（ability_data.effect）。無ければ null。
  Future<String?> abilityEffect(String name) async {
    if (_db == null) return null;
    final rows = await _db!.rawQuery(
      'SELECT effect FROM ability_data WHERE ability_name = ? LIMIT 1',
      [name],
    );
    if (rows.isEmpty) return null;
    return (rows.first['effect'] as String?)?.trim();
  }

  /// 持ち物の効果説明（item_data.effect）。無ければ null。
  Future<String?> itemEffect(String name) async {
    if (_db == null) return null;
    final rows = await _db!.rawQuery(
      'SELECT effect FROM item_data WHERE item_name = ? LIMIT 1',
      [name],
    );
    if (rows.isEmpty) return null;
    return (rows.first['effect'] as String?)?.trim();
  }

  /// ポケモンの特性候補（pokemon_data ability1/2/3）。
  Future<List<String>> abilitiesOf(String pid) async {
    if (_db == null) return const [];
    final parts = pid.split('-');
    final rows = await _db!.rawQuery(
      'SELECT ability1, ability2, ability3 FROM pokemon_data '
      'WHERE no = ? AND form = ? LIMIT 1',
      [int.parse(parts[0]), int.parse(parts[1])],
    );
    if (rows.isEmpty) return const [];
    final r = rows.first;
    return [
      for (final k in ['ability1', 'ability2', 'ability3'])
        if ((r[k] as String?)?.trim().isNotEmpty ?? false) r[k] as String,
    ];
  }
}
