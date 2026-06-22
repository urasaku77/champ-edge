import 'package:flutter/material.dart';

import '../model/battle_pokemon.dart';

/// 性格を表形式（↑行＝上昇能力 × ↓列＝下降能力）で選ぶピッカー。
/// Top（ホーム）と編集画面で共通利用する。選択した性格名を返す（キャンセルは null）。
Future<String?> pickNature(BuildContext context, String current) {
  const stat = ['', 'A', 'B', 'C', 'D', 'S'];
  String? natureAt(int up, int down) {
    if (up == down) return up == 3 ? 'まじめ' : null;
    for (final n in allNatures) {
      if (n.up == up && n.down == down) return n.name;
    }
    return null;
  }

  Widget headerCell(String t) => SizedBox(
        width: 54,
        height: 24,
        child: Center(
            child: Text(t,
                style: const TextStyle(fontSize: 11, color: Colors.black54))),
      );

  return showDialog<String>(
    context: context,
    builder: (_) => AlertDialog(
      titlePadding: const EdgeInsets.fromLTRB(16, 12, 16, 2),
      contentPadding: const EdgeInsets.fromLTRB(12, 0, 12, 8),
      title: const Text('性格（↑行 × ↓列）', style: TextStyle(fontSize: 14)),
      content: SingleChildScrollView(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Row(children: [
              headerCell(''),
              for (int d = 1; d <= 5; d++) headerCell('↓${stat[d]}')
            ]),
            for (int u = 1; u <= 5; u++)
              Row(
                children: [
                  headerCell('↑${stat[u]}'),
                  for (int d = 1; d <= 5; d++)
                    Builder(builder: (_) {
                      final name = natureAt(u, d);
                      final selected = name != null && name == current;
                      return GestureDetector(
                        onTap: name == null
                            ? null
                            : () => Navigator.of(context).pop(name),
                        child: Container(
                          width: 54,
                          height: 28,
                          margin: const EdgeInsets.all(1),
                          alignment: Alignment.center,
                          decoration: BoxDecoration(
                            color: name == null
                                ? Colors.grey.withValues(alpha: 0.08)
                                : selected
                                    ? Colors.blue.withValues(alpha: 0.25)
                                    : Colors.blue.withValues(alpha: 0.05),
                            borderRadius: BorderRadius.circular(4),
                            border: Border.all(
                                color: selected ? Colors.blue : Colors.black12),
                          ),
                          child: Text(name ?? '—',
                              style: const TextStyle(fontSize: 9),
                              textAlign: TextAlign.center),
                        ),
                      );
                    }),
                ],
              ),
          ],
        ),
      ),
    ),
  );
}
