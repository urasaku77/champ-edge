import 'package:flutter/material.dart';

import '../model/battle_pokemon.dart';

/// 重量比からヘビーボンバー/ヒートスタンプの威力を返す
/// （旧 champ-edge WeightComparing.calc_power と同一）。
/// ratio = 相手の重さ ÷ 自分の重さ。
int heavySlamPower(double ratio) {
  if (ratio < 0.2) return 120;
  if (ratio < 0.25) return 100;
  if (ratio < 0.3) return 80;
  if (ratio < 0.5) return 60;
  return 40;
}

/// 重さ比較ポップアップ（旧 champ-edge WeightComparing 踏襲）。
/// 両者の重さと、互いをヘビーボンバー/ヒートスタンプで攻撃した場合の威力を表示する。
Future<void> showWeightCompareDialog(
    BuildContext context, BattlePokemon mine, BattlePokemon opp) {
  final sides = [mine, opp];
  final w0 = mine.weight;
  final w1 = opp.weight;
  final mark = w0 > w1 ? '>' : (w0 < w1 ? '<' : '=');
  Color color(double me, double other) =>
      me > other ? Colors.red : (me < other ? Colors.blue : Colors.black87);
  // power[i] = 側 i が攻撃側のときの威力（重量比 = 相手 ÷ 自分）。
  final powers = [
    w0 > 0 ? heavySlamPower(w1 / w0) : 40,
    w1 > 0 ? heavySlamPower(w0 / w1) : 40,
  ];

  return showDialog<void>(
    context: context,
    builder: (ctx) => Dialog(
      insetPadding: const EdgeInsets.symmetric(horizontal: 40, vertical: 16),
      child: Padding(
        padding: const EdgeInsets.all(14),
        child: SingleChildScrollView(
          child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Text('重さ比較',
                style: TextStyle(fontSize: 13, fontWeight: FontWeight.bold)),
            const SizedBox(height: 8),
            Row(
              children: [
                for (var i = 0; i < 2; i++) ...[
                  if (i == 1)
                    SizedBox(
                      width: 40,
                      child: Center(
                        child: Text(mark,
                            style: const TextStyle(
                                fontSize: 20, fontWeight: FontWeight.bold)),
                      ),
                    ),
                  Expanded(
                    child: Column(
                      children: [
                        Row(
                          mainAxisAlignment: MainAxisAlignment.center,
                          children: [
                            Image.asset('assets/pokemon/${sides[i].pid}.png',
                                width: 34,
                                height: 34,
                                fit: BoxFit.contain,
                                errorBuilder: (_, __, ___) =>
                                    const SizedBox(width: 34)),
                            const SizedBox(width: 4),
                            Flexible(
                              child: Text(sides[i].name,
                                  maxLines: 1,
                                  overflow: TextOverflow.ellipsis,
                                  style: const TextStyle(
                                      fontSize: 12,
                                      fontWeight: FontWeight.bold)),
                            ),
                          ],
                        ),
                        Text('${sides[i].weight}kg',
                            style: TextStyle(
                                fontSize: 24,
                                fontWeight: FontWeight.bold,
                                color: color(sides[i].weight,
                                    sides[1 - i].weight))),
                      ],
                    ),
                  ),
                ],
              ],
            ),
            const Divider(height: 16),
            // ヘビーボンバー/ヒートスタンプの威力（各側が攻撃側のとき）
            Row(
              children: [
                for (var i = 0; i < 2; i++) ...[
                  if (i == 1)
                    const SizedBox(
                      width: 40,
                      child: Center(
                        child: Text('威力',
                            style: TextStyle(
                                fontSize: 11,
                                fontWeight: FontWeight.bold,
                                color: Colors.black54)),
                      ),
                    ),
                  Expanded(
                    child: Center(
                      child: Text('${powers[i]}',
                          style: const TextStyle(
                              fontSize: 24, fontWeight: FontWeight.bold)),
                    ),
                  ),
                ],
              ],
            ),
            const SizedBox(height: 2),
            const Text('ヘビーボンバー / ヒートスタンプ',
                style: TextStyle(fontSize: 9, color: Colors.black54)),
          ],
        ),
        ),
      ),
    ),
  );
}
