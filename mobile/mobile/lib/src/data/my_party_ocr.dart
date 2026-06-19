import 'dart:typed_data';
import 'dart:ui' show Rect;

import 'package:google_mlkit_text_recognition/google_mlkit_text_recognition.dart';
import 'package:opencv_dart/opencv_dart.dart' as cv;

import 'fuzzy_match.dart';
import 'party_ocr_logic.dart';
import 'poke_db.dart';

/// 自分パーティ取込（#自パーティOCR）。
///
/// 旧 champ-edge の party/image_parser.py を Flutter へ移植したもの。HOME / SV の
/// パーティ画面スクショ2枚（能力タブ・ステータスタブ）から6体の
/// 種族・特性・持ち物・技・努力値・性格を読み取る。
///
/// - カード6分割: 紫カード背景を opencv で検出（image_parser._detect_cards 相当）。
/// - テキスト: ML Kit（Apple Vision）の日本語OCRを画像全体に掛け、各行の
///   boundingBox でカード/領域へ割り当てる。
/// - 照合: DB名一覧へ difflib 相当の曖昧一致（fuzzy_match）。努力値/性格は
///   party_ocr_logic（_parse_ev / 矢印色→性格）。
class MyPartySlot {
  String pid = ''; // 確定したポケモン pid（'0445-0' 等）。空＝未確定。
  String name = '';
  String ability = '';
  String item = '';
  List<String> moves = ['', '', '', ''];
  String nature = 'まじめ';
  List<int> evs = [0, 0, 0, 0, 0, 0]; // H,A,B,C,D,S
}

class MyPartyOcr {
  MyPartyOcr._();
  static final MyPartyOcr instance = MyPartyOcr._();

  // 照合辞書（DBから一度だけ読み込む）。
  List<({String name, String pid})> _pokemon = const [];
  List<String> _abilities = const [];
  List<String> _waza = const [];
  List<String> _items = const [];
  bool _loaded = false;

  Future<void> _load() async {
    if (_loaded) return;
    await PokeDb.instance.open();
    _pokemon = await PokeDb.instance.allPokemonNamesWithPid();
    _abilities = await PokeDb.instance.allAbilityNames();
    _waza = await PokeDb.instance.allWazaNames();
    _items = (await PokeDb.instance.itemNames())..removeWhere((s) => s == 'なし');
    _loaded = true;
  }

  /// 能力タブ画像 [abilityPath] とステータスタブ画像 [statusPath]（いずれかは null 可、
  /// 最低1枚）を解析して6スロットを返す。[abilityBytes]/[statusBytes] は同じ画像の
  /// バイト列（カード検出・矢印色検出に使う）。
  Future<List<MyPartySlot>> parse({
    String? abilityPath,
    Uint8List? abilityBytes,
    String? statusPath,
    Uint8List? statusBytes,
  }) async {
    await _load();
    final slots = List.generate(6, (_) => MyPartySlot());

    // --- 能力タブ: 名前/特性/持ち物/技 ---
    if (abilityPath != null && abilityBytes != null) {
      final img = cv.imdecode(abilityBytes, cv.IMREAD_COLOR);
      try {
        final cards = _detectCards(img);
        final lines = await _ocrLines(abilityPath);
        for (var i = 0; i < cards.length && i < 6; i++) {
          _parseAbilityCard(cards[i], lines, slots[i]);
        }
      } finally {
        img.dispose();
      }
    }

    // --- ステータスタブ: 努力値/性格（＋名前の保険） ---
    if (statusPath != null && statusBytes != null) {
      final img = cv.imdecode(statusBytes, cv.IMREAD_COLOR);
      try {
        final cards = _detectCards(img);
        final lines = await _ocrLines(statusPath);
        for (var i = 0; i < cards.length && i < 6; i++) {
          _parseStatusCard(img, cards[i], lines, slots[i]);
        }
      } finally {
        img.dispose();
      }
    }

    // --- 名前確定（OCR名→DB曖昧一致）---
    for (final s in slots) {
      if (s.name.isEmpty) continue;
      // メガストーン所持なら基本形名はそのままでよい（フォーム切替で対応）。
      final hit = _closestPokemon(s.name);
      if (hit != null) {
        s.name = hit.name;
        s.pid = hit.pid;
      }
    }
    return slots;
  }

