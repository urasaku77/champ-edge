import 'package:champ_edge_mobile/src/data/ability_values.dart';
import 'package:champ_edge_mobile/src/model/battle_pokemon.dart';
import 'package:champ_edge_mobile/src/service/damage_engine.dart';
import 'package:flutter_test/flutter_test.dart';

BattlePokemon _mk(String ability) => BattlePokemon(
      name: 'テスト',
      pid: '0001-0',
      baseStats: const [100, 100, 100, 100, 100, 100],
      type1: PokeType.normal,
      abilityOptions: [ability],
      moves: [emptyMove()],
    );

const _move = BattleMove(
    name: 'たいあたり',
    type: PokeType.normal,
    category: MoveCategory.physical,
    power: 100);

DamageResult _calc(BattlePokemon atk, BattlePokemon def) =>
    DamageCalc.calculateDamage(atk.toAttacker(), def.toDefender(),
        _move.toMoveState(), const FieldState());

void main() {
  test('デフォルト値：ふかしのこぶし=無効、マルチスケイル=有効、テーブル外=空', () {
    expect(defaultAbilityValue('ふかしのこぶし'), '無効');
    expect(defaultAbilityValue('マルチスケイル'), '有効');
    expect(defaultAbilityValue('いかく'), '');
    expect(_mk('ふかしのこぶし').abilityValue, '無効');
    expect(_mk('マルチスケイル').abilityValue, '有効');
  });

  test('特性を変更するとデフォルト値へリセットされる', () {
    final p = _mk('ふかしのこぶし');
    p.abilityValue = '有効';
    p.ability = 'マルチスケイル';
    expect(p.abilityValue, '有効'); // マルチスケイルのデフォルト
    p.ability = 'ふかしのこぶし';
    expect(p.abilityValue, '無効'); // リセット
  });

  test('abilityValue は JSON 往復で保存される', () {
    final p = _mk('ふかしのこぶし')..abilityValue = '有効';
    final restored = BattlePokemon.fromJson(p.toJson());
    expect(restored.ability, 'ふかしのこぶし');
    expect(restored.abilityValue, '有効');
  });

  test('ふかしのこぶし有効でダメージが1/4になる', () {
    final def = _mk('—');
    final off = _calc(_mk('ふかしのこぶし'), def); // 無効（デフォルト）
    final on = _calc(_mk('ふかしのこぶし')..abilityValue = '有効', def);
    expect(on.maxDamage, lessThan(off.maxDamage));
    // ×1024/4096 = 1/4（端数処理で±1許容）
    expect((on.maxDamage - off.maxDamage / 4).abs() <= 1, isTrue,
        reason: '${off.maxDamage} → ${on.maxDamage}');
  });

  test('防御側マルチスケイル（デフォルト有効）で被ダメージ半減・無効で戻る', () {
    final atk = _mk('—');
    final on = _calc(atk, _mk('マルチスケイル'));
    final off = _calc(atk, _mk('マルチスケイル')..abilityValue = '無効');
    expect(on.maxDamage, lessThan(off.maxDamage));
    expect((on.maxDamage - off.maxDamage / 2).abs() <= 1, isTrue,
        reason: '${off.maxDamage} vs ${on.maxDamage}');
  });
}
