import 'dart:convert';

import 'package:flutter/foundation.dart';

import 'ref_data.dart';

/// HOME（pokedb.tokyo 集計）使用率データのカテゴリ。
/// 旧 champ-edge の `stats/home_*.csv` をモバイル用にアセット同梱して読む。
enum HomeCategory {
  waza('わざ', 'assets/data/home/home_waza.csv'),
  item('もちもの', 'assets/data/home/home_motimono.csv'),
  ability('とくせい', 'assets/data/home/home_tokusei.csv'),
  nature('せいかく', 'assets/data/home/home_seikaku.csv'),
  ev('どりょくち', 'assets/data/home/home_doryoku.csv');

  const HomeCategory(this.label, this.asset);
  final String label;
  final String asset;
}

/// HOME 使用率の1エントリ（値＋使用率%）。
class HomeEntry {
  const HomeEntry(this.value, this.pct);
  final String value;
  final double pct;
}

/// HOME 使用率データの読み取り層。アプリ実行時は同梱 CSV を読むだけ
/// （旧アプリ `pokedata.loader.get_home_data` 相当）。スクレイプ更新は対象外。
class HomeStats {
  HomeStats._();
  static final HomeStats instance = HomeStats._();

  /// フォーム名を基本形へ正規化する対象（旧 `exception.base_names`）。
  static const List<String> _baseNames = [
    'メロエッタ',
    'イルカマン',
    'イッカネズミ',
    'オーガポン',
    'テラパゴス',
  ];

  /// category -> (pokemon名 -> エントリ一覧)。
  final Map<HomeCategory, Map<String, List<HomeEntry>>> _data = {};
  bool _loaded = false;
  bool get isLoaded => _loaded;

  Future<void> load() async {
    if (_loaded) return;
    for (final cat in HomeCategory.values) {
      final map = <String, List<HomeEntry>>{};
      try {
        final text = await RefData.instance.loadString(cat.asset);
        for (final line in const LineSplitter().convert(text)) {
          if (line.isEmpty) continue;
          final c = line.split(',');
          if (c.length < 3) continue;
          final name = c[0];
          final pct = double.tryParse(c[2]) ?? 0;
          (map[name] ??= []).add(HomeEntry(c[1], pct));
        }
      } catch (e) {
        debugPrint('[HomeStats] load failed (${cat.asset}): $e');
      }
      _data[cat] = map;
    }
    _loaded = true;
  }

  String _normalize(String name) {
    for (final base in _baseNames) {
      if (name.contains(base)) return base;
    }
    // メガ（フォーム 10-19）は基本形名で引く（"メガリザードンX" → "リザードン"）。
    if (name.startsWith('メガ') && name != 'メガニウム') {
      return name.substring(2).replaceAll(RegExp(r'[XYＸＹ]$'), '');
    }
    return name;
  }

  /// 指定ポケモン・カテゴリの HOME 使用率一覧（CSV の並び＝使用率降順）。
  List<HomeEntry> entries(String name, HomeCategory cat) =>
      _data[cat]?[_normalize(name)] ?? const [];

  /// 努力値文字列（例 "H2A32S32"）を [H,A,B,C,D,S] の 0-32 配列へ。
  static List<int> parseDoryoku(String text) {
    final ev = List<int>.filled(6, 0);
    const order = {'H': 0, 'A': 1, 'B': 2, 'C': 3, 'D': 4, 'S': 5};
    for (final m in RegExp(r'([HABCDS])(\d+)').allMatches(text)) {
      ev[order[m.group(1)]!] = int.parse(m.group(2)!);
    }
    return ev;
  }
}
