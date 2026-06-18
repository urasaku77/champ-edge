import 'package:champ_edge_mobile/src/service/adder.dart';
import 'package:flutter_test/flutter_test.dart';

/// 加算ツールのロジック（原典 MultiWazaDamageWindow._calc_ko_text 移植）の検証。
void main() {
  List<int> uniform(int v) => List<int>.filled(16, v);

  test('単発で全16値がしきい値以上なら確定KO', () {
    final s = AdderSession(hp: 100, effectiveHp: 100);
    s.pressMove('A', uniform(100));
    expect(s.koText, '確定KO');
    expect(s.totalMin, 100);
    expect(s.totalMax, 100);
  });

  test('16値中8つがしきい値以上なら乱数KO (50.0%)', () {
    final s = AdderSession(hp: 100, effectiveHp: 100);
    s.pressMove('A', [...List.filled(8, 99), ...List.filled(8, 100)]);
    expect(s.koText, '乱数KO (50.0%)');
  });

  test('2技の直積：99+99=198<200 のみ外れ → 乱数KO', () {
    final s = AdderSession(hp: 200, effectiveHp: 200);
    final dmg = [...List.filled(8, 99), ...List.filled(8, 101)];
    s.pressMove('A', dmg);
    s.pressMove('B', dmg);
    // 99+99(64通り)のみ198<200。256-64=192/256 = 75%
    expect(s.koText, '乱数KO (75.0%)');
    expect(s.totalMin, 198);
    expect(s.totalMax, 202);
  });

  test('回復はしきい値に加算され、合計から減算される', () {
    final s = AdderSession(hp: 160, effectiveHp: 160);
    s.pressMove('A', uniform(170));
    expect(s.koText, '確定KO');
    // たべのこし 160/16=10 回復 → しきい値170 ちょうど＝KO（>=）
    s.pressHeal('たべのこし', 1, 16);
    expect(s.totalHeal, 10);
    expect(s.koText, '確定KO');
    expect(s.totalMin, 160); // 170-10
    // オボン 160/4=40 → しきい値210 > 170 で外れる
    s.pressHeal('オボンのみ', 1, 4);
    expect(s.koText, '');
  });

  test('行削除とクリア', () {
    final s = AdderSession(hp: 100, effectiveHp: 100);
    s.pressMove('A', uniform(60));
    s.pressMove('B', uniform(60));
    expect(s.koText, '確定KO'); // 120 >= 100
    s.removeAt(1);
    expect(s.koText, ''); // 60 < 100
    s.clear();
    expect(s.entries, isEmpty);
    expect(s.koText, '');
  });

  test('実効HP（ステルスロック差引）でしきい値が下がる', () {
    // HP100・ステロで実効HP88相当
    final s = AdderSession(hp: 100, effectiveHp: 88);
    s.pressMove('A', uniform(90));
    expect(s.koText, '確定KO'); // 90 >= 88
  });
}
