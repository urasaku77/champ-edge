import 'dart:convert';

import 'package:flutter/foundation.dart';

import 'ref_data.dart';

/// シーズン定義（旧 recog/season.json 相当）。
class SeasonDef {
  SeasonDef(this.name, this.from, this.to);
  final String name;
  final DateTime from;
  final DateTime to;
}

/// 構築記事1件（旧 構築記事DB 相当）。
class KouseiArticle {
  KouseiArticle(this.title, this.url, this.pokemons);
  final String title;
  final String url;
  final List<String> pokemons; // 6枠（空は '-1'）
}

/// スクレイピング由来データのローカルキャッシュ（原典の stats/ranking.txt・
/// recog/season.json・構築記事DB に相当）。
///
/// **重要な切り分け**：各機能はここを読むだけ。データの取得（更新）は別物で、
/// 現状はアプリ同梱の seed（assets/data/scrape/*.json）を読む。将来はサーバー集約
/// （API）で同じローカルキャッシュを更新する想定（Issue #25）。
class ScrapeData {
  ScrapeData._();
  static final ScrapeData instance = ScrapeData._();

  bool _loaded = false;

  /// 全体使用率ランキング（pid を使用率の高い順）。
  List<String> ranking = const [];

  /// pid → ランキング順位（0始まり）。未掲載は大きい値。
  Map<String, int> _rankIndex = const {};

  List<SeasonDef> seasons = const [];
  List<KouseiArticle> kousei = const [];

  /// ランキング順位（メガ等は呼び出し側で正規化して渡す想定）。未掲載は 1<<30。
  int rankOf(String pid) => _rankIndex[pid] ?? (1 << 30);

  /// pid が使用率トップ N に入るか。
  bool inTopN(String pid, int n) => rankOf(pid) < n;

  Future<void> load() async {
    if (_loaded) return;
    _loaded = true;
    try {
      final r = jsonDecode(
          await RefData.instance.loadString('assets/data/scrape/ranking.json'));
      ranking = [for (final p in (r as List)) p as String];
      _rankIndex = {for (var i = 0; i < ranking.length; i++) ranking[i]: i};

      final s = jsonDecode(
          await RefData.instance.loadString('assets/data/scrape/season.json'));
      seasons = [
        for (final e in (s as List))
          SeasonDef(e['name'] as String, DateTime.parse(e['from'] as String),
              DateTime.parse(e['to'] as String)),
      ];

      final k = jsonDecode(
          await RefData.instance.loadString('assets/data/scrape/kousei.json'));
      kousei = [
        for (final e in (k as List))
          KouseiArticle(
            (e['title'] as String?) ?? '',
            (e['url'] as String?) ?? '',
            [
              for (final p in (e['pokemons'] as List? ?? const []))
                p as String
            ],
          ),
      ];
    } catch (e) {
      debugPrint('[ScrapeData] load failed: $e');
    }
  }
}
