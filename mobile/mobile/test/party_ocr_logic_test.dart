import 'package:flutter_test/flutter_test.dart';
import 'package:champ_edge_mobile/src/data/party_ocr_logic.dart';
import 'package:champ_edge_mobile/src/data/fuzzy_match.dart';

void main() {
  group('parseEv', () {
    test('数字なしは0', () => expect(parseEv('まじめ'), 0));
    test('明示的な0', () => expect(parseEv('187 0'), 0));
    test('末尾 ≤32 を採用', () => expect(parseEv('187 32'), 32));
    test('連結 "18732" は末尾2桁=32', () => expect(parseEv('18732'), 32));
    test('隣接1桁2つ "2 1" は結合=21', () => expect(parseEv('216 2 1'), 21));
    test('stat<40なら連結分離しない', () => expect(parseEv('39'), 0));
    test('通常の実数値+努力値 "169 4"', () => expect(parseEv('169 4'), 4));
    test('252相当(SVは最大32表示)では ≤32 の最初', () => expect(parseEv('200 12'), 12));
  });

  group('natureFromArrows', () {
    test('A↑C↓ = いじっぱり', () => expect(natureFromArrows('A', 'C'), 'いじっぱり'));
    test('S↑C↓ = ようき', () => expect(natureFromArrows('S', 'C'), 'ようき'));
    test('C↑A↓ = ひかえめ', () => expect(natureFromArrows('C', 'A'), 'ひかえめ'));
    test('矢印なし = まじめ', () => expect(natureFromArrows(null, null), 'まじめ'));
    test('同一(無補正) = まじめ', () => expect(natureFromArrows('A', 'A'), 'まじめ'));
    test('片方欠落 = まじめ', () => expect(natureFromArrows('A', null), 'まじめ'));
  });

  group('fuzzy match', () {
    test('完全一致 ratio=1.0', () => expect(sequenceRatio('ガブリアス', 'ガブリアス'), 1.0));
    test('1文字違いでも高スコア', () {
      expect(sequenceRatio('ガブリアヌ', 'ガブリアス'), greaterThan(0.7));
    });
    test('closestMatch: OCR崩れを辞書へ寄せる', () {
      const dict = ['ガブリアス', 'マスカーニャ', 'サーフゴー', 'リザードン'];
      expect(closestMatch('ガブリアヌ', dict, cutoff: 0.6), 'ガブリアス');
    });
    test('closestMatch: cutoff未満は空', () {
      const dict = ['ガブリアス', 'リザードン'];
      expect(closestMatch('ぜんぜんちがう', dict, cutoff: 0.6), '');
    });
    test('normalize: 半角カナ→全角・空白除去', () {
      expect(normalizeText('ｶﾞﾌﾞﾘｱｽ'), 'ガブリアス');
      expect(normalizeText('リザード ン'), 'リザードン');
    });
  });
}
