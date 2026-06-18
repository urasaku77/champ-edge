import '../model/battle_record.dart';

/// 相手ポケモン1体ごとの集計（旧 champ-edge の分析画面の各カウント移植）。
class PokeStat {
  PokeStat(this.pid);
  final String pid;

  /// 出現（相手パーティに入っていた）対戦数 ＝ KP。
  int appeared = 0;

  /// 出現したうち勝った数。
  int appearedWin = 0;

  /// 相手が選出した対戦数。
  int chosen = 0;

  /// 選出されたうち勝った数。
  int chosenWin = 0;

  /// 相手が初手に選出した対戦数。
  int first = 0;
  int firstWin = 0;
}

/// 分析結果（対戦数・勝数・引分数・ポケモン別集計）。
class AnalysisResult {
  AnalysisResult(this.battles, this.wins, this.draws, this.stats);
  final int battles;
  final int wins;
  final int draws;

  /// 負け数（全体 − 勝 − 分）。
  int get loses => battles - wins - draws;

  /// 勝率＝勝 / 全対戦数（引分・負けも分母に含む。旧 champ-edge 準拠）。
  double get winRate => battles == 0 ? 0 : wins / battles * 100;
  final List<PokeStat> stats;
}

/// 自分パーティ1体ごとの成績（旧 champ-edge：P番号指定時のポケモン別勝率）。
class PlayerPokeStat {
  PlayerPokeStat(this.pid);
  final String pid;

  /// このポケモンを選出した対戦数／そのうち勝った数（＝選出時勝率）。
  int chosen = 0;
  int chosenWin = 0;

  /// 初手に選出した対戦数／そのうち勝った数。
  int first = 0;
  int firstWin = 0;
}

/// 自分パーティのポケモン別成績を集計する（旧 champ-edge の get_chosen_and_win_rate /
/// get_first_chosen_and_win_rate 相当）。[partyPids] は自分パーティ6枠の pid。
List<PlayerPokeStat> analyzePlayerParty(
    List<BattleRecord> records, List<String> partyPids,
    {bool megaMerge = true}) {
  String norm(String pid) => megaMerge ? normalizeMegaForm(pid) : pid;
  final order = <String>[];
  final map = <String, PlayerPokeStat>{};
  for (final pid in partyPids) {
    if (pid == '-1' || pid.isEmpty) continue;
    final key = norm(pid);
    map.putIfAbsent(key, () {
      order.add(key);
      return PlayerPokeStat(key);
    });
  }
  for (final r in records) {
    final win = r.isWin;
    final choices = {
      for (final c in r.playerChoices)
        if (c != '-1' && c.isNotEmpty) norm(c)
    };
    for (final pid in choices) {
      final s = map[pid];
      if (s == null) continue;
      s.chosen++;
      if (win) s.chosenWin++;
    }
    final firstPid = r.playerChoices.isNotEmpty ? r.playerChoices[0] : '-1';
    if (firstPid != '-1' && firstPid.isNotEmpty) {
      final s = map[norm(firstPid)];
      if (s != null) {
        s.first++;
        if (win) s.firstWin++;
      }
    }
  }
  return [for (final k in order) map[k]!];
}

/// 対戦記録群を集計する（メガ統合の有無を切替可能）。UI 非依存・テスト可能。
///
/// - 出現(KP)/勝率：相手パーティ6枠に出現した対戦数と、その勝数。
/// - 選出/選出時勝率：相手選出4枠に入った対戦数と、その勝数。
/// - 初手/初手時勝率：相手選出の1枠目に入った対戦数と、その勝数。
AnalysisResult analyzeBattles(List<BattleRecord> records,
    {bool megaMerge = true}) {
  String norm(String pid) => megaMerge ? normalizeMegaForm(pid) : pid;
  final map = <String, PokeStat>{};
  PokeStat stat(String pid) => map.putIfAbsent(pid, () => PokeStat(pid));

  var wins = 0;
  var draws = 0;
  for (final r in records) {
    final win = r.isWin;
    if (win) wins++;
    if (r.result == 2) draws++;
    // 出現（パーティ6枠・対戦内で重複排除）。
    final party = {
      for (final p in r.opponentPokemons)
        if (p != '-1' && p.isNotEmpty) norm(p)
    };
    for (final pid in party) {
      final s = stat(pid);
      s.appeared++;
      if (win) s.appearedWin++;
    }
    // 選出（4枠・重複排除）。
    final choices = {
      for (final c in r.opponentChoices)
        if (c != '-1' && c.isNotEmpty) norm(c)
    };
    for (final pid in choices) {
      final s = stat(pid);
      s.chosen++;
      if (win) s.chosenWin++;
    }
    // 初手（1枠目）。
    final firstPid = r.opponentChoices.isNotEmpty ? r.opponentChoices[0] : '-1';
    if (firstPid != '-1' && firstPid.isNotEmpty) {
      final s = stat(norm(firstPid));
      s.first++;
      if (win) s.firstWin++;
    }
  }
  return AnalysisResult(records.length, wins, draws, map.values.toList());
}
