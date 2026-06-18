import 'package:champ_edge_mobile/src/data/home_stats.dart';
import 'package:flutter_test/flutter_test.dart';

/// HOME 努力値文字列（"H2A32S32" 等）→ [H,A,B,C,D,S] のパースを検証する。
void main() {
  test('parseDoryoku: A32S32', () {
    expect(HomeStats.parseDoryoku('A32S32'), [0, 32, 0, 0, 0, 32]);
  });

  test('parseDoryoku: H2A32S32（合計66の代表型）', () {
    final ev = HomeStats.parseDoryoku('H2A32S32');
    expect(ev, [2, 32, 0, 0, 0, 32]);
    expect(ev.reduce((a, b) => a + b), 66);
  });

  test('parseDoryoku: 全能力', () {
    expect(HomeStats.parseDoryoku('H4A8B12C16D20S24'), [4, 8, 12, 16, 20, 24]);
  });

  test('parseDoryoku: 空文字は全0', () {
    expect(HomeStats.parseDoryoku(''), [0, 0, 0, 0, 0, 0]);
  });
}
