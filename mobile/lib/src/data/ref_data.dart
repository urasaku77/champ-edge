import 'dart:async';
import 'dart:convert';
import 'dart:io';

import 'package:flutter/foundation.dart';
import 'package:flutter/services.dart' show rootBundle;
import 'package:path/path.dart' as p;
import 'package:path_provider/path_provider.dart';

/// 参照データ（HOME使用率・構築記事・ランキング・シーズン）の配信レイヤ。
///
/// 取得元はクラウド上の静的ファイル（無料の Cloudflare Pages ＝ GitHub リポジトリ配信）。
/// 方針：**stale-while-revalidate**。読み込みは「キャッシュ → 無ければ同梱アセット」で
/// 常にオフラインでも動く。起動時にバックグラウンドで最新を取得してキャッシュを更新し、
/// 更新分は次回読み込み（次回起動）から反映する。クライアント側スクレイピングは行わない
/// （サーバー集約データを取得するだけ。Issue #25 の方針）。
class RefData {
  RefData._();
  static final RefData instance = RefData._();

  /// 配信ベースURL（無料・Cloudflare Pages）。データ更新はリポジトリへ push すれば
  /// Cloudflare が自動再デプロイして反映される。
  /// 取得失敗時は常に同梱アセットへフォールバックするため、オフラインでも動作する。
  static const String _base =
      'https://champ-edge-mobile.pages.dev/mobile/';

  /// 配信対象のアセットパス（同梱アセットと同じ相対パス）。
  static const List<String> refPaths = [
    'assets/data/scrape/ranking.json',
    'assets/data/scrape/season.json',
    'assets/data/scrape/kousei.json',
    'assets/data/home/home_waza.csv',
    'assets/data/home/home_motimono.csv',
    'assets/data/home/home_tokusei.csv',
    'assets/data/home/home_seikaku.csv',
    'assets/data/home/home_doryoku.csv',
  ];

  /// 再取得の最小間隔（これ未満の頻度では取得しない）。
  static const Duration _ttl = Duration(hours: 24);

  Directory? _cacheDir;
  Future<Directory> _dir() async {
    final d = _cacheDir ??=
        Directory(p.join((await getApplicationDocumentsDirectory()).path,
            'ref_cache'));
    if (!await d.exists()) await d.create(recursive: true);
    return d;
  }

  File _cacheFileSync(Directory dir, String assetPath) =>
      File(p.join(dir.path, assetPath.replaceAll('/', '_')));

  /// 参照ファイルを読む。キャッシュ（取得済み）があればそれ、無ければ同梱アセット。
  Future<String> loadString(String assetPath) async {
    try {
      final f = _cacheFileSync(await _dir(), assetPath);
      if (await f.exists()) return await f.readAsString();
    } catch (e) {
      debugPrint('[RefData] cache read failed ($assetPath): $e');
    }
    return rootBundle.loadString(assetPath);
  }

  bool _refreshing = false;

  /// 最終取得時刻（TTL 判定用）。
  Future<DateTime?> _lastRefresh() async {
    try {
      final f = File(p.join((await _dir()).path, '_last.txt'));
      if (await f.exists()) {
        return DateTime.tryParse(await f.readAsString());
      }
    } catch (_) {}
    return null;
  }

  Future<void> _markRefreshed() async {
    try {
      await File(p.join((await _dir()).path, '_last.txt'))
          .writeAsString(DateTime.now().toIso8601String());
    } catch (_) {}
  }

  /// 全参照ファイルをクラウドから取得してキャッシュ更新（TTL 内なら何もしない）。
  /// 失敗は無視（同梱アセットで動作）。[force] で TTL を無視。
  Future<void> refreshAll({bool force = false}) async {
    if (_refreshing) return;
    if (!force) {
      final last = await _lastRefresh();
      if (last != null && DateTime.now().difference(last) < _ttl) return;
    }
    _refreshing = true;
    var any = false;
    try {
      final dir = await _dir();
      final client = HttpClient()
        ..connectionTimeout = const Duration(seconds: 8);
      try {
        for (final path in refPaths) {
          try {
            final req = await client.getUrl(Uri.parse('$_base$path'));
            final res = await req.close().timeout(const Duration(seconds: 10));
            if (res.statusCode != 200) continue;
            final body = await res.transform(utf8.decoder).join();
            if (body.trim().isEmpty) continue;
            await _cacheFileSync(dir, path).writeAsString(body);
            any = true;
          } catch (e) {
            debugPrint('[RefData] fetch failed ($path): $e');
          }
        }
      } finally {
        client.close(force: true);
      }
      if (any) await _markRefreshed();
    } catch (e) {
      debugPrint('[RefData] refreshAll failed: $e');
    } finally {
      _refreshing = false;
    }
  }
}
