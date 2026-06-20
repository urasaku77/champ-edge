import 'dart:typed_data';
import 'dart:ui' show Rect;

import 'package:flutter/foundation.dart' show debugPrint;
import 'package:google_mlkit_text_recognition/google_mlkit_text_recognition.dart';
import 'package:opencv_dart/opencv_dart.dart' as cv;

import '../model/battle_pokemon.dart';
import '../service/damage/poke_types.dart';
import 'fuzzy_match.dart';
import 'party_ocr_logic.dart';
import 'poke_db.dart';

/// 取込結果(スロット)から6体の [BattlePokemon] を構築する。未認識スロットは空ポケモン。
/// 自パOCRの結果をパーティへ反映する共通処理（パーティ詳細編集・Top 双方で使う）。
Future<List<BattlePokemon>> buildPartyFromSlots(List<MyPartySlot> slots) async {
  final out = <BattlePokemon>[];
  for (final s in slots) {
    BattlePokemon? p;
    if (s.pid.isNotEmpty) {
      p = await PokeDb.instance.buildPokemon(s.pid);
      if (p != null) {
        if (s.ability.isNotEmpty && p.abilityOptions.contains(s.ability)) {
          p.ability = s.ability;
        }
        if (s.item.isNotEmpty) p.item = s.item;
        if (s.nature.isNotEmpty) p.nature = s.nature;
        p.ev = List<int>.from(s.evs);
        final moves = <BattleMove>[];
        for (final mn in s.moves) {
          if (mn.isEmpty) continue;
          final bm = await PokeDb.instance.moveByName(mn);
          if (bm != null) moves.add(bm);
        }
        while (moves.length < 4) {
          moves.add(emptyMove());
        }
        p.moves = moves.take(4).toList();
      }
    }
    out.add(p ?? _emptyBattlePokemon());
  }
  return out;
}

