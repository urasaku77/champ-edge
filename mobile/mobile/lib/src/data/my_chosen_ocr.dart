import 'dart:io';
import 'dart:math' as math;

import 'package:flutter/foundation.dart' show debugPrint;
import 'package:google_mlkit_text_recognition/google_mlkit_text_recognition.dart';
import 'package:opencv_dart/opencv_dart.dart' as cv;
import 'package:path_provider/path_provider.dart';

/// 自分の選出スクショ（選出画面）から「選出順」を読み取る。
///
/// PC版 recog/capture.py `recognize_chosen_num` 準拠。選出画面はニックネーム表示の
/// ことがあるため**名前照合は使わず、左の6ピル（＝パーティ枠順）で位置対応**する。
///
/// 仕組み（全5サンプルで選出順 5/5 一致を確認した方式）：
///  1. 左側の紫/黄緑ピルを色マスク＋行射影で検出 → ヘッダ/フッタを除いた中央6行。
///  2. 各行の左側で「白い縦長の角丸バッジ」を**連結成分**で検出。あれば選択。
///  3. そのバッジ矩形を精密に切り出し ML Kit で数字OCR（選出順）。読めない行は
///     上→下の位置順で空き番号を補完（読めた番号が他を確定させる）。
///  戻り値は選出順に並べたパーティ枠インデックス（0始まり）。例 [4,1,0]。
class MyChosenOcr {
  static Future<List<int>> parse(String path) async {
    final img = cv.imread(path);
    if (img.isEmpty) return const [];
    cv.Mat? whiteMask;
    try {
      final w = img.cols, h = img.rows;
      final pills = _detectPills(img, w, h);
      if (pills.isEmpty) return const [];
      // 白マスク（R,G,B すべて > 200）。BGR なので Scalar も (B,G,R)。
      whiteMask = cv.inRangebyScalar(
          img, cv.Scalar(201, 201, 201), cv.Scalar(255, 255, 255));
      final recognizer = TextRecognizer(script: TextRecognitionScript.latin);
      final tmp = (await getTemporaryDirectory()).path;
      final selected = <bool>[];
      final digitOf = <int, int>{};
      try {
        for (var i = 0; i < pills.length; i++) {
          final bb = _badgeBBox(whiteMask, pills[i], w);
          selected.add(bb != null);
          if (bb != null) {
            final d = await _readDigit(img, pills[i], bb, recognizer, tmp, i);
            if (d >= 1 && d <= 6) digitOf[i] = d;
          }
        }
      } finally {
        await recognizer.close();
      }
      return _buildOrder(pills.length, selected, digitOf);
    } catch (e) {
      debugPrint('MyChosenOcr.parse error: $e');
      return const [];
    } finally {
      whiteMask?.dispose();
      img.dispose();
    }
  }

  static List<int> _buildOrder(
      int n, List<bool> selected, Map<int, int> digitOf) {
    final slots = [for (var i = 0; i < n; i++) if (selected[i]) i];
    if (slots.isEmpty) return const [];
    final byPos = List<int?>.filled(slots.length, null);
    final used = <int>{};
    digitOf.forEach((slot, d) {
      final pos = d - 1;
      if (pos >= 0 && pos < slots.length && byPos[pos] == null) {
        byPos[pos] = slot;
        used.add(slot);
      }
    });
    final rest = [for (final s in slots) if (!used.contains(s)) s];
    var ri = 0;
    for (var pos = 0; pos < slots.length && ri < rest.length; pos++) {
      if (byPos[pos] == null) byPos[pos] = rest[ri++];
    }
    return [for (final s in byPos) if (s != null) s];
  }

