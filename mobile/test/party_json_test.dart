import 'dart:convert';

import 'package:champ_edge_mobile/src/model/battle_pokemon.dart';
import 'package:champ_edge_mobile/src/service/damage_engine.dart';
import 'package:flutter_test/flutter_test.dart';

/// パーティ永続化（JSON）の往復で全フィールドが保たれることを検証する。
void main() {
  test('BattlePokemon は JSON 往復で同値に復元される', () {
    final original = BattlePokemon(
      name: 'ガブリアス',
      pid: '0445-0',
      baseStats: const [108, 130, 95, 80, 85, 102],
      type1: PokeType.dragon,
      type2: PokeType.ground,
      tera: PokeType.fire,
      abilityOptions: const ['すながくれ', 'さめはだ'],
      ability: 'さめはだ',
      item: 'いのちのたま',
      nature: 'ようき',
      status: Ailment.burn,
      charging: true,
      critical: true,
      smackdown: true,
      wall: Wall.reflect,
      constantDamage: 0.1875,
      hasStealthRock: true,
      ev: const [4, 32, 0, 0, 8, 32],
      boosts: const [0, 2, 0, 0, -1, 1],
      moves: [
        const BattleMove(
            name: 'じしん',
            type: PokeType.ground,
            category: MoveCategory.physical,
            power: 100),
        emptyMove(),
        emptyMove(),
        emptyMove(),
      ],
    )..abilityDisabled = true;

    // JSON 文字列を介して往復（実ファイル保存と同じ経路）。
    final restored = BattlePokemon.fromJson(
        jsonDecode(jsonEncode(original.toJson())) as Map<String, dynamic>);

    expect(restored.name, original.name);
    expect(restored.pid, original.pid);
    expect(restored.baseStats, original.baseStats);
    expect(restored.type1, original.type1);
    expect(restored.type2, original.type2);
    expect(restored.tera, original.tera);
    expect(restored.abilityOptions, original.abilityOptions);
    expect(restored.ability, original.ability);
    expect(restored.item, original.item);
    expect(restored.nature, original.nature);
    expect(restored.status, original.status);
    expect(restored.charging, original.charging);
    expect(restored.critical, original.critical);
    expect(restored.smackdown, original.smackdown);
    expect(restored.wall, original.wall);
    expect(restored.constantDamage, original.constantDamage);
    expect(restored.hasStealthRock, original.hasStealthRock);
    expect(restored.ev, original.ev);
    expect(restored.boosts, original.boosts);
    expect(restored.abilityDisabled, isTrue);
    expect(restored.moves.first.name, 'じしん');
    expect(restored.moves.first.power, 100);
    // 実数値（性格・努力値込み）も一致する。
    expect(restored.stats, original.stats);
  });

  test('snapshot/applySnapshot で状態が復元される（メタモンへんしん用）', () {
    final p = BattlePokemon(
      name: 'メタモン',
      pid: '0132-0',
      baseStats: const [48, 48, 48, 48, 48, 48],
      type1: PokeType.normal,
      abilityOptions: const ['じゅうなん'],
      moves: [emptyMove()],
    );
    final snap = p.snapshot();
    // へんしん相当に改変
    p.name = 'ガブリアス';
    p.baseStats = [48, 130, 95, 80, 85, 102];
    p.type1 = PokeType.dragon;
    p.type2 = PokeType.ground;
    p.moves = [
      const BattleMove(
          name: 'じしん',
          type: PokeType.ground,
          category: MoveCategory.physical,
          power: 100)
    ];
    // 復元
    p.applySnapshot(snap);
    expect(p.name, 'メタモン');
    expect(p.baseStats, [48, 48, 48, 48, 48, 48]);
    expect(p.type1, PokeType.normal);
    expect(p.type2, PokeType.none);
    expect(p.moves.first.isEmpty, isTrue);
  });
}
