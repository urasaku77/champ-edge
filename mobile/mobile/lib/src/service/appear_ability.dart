import '../model/battle_pokemon.dart';

/// 登場時にランクを増減させる特性（自動適用・ポケモン単位で無効化可）。
const Set<String> appearRankAbilities = {
  'いかく',
  'ふとうのけん',
  'ふくつのたて',
  'ダウンロード',
};

/// 登場（選択）時の特性効果を p に適用する（旧 champ-edge の after_appear のランク/特性系）。
///
/// - **いかく**: 相手の『こうげき』ランク -1。
/// - **ふとうのけん**: 自分の『こうげき』ランク +1。
/// - **ふくつのたて**: 自分の『ぼうぎょ』ランク +1。
/// - **ダウンロード**: 相手の ぼうぎょ実数値 < とくぼう なら自分の『こうげき』、そうでなければ
///   『とくこう』ランク +1。
/// - **トレース**: 相手の特性を自分にコピー（元特性は traceBackup に退避）。
/// - **メタモン**: 相手を丸ごとコピー（HP 種族値 48 は維持、元状態は transformBackup に退避）。
///
/// 登場時ランク特性は `abilityDisabled` で無効化でき、`appearRankApplied` で二重適用を防ぐ。
void applyAppearAbility(BattlePokemon p, BattlePokemon opp) {
  if (!p.abilityDisabled && !p.appearRankApplied) {
    switch (p.ability) {
      case 'いかく':
        opp.boosts[1] = (opp.boosts[1] - 1).clamp(-6, 6);
        p.appearRankApplied = true;
      case 'ふとうのけん':
        p.boosts[1] = (p.boosts[1] + 1).clamp(-6, 6);
        p.appearRankApplied = true;
      case 'ふくつのたて':
        p.boosts[2] = (p.boosts[2] + 1).clamp(-6, 6);
        p.appearRankApplied = true;
      case 'ダウンロード':
        final od = opp.stats;
        final idx = od[2] < od[4] ? 1 : 3;
        p.boosts[idx] = (p.boosts[idx] + 1).clamp(-6, 6);
        p.appearRankApplied = true;
    }
  }
  if (p.ability == 'トレース' &&
      p.traceBackup == null &&
      opp.ability.isNotEmpty &&
      opp.ability != '—') {
    p.traceBackup = p.ability;
    p.ability = opp.ability;
  }
  if (p.name == 'メタモン' && p.transformBackup == null && opp.name.isNotEmpty) {
    p.transformBackup = p.snapshot();
    final keepH = p.baseStats[0]; // メタモンの H(48) は維持
    p.name = opp.name;
    p.pid = opp.pid;
    p.baseStats = [keepH, ...opp.baseStats.sublist(1)];
    p.type1 = opp.type1;
    p.type2 = opp.type2;
    p.weight = opp.weight; // 重量比技も相手基準に

    p.abilityOptions = List<String>.from(opp.abilityOptions);
    p.ability = opp.ability;
    p.moves = [
      for (final m in opp.moves)
        BattleMove(
            name: m.name, type: m.type, category: m.category, power: m.power),
    ];
  }
}

/// 場を離れるときの登場時特性の後始末。
///
/// ランク（いかく等）は**戻さない**：自分に入れたランクは切替時の boosts クリアで消え、
/// 相手に入れたランク（いかくの -1 等）は相手が場を離れるまで残す。再選出で再適用できるよう
/// 適用済みフラグだけ下ろす。トレース/メタモンは自分の状態なので復元する。
void resetAppearAbility(BattlePokemon p) {
  p.appearRankApplied = false;
  if (p.traceBackup != null) {
    p.ability = p.traceBackup!;
    p.traceBackup = null;
  }
  if (p.transformBackup != null) {
    p.applySnapshot(p.transformBackup!);
    p.transformBackup = null;
  }
}
