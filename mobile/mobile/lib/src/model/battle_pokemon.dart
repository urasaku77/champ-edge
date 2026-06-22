import 'package:flutter/material.dart';

import '../data/ability_values.dart';
import '../data/waza_effects.dart';
import '../service/damage_engine.dart';

/// 技（差し替え可能）。
class BattleMove {
  const BattleMove({
    required this.name,
    required this.type,
    required this.category,
    required this.power,
    this.effectValue,
  });

  final String name;
  final PokeType type;
  final MoveCategory category;
  final int power;

  /// 威力・回数の現在値（技効果ボタンで選択。null＝効果の初期値を使う）。
  final num? effectValue;

  /// この技の威力・回数効果（連続技/威力増加/威力補正）。
  WazaEffect get effect => wazaEffectOf(name);

  /// 効果ボタンを持つか。
  bool get hasEffect => effect.kind != WazaEffectKind.none;

  /// 現在の効果値（未選択なら初期値）。
  num get currentEffectValue => effectValue ?? effect.defaultValue;

  BattleMove copyWith({num? effectValue}) => BattleMove(
        name: name,
        type: type,
        category: category,
        power: power,
        effectValue: effectValue ?? this.effectValue,
      );

  MoveState toMoveState({bool critical = false, bool skillLink = false}) {
    final e = effect;
    final v = currentEffectValue;
    // オーラぐるま等：ON のとき技タイプを差し替える。
    final moveType =
        (e.kind == WazaEffectKind.moveTypeChange && v == 1) ? e.changeType : type;
    // スキルリンク：連続技は最大回数（5）で計算する。
    final hits = e.kind == WazaEffectKind.multiHit
        ? (skillLink ? 5 : v.toInt())
        : -1;
    return MoveState(
      name: name,
      type: moveType,
      category: category,
      power: power,
      critical: critical,
      multiHit: hits,
      addPower: e.kind == WazaEffectKind.addPower ? v.toDouble() : -1,
      powerHosei: e.kind == WazaEffectKind.powerHosei ? v.toDouble() : -1,
    );
  }

  /// 未設定スロットか。
  bool get isEmpty => name.isEmpty;

  Map<String, dynamic> toJson() => {
        'name': name,
        'type': type.name,
        'category': category.name,
        'power': power,
        if (effectValue != null) 'effectValue': effectValue,
      };

  factory BattleMove.fromJson(Map<String, dynamic> j) => BattleMove(
        name: j['name'] as String? ?? '',
        type: PokeType.values.byName(j['type'] as String? ?? 'none'),
        category:
            MoveCategory.values.byName(j['category'] as String? ?? 'status'),
        power: (j['power'] as num?)?.toInt() ?? 0,
        effectValue: j['effectValue'] as num?,
      );
}

/// 未設定の技スロット（パーティ編集で追加したポケモンの初期技）。
BattleMove emptyMove() => const BattleMove(
      name: '',
      type: PokeType.none,
      category: MoveCategory.status,
      power: 0,
    );

/// 性格定義（↑↓ の能力インデックス。1=A 2=B 3=C 4=D 5=S、0=補正なし）。
class Nature {
  const Nature(this.name, this.up, this.down);
  final String name;
  final int up;
  final int down;

  bool get isNeutral => up == 0;
}

/// 対戦画面で扱うポケモン1体分のモデル（編集可能）。
///
/// 種族値・個体値・努力値・レベル・性格から実数値を算出する。
/// 性格/特性/持ち物/技/努力値などはタップ編集で書き換わる。
class BattlePokemon {
  BattlePokemon({
    required this.name,
    required this.pid,
    required this.baseStats,
    required this.type1,
    this.type2 = PokeType.none,
    this.tera = PokeType.none,
    required this.abilityOptions,
    String? ability,
    this.item = 'なし',
    this.nature = 'まじめ',
    this.level = 50,
    this.status = Ailment.none,
    this.charging = false,
    this.critical = false,
    this.smackdown = false,
    this.wall = Wall.none,
    this.constantDamage = 0.0,
    this.hasStealthRock = false,
    this.spikes = 0,
    this.memo = '',
    this.weight = 0.0,
    List<int>? iv,
    List<int>? ev,
    List<int>? boosts,
    required this.moves,
  })  : _ability = ability ?? abilityOptions.first,
        abilityValue = defaultAbilityValue(ability ?? abilityOptions.first),
        baseForm = int.parse(pid.split('-').last),
        iv = iv ?? List<int>.filled(6, 31),
        ev = ev ?? List<int>.filled(6, 0),
        boosts = boosts ?? List<int>.filled(6, 0);

