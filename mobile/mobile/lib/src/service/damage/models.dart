/// ダメージエンジンの入出力モデル。
///
/// spec `damage-engine-dart-implementation` の API に沿いつつ、
/// 旧 `calc.py` が `Pokemon` / `Waza` から参照していた属性を
/// 解決済みの値として保持する（エンジン自体は DB 非依存）。
library;

import 'poke_types.dart';

/// ステータスキー（`stats.py` StatsKey）。0:H 1:A 2:B 3:C 4:D 5:S。
enum StatKey { h, a, b, c, d, s }

/// 戦闘に参加するポケモンの解決済み状態（攻守共通）。
class CombatantState {
  CombatantState({
    this.name = '',
    this.level = 50,
    required this.stats,
    List<int>? boosts,
    required this.type1,
    this.type2 = PokeType.none,
    this.battleType,
    this.tera = PokeType.none,
    this.ability = '',
    this.abilityValue = '',
    this.item = 'なし',
    this.status = Ailment.none,
    this.weight = 0.0,
    this.wall = Wall.none,
    this.charging = false,
    this.kyokenCharge = false,
    this.hasStealthRock = false,
    this.smackdown = false,
    this.constantDamage = 0.0,
  })  : assert(stats.length == 6, 'stats は [H,A,B,C,D,S] の 6 要素'),
        boosts = boosts ?? List<int>.filled(6, 0) {
    assert(this.boosts.length == 6, 'boosts は 6 要素（H は未使用）');
  }

  /// ポケモン名（特定種固有の補正に使用）。
  final String name;

  /// レベル。
  final int level;

  /// 実数値 [H, A, B, C, D, S]（ランク補正前）。
  final List<int> stats;

  /// ランク（段階）[H不使用, A, B, C, D, S]。-6〜+6。
  final List<int> boosts;

  final PokeType type1;
  final PokeType type2;

  /// バトル中に書き換わったタイプ（`battle_type`）。null なら type1/type2 を使う。
  final List<PokeType>? battleType;

  /// 適用中のテラスタイプ（`battle_terastype`）。なしなら未テラス。
  final PokeType tera;

  /// 特性。トレース特性の適用でエンジンが書き換える場合があるため可変。
  String ability;

  /// 特性の付随値（`ability_value`、例: こだいかっせいの "A"）。
  String abilityValue;

  final String item;
  final Ailment status;
  final double weight;
  final Wall wall;
  final bool charging;
  final bool kyokenCharge;
  final bool hasStealthRock;
  final bool smackdown;

  /// 定数ダメージ割合（やどりぎ等）。
  final double constantDamage;

  /// 特性が「有効」状態か（`ability_enable`）。
  bool get abilityEnable => abilityValue == '有効';

  int operator [](StatKey key) => stats[key.index];

  /// 元タイプのリスト（`type`）。
  List<PokeType> get types =>
      type2 == PokeType.none ? <PokeType>[type1] : <PokeType>[type1, type2];

  /// テラス適用中か。
  bool get isTera => tera != PokeType.none;

  /// 浮いているか（`is_flying`）。
  bool get isFlying {
    if (smackdown) return false;
    return types.contains(PokeType.flying) ||
        ability == 'ふゆう' ||
        item == 'ふうせん';
  }
}

/// 攻撃側状態（spec の AttackerState 相当）。技リストを持つ。
class AttackerState extends CombatantState {
  AttackerState({
    super.name,
    super.level,
    required super.stats,
    super.boosts,
    required super.type1,
    super.type2,
    super.battleType,
    super.tera,
    super.ability,
    super.abilityValue,
    super.item,
    super.status,
    super.weight,
    super.wall,
    super.charging,
    super.kyokenCharge,
    super.hasStealthRock,
    super.smackdown,
    super.constantDamage,
  });
}

/// 防御側状態（spec の DefenderState 相当）。
class DefenderState extends CombatantState {
  DefenderState({
    super.name,
    super.level,
    required super.stats,
    super.boosts,
    required super.type1,
    super.type2,
    super.battleType,
    super.tera,
    super.ability,
    super.abilityValue,
    super.item,
    super.status,
    super.weight,
    super.wall,
    super.charging,
    super.kyokenCharge,
    super.hasStealthRock,
    super.smackdown,
    super.constantDamage,
  });

  /// 防御側 HP 実数値。
  int get hp => stats[StatKey.h.index];
}

/// 場の状態（spec の FieldState 相当）。
class FieldState {
  const FieldState({
    this.weather = Weather.none,
    this.field = Field.none,
    this.doubleParams,
  });

  final Weather weather;
  final Field field;

  /// ダブルバトル用パラメータ（null ならシングル）。
  /// キー例: is_overall, is_tedasuke, is_friend_guard, is_wazawai_a/b/c/d。
  final Map<String, bool>? doubleParams;
}

/// 技の解決済み状態（`Waza` 相当）。
class MoveState {
  MoveState({
    required this.name,
    required this.type,
    required this.category,
    required this.power,
    this.isTouch = false,
    this.isGuard = false,
    this.target = '相手',
    this.priority = false,
    this.hasEffect = false,
    this.addPower = -1,
    this.powerHosei = -1,
    this.multiHit = -1,
    this.critical = false,
  });

  final String name;

  /// 技タイプ（エンジン内で書き換わる場合があるため可変）。
  PokeType type;

  /// 技分類（フォトンゲイザー等で書き換わるため可変）。
  MoveCategory category;

  final int power;
  final bool isTouch;
  final bool isGuard;
  final String target;
  final bool priority;

  /// 追加効果（確率 > 0%）を持つか（ちからずく判定用）。
  final bool hasEffect;

  /// 威力倍率系（`add_power`、-1 なら無し）。
  final double addPower;

  /// 威力補正系（`power_hosei`、-1 なし。2.0/1.5 を補正へ変換）。
  final double powerHosei;

  /// 連続攻撃回数（`multi_hit`、-1 なら単発）。
  final int multiHit;

  /// 急所か。
  bool critical;
}

/// ダメージ計算結果（spec の DamageResult 相当）。
class DamageResult {
  const DamageResult({
    required this.damages,
    required this.minDamage,
    required this.maxDamage,
    required this.percentage,
    required this.type,
  });

  /// 16 通りの乱数ダメージ（昇順）。変化技などダメージ無しなら空。
  final List<int> damages;

  /// 最小ダメージ（定数ダメージ込み）。
  final int minDamage;

  /// 最大ダメージ（定数ダメージ込み）。
  final int maxDamage;

  /// 最大ダメージの対 HP 割合（%）。
  final double percentage;

  /// 実際に適用された技タイプ（テラス/天候等の変化後）。
  final PokeType type;

  bool get isDamage => damages.isNotEmpty;
}
