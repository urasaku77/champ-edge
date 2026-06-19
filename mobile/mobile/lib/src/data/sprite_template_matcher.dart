import 'dart:typed_data';

import 'package:flutter/services.dart' show rootBundle;
import 'package:opencv_dart/opencv_dart.dart' as cv;

/// 相手スロットのスプライト照合（元 champ-edge の recognize_oppo_party と同方式）。
///
/// グレースケール＋CLAHE＋`cv.matchTemplate`(TM_CCOEFF_NORMED) を、同梱テンプレ
/// (`assets/data/sprite_templates.bin`) に対してマルチスケールで実行し、最大スコアの
/// pid を返す。タイプ絞り込みやアイコン検出は不要（全解像度マッチで安定して当たる）。
///
/// 相手パネル（右側の赤紫の縦長パネル）を色で検出し、その右端 xR と上端 yT を基準に
/// 6 スロットを相対配置する。機種（iPhone/Android）やアスペクト比でパネルの絶対位置が
/// 変わっても、検出した基準からの相対座標で吸収する。検出に失敗した場合は固定座標へ
/// フォールバックする。
///
/// テンプレは tools/gen_sprite_templates.py で「αを黒合成→グレー100x100」に前処理済み。
class SpriteTemplateMatcher {
  SpriteTemplateMatcher._();
  static final SpriteTemplateMatcher instance = SpriteTemplateMatcher._();

  static const int slotCount = 6;

  // --- パネル検出（赤紫マスク）パラメータ ---
  // 検出は幅 _detectWidth へ縮小した画像上で行い、原寸へ戻す（高速・安定）。
  static const int _detectWidth = 480;

  // --- スロット幾何（検出した xR/yT からの相対値、全て原寸の割合）---
  // パネル名バー上端 yT から 1 枚目カード上端までのオフセット。
  static const double _firstCardOffset = 0.058;
  // カードの縦ピッチ（カード上端→次カード上端）。9 機種で実測 0.116〜0.117。
  static const double _cardPitch = 0.117;
  // カード高（カード上端→下端）。窓をスプライト中央へ寄せる中心位置の算出に使う。
  static const double _cardHeight = 0.105;
  // 照合窓の高さ。窓はカード中央に置き matchTemplate が上下スライドで最適位置を探す。
  // 0.14 はスケール 1.25（th≈0.125h）が収まり、かつ隣カードへほぼ被らない値。
  static const double _winHeight = 0.14;
  // スプライト照合窓の水平位置（パネル右端 xR からの内側オフセットと幅）。
  // パネル幅 ≈0.125w・スプライトは左寄り。xR 基準にすると xL のノイズに影響されない。
  static const double _spriteRightInset = 0.121;
  static const double _spriteWinWidth = 0.069;

  // 検出失敗時のフォールバック（iPhone/Android の中間値）。
  static const double _fallbackXR = 0.875;
  static const double _fallbackYT = 0.073;

  // テンプレ高さ100pxを画面スプライト(≈H*0.10)へ合わせる基準スケール×係数。
  static const double _spriteFracH = 0.10;
  // マルチスケール倍率。窓を中央寄せ＋やや高め(_winHeight=0.14)にしたことで上限 1.25 が
  // 収まり、縦スライドの自由度が増えて照合スコアが上がる（際どいスロットの自動確定が改善）。
  static const List<double> _scales = [0.8, 0.95, 1.1, 1.25];

  final List<_Template> _templates = [];
  bool _loaded = false;

  Future<void> load() async {
    if (_loaded) return;
    final bytes = await rootBundle.load('assets/data/sprite_templates.bin');
    _parsePack(bytes.buffer.asUint8List(), _templates);
    _loaded = true;
  }