  ({String name, String pid})? _closestPokemon(String raw) {
    final names = [for (final p in _pokemon) p.name];
    final best = closestMatch(raw, names, cutoff: 0.6);
    if (best.isEmpty) return null;
    return _pokemon.firstWhere((p) => p.name == best);
  }

  // ML Kit で画像全体をOCRし、行（テキスト＋矩形）を返す。
  Future<List<_OcrLine>> _ocrLines(String path) async {
    final recognizer =
        TextRecognizer(script: TextRecognitionScript.japanese);
    try {
      final res = await recognizer.processImage(InputImage.fromFilePath(path));
      final out = <_OcrLine>[];
      for (final b in res.blocks) {
        for (final l in b.lines) {
          final t = l.text.trim();
          if (t.isNotEmpty) out.add(_OcrLine(t, l.boundingBox));
        }
      }
      return out;
    } finally {
      await recognizer.close();
    }
  }

  // カード内の行を集める（boundingBox 中心がカード矩形内）。
  List<_OcrLine> _linesIn(cv.Rect c, List<_OcrLine> lines) {
    final r = <_OcrLine>[];
    for (final l in lines) {
      final cx = l.box.center.dx, cy = l.box.center.dy;
      if (cx >= c.x && cx < c.x + c.width && cy >= c.y && cy < c.y + c.height) {
        r.add(l);
      }
    }
    return r;
  }

  // 能力カード: 左半分→名前/特性/持ち物、右半分→技4つ。
  void _parseAbilityCard(cv.Rect c, List<_OcrLine> lines, MyPartySlot s) {
    final midX = c.x + c.width / 2;
    final inCard = _linesIn(c, lines);
    final left = inCard.where((l) => l.box.center.dx < midX).toList()
      ..sort((a, b) => a.box.top.compareTo(b.box.top));
    final right = inCard.where((l) => l.box.center.dx >= midX).toList()
      ..sort((a, b) => a.box.top.compareTo(b.box.top));

    // 名前は左列の最上行（ニックネームでなく種族名表示なので最上）。
    if (left.isNotEmpty) s.name = left.first.text;
    // 特性・持ち物は名前以降の行を辞書照合（最初に当たったものを採用）。
    for (final l in left.skip(1)) {
      if (s.ability.isEmpty) {
        final a = closestMatch(l.text, _abilities, cutoff: 0.55);
        if (a.isNotEmpty) {
          s.ability = a;
          continue;
        }
      }
      if (s.item.isEmpty) {
        final it = closestMatch(l.text, _items, cutoff: 0.5);
        if (it.isNotEmpty) s.item = _fixItem(it);
      }
    }
    // 技：右列の各行を技辞書へ。
    var mi = 0;
    for (final l in right) {
      if (mi >= 4) break;
      final w = closestMatch(l.text, _waza, cutoff: 0.5);
      if (w.isNotEmpty) s.moves[mi++] = w;
    }
  }

  static String _fixItem(String s) {
    const corr = {'オレンのみ': 'オボンのみ', 'マゴのみ': 'カゴのみ'};
    return corr[s] ?? s;
  }