  /// 名前・pid・種族値・特性候補はフォーム切替（メガ進化）で書き換わる。
  String name;

  /// 図鑑番号-フォーム（画像アセット名）。例: '0445-0'。
  String pid;

  /// 元フォーム番号（メガ進化から戻る先）。
  final int baseForm;

  /// 種族値 [H, A, B, C, D, S]。
  List<int> baseStats;

  /// 重さ（kg、pokemon_data.weight）。重量比技（ヘビーボンバー等）と重さ比較に使用。
  double weight;

  /// タイプ（タップで変更可能。バトル中のタイプ変更に対応）。
  PokeType type1;
  PokeType type2;

  /// タイプ変更技（みずびたし等）適用時の元タイプ退避（解除で復元・非永続）。
  List<PokeType>? typeBackup;

  /// じこあんじ適用時の元ランク退避（解除で復元・非永続）。
  List<int>? boostsBackup;

  /// 登場時ランク特性（いかく/ふとうのけん/ふくつのたて/ダウンロード）を適用済みか。
  /// 場を離れると下ろし、再選出で再適用できるようにする（非永続）。
  bool appearRankApplied = false;

  /// 登場時ランク特性の自動適用をユーザーが無効化したか（永続・ポケモン単位の設定）。
  bool abilityDisabled = false;

  /// トレースで特性を上書きする前の元特性（切替で復元・非永続）。
  String? traceBackup;

  /// メタモンのへんしん適用前の状態スナップショット（切替で復元・非永続）。
  Map<String, dynamic>? transformBackup;

  /// HOME 使用率からの自動補完を済ませたか（初回選出時に1回だけ補完・非永続）。
  bool homeFilled = false;

  /// 現在の編集状態を JSON スナップショットとして取得（へんしん退避用）。
  Map<String, dynamic> snapshot() => toJson();

  /// スナップショット（snapshot/JSON）から編集状態を復元する（baseForm 以外）。
  void applySnapshot(Map<String, dynamic> j) {
    List<int> ints(String key, int len) {
      final v = j[key];
      if (v is List) return [for (final e in v) (e as num).toInt()];
      return List<int>.filled(len, 0);
    }

    name = j['name'] as String;
    pid = j['pid'] as String;
    baseStats = ints('baseStats', 6);
    type1 = PokeType.values.byName(j['type1'] as String? ?? 'none');
    type2 = PokeType.values.byName(j['type2'] as String? ?? 'none');
    tera = PokeType.values.byName(j['tera'] as String? ?? 'none');
    abilityOptions =
        (j['abilityOptions'] as List?)?.cast<String>() ?? const ['—'];
    ability = j['ability'] as String? ?? abilityOptions.first;
    abilityValue = j['abilityValue'] as String? ?? defaultAbilityValue(ability);
    item = j['item'] as String? ?? 'なし';
    nature = j['nature'] as String? ?? 'まじめ';
    level = (j['level'] as num?)?.toInt() ?? 50;
    status = Ailment.values.byName(j['status'] as String? ?? 'none');
    iv = ints('iv', 6);
    ev = ints('ev', 6);
    boosts = ints('boosts', 6);
    weight = (j['weight'] as num?)?.toDouble() ?? 0.0;
    moves = [
      for (final m in (j['moves'] as List? ?? const []))
        BattleMove.fromJson(m as Map<String, dynamic>),
    ];
  }

  // --- 編集可能フィールド ---
  PokeType tera;
  List<String> abilityOptions;
  String _ability;

  /// 特性。変更すると特性値（abilityValue）をその特性のデフォルトへリセットする
  /// （旧 champ-edge set_default_ability_value と同一）。
  String get ability => _ability;
  set ability(String v) {
    _ability = v;
    abilityValue = defaultAbilityValue(v);
  }

  /// 条件付き特性の切替値（'有効'/'無効'/'A' 等。テーブルに無い特性は空）。
  /// エンジンの abilityValue へ渡る。
  String abilityValue;

  String item;
  String nature;
  int level;
  List<int> iv;

  /// 努力値 [H,A,B,C,D,S]（champ-edge 準拠の 0〜32 スケール）。
  List<int> ev;

  /// ランク（段階）[H不使用, A, B, C, D, S]。-6〜+6。
  List<int> boosts;
  List<BattleMove> moves;

  /// 状態異常。
  Ailment status;

  /// じゅうでん（ためわざ：でんきタイプ技の威力2倍）。
  bool charging;

  /// 急所（このポケモンの技ダメージを急所として計算）。
  bool critical;