BattlePokemon _emptyBattlePokemon() => BattlePokemon(
      name: '',
      pid: '0000-0',
      baseStats: const [0, 0, 0, 0, 0, 0],
      type1: PokeType.none,
      abilityOptions: const ['—'],
      moves: List.generate(4, (_) => emptyMove()),
    );

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
  Map<String, List<int>> _baseStats = const {};
  bool _loaded = false;

  /// 直近の解析の診断情報（検出カード数・OCR生テキスト等）。実機デバッグ用に
  /// 取込画面で表示する。
  String debugInfo = '';

  Future<void> _load() async {
    if (_loaded) return;
    await PokeDb.instance.open();
    _pokemon = await PokeDb.instance.allPokemonNamesWithPid();
    _abilities = await PokeDb.instance.allAbilityNames();
    _waza = await PokeDb.instance.allWazaNames();
    _items = (await PokeDb.instance.itemNames())..removeWhere((s) => s == 'なし');
    _baseStats = await PokeDb.instance.allBaseStats();
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
    final dbg = StringBuffer();

    // --- 能力タブ: 名前/特性/持ち物/技 ---
    if (abilityPath != null && abilityBytes != null) {
      final img = cv.imdecode(abilityBytes, cv.IMREAD_COLOR);
      try {
        final cards = _detectCards(img);
        final lines = await _ocrLines(abilityPath);
        dbg.writeln('[能力] 画像 ${img.cols}x${img.rows} / カード ${cards.length} / OCR行 ${lines.length}');
        for (final l in lines.take(40)) {
          dbg.writeln('  "${l.text}" @(${l.box.left.round()},${l.box.top.round()})');
        }
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
        dbg.writeln('[ステータス] 画像 ${img.cols}x${img.rows} / カード ${cards.length} / OCR行 ${lines.length}');
        for (final l in lines.take(40)) {
          dbg.writeln('  "${l.text}" @(${l.box.left.round()},${l.box.top.round()})');
        }
        for (var i = 0; i < cards.length && i < 6; i++) {
          _parseStatusCard(img, cards[i], lines, slots[i]);
        }
      } finally {
        img.dispose();
      }
    }
    debugInfo = dbg.toString();
    debugPrint('[MyPartyOcr]\n$debugInfo');

    // --- 名前確定（ステータスタブのみで pid 未確定の保険）---
    for (final s in slots) {
      if (s.pid.isNotEmpty || s.name.isEmpty) continue;
      final hit = _bestPokemon(s.name);
      if (hit != null) {
        s.name = hit.name;
        s.pid = hit.pid;
      }
    }
    return slots;
  }

  // 種族名へ最も近いものを score 付きで返す（cutoff 未満は null）。
  ({String name, String pid, double score})? _bestPokemon(String raw,
      {double cutoff = 0.6}) {
    final t = normalizeText(raw);
    if (t.isEmpty) return null;
    ({String name, String pid})? best;
    var bestScore = -1.0;
    for (final p in _pokemon) {
      final s = sequenceRatio(t, p.name);
      if (s > bestScore) {
        bestScore = s;
        best = p;
      }
    }
    if (best == null || bestScore < cutoff) return null;
    return (name: best.name, pid: best.pid, score: bestScore);
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

    // 名前: 左列の各行を種族名へ照合し、最もスコアの高い行を名前とする
    // （最上行決め打ちだと、OCRが名前行を崩した/別行を拾った時に誤判定する。
    //  例: ガブリアス→アリアドス。全行を種族辞書で評価して最良を選ぶ方が堅牢）。
    var nameIdx = -1;
    var nameScore = 0.0;
    for (var k = 0; k < left.length; k++) {
      final hit = _bestPokemon(left[k].text, cutoff: 0.5);
      if (hit != null && hit.score > nameScore) {
        nameScore = hit.score;
        nameIdx = k;
        s.name = hit.name;
        s.pid = hit.pid;
      }
    }
    // 特性・持ち物は名前行を除く左列から辞書照合（最初に当たったものを採用）。
    for (var k = 0; k < left.length; k++) {
      if (k == nameIdx) continue;
      final l = left[k];
      if (s.ability.isEmpty) {
        final a = closestMatch(l.text, _abilities, cutoff: 0.5);
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
    // メガストーン → 種族名 即確定（PC版 _identify_pokemon 由来の安全な保険）。
    // 持ち物が「○○ナイト(X/Y)」なら末尾を除いた語から種族を確定し、名前OCRが
    // 崩れていても正す。10組検証で無回帰を確認済み。なお PC版の多段識別の
    // 画像フォールバック（スプライト/タイプアイコン照合）は ML Kit の高精度OCR
    // と相性が悪く誤爆して逆に精度が落ちたため移植しない。
    if (s.item.contains('ナイト')) {
      final stem = s.item.replaceAll(RegExp(r'ナイト[XYＸＹxy]?$'), '').trim();
      if (stem.isNotEmpty) {
        final hit = _bestPokemon(stem, cutoff: 0.45);
        if (hit != null) {
          s.name = hit.name;
          s.pid = hit.pid;
        }
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
  // 各行で「実数値（行内の最大の妥当数値）」と性格矢印（色）を取得し、
  // 実数値から努力値(0-32)を逆算する。小さいEV(1,2)はOCRが棒の後の小数字を
  // 読み落とすため、確実に読める実数値から逆算する方が堅牢。
  void _parseStatusCard(
      cv.Mat img, cv.Rect c, List<_OcrLine> lines, MyPartySlot s) {
    final statTop = c.y + (c.height * 0.27).round();
    final bodyH = c.y + c.height - statTop;
    final rowH = bodyH ~/ 3;
    final midX = c.x + c.width / 2;
    const leftKeys = [0, 1, 2]; // H,A,B
    const rightKeys = [3, 4, 5]; // C,D,S
    final actual = List<int>.filled(6, 0); // 実数値
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
        // 実数値 = 行内の最大の妥当数値(20-999)。EVの小数字より必ず大きい。
        var mx = 0;
        for (final l in lines) {
          final cx = l.box.center.dx, cy = l.box.center.dy;
          if (cx >= x0 && cx < x1 && cy >= y0 && cy < y1) {
            for (final m in RegExp(r'\d+').allMatches(l.text)) {
              final n = int.parse(m.group(0)!);
              if (n >= 20 && n <= 999 && n > mx) mx = n;
            }
          }
        }
        actual[key] = mx;
        // 性格矢印: 行の左60%領域で 桃(↑)/水(↓) 画素数を数える。
        final rr = _safeRect(
            img, x0.round(), y0, ((x1 - x0) * 0.6).round(), rowH);
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
    // 努力値逆算（実数値→EV）。種族値は能力タブで確定した pid から、IV31/L50固定。
    final base = _baseStats[s.pid];
    if (base != null) {
      for (var i = 0; i < 6; i++) {
        if (actual[i] <= 0) {
          s.evs[i] = 0;
          continue;
        }
        final mul = up == i ? 1.1 : (down == i ? 0.9 : 1.0);
        s.evs[i] = _solveEv(actual[i], base[i], mul, i == 0);
      }
    }
    // 名前が能力タブで取れていなければステータスタブの最上行で補完。
    if (s.name.isEmpty) {
      final inCard = _linesIn(c, lines)
        ..sort((a, b) => a.box.top.compareTo(b.box.top));
      if (inCard.isNotEmpty) s.name = inCard.first.text;
    }
  }

  // アプリの実数値計算（damage_calc と同式）。L50/IV31 固定で ev 0..32 を総当たり。
  static int _calcStat(int base, int iv, int ev, int level, double mul, bool isHp) {
    final common = 2 * base + iv + 2 * ev;
    if (isHp) return (common * level) ~/ 100 + 10 + level;
    var v = (common * level) ~/ 100 + 5;
    if (mul == 1.1) {
      v = (v * 11) ~/ 10;
    } else if (mul == 0.9) {
      v = (v * 9) ~/ 10;
    }
    return v;
  }

  static int _solveEv(int actual, int base, double mul, bool isHp) {
    for (var ev = 0; ev <= 32; ev++) {
      if (_calcStat(base, 31, ev, 50, mul, isHp) == actual) return ev;
    }
    var best = 0, bd = 1 << 30; // 一致なしは最近傍
    for (var ev = 0; ev <= 32; ev++) {
      final d = (_calcStat(base, 31, ev, 50, mul, isHp) - actual).abs();
      if (d < bd) {
        bd = d;
        best = ev;
      }
    }
    return best;
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
