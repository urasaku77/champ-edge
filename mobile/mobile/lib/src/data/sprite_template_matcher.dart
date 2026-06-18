import 'dart:typed_data';

import 'package:flutter/services.dart' show rootBundle;
import 'package:opencv_dart/opencv_dart.dart' as cv;

/// 相手スロットのスプライト照合（元 champ-edge の recognize_oppo_party と同方式）。
///
/// グレースケール＋CLAHE＋`cv.matchTemplate`(TM_CCOEFF_NORMED) を、同梱テンプレ
/// (`assets/data/sprite_templates.bin`) に対してマルチスケールで実行し、最大スコアの
/// pid を返す。タイプ絞り込みやアイコン検出は不要（全解像度マッチで安定して当たる）。
///
/// テンプレは tools/gen_sprite_templates.py で「αを黒合成→グレー100x100」に前処理済み。
class SpriteTemplateMatcher {
  SpriteTemplateMatcher._();
  static final SpriteTemplateMatcher instance = SpriteTemplateMatcher._();

  static const int slotCount = 6;
  // 相手列スロットの相対座標（選出画面）。matchTemplate がスライドで吸収するため窓は広め。
  // 縦窓 _rowCrop を大きめに取り、機種ごとのトレーナー名バー高さ差（パネル開始位置の
  // 縦ズレ）を縦スライドで吸収する（iPhone/Android 両対応）。
  static const double _rowY0 = 0.05, _rowH = 0.1385, _rowCrop = 0.20;
  static const double _spriteX0 = 0.772, _spriteX1 = 0.846;
  // テンプレ高さ100pxを画面スプライト(≈H*0.10)へ合わせる基準スケール×係数。
  static const double _spriteFracH = 0.10;
  static const List<double> _scales = [0.8, 0.95, 1.1, 1.25];

  final List<_Template> _templates = [];
  bool _loaded = false;

  Future<void> load() async {
    if (_loaded) return;
    final bytes = await rootBundle.load('assets/data/sprite_templates.bin');
    _parsePack(bytes.buffer.asUint8List(), _templates);
    _loaded = true;
  }

  /// 取り込んだスクショ(bytes)を 6 スロット照合。各スロット上位 [topK] 件を返す。
  /// [onProgress] は (完了スロット数, 総数) で都度呼ばれる（UIの進捗用に await で譲る）。
  Future<List<List<MatchResult>>> matchScreenshot(
    Uint8List shot, {
    int topK = 8,
    void Function(int done, int total)? onProgress,
  }) async {
    await load();
    final img = cv.imdecode(shot, cv.IMREAD_COLOR);
    final base = img.rows * _spriteFracH / 100.0;
    final clahe = cv.createCLAHE(clipLimit: 2.0, tileGridSize: (8, 8));
    final out = <List<MatchResult>>[];
    try {
      for (var i = 0; i < slotCount; i++) {
        out.add(_matchSlot(img, i, base, clahe, topK));
        onProgress?.call(i + 1, slotCount);
        await Future<void>.delayed(Duration.zero); // 進捗描画に譲る
      }
    } finally {
      clahe.dispose();
      img.dispose();
    }
    return out;
  }

  List<MatchResult> _matchSlot(
      cv.Mat img, int i, double base, cv.CLAHE clahe, int topK) {
    final h = img.rows, w = img.cols;
    var y0 = (h * _rowY0 + h * _rowH * i).round();
    var ch = (h * _rowCrop).round();
    final x0 = (w * _spriteX0).round();
    final cw = (w * (_spriteX1 - _spriteX0)).round();
    if (y0 + ch > h) ch = h - y0;
    if (y0 < 0 || ch < 16 || x0 + cw > w) return const [];

    final region = img.region(cv.Rect(x0, y0, cw, ch));
    final g = cv.cvtColor(region, cv.COLOR_BGR2GRAY);
    final gc = clahe.apply(g);
    final rh = g.rows, rw = g.cols;
    final results = <MatchResult>[];
    try {
      for (final t in _templates) {
        var mx = 0.0;
        for (final k in _scales) {
          final s = base * k;
          final tw = (t.cols * s).round(), th = (t.rows * s).round();
          if (th >= rh || tw >= rw || tw < 8 || th < 8) continue;
          final tt = cv.resize(t.mat, (tw, th), interpolation: cv.INTER_AREA);
          final tc = clahe.apply(tt);
          final r1 = cv.matchTemplate(g, tt, cv.TM_CCOEFF_NORMED);
          final r2 = cv.matchTemplate(gc, tc, cv.TM_CCOEFF_NORMED);
          final v1 = cv.minMaxLoc(r1).$2;
          final v2 = cv.minMaxLoc(r2).$2;
          final v = v1 > v2 ? v1 : v2;
          if (v > mx) mx = v;
          tt.dispose();
          tc.dispose();
          r1.dispose();
          r2.dispose();
        }
        results.add(MatchResult(t.pid, mx));
      }
    } finally {
      region.dispose();
      g.dispose();
      gc.dispose();
    }
    results.sort((a, b) => b.score.compareTo(a.score));
    return results.take(topK).toList();
  }

  static void _parsePack(Uint8List d, List<_Template> out) {
    final bd = ByteData.sublistView(d);
    // magic 'SPT1'
    if (d.length < 8 || d[0] != 0x53 || d[1] != 0x50 || d[2] != 0x54) {
      throw StateError('invalid sprite_templates.bin');
    }
    final n = bd.getUint32(4, Endian.little);
    var o = 8;
    for (var e = 0; e < n; e++) {
      final pl = d[o];
      o += 1;
      final pid = String.fromCharCodes(d.sublist(o, o + pl));
      o += pl;
      final th = bd.getUint16(o, Endian.little);
      final tw = bd.getUint16(o + 2, Endian.little);
      o += 4;
      final gray = d.sublist(o, o + th * tw);
      o += th * tw;
      final mat = cv.Mat.fromList(th, tw, cv.MatType.CV_8UC1, gray);
      out.add(_Template(pid, mat));
    }
  }
}

class MatchResult {
  MatchResult(this.pid, this.score);
  final String pid;
  final double score;
}

class _Template {
  _Template(this.pid, this.mat);
  final String pid;
  final cv.Mat mat;
  int get rows => mat.rows;
  int get cols => mat.cols;
}