  /// うちおとす（ひこう/ふゆう/ふうせんでも地面技が当たる）。
  bool smackdown;

  /// 壁（防御側として受けるとき適用）。
  Wall wall;

  /// 定数ダメージ（防御側として、最大HPに対する毎ターンのチップ割合の合計）。
  /// 例: やどりぎ1/8＋砂嵐1/16 → 0.1875。
  double constantDamage;

  /// ステルスロック（防御側の登場時ダメージ。いわ相性で算出）。
  bool hasStealthRock;

  /// まきびし枚数（防御側の登場時ダメージ。0=なし/1=1/8/2=1/6/3=1/4）。
  int spikes;

  /// ポケモン個別メモ（パーティ管理/ボックスで使用。型・役割など自由記述）。
  String memo;

  /// まきびしの登場時ダメージ割合（最大HP比）。
  double get spikesFraction => const [0.0, 1 / 8, 1 / 6, 1 / 4][spikes.clamp(0, 3)];

  String get imageAsset => 'assets/pokemon/$pid.png';

  /// 全国図鑑番号（pid '0445-0' → 445）。
  int get dexNo => int.parse(pid.split('-').first);

  /// フォーム番号。
  int get formNo => int.parse(pid.split('-').last);

  /// バトルデータベース用 pid（番号4桁-フォーム2桁。例 '0445-00'）。
  String get pokedbPid =>
      '${dexNo.toString().padLeft(4, '0')}-${formNo.toString().padLeft(2, '0')}';

  /// ポケモン徹底攻略（ポケ徹）の図鑑 URL。
  String get yakkunUrl => 'https://yakkun.com/sv/zukan/?national_no=$dexNo';

  /// バトルデータベースの URL。
  String pokedbUrl({String season = '1'}) =>
      'https://champs.pokedb.tokyo/pokemon/show/$pokedbPid?season=$season&rule=0';

  List<PokeType> get types =>
      type2 == PokeType.none ? [type1] : [type1, type2];

  /// 実数値 [H, A, B, C, D, S]。
  /// champ-edge と同じ式（努力値 0〜32 スケール）で算出する（検証済みエンジンに委譲）。
  List<int> get stats => DamageCalc.calculateStats(
        baseStats: baseStats,
        iv: iv,
        ev: ev,
        level: level,
        nature: nature,
      );

  int get hp => stats[0];

  AttackerState toAttacker() => AttackerState(
        name: name,
        level: level,
        stats: stats,
        boosts: boosts,
        type1: type1,
        type2: type2,
        // テラスは当面対象外（P4）。再導入までエンジンへ渡さない（none で無効化）。
        tera: PokeType.none,
        ability: ability,
        abilityValue: abilityValue,
        item: item,
        status: status,
        charging: charging,
        smackdown: smackdown,
        weight: weight,
      );

  DefenderState toDefender() => DefenderState(
        name: name,
        level: level,
        stats: stats,
        boosts: boosts,
        type1: type1,
        type2: type2,
        // テラスは当面対象外（P4）。再導入までエンジンへ渡さない（none で無効化）。
        tera: PokeType.none,
        ability: ability,
        item: item,
        status: status,
        wall: wall,
        smackdown: smackdown,
        constantDamage: constantDamage,
        hasStealthRock: hasStealthRock,
        weight: weight,
        abilityValue: abilityValue,
      );

  /// 永続化用 JSON。enum は安定した `.name`（英字識別子）で保存する。
  Map<String, dynamic> toJson() => {
        'name': name,
        'pid': pid,
        'baseStats': baseStats,
        'type1': type1.name,
        'type2': type2.name,
        'tera': tera.name,
        'abilityOptions': abilityOptions,
        'ability': ability,
        'abilityValue': abilityValue,
        'item': item,
        'nature': nature,
        'level': level,
        'status': status.name,
        'charging': charging,
        'critical': critical,
        'smackdown': smackdown,
        'wall': wall.name,
        'constantDamage': constantDamage,
        'hasStealthRock': hasStealthRock,
        'spikes': spikes,
        'memo': memo,
        'iv': iv,
        'ev': ev,
        'boosts': boosts,
        'abilityDisabled': abilityDisabled,
        'weight': weight,
        'moves': moves.map((m) => m.toJson()).toList(),
      };

