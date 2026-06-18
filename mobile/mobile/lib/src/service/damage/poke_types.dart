/// ポケモンのタイプ・天候・フィールド・状態異常・壁の定義と、
/// 旧 `pokedata/const.py` 由来のタイプ相性表。
///
/// インデックスは `const.py` の `Types` IntEnum と一致させている。
library;

/// タイプ（`const.py` Types と同じ序数）。
enum PokeType {
  none(-1, 'なし'),
  normal(0, 'ノーマル'),
  fire(1, 'ほのお'),
  water(2, 'みず'),
  electric(3, 'でんき'),
  grass(4, 'くさ'),
  ice(5, 'こおり'),
  fighting(6, 'かくとう'),
  poison(7, 'どく'),
  ground(8, 'じめん'),
  flying(9, 'ひこう'),
  psychic(10, 'エスパー'),
  bug(11, 'むし'),
  rock(12, 'いわ'),
  ghost(13, 'ゴースト'),
  dragon(14, 'ドラゴン'),
  dark(15, 'あく'),
  steel(16, 'はがね'),
  fairy(17, 'フェアリー'),
  stellar(18, 'ステラ');

  const PokeType(this.index_, this.jp);

  /// `const.py` の序数。
  final int index_;

  /// 日本語名（旧データとの照合・JSON フィクスチャ用）。
  final String jp;

  static PokeType fromJp(String name) {
    for (final t in PokeType.values) {
      if (t.jp == name) return t;
    }
    return PokeType.none;
  }
}

/// 天候（`const.py` Weathers）。
enum Weather {
  none('なし'),
  sunny('晴れ'),
  rainy('雨'),
  sandstorm('砂嵐'),
  snow('雪');

  const Weather(this.jp);
  final String jp;

  static Weather fromJp(String name) =>
      Weather.values.firstWhere((w) => w.jp == name, orElse: () => Weather.none);
}

/// フィールド（`const.py` Fields）。
enum Field {
  none('なし'),
  electric('エレキ'),
  psychic('サイコ'),
  grassy('グラス'),
  misty('ミスト');

  const Field(this.jp);
  final String jp;

  static Field fromJp(String name) =>
      Field.values.firstWhere((f) => f.jp == name, orElse: () => Field.none);
}

/// 状態異常（`const.py` Ailments）。
enum Ailment {
  none('なし'),
  burn('やけど'),
  freeze('こおり'),
  paralysis('まひ'),
  poison('どく'),
  badPoison('もうどく'),
  sleep('ねむり');

  const Ailment(this.jp);
  final String jp;

  static Ailment fromJp(String name) =>
      Ailment.values.firstWhere((a) => a.jp == name, orElse: () => Ailment.none);
}

/// 壁（`const.py` Walls）。
enum Wall {
  none('なし'),
  reflect('リフレクター'),
  lightScreen('ひかりのかべ'),
  auroraVeil('オーロラベール');

  const Wall(this.jp);
  final String jp;

  static Wall fromJp(String name) =>
      Wall.values.firstWhere((w) => w.jp == name, orElse: () => Wall.none);
}

/// 技分類（`const.py` 物理/特殊/変化）。
enum MoveCategory {
  physical('物理'),
  special('特殊'),
  status('変化');

  const MoveCategory(this.jp);
  final String jp;

  static MoveCategory fromJp(String name) => MoveCategory.values
      .firstWhere((c) => c.jp == name, orElse: () => MoveCategory.status);
}

