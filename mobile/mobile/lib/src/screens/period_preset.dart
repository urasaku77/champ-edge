import 'package:flutter/material.dart';

import '../data/scrape_data.dart';

/// シーズン選択（旧 champ-edge のシーズンドロップダウン）。スクレイピング由来の
/// season データ（ScrapeData.seasons）から選ぶと from/to を設定する。データが無ければ非表示。
class SeasonDropdown extends StatelessWidget {
  const SeasonDropdown(
      {super.key,
      required this.seasons,
      required this.onSelected,
      this.selectedName});

  final List<SeasonDef> seasons;
  final void Function(SeasonDef season) onSelected;

  /// 現在選択中のシーズン名（未選択なら null）。選択中は名前を表示・強調する。
  final String? selectedName;

  @override
  Widget build(BuildContext context) {
    if (seasons.isEmpty) return const SizedBox.shrink();
    final active = selectedName != null;
    return PopupMenuButton<SeasonDef>(
      tooltip: 'シーズン',
      itemBuilder: (_) => [
        for (final s in seasons)
          PopupMenuItem(
            value: s,
            child: Row(children: [
              Icon(Icons.check,
                  size: 16,
                  color: s.name == selectedName
                      ? Colors.indigo
                      : Colors.transparent),
              const SizedBox(width: 4),
              Text(s.name),
            ]),
          ),
      ],
      onSelected: onSelected,
      child: Container(
        margin: const EdgeInsets.only(left: 4),
        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
        decoration: BoxDecoration(
          color:
              active ? Colors.indigo.withValues(alpha: 0.12) : Colors.transparent,
          borderRadius: BorderRadius.circular(6),
          border: Border.all(color: active ? Colors.indigo : Colors.black26),
        ),
        child: Row(mainAxisSize: MainAxisSize.min, children: [
          Text(active ? 'シーズン: $selectedName' : 'シーズン',
              style: TextStyle(
                  fontSize: 12,
                  fontWeight: active ? FontWeight.bold : FontWeight.normal,
                  color: active ? Colors.indigo : Colors.black87)),
          Icon(Icons.arrow_drop_down,
              size: 18, color: active ? Colors.indigo : Colors.black54),
        ]),
      ),
    );
  }
}

/// ランク戦の日替り境界（11時）に期間端を合わせる1個のチェックチップ（旧 champ-edge：
/// 「開始日を11時以降にする」「終了日を11時までにする」）。開始日ボタンの左・終了日ボタンの
/// 右にそれぞれ置く。デフォルト ON。
class DayBoundaryChip extends StatelessWidget {
  const DayBoundaryChip({
    super.key,
    required this.label,
    required this.tooltip,
    required this.value,
    required this.onChanged,
  });

  final String label;
  final String tooltip;
  final bool value;
  final ValueChanged<bool> onChanged;

  @override
  Widget build(BuildContext context) {
    final on = value;
    return Tooltip(
      message: tooltip,
      child: InkWell(
        onTap: () => onChanged(!on),
        borderRadius: BorderRadius.circular(5),
        child: Container(
          padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 6),
          decoration: BoxDecoration(
            color: on ? Colors.indigo.withValues(alpha: 0.12) : null,
            borderRadius: BorderRadius.circular(5),
            border: Border.all(color: on ? Colors.indigo : Colors.black26),
          ),
          child: Row(mainAxisSize: MainAxisSize.min, children: [
            Icon(on ? Icons.check_box : Icons.check_box_outline_blank,
                size: 13, color: on ? Colors.indigo : Colors.black38),
            const SizedBox(width: 2),
            Text(label,
                style: TextStyle(
                    fontSize: 10,
                    color: on ? Colors.indigo : Colors.black54)),
          ]),
        ),
      ),
    );
  }
}

/// 期間プリセット（旧 champ-edge のシーズン選択に相当する、データ不要のクイック期間）。
/// シーズン名リスト（season.json）はスクレイプ依存のため、実用上同等のプリセットで代替する。
enum PeriodPreset { all, today, week, month, last30, last90, custom }

extension PeriodPresetLabel on PeriodPreset {
  String get label => switch (this) {
        PeriodPreset.all => '全期間',
        PeriodPreset.today => '今日',
        PeriodPreset.week => '今週',
        PeriodPreset.month => '今月',
        PeriodPreset.last30 => '過去30日',
        PeriodPreset.last90 => '過去90日',
        PeriodPreset.custom => 'カスタム',
      };

  /// (from, to) を返す。custom は null（日付ピッカーの値を使う）。
  (DateTime, DateTime)? range() {
    final now = DateTime.now();
    final today = DateTime(now.year, now.month, now.day);
    return switch (this) {
      PeriodPreset.all => (DateTime(2020), now),
      PeriodPreset.today => (today, now),
      PeriodPreset.week => (today.subtract(const Duration(days: 6)), now),
      PeriodPreset.month => (DateTime(now.year, now.month, 1), now),
      PeriodPreset.last30 => (today.subtract(const Duration(days: 29)), now),
      PeriodPreset.last90 => (today.subtract(const Duration(days: 89)), now),
      PeriodPreset.custom => null,
    };
  }
}

/// 期間プリセットのドロップダウン。選択で from/to を設定する。
class PeriodPresetDropdown extends StatelessWidget {
  const PeriodPresetDropdown(
      {super.key, required this.value, required this.onChanged});

  final PeriodPreset value;
  final ValueChanged<PeriodPreset> onChanged;

  @override
  Widget build(BuildContext context) {
    return DropdownButton<PeriodPreset>(
      value: value,
      isDense: true,
      underline: const SizedBox.shrink(),
      style: const TextStyle(fontSize: 12, color: Colors.black87),
      items: [
        for (final p in PeriodPreset.values)
          DropdownMenuItem(value: p, child: Text(p.label)),
      ],
      onChanged: (p) {
        if (p != null) onChanged(p);
      },
    );
  }
}
