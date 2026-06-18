import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:path/path.dart' as p;
import 'package:path_provider/path_provider.dart';

import '../data/battle_db.dart';
import '../data/poke_db.dart';
import '../data/scrape_data.dart';
import '../model/battle_record.dart';
import 'period_preset.dart';
import 'pokemon_picker.dart';

/// 並び替えの基準（旧 champ-edge：対戦時間／登録順）。
enum _SortField { time, registration }

/// 対戦履歴画面（旧 champ-edge の対戦履歴画面の移植）。
/// 期間・パーティ番号/連番・キーワード・お気に入りで絞り込み、並び替え・一覧表示・
/// 編集・範囲削除・新規追加・CSV エクスポートを行う。
class BattleHistoryScreen extends StatefulWidget {
  const BattleHistoryScreen({super.key});

  @override
  State<BattleHistoryScreen> createState() => _BattleHistoryScreenState();
}

class _BattleHistoryScreenState extends State<BattleHistoryScreen> {
  DateTime _from = DateTime.now().subtract(const Duration(days: 90));
  DateTime _to = DateTime.now();
  PeriodPreset _preset = PeriodPreset.last90;
  String? _season; // 選択中のシーズン名（M-1 等。未選択は null）
  final _partyNum = TextEditingController();
  final _partySubnum = TextEditingController();
  final _keyword = TextEditingController();
  bool _favoriteOnly = false;
  _SortField _sortField = _SortField.time; // 並び替え：対戦時間/登録順
  bool _ascending = false; // 既定は新しい順（降順）
  bool _startAt11 = true; // 開始日を11時以降にする（ランク日替り境界）
  bool _endAt11 = true; // 終了日を11時までにする
  List<BattleRecord> _records = const [];
  bool _searched = false;

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
    _search();
  }

  Future<void> _search() async {
    await ScrapeData.instance.load();
    await BattleDb.instance.open();
    final r = await BattleDb.instance.query(
      fromDate: _fromSec,
      toDate: _toSec,
      partyNum: _partyNum.text.trim(),
      partySubnum: _partySubnum.text.trim(),
      keyword: _keyword.text.trim(),
      favoriteOnly: _favoriteOnly,
    );
    if (!mounted) return;
    setState(() {
      _records = _sorted(r);
      _searched = true;
    });
  }

  /// 並び替え（対戦時間＝date／登録順＝id）。昇順/降順を反映。
  List<BattleRecord> _sorted(List<BattleRecord> rs) {
    final list = [...rs];
    int cmp(BattleRecord a, BattleRecord b) => switch (_sortField) {
          _SortField.time => a.date.compareTo(b.date),
          _SortField.registration => (a.id ?? 0).compareTo(b.id ?? 0),
        };
    list.sort((a, b) => _ascending ? cmp(a, b) : -cmp(a, b));
    return list;
  }

  void _setSort(_SortField f) {
    setState(() {
      // 同じ基準を再選択したら昇順/降順をトグル、別基準なら降順から。
      if (_sortField == f) {
        _ascending = !_ascending;
      } else {
        _sortField = f;
        _ascending = false;
      }
      _records = _sorted(_records);
    });
  }

  Future<void> _pickDate(bool isFrom) async {
    final init = isFrom ? _from : _to;
    final d = await showDatePicker(
      context: context,
      initialDate: init,
      firstDate: DateTime(2020),
      lastDate: DateTime(2100),
    );
    if (d == null) return;
    setState(() {
      isFrom ? _from = d : _to = d;
      _preset = PeriodPreset.custom;
      _season = null; // 手動日付指定でシーズン選択は解除。
    });
    _search();
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
    _search();
  }

  String _fmtDate(DateTime d) =>
      '${d.year}/${d.month.toString().padLeft(2, '0')}/${d.day.toString().padLeft(2, '0')}';

  /// 日付＋時刻（原典は対戦時間を時刻まで表示）。
  String _fmtDateTime(DateTime d) =>
      '${_fmtDate(d)} ${d.hour.toString().padLeft(2, '0')}:${d.minute.toString().padLeft(2, '0')}';

  @override
  Widget build(BuildContext context) {
    final wins = _records.where((r) => r.isWin).length;
    final draws = _records.where((r) => r.result == 2).length;
    final loses = _records.length - wins - draws;
    final rate =
        _records.isEmpty ? 0.0 : wins / _records.length * 100;
    return Scaffold(
      appBar: AppBar(
        title: const Text('対戦履歴'),
        actions: [
          IconButton(
            tooltip: 'CSVエクスポート',
            icon: const Icon(Icons.download),
            onPressed: _records.isEmpty ? null : _exportCsv,
          ),
          IconButton(
            tooltip: 'この範囲を全削除',
            icon: const Icon(Icons.delete_sweep),
            onPressed: _records.isEmpty ? null : _deleteRange,
          ),
          IconButton(
            tooltip: '新規追加',
            icon: const Icon(Icons.add),
            onPressed: _addNew,
          ),
        ],
      ),
      body: SafeArea(
        child: Column(
          children: [
            _filterBar(),
            Container(
              width: double.infinity,
              color: Colors.blueGrey.withValues(alpha: 0.06),
              padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 4),
              child: Row(
                children: [
                  Text('${_records.length}件',
                      style: const TextStyle(fontWeight: FontWeight.bold)),
                  if (_records.isNotEmpty) ...[
                    const SizedBox(width: 8),
                    Text('勝率${rate.toStringAsFixed(1)}%',
                        style: const TextStyle(
                            fontWeight: FontWeight.bold, color: Colors.red)),
                    const SizedBox(width: 6),
                    Text('$wins勝',
                        style: const TextStyle(
                            fontSize: 12, color: Colors.red)),
                    const Text('/', style: TextStyle(fontSize: 12)),
                    Text('$loses敗',
                        style: const TextStyle(
                            fontSize: 12, color: Colors.blueGrey)),
                    const Text('/', style: TextStyle(fontSize: 12)),
                    Text('$draws分',
                        style: TextStyle(
                            fontSize: 12, color: Colors.amber.shade800)),
                  ],
                  const Spacer(),
                  // キーワード・お気に入り・並び替えをこの行へ集約（1行削減）。
                  SizedBox(
                    width: 180,
                    child: TextField(
                      controller: _keyword,
                      style: const TextStyle(fontSize: 12),
                      decoration: const InputDecoration(
                          labelText: 'キーワード(TN/メモ)',
                          isDense: true,
                          border: OutlineInputBorder()),
                      onSubmitted: (_) => _search(),
                    ),
                  ),
                  IconButton(
                    icon: Icon(_favoriteOnly ? Icons.star : Icons.star_border,
                        color: _favoriteOnly ? Colors.amber : null),
                    tooltip: 'お気に入りのみ',
                    visualDensity: VisualDensity.compact,
                    onPressed: () {
                      setState(() => _favoriteOnly = !_favoriteOnly);
                      _search();
                    },
                  ),
                  const SizedBox(width: 4),
                  _sortChip('対戦時間', _SortField.time),
                  const SizedBox(width: 4),
                  _sortChip('登録順', _SortField.registration),
                ],
              ),
            ),
            const Divider(height: 1),
            Expanded(
              child: !_searched
                  ? const Center(child: CircularProgressIndicator())
                  : _records.isEmpty
                      ? const Center(child: Text('記録がありません'))
                      : ListView.separated(
                          itemCount: _records.length,
                          separatorBuilder: (_, __) =>
                              const Divider(height: 1),
                          itemBuilder: (_, i) => _row(_records[i]),
                        ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _filterBar() {
    return Padding(
      padding: const EdgeInsets.fromLTRB(12, 6, 12, 4),
      child: Column(
        children: [
          // 1段目：期間プリセット・シーズン・日付ボタン（シーズンの右）・P番号/連番/検索。
          Row(
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
                        _search();
                      })),
              const SizedBox(width: 6),
              // 開始日ボタンの左：開始11時チェック。
              DayBoundaryChip(
                label: '開始11時',
                tooltip: '開始日を11時以降にする',
                value: _startAt11,
                onChanged: (v) {
                  setState(() => _startAt11 = v);
                  _search();
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
                  child: Text(_fmtDate(_to),
                      style: const TextStyle(fontSize: 11))),
              const SizedBox(width: 3),
              // 終了日ボタンの右：終了11時チェック。
              DayBoundaryChip(
                label: '終了11時',
                tooltip: '終了日を11時までにする',
                value: _endAt11,
                onChanged: (v) {
                  setState(() => _endAt11 = v);
                  _search();
                },
              ),
              const Spacer(),
              SizedBox(
                width: 54,
                child: TextField(
                  controller: _partyNum,
                  keyboardType: TextInputType.number,
                  decoration:
                      const InputDecoration(labelText: 'P番号', isDense: true),
                  onSubmitted: (_) => _search(),
                ),
              ),
              const SizedBox(width: 4),
              SizedBox(
                width: 54,
                child: TextField(
                  controller: _partySubnum,
                  keyboardType: TextInputType.number,
                  decoration:
                      const InputDecoration(labelText: '連番', isDense: true),
                  onSubmitted: (_) => _search(),
                ),
              ),
              IconButton(
                  icon: const Icon(Icons.search),
                  visualDensity: VisualDensity.compact,
                  onPressed: _search),
            ],
          ),
        ],
      ),
    );
  }

  /// 並び替えチップ。選択中は方向（▲昇順/▼降順）を併記、再タップで方向トグル。
  Widget _sortChip(String label, _SortField field) {
    final active = _sortField == field;
    final arrow = !active ? '' : (_ascending ? ' ▲' : ' ▼');
    return OutlinedButton(
      style: OutlinedButton.styleFrom(
        visualDensity: VisualDensity.compact,
        padding: const EdgeInsets.symmetric(horizontal: 8),
        backgroundColor:
            active ? Colors.indigo.withValues(alpha: 0.12) : null,
        side: BorderSide(color: active ? Colors.indigo : Colors.black26),
      ),
      onPressed: () => _setSort(field),
      child: Text('$label$arrow',
          style: TextStyle(
              fontSize: 11,
              fontWeight: active ? FontWeight.bold : FontWeight.normal,
              color: active ? Colors.indigo : Colors.black87)),
    );
  }

  /// パーティ6体を選出ハイライト付きで描画（原典の「パーティ＋選出」列に相当）。
  /// choices に含まれる pid は枠を強調＋選出順を表示、それ以外は淡色。
  Widget _partyStrip(List<String> party, List<String> choices) {
    final order = <String, int>{};
    for (var i = 0; i < choices.length; i++) {
      final c = choices[i];
      if (c != '-1' && c.isNotEmpty) order.putIfAbsent(c, () => i + 1);
    }
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        for (final pid in party)
          if (pid != '-1')
            Padding(
              padding: const EdgeInsets.only(right: 1),
              child: () {
                final chosen = order.containsKey(pid);
                return Stack(
                  children: [
                    Opacity(
                      opacity: chosen ? 1.0 : 0.87,
                      child: Container(
                        decoration: chosen
                            ? BoxDecoration(
                                borderRadius: BorderRadius.circular(4),
                                border: Border.all(
                                    color: Colors.indigo, width: 1.5))
                            : null,
                        child: Image.asset('assets/pokemon/$pid.png',
                            width: 24,
                            height: 24,
                            errorBuilder: (_, __, ___) =>
                                const SizedBox(width: 24)),
                      ),
                    ),
                    if (chosen)
                      Positioned(
                        right: 0,
                        bottom: 0,
                        child: Container(
                          padding: const EdgeInsets.symmetric(horizontal: 2),
                          decoration: const BoxDecoration(
                            color: Colors.indigo,
                            borderRadius:
                                BorderRadius.all(Radius.circular(3)),
                          ),
                          child: Text('${order[pid]}',
                              style: const TextStyle(
                                  fontSize: 8,
                                  color: Colors.white,
                                  fontWeight: FontWeight.bold)),
                        ),
                      ),
                  ],
                );
              }(),
            ),
      ],
    );
  }

  Widget _row(BattleRecord r) {
    final (label, color) = switch (r.result) {
      1 => ('勝', Colors.red),
      2 => ('分', Colors.amber),
      _ => ('負', Colors.blueGrey),
    };
    return InkWell(
      onTap: () => _editRecord(r),
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 5),
        child: Row(
          children: [
            Container(
              width: 24,
              height: 24,
              alignment: Alignment.center,
              decoration: BoxDecoration(
                  color: color.withValues(alpha: 0.18),
                  shape: BoxShape.circle),
              child: Text(label,
                  style: TextStyle(
                      color: color, fontWeight: FontWeight.bold, fontSize: 12)),
            ),
            const SizedBox(width: 6),
            // 自分パーティ＋選出
            _partyStrip(r.playerPokemons, r.playerChoices),
            const Padding(
              padding: EdgeInsets.symmetric(horizontal: 4),
              child: Text('vs',
                  style: TextStyle(fontSize: 10, color: Colors.black38)),
            ),
            // 相手パーティ＋選出
            _partyStrip(r.opponentPokemons, r.opponentChoices),
            const Spacer(),
            SizedBox(
              width: 150,
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.end,
                children: [
                  Text(
                      '${_fmtDateTime(r.dateTime)}'
                      '${r.opponentRate.isEmpty ? '' : '  R${r.opponentRate}'}',
                      style: const TextStyle(fontSize: 10)),
                  if (r.opponentTn.isNotEmpty)
                    Text(r.opponentTn,
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                        style: const TextStyle(
                            fontSize: 11, fontWeight: FontWeight.w600)),
                ],
              ),
            ),
            if (r.isFavorite)
              const Icon(Icons.star, color: Colors.amber, size: 16),
          ],
        ),
      ),
    );
  }

  Future<void> _editRecord(BattleRecord r) async {
    final changed = await showDialog<bool>(
      context: context,
      builder: (ctx) => _EditRecordDialog(record: r),
    );
    if (changed == true) _search();
  }

  Future<void> _addNew() async {
    // 新規は空の負け記録を作り、編集ダイアログで内容を整える（相手ポケモンは現状空）。
    final blank = BattleRecord(
      date: DateTime.now().millisecondsSinceEpoch ~/ 1000,
      result: 0,
      playerPokemons: List.filled(6, '-1'),
      opponentPokemons: List.filled(6, '-1'),
      playerChoices: List.filled(4, '-1'),
      opponentChoices: List.filled(4, '-1'),
    );
    await BattleDb.instance.open();
    final id = await BattleDb.instance.register(blank);
    if (!mounted) return;
    final created = BattleRecord.fromRow({'id': id, ...blank.toColumns()});
    _editRecord(created);
  }

  Future<void> _deleteRange() async {
    final ok = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('範囲を全削除'),
        content: Text('現在の絞り込み ${_records.length} 件を削除します。元に戻せません。'),
        actions: [
          TextButton(
              onPressed: () => Navigator.pop(ctx, false),
              child: const Text('キャンセル')),
          FilledButton(
              style: FilledButton.styleFrom(backgroundColor: Colors.red),
              onPressed: () => Navigator.pop(ctx, true),
              child: const Text('削除')),
        ],
      ),
    );
    if (ok != true) return;
    await BattleDb.instance.deleteByQuery(
      fromDate: _fromSec,
      toDate: _toSec,
      partyNum: _partyNum.text.trim(),
      partySubnum: _partySubnum.text.trim(),
      keyword: _keyword.text.trim(),
      favoriteOnly: _favoriteOnly,
    );
    _search();
  }

  /// CSV を UTF-8 BOM 付きでアプリ領域へ書き出す（旧 Excel 互換）。
  Future<void> _exportCsv() async {
    final headers = [
      'date', 'rule', 'result', 'favorite', 'opponent_tn', 'opponent_rate',
      'battle_memo', 'player_party_num', 'player_party_subnum',
      for (var i = 1; i <= 6; i++) 'player_pokemon$i',
      for (var i = 1; i <= 6; i++) 'opponent_pokemon$i',
      for (var i = 1; i <= 4; i++) 'player_choice$i',
      for (var i = 1; i <= 4; i++) 'opponent_choice$i',
    ];
    String esc(Object? v) {
      final s = '$v';
      return (s.contains(',') || s.contains('"') || s.contains('\n'))
          ? '"${s.replaceAll('"', '""')}"'
          : s;
    }

    final buf = StringBuffer('﻿')..writeln(headers.join(','));
    for (final r in _records) {
      final c = r.toColumns();
      buf.writeln(headers.map((h) => esc(c[h])).join(','));
    }
    final dir = await getApplicationDocumentsDirectory();
    final name =
        'battle_export_${DateTime.now().millisecondsSinceEpoch}.csv';
    final file = File(p.join(dir.path, name));
    await file.writeAsString(buf.toString());
    if (!mounted) return;
    showDialog<void>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('CSVエクスポート完了'),
        content: SelectableText('${_records.length} 件を出力しました:\n${file.path}'),
        actions: [
          TextButton(
            onPressed: () {
              Clipboard.setData(ClipboardData(text: file.path));
              Navigator.pop(ctx);
            },
            child: const Text('パスをコピー'),
          ),
          TextButton(
              onPressed: () => Navigator.pop(ctx), child: const Text('閉じる')),
        ],
      ),
    );
  }
}

