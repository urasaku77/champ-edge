/// Python の difflib.SequenceMatcher 相当の曖昧一致（Ratcliff/Obershelp）。
///
/// image_parser.py の `_closest_match`（difflib.get_close_matches）を Dart へ移植したもの。
/// OCR で崩れたポケモン名・特性・技・道具名を辞書へ寄せるのに使う。
library;

/// 文字列正規化：前後空白除去・半角カナを全角化・空白(半/全)を除去。
/// jaconv.h2z(kana) 相当（濁点・半濁点の合成も処理）。
String normalizeText(String input) {
  var s = input.trim();
  s = _halfToFullKana(s);
  s = s.replaceAll(' ', '').replaceAll('　', '');
  return s;
}

// 半角カナ(U+FF61–U+FF9F)→全角。濁点/半濁点は直前の文字に合成する。
const Map<String, String> _kanaBase = {
  '｡': '。', '｢': '「', '｣': '」', '､': '、', '･': '・', 'ｰ': 'ー',
  'ｱ': 'ア', 'ｲ': 'イ', 'ｳ': 'ウ', 'ｴ': 'エ', 'ｵ': 'オ',
  'ｶ': 'カ', 'ｷ': 'キ', 'ｸ': 'ク', 'ｹ': 'ケ', 'ｺ': 'コ',
  'ｻ': 'サ', 'ｼ': 'シ', 'ｽ': 'ス', 'ｾ': 'セ', 'ｿ': 'ソ',
  'ﾀ': 'タ', 'ﾁ': 'チ', 'ﾂ': 'ツ', 'ﾃ': 'テ', 'ﾄ': 'ト',
  'ﾅ': 'ナ', 'ﾆ': 'ニ', 'ﾇ': 'ヌ', 'ﾈ': 'ネ', 'ﾉ': 'ノ',
  'ﾊ': 'ハ', 'ﾋ': 'ヒ', 'ﾌ': 'フ', 'ﾍ': 'ヘ', 'ﾎ': 'ホ',
  'ﾏ': 'マ', 'ﾐ': 'ミ', 'ﾑ': 'ム', 'ﾒ': 'メ', 'ﾓ': 'モ',
  'ﾔ': 'ヤ', 'ﾕ': 'ユ', 'ﾖ': 'ヨ',
  'ﾗ': 'ラ', 'ﾘ': 'リ', 'ﾙ': 'ル', 'ﾚ': 'レ', 'ﾛ': 'ロ',
  'ﾜ': 'ワ', 'ｦ': 'ヲ', 'ﾝ': 'ン',
  'ｧ': 'ァ', 'ｨ': 'ィ', 'ｩ': 'ゥ', 'ｪ': 'ェ', 'ｫ': 'ォ',
  'ｬ': 'ャ', 'ｭ': 'ュ', 'ｮ': 'ョ', 'ｯ': 'ッ',
};
// 濁点が付く全角カナ（base → 濁音）。
const Map<String, String> _dakuten = {
  'カ': 'ガ', 'キ': 'ギ', 'ク': 'グ', 'ケ': 'ゲ', 'コ': 'ゴ',
  'サ': 'ザ', 'シ': 'ジ', 'ス': 'ズ', 'セ': 'ゼ', 'ソ': 'ゾ',
  'タ': 'ダ', 'チ': 'ヂ', 'ツ': 'ヅ', 'テ': 'デ', 'ト': 'ド',
  'ハ': 'バ', 'ヒ': 'ビ', 'フ': 'ブ', 'ヘ': 'ベ', 'ホ': 'ボ',
  'ウ': 'ヴ',
};
const Map<String, String> _handakuten = {
  'ハ': 'パ', 'ヒ': 'ピ', 'フ': 'プ', 'ヘ': 'ペ', 'ホ': 'ポ',
};

String _halfToFullKana(String s) {
  final out = StringBuffer();
  String? prev;
  for (final ch in s.split('')) {
    if (ch == 'ﾞ' && prev != null && _dakuten.containsKey(prev)) {
      // 直前を濁音へ置換
      final str = out.toString();
      out.clear();
      out.write(str.substring(0, str.length - prev.length));
      final dak = _dakuten[prev]!;
      out.write(dak);
      prev = dak;
      continue;
    }
    if (ch == 'ﾟ' && prev != null && _handakuten.containsKey(prev)) {
      final str = out.toString();
      out.clear();
      out.write(str.substring(0, str.length - prev.length));
      final han = _handakuten[prev]!;
      out.write(han);
      prev = han;
      continue;
    }
    final mapped = _kanaBase[ch] ?? ch;
    out.write(mapped);
    prev = mapped;
  }
  return out.toString();
}

/// difflib.SequenceMatcher.ratio() 相当（Ratcliff/Obershelp）。0.0–1.0。
/// 一致ブロックを再帰的に求め、2*M/T を返す（M=一致文字総数, T=両長合計）。
double sequenceRatio(String a, String b) {
  final la = a.length, lb = b.length;
  if (la == 0 && lb == 0) return 1.0;
  final matches = _matchCount(a, 0, la, b, 0, lb);
  return 2.0 * matches / (la + lb);
}

int _matchCount(String a, int alo, int ahi, String b, int blo, int bhi) {
  final (i, j, k) = _longestMatch(a, alo, ahi, b, blo, bhi);
  if (k == 0) return 0;
  return k +
      _matchCount(a, alo, i, b, blo, j) +
      _matchCount(a, i + k, ahi, b, j + k, bhi);
}

// [alo,ahi) × [blo,bhi) の最長一致ブロック (i, j, size) を返す。
(int, int, int) _longestMatch(
    String a, int alo, int ahi, String b, int blo, int bhi) {
  var bestI = alo, bestJ = blo, bestSize = 0;
  // j2len[j] = a[i] で終わる b[..j] との連続一致長
  var j2len = <int, int>{};
  for (var i = alo; i < ahi; i++) {
    final newj2len = <int, int>{};
    for (var j = blo; j < bhi; j++) {
      if (a.codeUnitAt(i) == b.codeUnitAt(j)) {
        final k = (j2len[j - 1] ?? 0) + 1;
        newj2len[j] = k;
        if (k > bestSize) {
          bestI = i - k + 1;
          bestJ = j - k + 1;
          bestSize = k;
        }
      }
    }
    j2len = newj2len;
  }
  return (bestI, bestJ, bestSize);
}

/// 候補から最も近いものを返す。cutoff 未満なら ''。
/// difflib.get_close_matches(text, candidates, n=1, cutoff) 相当。
String closestMatch(String text, List<String> candidates,
    {double cutoff = 0.45}) {
  final t = normalizeText(text);
  if (t.isEmpty || candidates.isEmpty) return '';
  var best = '';
  var bestScore = -1.0;
  for (final c in candidates) {
    final score = sequenceRatio(t, c);
    if (score > bestScore) {
      bestScore = score;
      best = c;
    }
  }
  return bestScore >= cutoff ? best : '';
}