  /// 取り込んだスクショ(bytes)を 6 スロット照合。各スロットの上位 [topK] 件の候補と、
  /// 表示用にトリミングしたスプライト矩形（原寸ピクセル）を返す。
  /// [onProgress] は (完了スロット数, 総数) で都度呼ばれる（UIの進捗用に await で譲る）。
  Future<List<SlotMatch>> matchScreenshot(
    Uint8List shot, {
    int topK = 8,
    void Function(int done, int total)? onProgress,
  }) async {
    await load();
    final img = cv.imdecode(shot, cv.IMREAD_COLOR);
    final base = img.rows * _spriteFracH / 100.0;
    final clahe = cv.createCLAHE(clipLimit: 2.0, tileGridSize: (8, 8));
    final rects = _slotRects(img);
    final out = <SlotMatch>[];
    try {
      for (var i = 0; i < slotCount; i++) {
        final r = rects[i];
        out.add(SlotMatch(_matchSlot(img, r, base, clahe, topK), r));
        onProgress?.call(i + 1, slotCount);
        await Future<void>.delayed(Duration.zero); // 進捗描画に譲る
      }
    } finally {
      clahe.dispose();
      img.dispose();
    }
    return out;
  }

  /// 検出したパネル基準で 6 スロットのスプライト矩形（原寸ピクセル）を算出する。
  List<cv.Rect> _slotRects(cv.Mat img) {
    final h = img.rows, w = img.cols;
    final panel = _detectPanel(img);
    final xr = (panel?.xR ?? _fallbackXR * w);
    final yt = (panel?.yT ?? _fallbackYT * h);
    final firstTop = yt + _firstCardOffset * h;
    var x0 = (xr - _spriteRightInset * w).round();
    var cw = (_spriteWinWidth * w).round();
    if (x0 < 0) x0 = 0;
    if (x0 + cw > w) cw = w - x0;
    final ch0 = (_winHeight * h).round();
    return List.generate(slotCount, (i) {
      // 各カードの中央に窓を置く（カード上端 + カード高/2 を中心に、窓高/2 だけ上へ）。
      final center = firstTop + i * _cardPitch * h + _cardHeight * h / 2;
      var y0 = (center - ch0 / 2).round();
      if (y0 < 0) y0 = 0;
      var ch = ch0;
      if (y0 + ch > h) ch = h - y0;
      return cv.Rect(x0, y0, cw, ch);
    });
  }