  factory BattlePokemon.fromJson(Map<String, dynamic> j) {
    List<int> ints(String key, int len) {
      final v = j[key];
      if (v is List) return [for (final e in v) (e as num).toInt()];
      return List<int>.filled(len, 0);
    }

    final opts = (j['abilityOptions'] as List?)?.cast<String>() ?? const ['—'];
    return BattlePokemon(
      name: j['name'] as String,
      pid: j['pid'] as String,
      baseStats: ints('baseStats', 6),
      type1: PokeType.values.byName(j['type1'] as String? ?? 'none'),
      type2: PokeType.values.byName(j['type2'] as String? ?? 'none'),
      tera: PokeType.values.byName(j['tera'] as String? ?? 'none'),
      abilityOptions: opts.isEmpty ? const ['—'] : opts,
      ability: j['ability'] as String?,
      item: j['item'] as String? ?? 'なし',
      nature: j['nature'] as String? ?? 'まじめ',
      level: (j['level'] as num?)?.toInt() ?? 50,
      status: Ailment.values.byName(j['status'] as String? ?? 'none'),
      charging: j['charging'] as bool? ?? false,
      critical: j['critical'] as bool? ?? false,
      smackdown: j['smackdown'] as bool? ?? false,
      wall: Wall.values.byName(j['wall'] as String? ?? 'none'),
      constantDamage: (j['constantDamage'] as num?)?.toDouble() ?? 0.0,
      hasStealthRock: j['hasStealthRock'] as bool? ?? false,
      spikes: (j['spikes'] as num?)?.toInt() ?? 0,
      memo: (j['memo'] as String?) ?? '',
      weight: (j['weight'] as num?)?.toDouble() ?? 0.0,
      iv: ints('iv', 6),
      ev: ints('ev', 6),
      boosts: ints('boosts', 6),
      moves: [
        for (final m in (j['moves'] as List? ?? const []))
          BattleMove.fromJson(m as Map<String, dynamic>),
      ],
    )
      ..abilityDisabled = j['abilityDisabled'] as bool? ?? false
      // ability セッターがデフォルトを入れた後、保存済みの値で上書きする。
      ..abilityValue = j['abilityValue'] as String? ??
          defaultAbilityValue(j['ability'] as String? ?? '');
  }
}

/// 25 種の性格。
const List<Nature> allNatures = [
  Nature('さみしがり', 1, 2), Nature('いじっぱり', 1, 3), Nature('やんちゃ', 1, 4), Nature('ゆうかん', 1, 5),
  Nature('ずぶとい', 2, 1), Nature('わんぱく', 2, 3), Nature('のうてんき', 2, 4), Nature('のんき', 2, 5),
  Nature('ひかえめ', 3, 1), Nature('おっとり', 3, 2), Nature('うっかりや', 3, 4), Nature('れいせい', 3, 5),
  Nature('おだやか', 4, 1), Nature('おとなしい', 4, 2), Nature('しんちょう', 4, 3), Nature('なまいき', 4, 5),
  Nature('おくびょう', 5, 1), Nature('せっかち', 5, 2), Nature('ようき', 5, 3), Nature('むじゃき', 5, 4),
  Nature('まじめ', 0, 0), Nature('がんばりや', 0, 0), Nature('すなお', 0, 0),
  Nature('てれや', 0, 0), Nature('きまぐれ', 0, 0),
];

Nature natureByName(String name) =>
    allNatures.firstWhere((n) => n.name == name,
        orElse: () => const Nature('まじめ', 0, 0));

