/// 加算ツールのロジック（旧 champ-edge MultiWazaDamageWindow の移植・UI非依存）。
///
/// 技ごとの 16 値ダメージ分布（定数ダメージ加算済み）と回復を累積し、
/// 合計ダメージと KO 判定（確定KO/乱数KO%）を計算する。
library;

/// 累積リストの1行（技 or 回復）。
class AdderEntry {
  AdderEntry.move(this.label, List<int> damagesWithConstant)
      : damages = List.unmodifiable(damagesWithConstant),
        healHp = 0;

  AdderEntry.heal(this.label, this.healHp) : damages = const [];

  final String label;

  /// 16値ダメージ（定数ダメージ加算済み）。回復行は空。
  final List<int> damages;

  /// 回復量（実数）。技行は 0。
  final int healHp;

  bool get isHeal => healHp > 0;
  int get minDamage => damages.isEmpty ? 0 : damages.first;
  int get maxDamage => damages.isEmpty ? 0 : damages.last;
}

/// 加算セッション。防御側の HP・実効HP（ステルスロック差引後）を固定して行を積む。
class AdderSession {
  AdderSession({required this.hp, required this.effectiveHp});

  /// 防御側の最大HP。
  final int hp;

  /// ステルスロック分を差し引いた実効HP（最低1）。
  final int effectiveHp;

  final List<AdderEntry> entries = [];

  void pressMove(String label, List<int> damagesWithConstant) =>
      entries.add(AdderEntry.move(label, damagesWithConstant));

  void pressHeal(String label, int numerator, int denominator) =>
      entries.add(AdderEntry.heal(label, hp * numerator ~/ denominator));

  void removeAt(int index) => entries.removeAt(index);

  void clear() => entries.clear();

  int get totalHeal =>
      entries.fold(0, (sum, e) => sum + e.healHp);

  int get totalMin =>
      entries.fold(0, (sum, e) => sum + e.minDamage) - totalHeal;

  int get totalMax =>
      entries.fold(0, (sum, e) => sum + e.maxDamage) - totalHeal;

  bool get hasMove => entries.any((e) => !e.isHeal);

  /// KO 判定（原典 _calc_ko_text と同一）。各技の 16 値分布の直積を DP で集計し、
  /// しきい値（実効HP＋回復合計）以上の組み合わせ数で判定する。
  String get koText {
    final damageLists = [
      for (final e in entries)
        if (!e.isHeal && e.damages.isNotEmpty) e.damages,
    ];
    if (damageLists.isEmpty) return '';
    final threshold = effectiveHp + totalHeal;
    var dp = <int, int>{0: 1};
    var totalCombos = 1;
    for (final damages in damageLists) {
      final next = <int, int>{};
      dp.forEach((dmg, count) {
        for (final d in damages) {
          final key = dmg + d;
          next[key] = (next[key] ?? 0) + count;
        }
      });
      dp = next;
      totalCombos *= 16;
    }
    var koCount = 0;
    dp.forEach((dmg, count) {
      if (dmg >= threshold) koCount += count;
    });
    if (koCount == 0) return '';
    if (koCount == totalCombos) return '確定KO';
    final pct = (koCount / totalCombos * 1000).round() / 10;
    return '乱数KO ($pct%)';
  }
}
