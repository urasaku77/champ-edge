import 'package:flutter/material.dart';

import '../data/battle_db.dart';
import '../data/scrape_data.dart';
import '../service/battle_analysis.dart';
import 'period_preset.dart';

/// 表示モード（旧 champ-edge の分析画面の3択）。
enum _Mode { kp, chosen, first }

/// ソート条件（件数/勝率/使用率順）。
enum _Sort { count, rate, ranking }

/// 対戦分析画面（旧 champ-edge の対戦分析画面の移植）。
/// 相手ポケモンの KP・選出率・初手選出率と、それぞれの勝率を集計表示する。
/// 操作パネルで表示モード・ソート・表示形式・メガ統合・表示件数を切り替える。
class BattleAnalysisScreen extends StatefulWidget {
  const BattleAnalysisScreen({super.key});

  @override
  State<BattleAnalysisScreen> createState() => _BattleAnalysisScreenState();
}

class _BattleAnalysisScreenState extends State<BattleAnalysisScreen> {
  DateTime _from = DateTime.now().subtract(const Duration(days: 90));
  DateTime _to = DateTime.now();
  PeriodPreset _preset = PeriodPreset.last90;
  String? _season; // 選択中のシーズン名（M-1 等。未選択は null）
  final _partyNum = TextEditingController();
  final _partySubnum = TextEditingController();
  List<String> _recentParty = const []; // 直近使用した自分パーティ

  _Mode _mode = _Mode.kp;
  _Sort _sort = _Sort.count;
  bool _descending = true;
  bool _megaMerge = true;
  int _limit = 50;
  int _topN = 0; // 0=オフ、10/30/50=使用率トップN絞り

  AnalysisResult? _result;
  List<PlayerPokeStat> _playerStats = const []; // P番号指定時の自分パーティ別成績
  bool _showPlayerStats = true; // 自分パーティ別成績セクションの表示/非表示
  bool _loading = true;

  bool _startAt11 = true; // 開始日を11時以降にする（ランク日替り境界）
  bool _endAt11 = true; // 終了日を11時までにする

  // ランク日替り境界（11時）に合わせる。ON: from=当日11:00 / to=当日10:59:59。
  int get _fromSec =>
      DateTime(_from.year, _from.month, _from.day, _startAt11 ? 11 : 0)
          .millisecondsSinceEpoch ~/
      1000;
  int get _toSec => (_endAt11
              ? DateTime(_to.year, _to.month, _to.day, 10, 59, 59)
              : DateTime(_to.year, _to.month, _to.day, 23, 59, 59))
          .millisecondsSinceEpoch ~/
      1000;

  @override
  void initState() {
    super.initState();
    _run();
  }

  Future<void> _run() async {
    setState(() => _loading = true);
    await ScrapeData.instance.load();
    await BattleDb.instance.open();
    final records = await BattleDb.instance.query(
      fromDate: _fromSec,
      toDate: _toSec,
      partyNum: _partyNum.text.trim(),
      partySubnum: _partySubnum.text.trim(),
    );
    if (!mounted) return;
    setState(() {
      _result = analyzeBattles(records, megaMerge: _megaMerge);
      // 直近使用した自分パーティ（最新の記録）。
      _recentParty = records.isEmpty
          ? const []
          : records.first.playerPokemons.where((p) => p != '-1').toList();
      // P番号を指定したときだけ、自分パーティのポケモン別成績を集計する。
      if (_partyNum.text.trim().isNotEmpty && records.isNotEmpty) {
        // パーティ6枠は最新記録の自分パーティを基準にする。
        _playerStats = analyzePlayerParty(
            records, records.first.playerPokemons,
            megaMerge: _megaMerge);
      } else {
        _playerStats = const [];
      }
      _loading = false;
    });
  }

  /// P番号/連番での検索。閉じていた自分パーティ別成績を再表示する。
  void _searchByParty() {
    setState(() => _showPlayerStats = true);
    _run();
  }

  void _applyPreset(PeriodPreset p) {
    final r = p.range();
    setState(() {
      _preset = p;
      _season = null; // プリセット選択でシーズン選択は解除。
      if (r != null) {
        _from = r.$1;
        _to = r.$2;
      }
    });
    _run();
  }

  String _fmtDate(DateTime d) =>
      '${d.year}/${d.month.toString().padLeft(2, '0')}/${d.day.toString().padLeft(2, '0')}';

  Future<void> _pickDate(bool isFrom) async {
    final d = await showDatePicker(
      context: context,
      initialDate: isFrom ? _from : _to,
      firstDate: DateTime(2020),
      lastDate: DateTime(2100),
    );
    if (d == null) return;
    setState(() {
      isFrom ? _from = d : _to = d;
      _preset = PeriodPreset.custom;
      _season = null; // 手動日付指定でシーズン選択は解除。
    });
    _run();
  }