/// 対戦記録の編集ダイアログ（result/TN/レート/メモ/お気に入り）＋削除。
class _EditRecordDialog extends StatefulWidget {
  const _EditRecordDialog({required this.record});
  final BattleRecord record;

  @override
  State<_EditRecordDialog> createState() => _EditRecordDialogState();
}

class _EditRecordDialogState extends State<_EditRecordDialog> {
  late final _tn = TextEditingController(text: widget.record.opponentTn);
  late final _rate = TextEditingController(text: widget.record.opponentRate);
  late final _memo = TextEditingController(text: widget.record.battleMemo);
  late final _pnum =
      TextEditingController(text: widget.record.playerPartyNum);
  late final _psub =
      TextEditingController(text: widget.record.playerPartySubnum);
  late int _result = widget.record.result;
  late bool _favorite = widget.record.isFavorite;
  late DateTime _date = widget.record.dateTime;



  String _fmtDate(DateTime d) =>
      '${d.year}/${d.month.toString().padLeft(2, '0')}/${d.day.toString().padLeft(2, '0')}';

  String _fmtDateTime(DateTime d) =>
      '${_fmtDate(d)} ${d.hour.toString().padLeft(2, '0')}:${d.minute.toString().padLeft(2, '0')}';

  /// 日付＋時刻を続けて選択する。
  Future<void> _pickDateTime() async {
    final d = await showDatePicker(
      context: context,
      initialDate: _date,
      firstDate: DateTime(2020),
      lastDate: DateTime(2100),
    );
    if (d == null || !mounted) return;
    final t = await showTimePicker(
        context: context, initialTime: TimeOfDay.fromDateTime(_date));
    if (!mounted) return;
    setState(() => _date = DateTime(
        d.year, d.month, d.day, t?.hour ?? _date.hour, t?.minute ?? _date.minute));
  }

