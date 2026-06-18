import 'package:champ_edge_mobile/src/model/battle_record.dart';
import 'package:champ_edge_mobile/src/service/battle_analysis.dart';
import 'package:flutter_test/flutter_test.dart';

BattleRecord _rec(int result, List<String> oppParty, List<String> oppChoice,
        {List<String>? myParty, List<String>? myChoice}) =>
    BattleRecord(
      date: 0,
      result: result,
      playerPokemons: [
        ...?myParty,
        ...List.filled(6 - (myParty?.length ?? 0), '-1')
      ],
      opponentPokemons: [...oppParty, ...List.filled(6 - oppParty.length, '-1')],
      playerChoices: [
        ...?myChoice,
        ...List.filled(4 - (myChoice?.length ?? 0), '-1')
      ],
      opponentChoices: [
        ...oppChoice,
        ...List.filled(4 - oppChoice.length, '-1')
      ],
    );

void main() {
  test('KP・勝率・選出率・初手の集計', () {
    final records = [
      _rec(1, ['0130-0', '0094-0', '0006-0'], ['0130-0', '0094-0']), // 勝
      _rec(0, ['0130-0', '0445-0'], ['0445-0', '0130-0']), // 負（初手ガブ）
      _rec(1, ['0130-0', '0094-0'], ['0130-0']), // 勝（初手ギャラ）
    ];
    final res = analyzeBattles(records);
    expect(res.battles, 3);
    expect(res.wins, 2);

    final gyara = res.stats.firstWhere((s) => s.pid == '0130-0'); // ギャラドス
    expect(gyara.appeared, 3); // 3戦とも出現
    expect(gyara.appearedWin, 2); // うち2勝
    expect(gyara.chosen, 3); // 3戦とも選出
    expect(gyara.first, 2); // 初手2回（戦1・戦3）
    expect(gyara.firstWin, 2);

    final gabu = res.stats.firstWhere((s) => s.pid == '0445-0'); // ガブリアス
    expect(gabu.appeared, 1);
    expect(gabu.appearedWin, 0);
    expect(gabu.first, 1); // 戦2の初手
    expect(gabu.firstWin, 0);
  });

  test('引き分けを分母に含む勝率と勝/敗/分の内訳', () {
    final records = [
      _rec(1, ['0130-0'], ['0130-0']), // 勝
      _rec(0, ['0130-0'], ['0130-0']), // 負
      _rec(2, ['0130-0'], ['0130-0']), // 分
      _rec(2, ['0130-0'], ['0130-0']), // 分
    ];
    final res = analyzeBattles(records);
    expect(res.battles, 4);
    expect(res.wins, 1);
    expect(res.draws, 2);
    expect(res.loses, 1); // 4 - 1勝 - 2分
    expect(res.winRate, 25.0); // 勝 / 全対戦数（分も分母）
  });

  test('自分パーティのポケモン別成績（選出時勝率・初手）', () {
    final records = [
      _rec(1, ['0001-0'], ['0001-0'],
          myParty: ['0445-0', '0130-0'], myChoice: ['0445-0', '0130-0']), // 勝
      _rec(0, ['0001-0'], ['0001-0'],
          myParty: ['0445-0', '0130-0'], myChoice: ['0130-0', '0445-0']), // 負
      _rec(1, ['0001-0'], ['0001-0'],
          myParty: ['0445-0', '0130-0'], myChoice: ['0445-0']), // 勝（初手ガブ）
    ];
    final stats = analyzePlayerParty(records, ['0445-0', '0130-0', '-1']);
    final gabu = stats.firstWhere((s) => s.pid == '0445-0');
    expect(gabu.chosen, 3); // 3戦とも選出
    expect(gabu.chosenWin, 2); // うち2勝
    expect(gabu.first, 2); // 初手2回（戦1・戦3）
    expect(gabu.firstWin, 2);
    final gyara = stats.firstWhere((s) => s.pid == '0130-0');
    expect(gyara.chosen, 2); // 戦1・戦2
    expect(gyara.first, 1); // 戦2の初手
    expect(gyara.firstWin, 0);
  });

  test('メガ統合：メガ(10-19)は通常へ集約', () {
    final records = [
      _rec(1, ['0006-0'], ['0006-0']),
      _rec(0, ['0006-11'], ['0006-11']), // メガリザX
    ];
    final merged = analyzeBattles(records, megaMerge: true);
    expect(merged.stats.length, 1);
    expect(merged.stats.first.appeared, 2);

    final split = analyzeBattles(records, megaMerge: false);
    expect(split.stats.length, 2);
  });
}
