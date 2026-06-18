import 'dart:convert';
import 'dart:io';

import 'package:flutter/foundation.dart';
import 'package:path/path.dart' as p;
import 'package:path_provider/path_provider.dart';

import '../model/battle_pokemon.dart';

/// 保存パーティ1件（番号/連番/タイトル/パーティメモ＋6体）。
class SavedParty {
  SavedParty({
    required this.id,
    required this.num,
    required this.subnum,
    required this.title,
    required this.memo,
    required this.party,
    required this.modified,
  });

  final String id;
  final String num;
  final String subnum;
  final String title;
  final String memo;
  final List<BattlePokemon> party;

  /// 保存（登録）日時。一覧の既定ソート（登録日降順）に使う。
  final DateTime modified;

  /// 表示用ラベル（例「3-1 雨パ」）。番号が無ければタイトルのみ。
  String get label {
    final n = [num, subnum].where((e) => e.isNotEmpty).join('-');
    return [if (n.isNotEmpty) n, if (title.isNotEmpty) title].join(' ').trim();
  }
}

/// パーティの永続化（JSON）。旧 champ-edge の CSV 保存（`party/csv/*.csv`）に相当する
/// 機能をモバイル向けに JSON で実装する。
///
/// - 名前付き保存パーティ: `parties/saved/{title}.json`（一覧・読込・削除）
/// - 直近セッションの自動復元: `parties/last_my.json` / `parties/last_opp.json`
///   （旧アプリの「使用中」パーティに相当。次回起動時にそのまま復元する）
class PartyStore {
  PartyStore._();
  static final PartyStore instance = PartyStore._();

  Future<Directory> _dir(String sub) async {
    final base = await getApplicationDocumentsDirectory();
    final dir = Directory(p.join(base.path, 'parties', sub));
    if (!await dir.exists()) await dir.create(recursive: true);
    return dir;
  }

  Future<File> _file(String sub, String name) async =>
      File(p.join((await _dir(sub)).path, name));

  List<Map<String, dynamic>> _encode(List<BattlePokemon> party) =>
      [for (final p in party) p.toJson()];

  List<BattlePokemon> _decode(List<dynamic> list) =>
      [for (final j in list) BattlePokemon.fromJson(j as Map<String, dynamic>)];

  // --- 名前付き保存パーティ（番号/連番/タイトル/パーティメモ＋6体）---

  /// 保存済みパーティ一覧（番号→連番→タイトルの昇順）。旧形式 `{title, pokemons}` も読む。
  Future<List<SavedParty>> listSavedParties() async {
    final dir = await _dir('saved');
    final files = dir
        .listSync()
        .whereType<File>()
        .where((f) => f.path.endsWith('.json'))
        .toList();
    final list = <SavedParty>[];
    for (final f in files) {
      try {
        final j = jsonDecode(await f.readAsString()) as Map<String, dynamic>;
        list.add(SavedParty(
          id: p.basenameWithoutExtension(f.path),
          num: (j['num'] as String?) ?? '',
          subnum: (j['subnum'] as String?) ?? '',
          title: (j['title'] as String?) ?? '',
          memo: (j['memo'] as String?) ?? '',
          party: _decode((j['pokemons'] as List?) ?? const []),
          modified: f.statSync().modified,
        ));
      } catch (e) {
        debugPrint('[PartyStore] skip broken saved: ${f.path} ($e)');
      }
    }
    // 既定は登録日降順（新しい順）。画面側で番号順にも切り替えられる。
    list.sort((a, b) => b.modified.compareTo(a.modified));
    return list;
  }

  /// 保存パーティを書き込む（id 省略でタイムスタンプ採番＝新規）。id を返す。
  Future<String> savePartyEntry({
    String? id,
    required String num,
    required String subnum,
    required String title,
    required String memo,
    required List<BattlePokemon> party,
  }) async {
    final eid = id ?? 'p${DateTime.now().millisecondsSinceEpoch}';
    final f = await _file('saved', '$eid.json');
    await f.writeAsString(jsonEncode({
      'num': num,
      'subnum': subnum,
      'title': title,
      'memo': memo,
      'pokemons': _encode(party),
    }));
    debugPrint('[PartyStore] saved party: ${f.path}');
    return eid;
  }

  Future<void> deletePartyEntry(String id) async {
    final f = await _file('saved', '$id.json');
    if (await f.exists()) await f.delete();
    if (await loadUsingPartyId() == id) await saveUsingPartyId('');
  }

