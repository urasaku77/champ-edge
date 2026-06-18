import 'package:champ_edge_mobile/src/model/battle_pokemon.dart';
import 'package:champ_edge_mobile/src/screens/weight_compare_dialog.dart';
import 'package:champ_edge_mobile/src/service/damage_engine.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  test('重量比からヘビーボンバー威力（原典 calc_power と同一閾値）', () {
    expect(heavySlamPower(0.19), 120);
    expect(heavySlamPower(0.24), 100);
    expect(heavySlamPower(0.29), 80);
    expect(heavySlamPower(0.49), 60);
    expect(heavySlamPower(0.5), 40);
    expect(heavySlamPower(1.5), 40);
  });

  test('BattlePokemon.weight がエンジンへ渡りヘビーボンバーの威力に反映される', () {
    BattlePokemon mk(String name, double weight) => BattlePokemon(
          name: name,
          pid: '0001-0',
          baseStats: const [100, 100, 100, 100, 100, 100],
          type1: PokeType.steel,
          abilityOptions: const ['—'],
          weight: weight,
          moves: [emptyMove()],
        );
    const move = BattleMove(
        name: 'ヘビーボンバー',
        type: PokeType.steel,
        category: MoveCategory.physical,
        power: 40);

    final heavy = mk('コスモウム', 999.9); // 最重量
    final light = mk('フワンテ', 1.2);
    final sameW = mk('同重量', 999.9);
    const field = FieldState();

    final vsLight = DamageCalc.calculateDamage(
        heavy.toAttacker(), light.toDefender(), move.toMoveState(), field);
    final vsSame = DamageCalc.calculateDamage(
        heavy.toAttacker(), sameW.toDefender(), move.toMoveState(), field);
    // 重量比 999.9/1.2 → 威力120、同重量 → 威力40。ダメージが大きく異なる。
    expect(vsLight.maxDamage > vsSame.maxDamage * 2, isTrue,
        reason: '軽い相手への威力(120)は同重量(40)の3倍のはず');
  });

  test('weight は JSON 往復で保存される', () {
    final p = BattlePokemon(
      name: 'カビゴン',
      pid: '0143-0',
      baseStats: const [160, 110, 65, 65, 110, 30],
      type1: PokeType.normal,
      abilityOptions: const ['あついしぼう'],
      weight: 460.0,
      moves: [emptyMove()],
    );
    final restored = BattlePokemon.fromJson(p.toJson());
    expect(restored.weight, 460.0);
  });
}