  // モードに応じた (上段=主指標, 下段=勝率) の (分子, 分母) を返す。
  (int, int) _primary(PokeStat s) => switch (_mode) {
        _Mode.kp => (s.appeared, s.appeared), // KP は出現数そのもの
        _Mode.chosen => (s.chosen, s.appeared), // 選出率
        _Mode.first => (s.first, s.appeared), // 初手選出率
      };
  (int, int) _winRate(PokeStat s) => switch (_mode) {
        _Mode.kp => (s.appearedWin, s.appeared),
        _Mode.chosen => (s.chosenWin, s.chosen),
        _Mode.first => (s.firstWin, s.first),
      };

  double _sortKey(PokeStat s) {
    switch (_sort) {
      case _Sort.rate:
        final (n, d) = _winRate(s);
        return d == 0 ? -1 : n / d;
      case _Sort.ranking:
        // 使用率順：ランキング上位ほど大きいキー（降順で上位が先頭）。
        return -ScrapeData.instance.rankOf(s.pid).toDouble();
      case _Sort.count:
        return switch (_mode) {
          _Mode.kp => s.appeared.toDouble(),
          _Mode.chosen => s.chosen.toDouble(),
          _Mode.first => s.first.toDouble(),
        };
    }
  }

  // スマホ版は常に「%（分数）」の両方表示。
  String _fmtVal(int n, int d, {bool isCount = false}) {
    if (isCount) return '$n'; // KP の上段は出現数（実数）
    final pct = d == 0 ? 0.0 : n / d * 100;
    return '${pct.toStringAsFixed(1)}% ($n/$d)';
  }

