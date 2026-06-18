import 'package:champ_edge_mobile/src/service/similar_party.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  List<String> party(List<String> xs) =>
      [...xs, ...List.filled(6 - xs.length, '-1')];

  test('並びまで一致は exactOrder', () {
    expect(
      matchParty(party(['0130-0', '0094-0', '0006-0']),
          party(['0130-0', '0094-0', '0006-0'])),
      PartyMatch.exactOrder,
    );
  });

  test('中身は同じだが並びが違う → sameSet', () {
    expect(
      matchParty(party(['0130-0', '0094-0', '0006-0']),
          party(['0006-0', '0130-0', '0094-0'])),
      PartyMatch.sameSet,
    );
  });

  test('構成が違う → none', () {
    expect(
      matchParty(party(['0130-0', '0094-0']), party(['0130-0', '0445-0'])),
      PartyMatch.none,
    );
  });

  test('メガ統合：メガ違いは同一構成として一致', () {
    // 並びは同じだがメガform違い → 正規化で並び一致
    expect(
      matchParty(party(['0006-11', '0130-0']), party(['0006-0', '0130-0'])),
      PartyMatch.exactOrder,
    );
    // メガ統合 OFF なら不一致
    expect(
      matchParty(party(['0006-11', '0130-0']), party(['0006-0', '0130-0']),
          megaMerge: false),
      PartyMatch.none,
    );
  });

  test('空パーティは none', () {
    expect(matchParty(party([]), party(['0130-0'])), PartyMatch.none);
  });
}
