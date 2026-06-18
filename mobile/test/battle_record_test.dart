import 'package:champ_edge_mobile/src/model/battle_record.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  test('toColumns / fromRow は往復で同値', () {
    final b = BattleRecord(
      date: 1700000000,
      rule: 1,
      result: 1,
      favorite: 1,
      opponentTn: 'トレーナー',
      opponentRate: '1850',
      battleMemo: 'メモ',
      playerPartyNum: '3',
      playerPartySubnum: '2',
      playerPokemons: const ['0445-0', '0143-0', '-1', '-1', '-1', '-1'],
      opponentPokemons: const ['0130-0', '0094-0', '0006-0', '-1', '-1', '-1'],
      playerChoices: const ['0445-0', '0143-0', '-1', '-1'],
      opponentChoices: const ['0130-0', '0094-0', '0006-0', '-1'],
    );
    final r = BattleRecord.fromRow({'id': 5, ...b.toColumns()});
    expect(r.id, 5);
    expect(r.result, 1);
    expect(r.isWin, isTrue);
    expect(r.isFavorite, isTrue);
    expect(r.opponentTn, 'トレーナー');
    expect(r.opponentRate, '1850');
    expect(r.playerPartyNum, '3');
    expect(r.playerPokemons, b.playerPokemons);
    expect(r.opponentChoices, b.opponentChoices);
  });

  test('normalizeMegaForm はメガ(10-19)を-0へ、通常/空きはそのまま', () {
    expect(normalizeMegaForm('0006-11'), '0006-0'); // メガリザードンX
    expect(normalizeMegaForm('0445-0'), '0445-0');
    expect(normalizeMegaForm('-1'), '-1');
    expect(normalizeMegaForm(''), '');
  });
}
