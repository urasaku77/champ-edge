import 'package:champ_edge_mobile/src/screens/speed_compare_dialog.dart';
import 'package:flutter_test/flutter_test.dart';

/// 素早さ比較の計算式（旧 champ-edge SpeedComparing.calc_speed と同一）の検証。
void main() {
  int calc({
    int base = 100,
    int ev = 0,
    double nature = 1.0,
    double ability = 1.0,
    double item = 1.0,
    bool tailwind = false,
    bool paralysis = false,
    int rank = 0,
  }) =>
      calcSpeedValue(
          base: base,
          ev: ev,
          nature: nature,
          ability: ability,
          item: item,
          tailwind: tailwind,
          paralysis: paralysis,
          rank: rank);

  test('基本値：種族値100・無振り＝120、最速(252振り+1.1)＝167', () {
    // floor((100*2+31+0*2)*50/100)+5 = 120
    expect(calc(), 120);
    // floor((100*2+31+32*2)*50/100)+5 = 152 → ×1.1 = 167.2 → 167
    expect(calc(ev: 32, nature: 1.1), 167);
  });

  test('ランク倍率：+1で×1.5、+2で×2、−1で×2/3', () {
    expect(calc(rank: 1), (120 * 1.5).toInt()); // 180
    expect(calc(rank: 2), 240);
    expect(calc(rank: -1), (120 * 2 / 3).toInt()); // 80
  });

  test('スカーフ×1.5・おいかぜ×2・まひ×0.5 が乗算される', () {
    expect(calc(item: 1.5), 180);
    expect(calc(tailwind: true), 240);
    expect(calc(paralysis: true), 60);
    // 併用：120×1.5×2×0.5 = 180
    expect(calc(item: 1.5, tailwind: true, paralysis: true), 180);
  });

  test('ガブリアス(S102) 最速スカーフ vs ようきマンムー(S80)+1', () {
    // ガブ: floor((204+31+64)*0.5)+5 = 154 → ×1.1×1.5 = 254.1 → 254
    final garchomp = calc(base: 102, ev: 32, nature: 1.1, item: 1.5);
    expect(garchomp, 254);
    // マンムー: floor((160+31+64)*0.5)+5 = 132 → ×1.1×1.5(rank+1) = 217.8 → 217
    final mamoswine = calc(base: 80, ev: 32, nature: 1.1, rank: 1);
    expect(mamoswine, 217);
    expect(garchomp > mamoswine, isTrue);
  });
}
