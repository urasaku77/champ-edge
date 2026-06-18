import 'package:champ_edge_mobile/src/model/battle_pokemon.dart';
import 'package:champ_edge_mobile/src/service/damage_engine.dart';
import 'package:flutter_test/flutter_test.dart';

/// テラスは当面対象外（P4）。`tera` が設定されていてもダメージ計算に影響しないこと。
void main() {
  BattlePokemon gabu(PokeType tera) => BattlePokemon(
        name: 'ガブリアス',
        pid: '0445-0',
        baseStats: const [108, 130, 95, 80, 85, 102],
        type1: PokeType.dragon,
        type2: PokeType.ground,
        tera: tera,
        abilityOptions: const ['すながくれ'],
        moves: [emptyMove()],
      );
  final atk = BattlePokemon(
    name: 'アタッカー',
    pid: '0001-0',
    baseStats: const [100, 100, 100, 130, 100, 100],
    type1: PokeType.normal,
    abilityOptions: const ['—'],
    moves: [emptyMove()],
  );
  const fighting = BattleMove(
      name: 'はどうだん',
      type: PokeType.fighting,
      category: MoveCategory.special,
      power: 80);

  int dmg(BattlePokemon def) => DamageCalc.calculateDamage(atk.toAttacker(),
          def.toDefender(), fighting.toMoveState(), const FieldState())
      .maxDamage;

  test('tera=steel でも かくとう技は等倍（テラス無効）', () {
    // 本来 はがねテラスなら かくとう2倍だが、テラス対象外なので ドラゴン/じめん の等倍のまま。
    expect(dmg(gabu(PokeType.steel)), dmg(gabu(PokeType.none)));
  });
}
