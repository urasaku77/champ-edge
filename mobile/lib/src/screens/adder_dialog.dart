import 'package:flutter/material.dart';

import '../model/battle_pokemon.dart';
import '../service/adder.dart';
import '../service/damage_engine.dart';

/// 回復ボタン（旧 champ-edge _HEAL_ITEMS と同一）。(名前, 分子, 分母)
const List<(String, int, int)> _healItems = [
  ('オボンのみ', 1, 4),
  ('たべのこし', 1, 16),
  ('混乱実', 1, 3),
  ('やどりぎのタネ', 1, 8),
];

/// 加算ツール（旧 champ-edge MultiWazaDamageWindow 踏襲）。
/// 攻撃側の技を押すたびにダメージを累積し、回復を減算して合計と KO 判定を表示する。
Future<void> showAdderDialog(BuildContext context, BattlePokemon attacker,
    BattlePokemon defender, FieldState field) {
  final hp = defender.hp;
  final entry = defender.hasStealthRock
      ? (hp *
              DamageCalc.getTypeEffectiveness(PokeType.rock, defender.types) /
              8)
          .floor()
      : 0;
  final effHp = (hp - entry) < 1 ? 1 : hp - entry;
  final constant = (hp * defender.constantDamage).floor();

  // 設定済み技のダメージ分布（定数ダメージ加算済み）を先に計算しておく。
  final moves = <(String, List<int>)>[];
  for (final m in attacker.moves) {
    if (m.isEmpty) continue;
    final r = DamageCalc.calculateDamage(
      attacker.toAttacker(),
      defender.toDefender(),
      m.toMoveState(
          critical: attacker.critical,
          skillLink: attacker.ability == 'スキルリンク'),
      field,
    );
    if (r.damages.isEmpty) continue;
    moves.add((m.name, [for (final d in r.damages) d + constant]));
  }

  final session = AdderSession(hp: hp, effectiveHp: effHp);
  return showDialog<void>(
    context: context,
    builder: (ctx) => Dialog(
      insetPadding: const EdgeInsets.symmetric(horizontal: 24, vertical: 16),
      child: StatefulBuilder(
        builder: (ctx, setLocal) => Padding(
          padding: const EdgeInsets.all(12),
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 460),
            child: SingleChildScrollView(
              child: Column(
                mainAxisSize: MainAxisSize.min,
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  const Center(
                    child: Text('加算ツール',
                        style: TextStyle(
                            fontSize: 13, fontWeight: FontWeight.bold)),
                  ),
                  const SizedBox(height: 6),
                  // 技ボタン＋クリア
                  Wrap(
                    spacing: 4,
                    runSpacing: 4,
                    children: [
                      for (final (name, damages) in moves)
                        _btn(name, Colors.blueGrey,
                            () => setLocal(() => session.pressMove(name, damages))),
                      _btn('クリア', Colors.red,
                          () => setLocal(session.clear)),
                    ],
                  ),
                  const SizedBox(height: 6),
                  // 回復ボタン
                  Row(
                    children: [
                      const Text('回復: ',
                          style:
                              TextStyle(fontSize: 10, color: Colors.black54)),
                      Expanded(
                        child: Wrap(
                          spacing: 4,
                          runSpacing: 4,
                          children: [
                            for (final (name, num, den) in _healItems)
                              _btn(name, Colors.green,
                                  () => setLocal(() =>
                                      session.pressHeal(name, num, den))),
                          ],
                        ),
                      ),
                    ],
                  ),
                  const Divider(height: 14),
                  // 累積リスト（行タップで削除）
                  if (session.entries.isEmpty)
                    const Padding(
                      padding: EdgeInsets.symmetric(vertical: 8),
                      child: Center(
                        child: Text('技/回復ボタンを押すと行が追加されます（行タップで削除）',
                            style: TextStyle(
                                fontSize: 10, color: Colors.black45)),
                      ),
                    )
                  else
                    for (final (i, e) in session.entries.indexed)
                      InkWell(
                        onTap: () => setLocal(() => session.removeAt(i)),
                        child: Padding(
                          padding: const EdgeInsets.symmetric(vertical: 2),
                          child: Row(
                            children: [
                              SizedBox(
                                width: 110,
                                child: Text(e.label,
                                    maxLines: 1,
                                    overflow: TextOverflow.ellipsis,
                                    style: TextStyle(
                                        fontSize: 11,
                                        color: e.isHeal
                                            ? Colors.green.shade700
                                            : Colors.black87)),
                              ),
                              SizedBox(
                                width: 90,
                                child: Text(
                                    e.isHeal
                                        ? '-${e.healHp}'
                                        : '${e.minDamage}〜${e.maxDamage}',
                                    style: const TextStyle(
                                        fontSize: 11,
                                        fontWeight: FontWeight.w600)),
                              ),
                              Expanded(
                                child: Text(
                                    e.isHeal
                                        ? '-${(e.healHp / hp * 1000).round() / 10}%'
                                        : '${(e.minDamage / hp * 1000).round() / 10}'
                                            '〜${(e.maxDamage / hp * 1000).round() / 10}%'
                                            '${_rowKo(e, effHp)}',
                                    style: const TextStyle(
                                        fontSize: 9, color: Colors.black54)),
                              ),
                            ],
                          ),
                        ),
                      ),
                  const Divider(height: 14),
                  // 合計
                  Builder(builder: (_) {
                    if (!session.hasMove) {
                      return const Text('合計: —',
                          style: TextStyle(fontSize: 11));
                    }
                    final ko = session.koText;
                    final minP = (session.totalMin / hp * 1000).round() / 10;
                    final maxP = (session.totalMax / hp * 1000).round() / 10;
                    return Text(
                      '合計: ${session.totalMin}〜${session.totalMax}'
                      '  $minP〜$maxP%${ko.isEmpty ? '' : '  $ko'}',
                      style: TextStyle(
                          fontSize: 12,
                          fontWeight: FontWeight.bold,
                          color: ko.startsWith('確定')
                              ? Colors.red
                              : Colors.black87),
                    );
                  }),
                ],
              ),
            ),
          ),
        ),
      ),
    ),
  );
}

/// 単発技の確定数（行表示用、メイン画面の ko_text と同一規則）。
String _rowKo(AdderEntry e, int effHp) {
  for (var n = 1; n <= 4; n++) {
    final k = e.damages.where((d) => d * n >= effHp).length;
    if (k == 16) return ' 確定$n発';
    if (k > 0) return ' 乱数$n発($k/16)';
  }
  return '';
}

Widget _btn(String text, MaterialColor color, VoidCallback onTap) {
  return InkWell(
    onTap: onTap,
    child: Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 5),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.12),
        borderRadius: BorderRadius.circular(5),
        border: Border.all(color: color.withValues(alpha: 0.5)),
      ),
      child: Text(text, style: const TextStyle(fontSize: 11)),
    ),
  );
}