  /// パーティの非空ポケモンから選出を1体選ぶ（原典準拠）。
  /// メガを持つポケモンは**メガフォームも候補に出す**（選出＝対戦で進化した姿を記録）。
  Future<String?> _pickFromParty(List<String> party,
      {Set<int> takenDex = const {}}) async {
    final members = [
      for (final pid in party)
        if (pid != '-1' && pid.isNotEmpty) pid
    ];
    int dexOf(String pid) => int.tryParse(pid.split('-').first) ?? -1;
    if (members.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(const SnackBar(
          duration: Duration(milliseconds: 1200),
          content: Text('先にパーティのポケモンを登録してください')));
      return null;
    }
    // 各メンバーごとに「素体＋（あれば）メガ」を1行に並べる（半端な折り返しを防ぐ）。
    final megaOf = <String, List<String>>{};
    for (final pid in members) {
      megaOf[pid] = await PokeDb.instance.megaPidsOf(pid);
    }
    if (!mounted) return null;
    Widget cell(BuildContext ctx, String pid, bool mega) {
      // 既に他の枠で選出済みの種（メガ込み）はグレーアウト＋選択不可（表示は残す）。
      final disabled = takenDex.contains(dexOf(pid));
      return InkWell(
          onTap: disabled ? null : () => Navigator.pop(ctx, pid),
          child: Stack(
            children: [
              Opacity(
                opacity: disabled ? 0.3 : 1.0,
                child: Image.asset('assets/pokemon/$pid.png',
                    width: 46,
                    height: 46,
                    errorBuilder: (_, __, ___) => const SizedBox(width: 46)),
              ),
              if (mega)
                Positioned(
                  left: 0,
                  bottom: 0,
                  child: Container(
                    padding: const EdgeInsets.symmetric(horizontal: 3),
                    color: Colors.deepPurple,
                    child: const Text('メガ',
                        style: TextStyle(fontSize: 8, color: Colors.white)),
                  ),
                ),
            ],
          ),
        );
    }
    // 上段に6体を横並び、各ポケモンの下にメガを縦に並べる（スクロール不要）。
    return showDialog<String>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('選出を選ぶ（メガは進化後を選択）',
            style: TextStyle(fontSize: 14)),
        contentPadding: const EdgeInsets.fromLTRB(12, 8, 12, 0),
        content: Row(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            for (final pid in members)
              Padding(
                padding: const EdgeInsets.symmetric(horizontal: 3),
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    cell(ctx, pid, false),
                    for (final m in megaOf[pid]!)
                      Padding(
                        padding: const EdgeInsets.only(top: 4),
                        child: cell(ctx, m, true),
                      ),
                  ],
                ),
              ),
          ],
        ),
        actions: [
          TextButton(
              onPressed: () => Navigator.pop(ctx), child: const Text('閉じる')),
        ],
      ),
    );
  }

  /// ポケモン枠の行（タップで選択、長押しで空に）。
  /// [fromParty] 指定時は選出としてそのパーティ内から選ぶ。未指定はメガ込み検索。
  Widget _slotRow(String label, List<String> pids, int count,
      {List<String>? fromParty}) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 2),
      child: Row(
        children: [
          SizedBox(
              width: 64,
              child: Text(label, style: const TextStyle(fontSize: 11))),
          for (var i = 0; i < count; i++)
            GestureDetector(
              onTap: () async {
                // 既に選出済みの種（メガ込み＝全国図鑑番号）を集める（編集中の枠は除く）。
                final takenDex = <int>{
                  for (var j = 0; j < count; j++)
                    if (j != i && pids[j] != '-1' && pids[j].isNotEmpty)
                      int.tryParse(pids[j].split('-').first) ?? -1
                };
                final pid = fromParty != null
                    ? await _pickFromParty(fromParty, takenDex: takenDex)
                    : await pickPokemon(context);
                if (pid != null) setState(() => pids[i] = pid);
              },
              onLongPress: () => setState(() => pids[i] = '-1'),
              child: Container(
                width: 32,
                height: 32,
                margin: const EdgeInsets.only(right: 2),
                decoration: BoxDecoration(
                  color: Colors.white,
                  borderRadius: BorderRadius.circular(5),
                  border: Border.all(color: Colors.black26),
                ),
                child: pids[i] == '-1'
                    ? const Icon(Icons.add, size: 14, color: Colors.black26)
                    : Image.asset('assets/pokemon/${pids[i]}.png',
                        errorBuilder: (_, __, ___) =>
                            const SizedBox.shrink()),
              ),
            ),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final r = widget.record;
    return AlertDialog(
      insetPadding: const EdgeInsets.symmetric(horizontal: 24, vertical: 16),
      title: const Text('記録の編集', style: TextStyle(fontSize: 15)),
      contentPadding: const EdgeInsets.fromLTRB(20, 8, 20, 0),
      content: SizedBox(
        width: 720,
        child: SingleChildScrollView(
          child: Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // 左列：日時/番号・勝敗＋レート・TN＋匿名＋お気に入り（ラベルはヒントで代用）。
              Expanded(
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        OutlinedButton.icon(
                          style: OutlinedButton.styleFrom(
                              visualDensity: VisualDensity.compact,
                              padding:
                                  const EdgeInsets.symmetric(horizontal: 8)),
                          icon: const Icon(Icons.schedule, size: 14),
                          label: Text(_fmtDateTime(_date),
                              style: const TextStyle(fontSize: 11)),
                          onPressed: _pickDateTime,
                        ),
                        const SizedBox(width: 6),
                        SizedBox(
                          width: 48,
                          child: TextField(
                              controller: _pnum,
                              keyboardType: TextInputType.number,
                              decoration: const InputDecoration(
                                  hintText: 'P番号', isDense: true)),
                        ),
                        const SizedBox(width: 4),
                        SizedBox(
                          width: 44,
                          child: TextField(
                              controller: _psub,
                              keyboardType: TextInputType.number,
                              decoration: const InputDecoration(
                                  hintText: '連番', isDense: true)),
                        ),
                      ],
                    ),
                    const SizedBox(height: 8),
                    // 勝敗＋レートを同じ行に。
                    Row(
                      children: [
                        SegmentedButton<int>(
                          style: const ButtonStyle(
                              visualDensity: VisualDensity.compact),
                          segments: const [
                            ButtonSegment(value: 1, label: Text('勝')),
                            ButtonSegment(value: 2, label: Text('分')),
                            ButtonSegment(value: 0, label: Text('負')),
                          ],
                          selected: {_result},
                          onSelectionChanged: (s) =>
                              setState(() => _result = s.first),
                        ),
                        const SizedBox(width: 8),
                        Expanded(
                          child: TextField(
                              controller: _rate,
                              keyboardType: TextInputType.number,
                              decoration: const InputDecoration(
                                  hintText: '相手レート', isDense: true)),
                        ),
                      ],
                    ),
                    const SizedBox(height: 8),
                    // TN＋匿名＋お気に入り。
                    Row(
                      children: [
                        Expanded(
                          child: TextField(
                              controller: _tn,
                              decoration: const InputDecoration(
                                  hintText: '相手TN', isDense: true)),
                        ),
                        const SizedBox(width: 4),
                        OutlinedButton(
                          style: OutlinedButton.styleFrom(
                              visualDensity: VisualDensity.compact,
                              padding:
                                  const EdgeInsets.symmetric(horizontal: 8)),
                          onPressed: () =>
                              setState(() => _tn.text = 'トレーナー'),
                          child: const Text('匿名',
                              style: TextStyle(fontSize: 12)),
                        ),
                        IconButton(
                          tooltip: 'お気に入り',
                          visualDensity: VisualDensity.compact,
                          icon: Icon(
                              _favorite ? Icons.star : Icons.star_border,
                              color: _favorite ? Colors.amber : null),
                          onPressed: () =>
                              setState(() => _favorite = !_favorite),
                        ),
                      ],
                    ),
                    const SizedBox(height: 8),
                    TextField(
                        controller: _memo,
                        minLines: 2,
                        maxLines: 4,
                        decoration: const InputDecoration(
                            hintText: 'メモ', isDense: true)),
                  ],
                ),
              ),
              const SizedBox(width: 16),
              // 右列：ポケモン（パーティ/選出）。
              Expanded(
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Text('ポケモン（枠タップで選択・長押しで空）',
                        style: TextStyle(fontSize: 10, color: Colors.black45)),
                    _slotRow('相手パーティ', r.opponentPokemons, 6),
                    _slotRow('相手選出', r.opponentChoices, 4,
                        fromParty: r.opponentPokemons),
                    const SizedBox(height: 2),
                    _slotRow('自分パーティ', r.playerPokemons, 6),
                    _slotRow('自分選出', r.playerChoices, 4,
                        fromParty: r.playerPokemons),
                  ],
                ),
              ),
            ],
          ),
        ),
      ),
      actions: [
        TextButton(
          style: TextButton.styleFrom(foregroundColor: Colors.red),
          onPressed: () async {
            await BattleDb.instance.deleteById(widget.record.id!);
            if (context.mounted) Navigator.pop(context, true);
          },
          child: const Text('削除'),
        ),
        TextButton(
            onPressed: () => Navigator.pop(context, false),
            child: const Text('キャンセル')),
        FilledButton(
          onPressed: () async {
            final r = widget.record;
            r.result = _result;
            r.opponentTn = _tn.text.trim();
            r.opponentRate = _rate.text.trim();
            r.battleMemo = _memo.text.trim();
            r.favorite = _favorite ? 1 : 0;
            r.date = _date.millisecondsSinceEpoch ~/ 1000;
            r.playerPartyNum = _pnum.text.trim();
            r.playerPartySubnum = _psub.text.trim();
            await BattleDb.instance.updateFull(r.id!, r);
            if (context.mounted) Navigator.pop(context, true);
          },
          child: const Text('保存'),
        ),
      ],
    );
  }
}
