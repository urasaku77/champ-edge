import 'package:flutter/material.dart';
import 'package:url_launcher/url_launcher.dart';

import '../data/app_settings.dart';
import '../data/battle_db.dart';
import '../data/scrape_data.dart';
import '../model/battle_pokemon.dart';
import '../service/similar_party.dart';

/// 類似パーティ検索の結果。
class SimilarResult {
  final List<(PartyMatch, List<String>)> history;
  final List<(PartyMatch, String, String, List<String>)> articles;
  const SimilarResult(this.history, this.articles);
  int get total => history.length + articles.length;
}

/// 相手パーティに対する類似候補（対戦履歴＋構築記事）を計算する。
/// ダイアログ表示と自動検索バッジの両方から使う。
Future<SimilarResult> findSimilarParties(List<BattlePokemon> oppParty) async {
  final target = [
    for (var i = 0; i < 6; i++)
      (i < oppParty.length && oppParty[i].name.isNotEmpty)
          ? oppParty[i].pid
          : '-1'
  ];
  // 相手が1体も入っていなければ検索しない。
  if (target.every((t) => t == '-1')) return const SimilarResult([], []);

  await BattleDb.instance.open();
  await ScrapeData.instance.load();

  // 対戦履歴：相手パーティの重複を除いて照合。
  final records = await BattleDb.instance.allRecords();
  final seen = <String>{};
  final historyHits = <(PartyMatch, List<String>)>[];
  for (final r in records) {
    final key = r.opponentPokemons.join(',');
    if (!seen.add(key)) continue;
    final m = matchParty(target, r.opponentPokemons);
    if (m != PartyMatch.none) historyHits.add((m, r.opponentPokemons));
  }

  // 構築記事（スクレイピング由来の seed ＋ 手動登録の DB 分）。
  final articles = [
    for (final a in ScrapeData.instance.kousei)
      (title: a.title, url: a.url, pokemons: a.pokemons),
    ...await BattleDb.instance.allKousei(),
  ];
  final articleHits =
      <(PartyMatch, String, String, List<String>)>[]; // match,title,url,party
  for (final a in articles) {
    final m = matchParty(target, a.pokemons);
    if (m != PartyMatch.none) {
      articleHits.add((m, a.title, a.url, a.pokemons));
    }
  }

  int order(PartyMatch m) => m == PartyMatch.exactOrder ? 0 : 1;
  historyHits.sort((a, b) => order(a.$1).compareTo(order(b.$1)));
  articleHits.sort((a, b) => order(a.$1).compareTo(order(b.$1)));
  return SimilarResult(historyHits, articleHits);
}

/// 類似パーティ検索の結果ダイアログ（旧 champ-edge の SimilarParty / 類似パーティ）。
///
/// 相手の選択パーティと一致する候補を、**対戦履歴**と**構築記事**の両方から探し、
/// 「並びまで一致」「中身だけ同じ」を区別して表示する。構築記事はリンクに飛べる。
/// タイトル横の「自動検索」トグルは相手確定時の自動検索（Topのバッジ）の ON/OFF。
Future<void> showSimilarPartyDialog(
    BuildContext context, List<BattlePokemon> oppParty) async {
  final result = await findSimilarParties(oppParty);
  final historyHits = result.history;
  final articleHits = result.articles;

  if (!context.mounted) return;

  await showDialog<void>(
    context: context,
    builder: (ctx) => AlertDialog(
      title: Row(
        children: [
          const Text('類似パーティ検索', style: TextStyle(fontSize: 15)),
          const Spacer(),
          const Text('自動検索', style: TextStyle(fontSize: 12)),
          StatefulBuilder(
            builder: (_, setSB) => Switch(
              value: AppSettings.instance.autoSimilarSearch,
              materialTapTargetSize: MaterialTapTargetSize.shrinkWrap,
              onChanged: (v) {
                setSB(() => AppSettings.instance.autoSimilarSearch = v);
                AppSettings.instance.save();
              },
            ),
          ),
        ],
      ),
      content: SizedBox(
        width: 360,
        child: SingleChildScrollView(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              _section('対戦履歴（${historyHits.length}件）'),
              if (historyHits.isEmpty)
                _empty()
              else
                for (final h in historyHits)
                  _partyRow(h.$1, h.$2),
              const SizedBox(height: 10),
              _section('構築記事（${articleHits.length}件）'),
              if (articleHits.isEmpty)
                _empty(note: '構築記事データは未取得です（将来対応）')
              else
                for (final a in articleHits)
                  _articleRow(a.$1, a.$2, a.$3, a.$4),
            ],
          ),
        ),
      ),
      actions: [
        TextButton(
            onPressed: () => Navigator.of(ctx).pop(),
            child: const Text('閉じる')),
      ],
    ),
  );
}

