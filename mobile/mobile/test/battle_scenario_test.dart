import 'package:champ_edge_mobile/src/model/battle_pokemon.dart';
import 'package:champ_edge_mobile/src/service/damage_engine.dart';
import 'package:flutter_test/flutter_test.dart';

/// UI（対戦画面）が使う `BattlePokemon.toAttacker/toDefender` → `DamageCalc`
/// の経路を直接叩き、各トグル（やけど・じゅうでん・壁・天候・砂嵐岩特防・
/// ランク・性格）がダメージへ正しく反映されることを検証する。
///
/// エンジン本体の数値正当性は damage_calc_test.dart（250/250）で担保済み。
/// 本テストは「UI のモデル配線が計算へ届くか」を回帰的に守るのが目的。
void main() {
  // 物理ほのお技（攻撃側 type と一致＝タイプ一致補正あり）。
  BattleMove firePhysical() => const BattleMove(
        name: 'フレアドライブ',
        type: PokeType.fire,
        category: MoveCategory.physical,
        power: 120,
      );

  // 特殊技（砂嵐・岩特防の検証用。相性等倍になるノーマル特殊）。
  BattleMove normalSpecial() => const BattleMove(
        name: 'はかいこうせん',
        type: PokeType.normal,
        category: MoveCategory.special,
        power: 90,
      );

  // でんき特殊技（じゅうでん検証用）。
  BattleMove electricSpecial() => const BattleMove(
        name: '10まんボルト',
        type: PokeType.electric,
        category: MoveCategory.special,
        power: 90,
      );

  // 攻撃側：ほのお単タイプ（フレアドライブにタイプ一致）。
  BattlePokemon attacker({
    String nature = 'まじめ',
    Ailment status = Ailment.none,
    bool charging = false,
    List<int>? boosts,
  }) =>
      BattlePokemon(
        name: 'こうげき',
        pid: '0006-0',
        baseStats: [78, 130, 78, 130, 85, 100],
        type1: PokeType.fire,
        abilityOptions: const ['もうか'],
        ability: 'もうか',
        nature: nature,
        status: status,
        charging: charging,
        boosts: boosts,
        ev: List<int>.filled(6, 0),
        moves: [firePhysical()],
      );

  // 防御側：ノーマル単（壁・天候検証用）。岩テストは type1 を差し替える。
  BattlePokemon defender({
    PokeType type1 = PokeType.normal,
    Wall wall = Wall.none,
  }) =>
      BattlePokemon(
        name: 'ぼうぎょ',
        pid: '0143-0',
        baseStats: [160, 110, 65, 65, 110, 30],
        type1: type1,
        abilityOptions: const ['めんえき'],
        ability: 'めんえき',
        wall: wall,
        ev: List<int>.filled(6, 0),
        moves: [emptyMove()],
      );

  int maxDmg(BattlePokemon atk, BattlePokemon def, BattleMove mv,
          {FieldState field = const FieldState()}) =>
      DamageCalc.calculateDamage(
        atk.toAttacker(),
        def.toDefender(),
        mv.toMoveState(critical: atk.critical),
        field,
      ).maxDamage;

  test('やけど：物理技ダメージが約半減する', () {
    final normal = maxDmg(attacker(), defender(), firePhysical());
    final burned =
        maxDmg(attacker(status: Ailment.burn), defender(), firePhysical());
    expect(burned, lessThan(normal));
    // 約 1/2（端数・補正で完全な半分にはならないため幅を持たせる）。
    expect(burned, closeTo(normal / 2, normal * 0.08));
  });

  test('じゅうでん：でんき技の威力が2倍 → ダメージ増', () {
    final base = maxDmg(attacker(), defender(), electricSpecial());
    final charged =
        maxDmg(attacker(charging: true), defender(), electricSpecial());
    expect(charged, greaterThan(base));
  });

  test('壁（リフレクター）：物理技ダメージが半減する', () {
    final noWall = maxDmg(attacker(), defender(), firePhysical());
    final withWall =
        maxDmg(attacker(), defender(wall: Wall.reflect), firePhysical());
    expect(withWall, lessThan(noWall));
    expect(withWall, closeTo(noWall / 2, noWall * 0.08));
  });

  test('天候 雨：ほのお技が弱化、みず強化方向（ほのおは減）', () {
    final clear = maxDmg(attacker(), defender(), firePhysical());
    final rain = maxDmg(attacker(), defender(), firePhysical(),
        field: const FieldState(weather: Weather.rainy));
    expect(rain, lessThan(clear));
  });

  test('砂嵐 × 岩タイプ防御：特防1.5倍で特殊ダメージが減る', () {
    final rockDef = defender(type1: PokeType.rock);
    final clear = maxDmg(attacker(), rockDef, normalSpecial());
    final sand = maxDmg(attacker(), rockDef, normalSpecial(),
        field: const FieldState(weather: Weather.sandstorm));
    expect(sand, lessThan(clear));
  });

  test('ランク +2（こうげき）：物理ダメージが増える', () {
    final base = maxDmg(attacker(), defender(), firePhysical());
    final boosted = maxDmg(
        attacker(boosts: [0, 2, 0, 0, 0, 0]), defender(), firePhysical());
    expect(boosted, greaterThan(base));
  });

  test('性格 いじっぱり（A↑C↓）：物理実数値が上がりダメージ増', () {
    final neutral = maxDmg(attacker(nature: 'まじめ'), defender(), firePhysical());
    final adamant =
        maxDmg(attacker(nature: 'いじっぱり'), defender(), firePhysical());
    expect(adamant, greaterThan(neutral));
  });

  test('努力値（こうげき 0→32）：実数値が上がりダメージ増', () {
    final base = attacker();
    final invested = attacker()..ev = [0, 32, 0, 0, 0, 0];
    expect(invested.stats[1], greaterThan(base.stats[1])); // A 実数値増
    expect(maxDmg(invested, defender(), firePhysical()),
        greaterThan(maxDmg(base, defender(), firePhysical())));
  });

  test('急所：ダメージが増える（1.5倍・有利ランク無視）', () {
    final base = attacker();
    final crit = attacker()..critical = true;
    expect(maxDmg(crit, defender(), firePhysical()),
        greaterThan(maxDmg(base, defender(), firePhysical())));
  });

  test('定数ダメージ：表示ダメージにチップ floor(HP/8) が加算される', () {
    final base = maxDmg(attacker(), defender(), firePhysical());
    final withConst = defender()..constantDamage = 1 / 8;
    final c = maxDmg(attacker(), withConst, firePhysical());
    expect(c - base, (withConst.hp / 8).floor());
  });

  test('連続技 multiHit：回数を増やすとダメージが増える', () {
    const seed = BattleMove(
        name: 'タネマシンガン',
        type: PokeType.grass,
        category: MoveCategory.physical,
        power: 25);
    expect(seed.hasEffect, isTrue);
    expect(seed.currentEffectValue, 3); // 既定3発
    final d3 = maxDmg(attacker(), defender(), seed);
    final d2 = maxDmg(attacker(), defender(), seed.copyWith(effectValue: 2));
    expect(d3, greaterThan(d2));
  });

  test('威力増加 addPower：倍率を上げるとダメージが増える', () {
    const acro = BattleMove(
        name: 'アクロバット',
        type: PokeType.flying,
        category: MoveCategory.physical,
        power: 55);
    expect(acro.currentEffectValue, 2.0); // 既定×2
    final x2 = maxDmg(attacker(), defender(), acro);
    final x1 = maxDmg(attacker(), defender(), acro.copyWith(effectValue: 1.0));
    expect(x2, greaterThan(x1));
  });
}