  @override
  Widget build(BuildContext context) {
    final res = _result;
    final stats = (res?.stats ?? [])
        .where((s) => s.appeared > 0)
        // トップに絞る：使用率トップ N に該当しないポケモンを除外。
        .where((s) => _topN == 0 || ScrapeData.instance.inTopN(s.pid, _topN))
        .toList()
      ..sort((a, b) {
        final cmp = _sortKey(a).compareTo(_sortKey(b));
        return _descending ? -cmp : cmp;
      });
    final shown = stats.take(_limit).toList();

    return Scaffold(
      appBar: AppBar(title: const Text('対戦分析')),
      body: SafeArea(
        child: Column(
          children: [
            _filterBar(),
            _summary(res),
            if (_playerStats.isNotEmpty) _playerPartySection(),
            _panel(),
            const Divider(height: 1),
            Expanded(
              child: _loading
                  ? const Center(child: CircularProgressIndicator())
                  : shown.isEmpty
                      ? const Center(child: Text('対象の記録がありません'))
                      // 原典準拠のグリッド表示（各セル＝アイコン＋主指標＋勝率）。
                      : GridView.builder(
                          padding: const EdgeInsets.all(4),
                          gridDelegate:
                              const SliverGridDelegateWithMaxCrossAxisExtent(
                            // 横幅は元に戻す（数値が途切れないように）。縦だけ小さく。
                            maxCrossAxisExtent: 168,
                            mainAxisExtent: 50,
                            crossAxisSpacing: 4,
                            mainAxisSpacing: 4,
                          ),
                          itemCount: shown.length,
                          itemBuilder: (_, i) => _statCell(i + 1, shown[i]),
                        ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _filterBar() {
    // 1段に集約：期間プリセット・シーズン・日付ボタン（シーズンの右）・
    // 右端に P番号/連番/検索。
    return Padding(
      padding: const EdgeInsets.fromLTRB(12, 6, 12, 2),
      child: Row(
        children: [
          PeriodPresetDropdown(value: _preset, onChanged: _applyPreset),
          SeasonDropdown(
              seasons: ScrapeData.instance.seasons,
              selectedName: _season,
              onSelected: (s) => setState(() {
                    _from = s.from;
                    _to = s.to;
                    _season = s.name;
                    _preset = PeriodPreset.custom;
                    _run();
                  })),
          const SizedBox(width: 6),
          DayBoundaryChip(
            label: '開始11時',
            tooltip: '開始日を11時以降にする',
            value: _startAt11,
            onChanged: (v) {
              setState(() => _startAt11 = v);
              _run();
            },
          ),
          const SizedBox(width: 3),
          OutlinedButton(
              style: OutlinedButton.styleFrom(
                  visualDensity: VisualDensity.compact,
                  padding: const EdgeInsets.symmetric(horizontal: 8)),
              onPressed: () => _pickDate(true),
              child: Text('${_fmtDate(_from)} 〜',
                  style: const TextStyle(fontSize: 11))),
          const SizedBox(width: 3),
          OutlinedButton(
              style: OutlinedButton.styleFrom(
                  visualDensity: VisualDensity.compact,
                  padding: const EdgeInsets.symmetric(horizontal: 8)),
              onPressed: () => _pickDate(false),
              child:
                  Text(_fmtDate(_to), style: const TextStyle(fontSize: 11))),
          const SizedBox(width: 3),
          DayBoundaryChip(
            label: '終了11時',
            tooltip: '終了日を11時までにする',
            value: _endAt11,
            onChanged: (v) {
              setState(() => _endAt11 = v);
              _run();
            },
          ),
          const Spacer(),
          SizedBox(
            width: 54,
            child: TextField(
              controller: _partyNum,
              keyboardType: TextInputType.number,
              decoration: const InputDecoration(labelText: 'P番号', isDense: true),
              onSubmitted: (_) => _searchByParty(),
            ),
          ),
          const SizedBox(width: 4),
          SizedBox(
            width: 54,
            child: TextField(
              controller: _partySubnum,
              keyboardType: TextInputType.number,
              decoration: const InputDecoration(labelText: '連番', isDense: true),
              onSubmitted: (_) => _searchByParty(),
            ),
          ),
          IconButton(
              icon: const Icon(Icons.search),
              visualDensity: VisualDensity.compact,
              onPressed: _searchByParty),
        ],
      ),
    );
  }

  Widget _summary(AnalysisResult? res) {
    if (res == null) return const SizedBox.shrink();
    return Container(
      width: double.infinity,
      color: Colors.blueGrey.withValues(alpha: 0.06),
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 4),
      child: Row(
        children: [
          Text('対戦数 ${res.battles}',
              style: const TextStyle(fontWeight: FontWeight.bold)),
          const SizedBox(width: 10),
          Text('勝率 ${res.winRate.toStringAsFixed(1)}%',
              style: const TextStyle(
                  fontWeight: FontWeight.bold, color: Colors.red)),
          const SizedBox(width: 6),
          // 勝/敗/分を色分けで明示（勝率＝勝/全対戦数）。
          Text('${res.wins}勝',
              style: const TextStyle(fontSize: 12, color: Colors.red)),
          const Text(' / ', style: TextStyle(fontSize: 12)),
          Text('${res.loses}敗',
              style: const TextStyle(fontSize: 12, color: Colors.blueGrey)),
          const Text(' / ', style: TextStyle(fontSize: 12)),
          Text('${res.draws}分',
              style: TextStyle(fontSize: 12, color: Colors.amber.shade800)),
          const Spacer(),
          // 直近使用した自分パーティ
          if (_recentParty.isNotEmpty) ...[
            const Text('直近: ',
                style: TextStyle(fontSize: 10, color: Colors.black45)),
            for (final pid in _recentParty)
              Image.asset('assets/pokemon/$pid.png',
                  width: 20,
                  height: 20,
                  errorBuilder: (_, __, ___) => const SizedBox(width: 20)),
          ],
        ],
      ),
    );
  }

  /// P番号指定時：自分パーティのポケモン別成績（選出率・選出時勝率・初手率）。
  Widget _playerPartySection() {
    final battles = _result?.battles ?? 0;
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.fromLTRB(10, 4, 10, 6),
      decoration: BoxDecoration(
        color: Colors.indigo.withValues(alpha: 0.04),
        border: Border(
            bottom: BorderSide(color: Colors.indigo.withValues(alpha: 0.15))),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // ヘッダ全体タップで開閉（上下シェブロン）。
          InkWell(
            onTap: () => setState(() => _showPlayerStats = !_showPlayerStats),
            child: Padding(
              padding: const EdgeInsets.symmetric(vertical: 2),
              child: Row(
                children: [
                  const Expanded(
                    child: Text('自分パーティのポケモン別成績（選出率／選出時勝率／初手）',
                        style: TextStyle(
                            fontSize: 10, fontWeight: FontWeight.bold)),
                  ),
                  Icon(
                      _showPlayerStats
                          ? Icons.keyboard_arrow_up
                          : Icons.keyboard_arrow_down,
                      size: 18,
                      color: Colors.black45),
                ],
              ),
            ),
          ),
          if (_showPlayerStats)
            SingleChildScrollView(
              scrollDirection: Axis.horizontal,
              child: Row(
                children: [
                  for (final s in _playerStats) _playerStatCell(s, battles),
                ],
              ),
            ),
        ],
      ),
    );
  }

  Widget _playerStatCell(PlayerPokeStat s, int battles) {
    String pct(int n, int d) => d == 0 ? '—' : '${(n / d * 100).round()}%';
    final winRate = s.chosen == 0 ? -1.0 : s.chosenWin / s.chosen;
    final winColor = winRate < 0
        ? Colors.black38
        : winRate >= 0.5
            ? Colors.red
            : Colors.blueGrey;
    return Container(
      width: 92,
      margin: const EdgeInsets.only(right: 6),
      padding: const EdgeInsets.symmetric(horizontal: 4, vertical: 3),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(6),
        border: Border.all(color: Colors.black12),
      ),
      child: Row(
        children: [
          Image.asset('assets/pokemon/${s.pid}.png',
              width: 34,
              height: 34,
              errorBuilder: (_, __, ___) => const SizedBox(width: 34)),
          const SizedBox(width: 2),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                Text('選${pct(s.chosen, battles)}',
                    style: const TextStyle(fontSize: 10)),
                Text('勝${pct(s.chosenWin, s.chosen)}',
                    style: TextStyle(
                        fontSize: 11,
                        fontWeight: FontWeight.bold,
                        color: winColor)),
                Text('初${pct(s.first, battles)}',
                    style: const TextStyle(
                        fontSize: 9, color: Colors.black45)),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _panel() {
    // 横スクロールをやめ、Wrap で折り返して全コントロールを常時表示する
    // （旧実装はノッチ裏に隠れていた）。
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
      child: Wrap(
        spacing: 6,
        runSpacing: 4,
        crossAxisAlignment: WrapCrossAlignment.center,
        children: [
          _seg<_Mode>(_mode, const {
            _Mode.kp: 'KP',
            _Mode.chosen: '選出',
            _Mode.first: '初手',
          }, (v) => setState(() => _mode = v)),
          _seg<_Sort>(_sort, const {
            _Sort.count: '件数',
            _Sort.rate: '勝率',
            _Sort.ranking: '使用率',
          }, (v) => setState(() => _sort = v)),
          _toggle('順', _descending ? '降順' : '昇順',
              () => setState(() => _descending = !_descending)),
          _toggle('メガ統合', _megaMerge ? 'ON' : 'OFF', () {
            setState(() => _megaMerge = !_megaMerge);
            _run();
          }),
          // トップに絞る（使用率トップN）。
          _toggle('トップ', _topN == 0 ? 'OFF' : '$_topN', () {
            setState(() => _topN = switch (_topN) {
                  0 => 10,
                  10 => 30,
                  30 => 50,
                  _ => 0,
                });
          }),
          _seg<int>(_limit, const {50: '50位', 100: '100位'},
              (v) => setState(() => _limit = v)),
        ],
      ),
    );
  }

  Widget _seg<T>(T value, Map<T, String> options, ValueChanged<T> onChanged) {
    return SegmentedButton<T>(
      style: const ButtonStyle(visualDensity: VisualDensity.compact),
      segments: [
        for (final e in options.entries)
          ButtonSegment(
              value: e.key,
              label: Text(e.value, style: const TextStyle(fontSize: 11))),
      ],
      selected: {value},
      showSelectedIcon: false,
      onSelectionChanged: (s) => onChanged(s.first),
    );
  }

  Widget _toggle(String label, String value, VoidCallback onTap) {
    return OutlinedButton(
      style: OutlinedButton.styleFrom(
          visualDensity: VisualDensity.compact,
          padding: const EdgeInsets.symmetric(horizontal: 8)),
      onPressed: onTap,
      child: Text('$label:$value', style: const TextStyle(fontSize: 11)),
    );
  }

  /// グリッドの1セル（原典準拠：アイコン＋主指標＋勝率＋順位バッジ）。
  Widget _statCell(int rank, PokeStat s) {
    final (pn, pd) = _primary(s);
    final (wn, wd) = _winRate(s);
    final primaryLabel = switch (_mode) {
      _Mode.kp => 'KP',
      _Mode.chosen => '選出',
      _Mode.first => '初手',
    };
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 4, vertical: 3),
      decoration: BoxDecoration(
        color: Colors.blueGrey.withValues(alpha: 0.05),
        borderRadius: BorderRadius.circular(6),
        border: Border.all(color: Colors.black12),
      ),
      child: Row(
        children: [
          Stack(
            children: [
              Image.asset('assets/pokemon/${s.pid}.png',
                  width: 30,
                  height: 30,
                  errorBuilder: (_, __, ___) => const SizedBox(width: 30)),
              Positioned(
                left: 0,
                top: 0,
                child: Container(
                  padding:
                      const EdgeInsets.symmetric(horizontal: 2, vertical: 1),
                  color: Colors.black54,
                  child: Text('$rank',
                      style: const TextStyle(
                          fontSize: 7, color: Colors.white)),
                ),
              ),
            ],
          ),
          const SizedBox(width: 3),
          Expanded(
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                    '$primaryLabel ${_mode == _Mode.kp ? _fmtVal(pn, pd, isCount: true) : _fmtVal(pn, pd)}',
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: const TextStyle(
                        fontSize: 10, fontWeight: FontWeight.bold)),
                Text('勝 ${_fmtVal(wn, wd)}',
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: const TextStyle(
                        fontSize: 8, color: Colors.black54)),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