Widget _section(String label) => Padding(
      padding: const EdgeInsets.only(bottom: 4),
      child: Text(label,
          style: const TextStyle(fontSize: 13, fontWeight: FontWeight.bold)),
    );

Widget _empty({String? note}) => Padding(
      padding: const EdgeInsets.only(bottom: 4),
      child: Text(note ?? '一致なし',
          style: const TextStyle(fontSize: 11, color: Colors.black45)),
    );

Widget _matchBadge(PartyMatch m) {
  final exact = m == PartyMatch.exactOrder;
  return Container(
    padding: const EdgeInsets.symmetric(horizontal: 5, vertical: 1),
    decoration: BoxDecoration(
      color: (exact ? Colors.red : Colors.blueGrey).withValues(alpha: 0.15),
      borderRadius: BorderRadius.circular(3),
    ),
    child: Text(exact ? '並び一致' : '中身一致',
        style: TextStyle(
            fontSize: 9, color: exact ? Colors.red : Colors.blueGrey)),
  );
}

Widget _icons(List<String> pids) => Row(
      children: [
        for (final pid in pids)
          if (pid != '-1')
            Padding(
              padding: const EdgeInsets.only(right: 1),
              child: Image.asset('assets/pokemon/$pid.png',
                  width: 26,
                  height: 26,
                  errorBuilder: (_, __, ___) => const SizedBox(width: 26)),
            ),
      ],
    );

Widget _partyRow(PartyMatch m, List<String> pids) => Padding(
      padding: const EdgeInsets.symmetric(vertical: 3),
      child: Row(
        children: [_matchBadge(m), const SizedBox(width: 6), _icons(pids)],
      ),
    );

Widget _articleRow(
        PartyMatch m, String title, String url, List<String> pids) =>
    Padding(
      padding: const EdgeInsets.symmetric(vertical: 3),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // バッジ＋ポケモン、その右に構築記事リンクボタンを配置。
          Row(
            children: [
              _matchBadge(m),
              const SizedBox(width: 6),
              _icons(pids),
              if (url.isNotEmpty) ...[
                const SizedBox(width: 4),
                OutlinedButton.icon(
                  style: OutlinedButton.styleFrom(
                    visualDensity: VisualDensity.compact,
                    padding: const EdgeInsets.symmetric(horizontal: 8),
                    minimumSize: const Size(0, 28),
                    tapTargetSize: MaterialTapTargetSize.shrinkWrap,
                  ),
                  onPressed: () => launchUrl(Uri.parse(url),
                      mode: LaunchMode.externalApplication),
                  icon: const Icon(Icons.open_in_new, size: 13),
                  label: const Text('構築記事', style: TextStyle(fontSize: 11)),
                ),
              ],
            ],
          ),
          if (title.isNotEmpty)
            Padding(
              padding: const EdgeInsets.only(top: 1),
              child: Text(title,
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: const TextStyle(fontSize: 11, color: Colors.black54)),
            ),
        ],
      ),
    );