/// 単タイプ × 単タイプの相性倍率表。
///
/// `database/pokemon.db` の type_effective テーブルから抽出した値で、
/// 行が攻撃タイプ(0-17)、列が防御タイプ(0-17)。ステラ(18)は別処理。
const List<List<double>> typeChart = <List<double>>[
  [1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 0.5, 0.0, 1.0, 1.0, 0.5, 1.0], // ノーマル
  [1.0, 0.5, 0.5, 1.0, 2.0, 2.0, 1.0, 1.0, 1.0, 1.0, 1.0, 2.0, 0.5, 1.0, 0.5, 1.0, 2.0, 1.0], // ほのお
  [1.0, 2.0, 0.5, 1.0, 0.5, 1.0, 1.0, 1.0, 2.0, 1.0, 1.0, 1.0, 2.0, 1.0, 0.5, 1.0, 1.0, 1.0], // みず
  [1.0, 1.0, 2.0, 0.5, 0.5, 1.0, 1.0, 1.0, 0.0, 2.0, 1.0, 1.0, 1.0, 1.0, 0.5, 1.0, 1.0, 1.0], // でんき
  [1.0, 0.5, 2.0, 1.0, 0.5, 1.0, 1.0, 0.5, 2.0, 0.5, 1.0, 0.5, 2.0, 1.0, 0.5, 1.0, 0.5, 1.0], // くさ
  [1.0, 0.5, 0.5, 1.0, 2.0, 0.5, 1.0, 1.0, 2.0, 2.0, 1.0, 1.0, 1.0, 1.0, 2.0, 1.0, 0.5, 1.0], // こおり
  [2.0, 1.0, 1.0, 1.0, 1.0, 2.0, 1.0, 0.5, 1.0, 0.5, 0.5, 0.5, 2.0, 0.0, 1.0, 2.0, 2.0, 0.5], // かくとう
  [1.0, 1.0, 1.0, 1.0, 2.0, 1.0, 1.0, 0.5, 0.5, 1.0, 1.0, 1.0, 0.5, 0.5, 1.0, 1.0, 0.0, 2.0], // どく
  [1.0, 2.0, 1.0, 2.0, 0.5, 1.0, 1.0, 2.0, 1.0, 0.0, 1.0, 0.5, 2.0, 1.0, 1.0, 1.0, 2.0, 1.0], // じめん
  [1.0, 1.0, 1.0, 0.5, 2.0, 1.0, 2.0, 1.0, 1.0, 1.0, 1.0, 2.0, 0.5, 1.0, 1.0, 1.0, 0.5, 1.0], // ひこう
  [1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 2.0, 2.0, 1.0, 1.0, 0.5, 1.0, 1.0, 1.0, 1.0, 0.0, 0.5, 1.0], // エスパー
  [1.0, 0.5, 1.0, 1.0, 2.0, 1.0, 0.5, 0.5, 1.0, 0.5, 2.0, 1.0, 1.0, 0.5, 1.0, 2.0, 0.5, 0.5], // むし
  [1.0, 2.0, 1.0, 1.0, 1.0, 2.0, 0.5, 1.0, 0.5, 2.0, 1.0, 2.0, 1.0, 1.0, 1.0, 1.0, 0.5, 1.0], // いわ
  [0.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 2.0, 1.0, 1.0, 2.0, 1.0, 0.5, 1.0, 1.0], // ゴースト
  [1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 2.0, 1.0, 0.5, 0.0], // ドラゴン
  [1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 0.5, 1.0, 1.0, 1.0, 2.0, 1.0, 1.0, 2.0, 1.0, 0.5, 1.0, 0.5], // あく
  [1.0, 0.5, 0.5, 0.5, 1.0, 2.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 2.0, 1.0, 1.0, 1.0, 0.5, 2.0], // はがね
  [1.0, 0.5, 1.0, 1.0, 1.0, 1.0, 2.0, 0.5, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 2.0, 2.0, 0.5, 1.0], // フェアリー
];

/// 攻撃タイプ→防御単タイプの相性倍率（基礎値）。
double singleTypeEffective(PokeType attack, PokeType defense) {
  if (attack.index_ < 0 || attack.index_ > 17) return 1.0;
  if (defense.index_ < 0 || defense.index_ > 17) return 1.0;
  return typeChart[attack.index_][defense.index_];
}
