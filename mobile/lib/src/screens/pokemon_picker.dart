import 'package:flutter/material.dart';

import '../data/poke_db.dart';
import '../data/scrape_data.dart';

/// ポケモンを文字入力検索で選択するボトムシート。選んだ pid を返す（キャンセルで null）。
/// 対戦画面のパーティ編集・対戦記録の編集などで共有する。
/// [includeMega] = true でメガフォームも検索結果に含める（対戦記録でメガを登録する用）。
Future<String?> pickPokemon(BuildContext context, {bool includeMega = false}) {
  String query = '';
  List<({String name, String pid})> results = const [];
  bool started = false;

  Future<void> runSearch(void Function(void Function()) setSheet) async {
    final res =
        await PokeDb.instance.searchPokemon(query, includeMega: includeMega);
    // 無入力時は全体使用率(ranking.json)の高い順に並べる（未掲載は末尾＝図鑑番号順）。
    if (query.trim().isEmpty) {
      await ScrapeData.instance.load();
      final sd = ScrapeData.instance;
      res.sort((a, b) => sd.rankOf(a.pid).compareTo(sd.rankOf(b.pid)));
    }
    setSheet(() => results = res);
  }

  return showModalBottomSheet<String>(
    context: context,
    isScrollControlled: true,
    builder: (_) => StatefulBuilder(
      builder: (context, setSheet) {
        if (!started) {
          started = true;
          runSearch(setSheet);
        }
        return SafeArea(
          child: Padding(
            padding:
                EdgeInsets.only(bottom: MediaQuery.of(context).viewInsets.bottom),
            child: SizedBox(
              height: 380,
              child: Column(
                children: [
                  Padding(
                    padding: const EdgeInsets.fromLTRB(12, 12, 12, 4),
                    child: TextField(
                      autofocus: true,
                      decoration: const InputDecoration(
                        isDense: true,
                        prefixIcon: Icon(Icons.search, size: 18),
                        hintText: 'ポケモン名で検索（例: ガブ）',
                        border: OutlineInputBorder(),
                      ),
                      onChanged: (v) {
                        query = v;
                        runSearch(setSheet);
                      },
                    ),
                  ),
                  Expanded(
                    child: results.isEmpty
                        ? const Center(child: Text('該当するポケモンがありません'))
                        : ListView(
                            children: [
                              for (final p in results)
                                ListTile(
                                  dense: true,
                                  leading: Image.asset(
                                      'assets/pokemon/${p.pid}.png',
                                      width: 32,
                                      height: 32,
                                      errorBuilder: (_, __, ___) =>
                                          const SizedBox(width: 32)),
                                  title: Text(p.name),
                                  onTap: () => Navigator.of(context).pop(p.pid),
                                ),
                            ],
                          ),
                  ),
                ],
              ),
            ),
          ),
        );
      },
    ),
  );
}
