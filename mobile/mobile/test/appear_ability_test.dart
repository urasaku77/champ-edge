import 'package:champ_edge_mobile/src/model/battle_pokemon.dart';
import 'package:champ_edge_mobile/src/service/appear_ability.dart';
import 'package:champ_edge_mobile/src/service/damage_engine.dart';
import 'package:flutter_test/flutter_test.dart';

BattlePokemon _mk(String name,
    {String? ability,
    List<int> baseStats = const [100, 100, 100, 100, 100, 100]}) {
  return BattlePokemon(
    name: name,
    pid: '0001-0',
    baseStats: baseStats,
    type1: PokeType.normal,
    abilityOptions: ability == null ? const ['—'] : [ability],
    ability: ability,
    moves: [emptyMove()],
  );
}

void main() {
  test('いかくは相手の攻撃ランクを-1する', () {
    final p = _mk('ガオガエン', ability: 'いかく');
    final opp = _mk('カビゴン', ability: 'あついしぼう');
    applyAppearAbility(p, opp);
    expect(opp.boosts[1], -1);
    expect(p.appearRankApplied, isTrue);
  });

  test('いかくのポケモンが場を離れても相手の-1は残る（適用側は戻さない）', () {
    final p = _mk('ガオガエン', ability: 'いかく');
    final opp = _mk('カビゴン', ability: 'あついしぼう');
    applyAppearAbility(p, opp);
    expect(opp.boosts[1], -1);
    // いかくのポケモンが引っ込む → 相手の-1は残る。フラグだけ下りる。
    resetAppearAbility(p);
    expect(opp.boosts[1], -1, reason: '相手に入れたランクは相手が場を離れるまで残す');
    expect(p.appearRankApplied, isFalse);
  });

  test('登場時ランク特性を無効化すると適用されない', () {
    final p = _mk('ガオガエン', ability: 'いかく')..abilityDisabled = true;
    final opp = _mk('カビゴン', ability: 'あついしぼう');
    applyAppearAbility(p, opp);
    expect(opp.boosts[1], 0);
    expect(p.appearRankApplied, isFalse);
  });

  test('ふとうのけんは自分の攻撃+1、ふくつのたては自分の防御+1', () {
    final sword = _mk('ザシアン', ability: 'ふとうのけん');
    final shield = _mk('ザマゼンタ', ability: 'ふくつのたて');
    final opp = _mk('カビゴン');
    applyAppearAbility(sword, opp);
    applyAppearAbility(shield, opp);
    expect(sword.boosts[1], 1);
    expect(shield.boosts[2], 1);
  });

  test('ダウンロード：相手の防御<特防なら攻撃+1、そうでなければ特攻+1', () {
    // 防御が低い相手 → こうげき(+1)
    final lowDef = _mk('ポリゴン2', ability: 'ダウンロード');
    final defLow = _mk('A', baseStats: const [100, 100, 50, 100, 150, 100]);
    applyAppearAbility(lowDef, defLow);
    expect(lowDef.boosts[1], 1);
    expect(lowDef.boosts[3], 0);
    // 特防が低い相手 → とくこう(+1)
    final lowSpd = _mk('ポリゴン2', ability: 'ダウンロード');
    final spdLow = _mk('B', baseStats: const [100, 100, 150, 100, 50, 100]);
    applyAppearAbility(lowSpd, spdLow);
    expect(lowSpd.boosts[3], 1);
    expect(lowSpd.boosts[1], 0);
  });

  test('適用済みフラグで二重適用されない', () {
    final p = _mk('ガオガエン', ability: 'いかく');
    final opp = _mk('カビゴン');
    applyAppearAbility(p, opp);
    applyAppearAbility(p, opp); // 2回目は無視
    expect(opp.boosts[1], -1);
  });
}