  // ステータスカード: 上27%スキップ→左右半分×3行で H/A/B・C/D/S。
  // 各行で努力値数字（OCR）と性格矢印（色）を取得。
  void _parseStatusCard(
      cv.Mat img, cv.Rect c, List<_OcrLine> lines, MyPartySlot s) {
    final statTop = c.y + (c.height * 0.27).round();
    final bodyH = c.y + c.height - statTop;
    final rowH = bodyH ~/ 3;
    final midX = c.x + c.width / 2;
    // 左右×3行のステータスキー割当。
    const leftKeys = [0, 1, 2]; // H,A,B
    const rightKeys = [3, 4, 5]; // C,D,S
    final upPx = <int, int>{};
    final downPx = <int, int>{};
    for (final half in [false, true]) {
      final x0 = half ? midX : c.x.toDouble();
      final x1 = half ? (c.x + c.width).toDouble() : midX;
      final keys = half ? rightKeys : leftKeys;
      for (var r = 0; r < 3; r++) {
        final y0 = statTop + r * rowH;
        final y1 = y0 + rowH;
        final key = keys[r];
        // 努力値: 行内(右60%は実数値/EVバー)の数字トークンから EV を抽出。
        final nums = <String>[];
        for (final l in lines) {
          final cx = l.box.center.dx, cy = l.box.center.dy;
          if (cx >= x0 && cx < x1 && cy >= y0 && cy < y1) {
            nums.add(l.text);
          }
        }
        s.evs[key] = parseEv(nums.join(' '));
        // 性格矢印: 行の左60%領域で 桃(↑)/水(↓) 画素数を数える。
        final rx0 = x0.round();
        final rw = ((x1 - x0) * 0.6).round();
        final rr = _safeRect(img, rx0, y0, rw, rowH);
        if (rr != null) {
          final (u, d) = _arrowPixels(img, rr);
          if (u > 5) upPx[key] = u;
          if (d > 5) downPx[key] = d;
          rr.dispose();
        }
      }
    }
    final up = _maxKey(upPx);
    final down = _maxKey(downPx);
    final nat = natureFromArrows(_statLetter(up), _statLetter(down));
    if (nat != 'まじめ') s.nature = nat;
    // 名前が能力タブで取れていなければステータスタブの最上行で補完。
    if (s.name.isEmpty) {
      final inCard = _linesIn(c, lines)
        ..sort((a, b) => a.box.top.compareTo(b.box.top));
      if (inCard.isNotEmpty) s.name = inCard.first.text;
    }
  }

  static String? _statLetter(int? k) =>
      k == null ? null : const ['H', 'A', 'B', 'C', 'D', 'S'][k];

  static int? _maxKey(Map<int, int> m) {
    if (m.isEmpty) return null;
    int? best;
    var bv = -1;
    m.forEach((k, v) {
      if (v > bv) {
        bv = v;
        best = k;
      }
    });
    return best;
  }

  cv.Rect? _safeRect(cv.Mat img, int x, int y, int w, int h) {
    if (w < 2 || h < 2) return null;
    if (x < 0) x = 0;
    if (y < 0) y = 0;
    if (x + w > img.cols) w = img.cols - x;
    if (y + h > img.rows) h = img.rows - y;
    if (w < 2 || h < 2) return null;
    return cv.Rect(x, y, w, h);
  }

  // 矢印色の画素数（桃 ↑: R>160 & R>G+45 / 水 ↓: G>200 & B>200 & G>R+30）。
  (int, int) _arrowPixels(cv.Mat img, cv.Rect r) {
    final region = img.region(r);
    var up = 0, down = 0;
    try {
      final ch = cv.split(region); // BGR
      final b = ch[0], g = ch[1], rr = ch[2];
      final data = region; // 使わない（per-pixel は下で）
      // しきい処理で画素数を数える。
      final rg = cv.subtract(rr, g);
      final gr = cv.subtract(g, rr);
      final (_, upMask1) = cv.threshold(rr, 160, 255, cv.THRESH_BINARY);
      final (_, upMask2) = cv.threshold(rg, 45, 255, cv.THRESH_BINARY);
      final upMask = cv.bitwiseAND(upMask1, upMask2);
      up = cv.countNonZero(upMask);
      final (_, dM1) = cv.threshold(g, 200, 255, cv.THRESH_BINARY);
      final (_, dM2) = cv.threshold(b, 200, 255, cv.THRESH_BINARY);
      final (_, dM3) = cv.threshold(gr, 30, 255, cv.THRESH_BINARY);
      var dMask = cv.bitwiseAND(dM1, dM2);
      dMask = cv.bitwiseAND(dMask, dM3);
      down = cv.countNonZero(dMask);
      for (final m in [b, g, rr, rg, gr, upMask1, upMask2, upMask, dM1, dM2, dM3, dMask]) {
        m.dispose();
      }
      data; // no-op
    } finally {
      region.dispose();
    }
    return (up, down);
  }

