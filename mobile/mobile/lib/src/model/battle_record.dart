/// 対戦記録（旧 champ-edge database/battle.py の Battle dataclass / battle テーブルの移植）。
///
/// ポケモンは pid 文字列（'0445-0' 等）、空き枠は '-1'。
/// result: 1=勝ち / 2=引き分け / 0=負け（原典準拠）。favorite: 1=お気に入り。
class BattleRecord {
  BattleRecord({
    this.id,
    required this.date,
    this.rule = 1,
    required this.result,
    this.favorite = 0,
    this.opponentTn = '',
    this.opponentRate = '',
    this.battleMemo = '',
    this.playerPartyNum = '',
    this.playerPartySubnum = '',
    required this.playerPokemons, // 6
    required this.opponentPokemons, // 6
    required this.playerChoices, // 4（シングルは後半 '-1'）
    required this.opponentChoices, // 4
  });

  final int? id;
  int date; // epoch 秒（編集で変更可）
  final int rule; // 1=シングル, 2=ダブル
  int result; // 1=勝ち / 2=分け / 0=負け
  int favorite;
  String opponentTn;
  String opponentRate;
  String battleMemo;
  String playerPartyNum;
  String playerPartySubnum;
  final List<String> playerPokemons;
  final List<String> opponentPokemons;
  final List<String> playerChoices;
  final List<String> opponentChoices;

  bool get isWin => result == 1;
  bool get isFavorite => favorite == 1;

  DateTime get dateTime => DateTime.fromMillisecondsSinceEpoch(date * 1000);

  /// DB の1行（column→値）から構築。
  factory BattleRecord.fromRow(Map<String, Object?> r) {
    List<String> picks(String prefix, int n) =>
        [for (var i = 1; i <= n; i++) (r['$prefix$i'] as String?) ?? '-1'];
    return BattleRecord(
      id: r['id'] as int?,
      date: (r['date'] as int?) ?? 0,
      rule: (r['rule'] as int?) ?? 1,
      result: (r['result'] as int?) ?? 0,
      favorite: (r['favorite'] as int?) ?? 0,
      opponentTn: (r['opponent_tn'] as String?) ?? '',
      opponentRate: (r['opponent_rate'] as String?) ?? '',
      battleMemo: (r['battle_memo'] as String?) ?? '',
      playerPartyNum: (r['player_party_num'] as String?) ?? '',
      playerPartySubnum: (r['player_party_subnum'] as String?) ?? '',
      playerPokemons: picks('player_pokemon', 6),
      opponentPokemons: picks('opponent_pokemon', 6),
      playerChoices: picks('player_choice', 4),
      opponentChoices: picks('opponent_choice', 4),
    );
  }

  /// INSERT/UPDATE 用の column→値マップ（id は除く）。
  Map<String, Object?> toColumns() => {
        'date': date,
        'rule': rule,
        'result': result,
        'favorite': favorite,
        'opponent_tn': opponentTn,
        'opponent_rate': opponentRate,
        'battle_memo': battleMemo,
        'player_party_num': playerPartyNum,
        'player_party_subnum': playerPartySubnum,
        for (var i = 0; i < 6; i++) 'player_pokemon${i + 1}': playerPokemons[i],
        for (var i = 0; i < 6; i++)
          'opponent_pokemon${i + 1}': opponentPokemons[i],
        for (var i = 0; i < 4; i++) 'player_choice${i + 1}': playerChoices[i],
        for (var i = 0; i < 4; i++)
          'opponent_choice${i + 1}': opponentChoices[i],
      };
}

/// メガ進化フォーム（form 10-19）を通常フォーム（-0）へ正規化する
/// （旧 _normalize_mega_form 相当。メガ統合集計用）。
String normalizeMegaForm(String pid) {
  if (pid.isEmpty || pid == '-1') return pid;
  final parts = pid.split('-');
  if (parts.length < 2) return pid;
  final form = int.tryParse(parts.last);
  if (form != null && form >= 10 && form <= 19) return '${parts.first}-0';
  return pid;
}