  static List<_Pill> _detectPills(cv.Mat img, int w, int h) {
    final data = img.data; // BGR
    final lw = (w * 0.38).round();
    final rowCnt = List<int>.filled(h, 0);
    for (var y = 0; y < h; y++) {
      final base = y * w * 3;
      var cnt = 0;
      for (var x = 0; x < lw; x++) {
        final i = base + x * 3;
        final b = data[i], g = data[i + 1], r = data[i + 2];
        final purple = b > 130 && (b - g) > 25 && r > 60 && r < 200;
        final yellow = g > 150 && r > 120 && (b * 4) < (g * 3);
        if (purple || yellow) cnt++;
      }
      rowCnt[y] = cnt;
    }
    final maxCnt = rowCnt.fold<int>(0, math.max);
    if (maxCnt == 0) return const [];
    final th = math.max(lw * 0.18, maxCnt * 0.25);
    final bands = <List<int>>[];
    var inb = false, st = 0;
    for (var y = 0; y < h; y++) {
      if (rowCnt[y] > th && !inb) {
        inb = true;
        st = y;
      } else if (rowCnt[y] <= th && inb) {
        inb = false;
        if (y - st > h * 0.03) bands.add([st, y]);
      }
    }
    if (inb && h - st > h * 0.03) bands.add([st, h]);
    if (bands.isEmpty) return const [];
    final maxH = bands.map((b) => b[1] - b[0]).fold<int>(0, math.max);
    return [
      for (final b in bands)
        if ((b[1] - b[0]) >= 0.75 * maxH) _Pill(top: b[0], bottom: b[1])
    ].take(6).toList();
  }

  /// ピル左側の「白い縦長角丸バッジ」を連結成分で探す。見つかれば全画像座標の矩形。
  static cv.Rect? _badgeBBox(cv.Mat whiteMask, _Pill p, int w) {
    final bh = p.bottom - p.top;
    final rw = (w * 0.18).round();
    cv.Mat? sub, labels, stats, centroids;
    try {
      sub = whiteMask.region(cv.Rect(0, p.top, rw, bh));
      labels = cv.Mat.empty();
      stats = cv.Mat.empty();
      centroids = cv.Mat.empty();
      final cnt = cv.connectedComponentsWithStats(
          sub, labels, stats, centroids, 8, cv.MatType.CV_32S, cv.CCL_DEFAULT);
      int? bestX, bestY, bestW, bestH;
      var bestArea = -1;
      for (var i = 1; i < cnt; i++) {
        final x = stats.at<int>(i, 0);
        final y = stats.at<int>(i, 1);
        final cw = stats.at<int>(i, 2);
        final ch = stats.at<int>(i, 3);
        final area = stats.at<int>(i, 4);
        if (ch < 0.60 * bh) continue; // 縦長
        if (cw < 0.20 * bh || cw > 0.70 * bh) continue; // 細め
        if ((x + cw / 2) > w * 0.16) continue; // 左端
        if (area < 0.12 * bh * bh) continue;
        if (area > bestArea) {
          bestArea = area;
          bestX = x;
          bestY = y;
          bestW = cw;
          bestH = ch;
        }
      }
      if (bestX == null) return null;
      return cv.Rect(bestX, p.top + bestY!, bestW!, bestH!);
    } finally {
      sub?.dispose();
      labels?.dispose();
      stats?.dispose();
      centroids?.dispose();
    }
  }

  /// バッジ矩形を精密に切り出し、二値化（複数閾値）して数字OCR。読めた数字を返す。
  static Future<int> _readDigit(cv.Mat img, _Pill p, cv.Rect bb,
      TextRecognizer rec, String tmpDir, int idx) async {
    if (bb.width < 4 || bb.height < 4) return -1;
    cv.Mat? roi, up, gray;
    try {
      roi = img.region(bb);
      up = cv.resize(roi, (bb.width * 8, bb.height * 8),
          interpolation: cv.INTER_CUBIC);
      gray = cv.cvtColor(up, cv.COLOR_BGR2GRAY);
      for (final thr in [140, 120, 160]) {
        final (_, bw) = cv.threshold(gray, thr.toDouble(), 255, cv.THRESH_BINARY);
        try {
          final (ok, buf) = cv.imencode('.png', bw);
          if (!ok) continue;
          final f = File('$tmpDir/_chosen_$idx.png');
          await f.writeAsBytes(buf);
          final res = await rec.processImage(InputImage.fromFilePath(f.path));
          for (final block in res.blocks) {
            for (final line in block.lines) {
              for (final ch in line.text.trim().split('')) {
                if ('123456'.contains(ch)) return int.parse(ch);
              }
            }
          }
        } finally {
          bw.dispose();
        }
      }
      return -1;
    } finally {
      roi?.dispose();
      up?.dispose();
      gray?.dispose();
    }
  }
}

class _Pill {
  _Pill({required this.top, required this.bottom});
  final int top;
  final int bottom;
}