  // 紫カード背景を検出して6カード矩形を返す（image_parser._detect_cards 相当）。
  List<cv.Rect> _detectCards(cv.Mat img) {
    final h = img.rows, w = img.cols;
    final ch = cv.split(img); // BGR
    final b = ch[0], g = ch[1], r = ch[2];
    // is_card = b>100 & b>g+20 & r>80 & b<250 & g<200
    final bg = cv.subtract(b, g);
    final (_, m1) = cv.threshold(b, 100, 255, cv.THRESH_BINARY);
    final (_, m2) = cv.threshold(bg, 20, 255, cv.THRESH_BINARY);
    final (_, m3) = cv.threshold(r, 80, 255, cv.THRESH_BINARY);
    final (_, m4) = cv.threshold(b, 250, 255, cv.THRESH_BINARY_INV);
    final (_, m5) = cv.threshold(g, 200, 255, cv.THRESH_BINARY_INV);
    var mask = cv.bitwiseAND(m1, m2);
    mask = cv.bitwiseAND(mask, m3);
    mask = cv.bitwiseAND(mask, m4);
    mask = cv.bitwiseAND(mask, m5);
    final data = mask.data;
    final result = <cv.Rect>[];
    try {
      final mid = w ~/ 2;
      final leftFrac = List<double>.filled(h, 0);
      final rightFrac = List<double>.filled(h, 0);
      final colCnt = List<int>.filled(w, 0);
      for (var y = 0; y < h; y++) {
        final off = y * w;
        var lc = 0, rc = 0;
        for (var x = 0; x < w; x++) {
          if (data[off + x] != 0) {
            if (x < mid) {
              lc++;
            } else {
              rc++;
            }
            colCnt[x]++;
          }
        }
        leftFrac[y] = lc / (w / 2);
        rightFrac[y] = rc / (w / 2);
      }
      // 両列が紫＝カード行。連続セグメントへ分割。
      final segs = <List<int>>[];
      var inSeg = false, st = 0;
      for (var y = 0; y < h; y++) {
        final both = leftFrac[y] > 0.05 && rightFrac[y] > 0.05;
        if (both && !inSeg) {
          st = y;
          inSeg = true;
        } else if (!both && inSeg) {
          segs.add([st, y]);
          inSeg = false;
        }
      }
      if (inSeg) segs.add([st, h]);
      segs.sort((a, b) => (b[1] - b[0]).compareTo(a[1] - a[0]));
      final top3 = segs.take(3).toList()..sort((a, b) => a[0].compareTo(b[0]));
      // 列範囲。
      var x1 = 0, x2 = w;
      final cols = [for (var x = 0; x < w; x++) if (colCnt[x] / h > 0.05) x];
      if (cols.length >= 10) {
        x1 = cols.first;
        x2 = cols.last + 1;
      } else {
        x1 = (w * 0.09).round();
        x2 = (w * 0.91).round();
      }
      // 中央の列ギャップ。
      final span = x2 - x1;
      final ss = x1 + span ~/ 3, se = x1 + 2 * span ~/ 3;
      var gapX = (x1 + x2) ~/ 2, gapMin = 1 << 30;
      for (var x = ss; x < se; x++) {
        if (colCnt[x] < gapMin) {
          gapMin = colCnt[x];
          gapX = x;
        }
      }
      const trim = 4;
      for (final sgmt in top3) {
        final y1 = sgmt[0] + trim, y2 = sgmt[1] - trim;
        if (y2 - y1 < 10) continue;
        result.add(cv.Rect(x1, y1, gapX - x1, y2 - y1));
        result.add(cv.Rect(gapX, y1, x2 - gapX, y2 - y1));
      }
    } finally {
      for (final m in [b, g, r, bg, m1, m2, m3, m4, m5, mask]) {
        m.dispose();
      }
    }
    return result;
  }
}

class _OcrLine {
  _OcrLine(this.text, this.box);
  final String text;
  final Rect box;
}