/// 性格に応じた標準努力値を返す（PC版 pokedata/nature.py get_default_doryoku の移植）。
/// EV は表示スケール(0-32)。[baseStats] は [H,A,B,C,D,S]、戻り値も [H,A,B,C,D,S]。
/// 該当しない性格（まじめ等）は全 0。
List<int> defaultEvForNature(String nature, List<int> baseStats) {
  final a = baseStats.length > 1 ? baseStats[1] : 0;
  final c = baseStats.length > 3 ? baseStats[3] : 0;
  final s = baseStats.length > 5 ? baseStats[5] : 0;
  final ev = List<int>.filled(6, 0); // [H,A,B,C,D,S]
  switch (nature) {
    case 'ようき': // A↑ S↑
      ev[1] = 32; ev[5] = 32;
    case 'おくびょう': // C↑ S↑
      ev[3] = 32; ev[5] = 32;
    case 'ゆうかん': // H↑ A↑
      ev[0] = 32; ev[1] = 32;
    case 'れいせい': // H↑ C↑
      ev[0] = 32; ev[3] = 32;
    case 'ずぶとい':
    case 'わんぱく':
    case 'のんき': // H↑ B↑
      ev[0] = 32; ev[2] = 32;
    case 'おだやか':
    case 'しんちょう':
    case 'なまいき': // H↑ D↑
      ev[0] = 32; ev[4] = 32;
    case 'いじっぱり':
    case 'さみしがり':
    case 'やんちゃ': // A↑ ＋（素早90以上なら S、未満なら H）
      ev[1] = 32;
      if (s >= 90) { ev[5] = 32; } else { ev[0] = 32; }
    case 'ひかえめ':
    case 'おっとり':
    case 'うっかりや': // C↑ ＋（素早90以上なら S、未満なら H）
      ev[3] = 32;
      if (s >= 90) { ev[5] = 32; } else { ev[0] = 32; }
    case 'せっかち':
    case 'むじゃき': // S↑ ＋（攻撃と特攻の高い方）
      if (a > c) ev[1] = 32;
      if (c > a) ev[3] = 32;
      ev[5] = 32;
  }
  // 主配分が無い性格（まじめ等）は全 0 のまま。
  if (ev.every((e) => e == 0)) return ev;
  // 余り（合計 66＝32+32+2 にする）の配分。
  // ev 添字: 0=H 1=A 2=B 3=C 4=D 5=S。性格の up/down も 1=A..5=S で ev 添字と一致。
  final n = natureByName(nature);
  final lowered = n.down; // 0=なし, 1=A..5=S
  var remaining = 66 - ev.fold<int>(0, (x, y) => x + y);
  if (remaining <= 0) return ev;

  int cap(int v) => v > 32 ? 32 : v;

  // ルール2: 防御能力(B/D)が下降補正の性格は、余りを全て S（素早）へ。
  if ((lowered == 2 || lowered == 4) && ev[5] < 32) {
    ev[5] = cap(ev[5] + remaining);
    return ev;
  }

  // ルール1: H が空き（攻撃型）なら余りは H へ。ただし HP 実数値が奇数になるよう調整。
  // lv50: HP = 種族H + 努力H + 75 → 奇数 ⟺ (種族H + 努力H) が偶数。
  // 努力H=2 だと種族Hが奇数のとき HP 偶数になるので、その場合は H1＋残りを B/D へ。
  if (ev[0] < 32) {
    final baseHp = baseStats.isNotEmpty ? baseStats[0] : 0;
    if (baseHp.isEven) {
      ev[0] = cap(ev[0] + remaining); // H+2 → HP 奇数
    } else {
      ev[0] += 1;
      remaining -= 1; // H+1 → HP 奇数。残りは B/D（無ければ C/A/S）へ。
      for (final idx in [2, 4, 3, 1, 5]) {
        if (remaining <= 0) break;
        if (idx == lowered || ev[idx] >= 32) continue;
        ev[idx] += 1;
        remaining -= 1;
      }
    }
    return ev;
  }

  // その他（H は既に 32）: 守備寄りの 1 ステへまとめて配分。
  for (final idx in [0, 2, 4, 3, 1, 5]) {
    if (remaining <= 0) break;
    if (idx == lowered || ev[idx] >= 32) continue;
    final add = remaining < 32 - ev[idx] ? remaining : 32 - ev[idx];
    ev[idx] += add;
    remaining -= add;
  }
  return ev;
}

/// タイプ→表示色（旧アプリのタイプアイコン色に準拠した近似）。
const Map<PokeType, Color> typeColors = {
  PokeType.normal: Color(0xFF9099A1),
  PokeType.fire: Color(0xFFFF6B45),
  PokeType.water: Color(0xFF4D90D5),
  PokeType.electric: Color(0xFFF3D23B),
  PokeType.grass: Color(0xFF63BB5B),
  PokeType.ice: Color(0xFF73CEC0),
  PokeType.fighting: Color(0xFFCE4069),
  PokeType.poison: Color(0xFFAB6AC8),
  PokeType.ground: Color(0xFFD97746),
  PokeType.flying: Color(0xFF8FA8DD),
  PokeType.psychic: Color(0xFFFA7179),
  PokeType.bug: Color(0xFF90C12C),
  PokeType.rock: Color(0xFFC7B78B),
  PokeType.ghost: Color(0xFF5269AD),
  PokeType.dragon: Color(0xFF0B6DC3),
  PokeType.dark: Color(0xFF5A5366),
  PokeType.steel: Color(0xFF5A8EA1),
  PokeType.fairy: Color(0xFFEC8FE6),
  PokeType.stellar: Color(0xFF40B5A5),
  PokeType.none: Color(0xFFBDBDBD),
};

Color typeColorOf(PokeType t) => typeColors[t] ?? const Color(0xFFBDBDBD);