  /// 右側の相手パネルを赤紫マスクで検出し、右端 xR と名バー上端 yT を原寸で返す。
  /// 検出できなければ null。
  _Panel? _detectPanel(cv.Mat img) {
    final w = img.cols, h = img.rows;
    const sw = _detectWidth;
    final sh = (h * sw / w).round();
    final small = cv.resize(img, (sw, sh), interpolation: cv.INTER_AREA);
    final channels = cv.split(small); // BGR
    final b = channels[0], g = channels[1], r = channels[2];
    final rg = cv.subtract(r, g);
    final rb = cv.subtract(r, b);
    final (_, mRhi) = cv.threshold(r, 70, 255, cv.THRESH_BINARY); // R>70
    final (_, mRlo) = cv.threshold(r, 214, 255, cv.THRESH_BINARY_INV); // R<215
    final (_, mGlo) = cv.threshold(g, 79, 255, cv.THRESH_BINARY_INV); // G<80
    final (_, mRG) = cv.threshold(rg, 40, 255, cv.THRESH_BINARY); // R-G>40
    final (_, mRB) = cv.threshold(rb, 15, 255, cv.THRESH_BINARY); // R-B>15
    var mask = cv.bitwiseAND(mRhi, mRlo);
    mask = cv.bitwiseAND(mask, mGlo);
    mask = cv.bitwiseAND(mask, mRG);
    mask = cv.bitwiseAND(mask, mRB);
    final data = mask.data; // CV_8U 単チャンネル, row-major
    _Panel? result;
    try {
      // 列ごとの該当画素数
      final colCnt = List<int>.filled(sw, 0);
      for (var y = 0; y < sh; y++) {
        final off = y * sw;
        for (var x = 0; x < sw; x++) {
          if (data[off + x] != 0) colCnt[x]++;
        }
      }
      // 右端 xR: 右側(>0.6幅)で十分赤い最右列
      final colThr = sh * 0.15;
      var xR = -1;
      for (var x = sw - 1; x > (sw * 0.6).floor(); x--) {
        if (colCnt[x] > colThr) {
          xR = x;
          break;
        }
      }
      if (xR < 0) return null;
      // 名バー上端 yT: xR 基準の固定幅バンド内で、赤の「水平連続長」が長い行が連続する
      // 最初の行。被覆率(行内の赤画素数)ではなく連続長を使うのが要点。名バー（赤紫ピル）は
      // 帯を端から端まで連続して埋めるが、斜めのレーザービームは帯を細く横切るだけなので、
      // 被覆率が高くても連続長は短い（実測でレーザーの連続長は最大でも帯幅の 0.31）。一方
      // 名バーは明るい背景のカジュアル対戦で淡くなる機種でも、上端から 2 行目までに連続長
      // 0.43 以上へ達する。閾値 0.38・2 行連続なら、淡い名バーを掴みつつレーザーを確実に
      // 除外でき、被覆率方式では分離できなかった「淡い名バー上端(0.34)とレーザー(0.41)」の
      // 衝突を解消する。各行の連続長は [xL, xR] 内の最長連続 ON 区間で求める。
      final xL = (xR - 0.125 * sw).round().clamp(0, sw - 1);
      final bandW = xR - xL + 1;
      final runThr = bandW * 0.38;
      const lines = 2;
      final rowRun = List<int>.filled(sh, 0);
      for (var y = 0; y < sh; y++) {
        final off = y * sw;
        var best = 0, cur = 0;
        for (var x = xL; x <= xR; x++) {
          if (data[off + x] != 0) {
            cur++;
            if (cur > best) best = cur;
          } else {
            cur = 0;
          }
        }
        rowRun[y] = best;
      }
      var yT = -1;
      for (var y = 0; y <= sh - lines; y++) {
        var ok = true;
        for (var k = 0; k < lines; k++) {
          if (rowRun[y + k] < runThr) {
            ok = false;
            break;
          }
        }
        if (ok) {
          yT = y;
          break;
        }
      }
      if (yT < 0) return null;
      final scale = w / sw;
      result = _Panel(xR * scale, yT * scale);
    } finally {
      small.dispose();
      b.dispose();
      g.dispose();
      r.dispose();
      rg.dispose();
      rb.dispose();
      mRhi.dispose();
      mRlo.dispose();
      mGlo.dispose();
      mRG.dispose();
      mRB.dispose();
      mask.dispose();
    }
    return result;
  }

  List<MatchResult> _matchSlot(
      cv.Mat img, cv.Rect rect, double base, cv.CLAHE clahe, int topK) {
    final h = img.rows, w = img.cols;
    if (rect.height < 16 ||
        rect.width < 8 ||
        rect.x < 0 ||
        rect.y < 0 ||
        rect.x + rect.width > w ||
        rect.y + rect.height > h) {
      return const [];
    }

    final region = img.region(rect);
    final gg = cv.cvtColor(region, cv.COLOR_BGR2GRAY);
    final gc = clahe.apply(gg);
    final rh = gg.rows, rw = gg.cols;
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
          final r1 = cv.matchTemplate(gg, tt, cv.TM_CCOEFF_NORMED);
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
      gg.dispose();
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

/// 1 スロットの照合結果と、表示用スプライト矩形（原寸ピクセル）。
class SlotMatch {
  SlotMatch(this.candidates, this.rect);
  final List<MatchResult> candidates;
  final cv.Rect rect;
}

class MatchResult {
  MatchResult(this.pid, this.score);
  final String pid;
  final double score;
}

class _Panel {
  _Panel(this.xR, this.yT);
  final double xR;
  final double yT;
}

class _Template {
  _Template(this.pid, this.mat);
  final String pid;
  final cv.Mat mat;
  int get rows => mat.rows;
  int get cols => mat.cols;
}
