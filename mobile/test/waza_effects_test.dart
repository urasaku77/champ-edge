import 'package:champ_edge_mobile/src/data/waza_effects.dart';
import 'package:champ_edge_mobile/src/model/battle_pokemon.dart';
import 'package:champ_edge_mobile/src/screens/home_screen.dart';
import 'package:champ_edge_mobile/src/service/damage_engine.dart';
import 'package:flutter_test/flutter_test.dart';

BattlePokemon _mk({String ability = 'A', Wall wall = Wall.none}) => BattlePokemon(
      name: 'p',
      pid: '0001-0',
      baseStats: const [100, 100, 100, 100, 100, 100],
      type1: PokeType.normal,
      abilityOptions: [ability],
      ability: ability,
      wall: wall,
      moves: [emptyMove()],
    );

/// 技効果テーブル（ランク変化・タイプ変更）と段階差分パーサの検証。
void main() {
  test('parseRankSpec: 単一/複合', () {
    expect(parseRankSpec('A+2'), [0, 2, 0, 0, 0, 0]);
    expect(parseRankSpec('AS+1'), [0, 1, 0, 0, 0, 1]);
    expect(parseRankSpec('ACS+2 BD-1'), [0, 2, -1, 2, -1, 2]);
    expect(parseRankSpec('S-1'), [0, 0, 0, 0, 0, -1]);
  });

  test('自分ランク上昇技：つるぎのまい=A+2', () {
    final e = wazaEffectOf('つるぎのまい');
    expect(e.kind, WazaEffectKind.selfRank);
    expect(e.rankDelta, [0, 2, 0, 0, 0, 0]);
    expect(e.targetOpponent, isFalse);
    expect(e.isToggle, isTrue);
    expect(e.next(0), 1); // トグル
    expect(e.next(1), 0);
  });

  test('相手ランク下降技：あまえる=A-2（相手対象）', () {
    final e = wazaEffectOf('あまえる');
    expect(e.kind, WazaEffectKind.opponentRank);
    expect(e.rankDelta, [0, -2, 0, 0, 0, 0]);
    expect(e.targetOpponent, isTrue);
  });

  test('タイプ変更技：みずびたし=相手みず／もえつきる=自分ほのお除去', () {
    final mizu = wazaEffectOf('みずびたし');
    expect(mizu.kind, WazaEffectKind.typeChange);
    expect(mizu.changeType, PokeType.water);
    expect(mizu.removeType, isFalse);
    expect(mizu.targetOpponent, isTrue);

    final moe = wazaEffectOf('もえつきる');
    expect(moe.kind, WazaEffectKind.typeChange);
    expect(moe.changeType, PokeType.fire);
    expect(moe.removeType, isTrue);
    expect(moe.targetOpponent, isFalse);
  });

  test('既存の威力・回数効果は維持（タネマシンガン=連続技、きょけんとつげき=addPower）', () {
    expect(wazaEffectOf('タネマシンガン').kind, WazaEffectKind.multiHit);
    expect(wazaEffectOf('きょけんとつげき').kind, WazaEffectKind.addPower);
    expect(wazaEffectOf('じしん').kind, WazaEffectKind.addPower);
    expect(wazaEffectOf('みやぶる').kind, WazaEffectKind.none); // 無効果
  });

  test('other_effect 系：じこあんじ/スキルスワップ/コートチェンジ/オーラぐるま', () {
    expect(wazaEffectOf('じこあんじ').kind, WazaEffectKind.copyBoosts);
    expect(wazaEffectOf('スキルスワップ').kind, WazaEffectKind.swapAbility);
    expect(wazaEffectOf('コートチェンジ').kind, WazaEffectKind.swapField);
    final aura = wazaEffectOf('オーラぐるま');
    expect(aura.kind, WazaEffectKind.moveTypeChange);
    expect(aura.changeType, PokeType.dark);
    expect(aura.isToggle, isTrue);
  });

  test('オーラぐるま：ON で技タイプが あく になる（toMoveState）', () {
    const move = BattleMove(
        name: 'オーラぐるま',
        type: PokeType.electric,
        category: MoveCategory.physical,
        power: 110);
    expect(move.toMoveState().type, PokeType.electric); // OFF
    expect(move.copyWith(effectValue: 1).toMoveState().type, PokeType.dark);
  });

  test('applyMoveToggle: スキルスワップで特性入替・解除で戻る', () {
    final a = _mk(ability: 'いかく');
    final d = _mk(ability: 'ちくでん');
    final e = wazaEffectOf('スキルスワップ');
    applyMoveToggle(e, a, d, true);
    expect(a.ability, 'ちくでん');
    expect(d.ability, 'いかく');
    applyMoveToggle(e, a, d, false); // 自己逆
    expect(a.ability, 'いかく');
    expect(d.ability, 'ちくでん');
  });

  test('applyMoveToggle: じこあんじで相手ランクをコピー・解除で復元', () {
    final a = _mk()..boosts[1] = 1; // 自分 A+1
    final d = _mk()..boosts[1] = 3; // 相手 A+3
    final e = wazaEffectOf('じこあんじ');
    applyMoveToggle(e, a, d, true);
    expect(a.boosts[1], 3); // コピー
    applyMoveToggle(e, a, d, false);
    expect(a.boosts[1], 1); // 復元
  });

  test('applyMoveToggle: コートチェンジで壁を入替', () {
    final a = _mk(wall: Wall.reflect);
    final d = _mk(wall: Wall.none);
    final e = wazaEffectOf('コートチェンジ');
    applyMoveToggle(e, a, d, true);
    expect(a.wall, Wall.none);
    expect(d.wall, Wall.reflect);
  });

  test('スキルリンク：連続技の回数が最大(5)で計算される', () {
    const seed = BattleMove(
        name: 'タネマシンガン',
        type: PokeType.grass,
        category: MoveCategory.physical,
        power: 25);
    expect(seed.toMoveState().multiHit, 3); // 既定3
    expect(seed.toMoveState(skillLink: true).multiHit, 5);
  });

  test('ランク技：累積適用（複数回）と一括解除', () {
    final a = _mk();
    final d = _mk();
    final e = wazaEffectOf('つるぎのまい'); // A+2/回
    applyMoveToggle(e, a, d, true);
    applyMoveToggle(e, a, d, true);
    expect(a.boosts[1], 4); // 2回で A+4
    applyMoveToggle(e, a, d, true);
    expect(a.boosts[1], 6); // 3回（+6でクランプ）
    applyMoveToggle(e, a, d, false);
    applyMoveToggle(e, a, d, false);
    applyMoveToggle(e, a, d, false);
    expect(a.boosts[1], 0); // 解除
  });
}
