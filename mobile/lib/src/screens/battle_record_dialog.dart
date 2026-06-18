import 'package:flutter/material.dart';

import '../data/battle_db.dart';
import '../model/battle_pokemon.dart';
import '../model/battle_record.dart';

/// 対戦記録の登録ダイアログ（旧 champ-edge の RecordFrame / record_battle 相当）。
///
/// TN・レート・メモ・お気に入りを手動入力し、勝ち/分け/負けで保存する
/// （TN/レートの OCR 自動入力は P4 保留）。保存後 [onSaved] を呼ぶ。
///
/// 入力中の値は呼び出し側が保持する [TextEditingController] に書かれるため、
/// 登録せずにダイアログを閉じても次回開いたときに残る（登録時に呼び出し側で
/// クリアする）。パーティ番号/連番は [partyNum]/[partySubnum] に自動補完済み。
Future<void> showBattleRecordDialog(
  BuildContext context, {
  required List<BattlePokemon> myParty,
  required List<BattlePokemon> oppParty,
  required List<int> myChosen,
  required List<int> oppChosen,
  required TextEditingController tn,
  required TextEditingController rate,
  required TextEditingController memo,
  required TextEditingController partyNum,
  required TextEditingController partySubnum,
  required bool favorite,
  required ValueChanged<bool> onFavoriteChanged,
  String partyTitle = '',
  required VoidCallback onSaved,
}) async {
  var fav = favorite;

  String pidAt(List<BattlePokemon> party, int i) =>
      (i < party.length && party[i].name.isNotEmpty) ? party[i].pid : '-1';
  List<String> partyPids(List<BattlePokemon> party) =>
      [for (var i = 0; i < 6; i++) pidAt(party, i)];
  // 選出（最大4枠。シングルは3＋'-1'）。chosen はスロット番号のリスト。
  List<String> choicePids(List<BattlePokemon> party, List<int> chosen) => [
        for (var k = 0; k < 4; k++)
          (k < chosen.length) ? pidAt(party, chosen[k]) : '-1'
      ];

  Future<void> save(int result) async {
    final rec = BattleRecord(
      date: DateTime.now().millisecondsSinceEpoch ~/ 1000,
      rule: 1,
      result: result,
      favorite: fav ? 1 : 0,
      opponentTn: tn.text.trim(),
      opponentRate: rate.text.trim(),
      battleMemo: memo.text.trim(),
      playerPartyNum: partyNum.text.trim(),
      playerPartySubnum: partySubnum.text.trim(),
      playerPokemons: partyPids(myParty),
      opponentPokemons: partyPids(oppParty),
      playerChoices: choicePids(myParty, myChosen),
      opponentChoices: choicePids(oppParty, oppChosen),
    );
    await BattleDb.instance.open();
    await BattleDb.instance.register(rec);
    onSaved();
  }

  await showDialog<void>(
    context: context,
    builder: (ctx) => StatefulBuilder(
      builder: (ctx, setLocal) => AlertDialog(
        insetPadding:
            const EdgeInsets.symmetric(horizontal: 24, vertical: 16),
        title: const Text('対戦記録', style: TextStyle(fontSize: 15)),
        contentPadding: const EdgeInsets.fromLTRB(20, 8, 20, 0),
        content: SizedBox(
          width: 340,
          child: SingleChildScrollView(
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
              // 自分パーティ番号/連番（使用中パーティから自動補完・編集可）。
              Row(
                children: [
                  SizedBox(
                    width: 96,
                    child: TextField(
                      controller: partyNum,
                      keyboardType: TextInputType.number,
                      style: const TextStyle(fontSize: 13),
                      decoration: const InputDecoration(
                          labelText: 'P番号', isDense: true),
                    ),
                  ),
                  const SizedBox(width: 8),
                  SizedBox(
                    width: 96,
                    child: TextField(
                      controller: partySubnum,
                      keyboardType: TextInputType.number,
                      style: const TextStyle(fontSize: 13),
                      decoration: const InputDecoration(
                          labelText: '連番', isDense: true),
                    ),
                  ),
                  if (partyTitle.isNotEmpty) ...[
                    const SizedBox(width: 8),
                    Expanded(
                      child: Text(partyTitle,
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                          style: const TextStyle(
                              fontSize: 11, color: Colors.black54)),
                    ),
                  ],
                ],
              ),
              const SizedBox(height: 4),
              Row(
                children: [
                  Expanded(
                    child: TextField(
                      controller: tn,
                      style: const TextStyle(fontSize: 13),
                      decoration: const InputDecoration(
                          labelText: '相手TN', isDense: true),
                    ),
                  ),
                  const SizedBox(width: 8),
                  TextButton(
                    onPressed: () => tn.text = 'トレーナー',
                    child: const Text('匿名'),
                  ),
                ],
              ),
              // レートは幅をとらないので、横にお気に入りトグルを並べる。
              Row(
                children: [
                  SizedBox(
                    width: 130,
                    child: TextField(
                      controller: rate,
                      keyboardType: TextInputType.number,
                      style: const TextStyle(fontSize: 13),
                      decoration: const InputDecoration(
                          labelText: '相手レート', isDense: true),
                    ),
                  ),
                  const Spacer(),
                  const Text('お気に入り', style: TextStyle(fontSize: 13)),
                  Switch(
                    value: fav,
                    onChanged: (v) {
                      setLocal(() => fav = v);
                      onFavoriteChanged(v);
                    },
                  ),
                ],
              ),
              TextField(
                controller: memo,
                style: const TextStyle(fontSize: 13),
                minLines: 1,
                maxLines: 3,
                decoration:
                    const InputDecoration(labelText: 'メモ', isDense: true),
              ),
            ],
            ),
          ),
        ),
        actions: [
          TextButton(
              onPressed: () => Navigator.of(ctx).pop(),
              child: const Text('キャンセル')),
          _resultBtn(ctx, '負け', Colors.blueGrey, () => save(0)),
          _resultBtn(ctx, '分け', Colors.amber, () => save(2)),
          _resultBtn(ctx, '勝ち', Colors.red, () => save(1)),
        ],
      ),
    ),
  );
}

Widget _resultBtn(
    BuildContext ctx, String label, Color color, Future<void> Function() save) {
  return FilledButton(
    style: FilledButton.styleFrom(
        backgroundColor: color, padding: const EdgeInsets.symmetric(horizontal: 12)),
    onPressed: () async {
      await save();
      if (ctx.mounted) Navigator.of(ctx).pop();
      if (ctx.mounted) {
        ScaffoldMessenger.of(ctx).showSnackBar(SnackBar(
            duration: const Duration(milliseconds: 1200),
            content: Text('対戦記録を保存しました（$label）')));
      }
    },
    child: Text(label),
  );
}
