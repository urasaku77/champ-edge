# damage-engine-dart-implementation Specification

## Purpose
TBD - created by archiving change decide-damage-engine-language. Update Purpose after archive.
## Requirements
### Requirement: Dart でのダメージ計算エンジン実装

ダメージ計算エンジンは Dart で実装され、Flutter アプリ内で直接呼び出し可能な形で提供され**なければならない（MUST）**。実装は `lib/src/service/damage_engine.dart` 内に集約され、入力モデル・計算パラメータ・結果モデルを明確に分離する。

#### Scenario: ダメージ計算エンジンの初期化と実行

- **WHEN** UI から攻撃側ポケモン、防御側ポケモン、技、フィールド状態を指定して `calculateDamage()` を呼び出す
- **THEN** 計算完了時に `DamageResult { minDamage: int, maxDamage: int, percentage: double }` を返す

#### Scenario: 計算パフォーマンス要件

- **WHEN** 計算パラメータが確定した状態で `calculateDamage()` を実行する
- **THEN** 実行時間は **100ms 未満**で完了し、UI がフリーズしない

### Requirement: Python calc.py ロジックからの移植

旧リポジトリ `~/Documents/champ-edge/pokedata/calc.py` の計算ロジックを Dart に移植し**なければならない（MUST）**。移植版は既存の計算結果と一致すること。

#### Scenario: ダメージ計算の正確性確認

- **WHEN** 既存 Python ロジックで計算した結果とその入力パラメータを用いて Dart 実装を実行する
- **THEN** 計算結果が完全に一致する（minDamage、maxDamage、百分比すべて同じ）

#### Scenario: テラスタイプ・特殊技仕様の対応

- **WHEN** テラスタイプ変更後のポケモンに対してダメージを計算する
- **THEN** テラスタイプに基づいたタイプ相性が正しく適用され、ダメージが再計算される

### Requirement: エンジン API インターフェース

ダメージエンジンは以下の基本 API を提供し**なければならない（MUST）**：

1. `DamageEngine.calculateDamage(attackerState, defenderState, move, field)` → `DamageResult`
2. `DamageEngine.getTypeEffectiveness(offenseType, defenseType, weather, terrain)` → `double` (倍率)
3. `DamageEngine.calculateStats(baseStats, iv, ev, level, nature)` → `Stats`

#### Scenario: タイプ相性の参照

- **WHEN** 特定のタイプ組み合わせに対して `getTypeEffectiveness()` を呼び出す
- **THEN** 正しい相性倍率（0.25, 0.5, 1.0, 2.0, 4.0 等）が返される

#### Scenario: ステータス計算

- **WHEN** ポケモンの種族値・個体値・努力値・性格・レベルを指定して `calculateStats()` を呼び出す
- **THEN** 実ステータス（HP、攻撃、防御、特攻、特防、素早さ）が正しく計算される

### Requirement: ダメージ計算の入力・出力データモデル

ダメージエンジンの入力・出力は以下のモデルで統一され**なければならない（MUST）**：

```dart
class AttackerState {
  String pokemonId;
  List<int> stats;        // [HP, Atk, Def, SpA, SpD, Spe]
  List<int> boosts;       // [Atk, Def, SpA, SpD, Spe] ランク（-6～+6）
  String type1, type2;
  String ability;
  List<String> moves;
  String status;          // none, burn, paralysis, etc.
  String tera;            // テラスタイプ（null の場合は無指定）
}

class DefenderState {
  String pokemonId;
  List<int> stats;
  List<int> boosts;
  String type1, type2;
  String ability;
  String status;
  String tera;
}

class FieldState {
  String weather;         // sunny, rainy, sandstorm, hail, null
  String terrain;         // psychic, electric, grassy, misty, null
  bool reflect;           // Light Screen
  bool lightScreen;       // Reflect
  bool tailwind;          // Tailwind
  String side;            // 反射・テイルウィンドの適用側
}

class DamageResult {
  int minDamage;
  int maxDamage;
  double percentage;      // (maxDamage / defenderHP) * 100
  String type;            // actual move type after tera/overworld effects
}
```

#### Scenario: 複雑なダメージ計算シナリオ

- **WHEN** 天候、フィールド、ステータス変化、特性、テラスタイプが複数組み合わさった状態でダメージを計算する
- **THEN** すべての修正倍率が正しく適用されて結果が返される

### Requirement: オフライン動作と動的ロード

ダメージエンジンはオフラインで動作し**なければならない（MUST）**。事前にロードしたポケモンデータベース（SQLite）に依存し、エンジン本体には種族値・技データ・特性等は埋め込まず、DB から参照する仕組みとする。

#### Scenario: DB 参照なしでの計算

- **WHEN** `AttackerState` と `DefenderState` がすべてのステータス・タイプ情報を直接指定されている場合
- **THEN** DB を参照せずに計算が完了し、100ms 未満で結果を返す

### Requirement: 単体テスト可能な設計

ダメージエンジンのロジックはすべて純粋関数として実装され**なければならない（MUST）**。入力値に対する出力値が決定論的であり、テストは既存 Python ロジックとの比較テストを主体とする。

#### Scenario: 既存 calc.py との結果比較テスト

- **WHEN** テストケースとして既存 calc.py の計算結果 100 件以上を用意し、同一の入力パラメータで Dart 実装を実行する
- **THEN** すべてのテストケースでダメージ計算結果が一致する

### Requirement: 将来的な Rust 化への準備

将来の移行に備え、現在の Dart ロジックは仕様ドキュメントとして保持し**なければならない（MUST）**。Dart 実装が性能不足と判明した場合、Rust 共有ライブラリ化への移行を想定する。

#### Scenario: 性能ベンチマーク

- **WHEN** 1000 個のダメージ計算を連続実行する
- **THEN** 平均実行時間が 100ms 未満であることを確認し、ベンチマーク結果をログに記録する