  /// 使用中パーティの id（旧 champ-edge の「使用パーティ」。1つだけ）。
  Future<void> saveUsingPartyId(String id) async {
    final f = await _file('', 'using_party.json');
    await f.writeAsString(jsonEncode({'id': id}));
  }

  Future<String?> loadUsingPartyId() async {
    final f = await _file('', 'using_party.json');
    if (!await f.exists()) return null;
    try {
      final j = jsonDecode(await f.readAsString()) as Map<String, dynamic>;
      final id = (j['id'] as String?) ?? '';
      return id.isEmpty ? null : id;
    } catch (e) {
      return null;
    }
  }

  // --- ボックス（個別ポケモンの保管庫）---

  /// ボックスの全ポケモン（新しい順）。各要素は (id, pokemon)。
  Future<List<({String id, BattlePokemon pokemon})>> listBox() async {
    final dir = await _dir('box');
    final files = dir
        .listSync()
        .whereType<File>()
        .where((f) => f.path.endsWith('.json'))
        .toList()
      ..sort((a, b) =>
          b.statSync().modified.compareTo(a.statSync().modified));
    final out = <({String id, BattlePokemon pokemon})>[];
    for (final f in files) {
      try {
        final j = jsonDecode(await f.readAsString()) as Map<String, dynamic>;
        out.add((
          id: p.basenameWithoutExtension(f.path),
          pokemon: BattlePokemon.fromJson(j),
        ));
      } catch (e) {
        debugPrint('[PartyStore] skip broken box: ${f.path} ($e)');
      }
    }
    return out;
  }

  /// ボックスへポケモンを保存（id 省略で新規採番）。id を返す。
  Future<String> saveBoxPokemon(BattlePokemon pokemon, {String? id}) async {
    final eid = id ?? 'b${DateTime.now().millisecondsSinceEpoch}';
    final f = await _file('box', '$eid.json');
    await f.writeAsString(jsonEncode(pokemon.toJson()));
    return eid;
  }

  Future<void> deleteBoxPokemon(String id) async {
    final f = await _file('box', '$id.json');
    if (await f.exists()) await f.delete();
  }

  // --- 直近セッションの自動保存／復元 ---

  Future<void> saveLast(String side, List<BattlePokemon> party) async {
    final f = await _file('', 'last_$side.json');
    await f.writeAsString(jsonEncode(_encode(party)));
  }

  Future<List<BattlePokemon>?> loadLast(String side) async {
    final f = await _file('', 'last_$side.json');
    if (!await f.exists()) return null;
    try {
      final list = jsonDecode(await f.readAsString()) as List;
      final party = _decode(list);
      return party.isEmpty ? null : party;
    } catch (e) {
      debugPrint('[PartyStore] loadLast($side) failed: $e');
      return null;
    }
  }

  // --- 自分パーティの識別（番号/連番/タイトル。対戦記録の絞り込みキー）---

  Future<void> saveMyPartyMeta(String num, String subnum, String title) async {
    final f = await _file('', 'party_meta.json');
    await f.writeAsString(
        jsonEncode({'num': num, 'subnum': subnum, 'title': title}));
  }

  /// (num, subnum, title) を返す。無ければ null。
  Future<(String, String, String)?> loadMyPartyMeta() async {
    final f = await _file('', 'party_meta.json');
    if (!await f.exists()) return null;
    try {
      final j = jsonDecode(await f.readAsString()) as Map<String, dynamic>;
      return ((j['num'] as String?) ?? '', (j['subnum'] as String?) ?? '',
          (j['title'] as String?) ?? '');
    } catch (e) {
      debugPrint('[PartyStore] loadMyPartyMeta failed: $e');
      return null;
    }
  }

  // --- カウンタ（PP管理等。対戦記録や明示リセットまで保持）---

  Future<void> saveCounters(List<int> values, List<String> titles) async {
    final f = await _file('', 'counters.json');
    await f.writeAsString(jsonEncode({'values': values, 'titles': titles}));
  }

  /// (values, titles) を返す。無ければ null。
  Future<(List<int>, List<String>)?> loadCounters() async {
    final f = await _file('', 'counters.json');
    if (!await f.exists()) return null;
    try {
      final j = jsonDecode(await f.readAsString()) as Map<String, dynamic>;
      final values = [for (final v in (j['values'] as List)) (v as num).toInt()];
      final titles = [for (final t in (j['titles'] as List)) t as String];
      return (values, titles);
    } catch (e) {
      debugPrint('[PartyStore] loadCounters failed: $e');
      return null;
    }
  }
}
