# ダメージエンジン（Dart 直実装）

Phase 1 のダメージ計算エンジン。旧リポジトリ `~/Documents/champ-edge/pokedata/calc.py`
（1494 行）の計算ロジックを Dart へ忠実移植したもの。

## 設計方針

- **純粋関数 / DB 非依存**: エンジンは解決済みの状態
  （[`CombatantState`] / [`MoveState`] / [`FieldState`]）のみを入力に取り、
  決定論的に 16 通りの乱数ダメージを返す。種族値・技データ・タイプ相性表は
  エンジンに埋め込まず、呼び出し側（DB 層）が解決して渡す。
- **数値の完全一致**: Python の `decimal.Decimal.quantize`（ROUND_FLOOR /
  ROUND_HALF_UP / 五捨五超入=ROUND_HALF_DOWN）を整数演算で再現
  （[`rounding.dart`]）。浮動小数の誤差は排除している。

## ファイル構成（`lib/src/service/damage/`）

| ファイル | 役割 |
|---|---|
| `poke_types.dart` | タイプ/天候/フィールド/状態異常/壁の列挙と 18×18 タイプ相性表 |
| `rounding.dart` | Decimal 相当の丸めヘルパ（floor / half_up / half_down） |
| `move_tables.dart` | 技名リスト・特性/持ち物マップ（calc.py の定義領域を移植） |
| `models.dart` | 入出力モデル（spec の AttackerState 等） |
| `damage_calc.dart` | エンジン本体（威力/攻撃/防御/補正/最終ダメージの 5 関数 + ステータス計算 + タイプ相性） |
| `../damage_engine.dart` | 公開ファサード兼再エクスポート |

## 公開 API

```dart
// 16 通りのダメージ・最小/最大・割合
DamageResult r = DamageCalc.calculateDamage(attacker, defender, move, field);

// 攻撃タイプ × 防御タイプ群の相性倍率
double e = DamageCalc.getTypeEffectiveness(PokeType.electric,
    [PokeType.water, PokeType.flying]); // 4.0

// 種族値等から実数値（努力値は 0-32 換算、旧実装準拠）
List<int> stats = DamageCalc.calculateStats(
    baseStats: [...], iv: [...], ev: [...], level: 50, nature: 'ようき');
```

## 妥当性（calc.py との一致）

`test/fixtures/generate_damage_cases.py` が旧 `pokedata.calc` を実際に実行し、
**変化前の解決済み入力**と期待ダメージ（16 ロール・最小・最大・対 HP 割合）を
`damage_cases.json` に出力する。これを Dart 実装と突き合わせて検証する。

- ケース数: **258 件**（うちダメージ有り 235 件）
- 結果: **258 / 258 完全一致**（16 ロール配列・min・max・割合すべて）
- 網羅範囲: タイプ一致(STAB)/テラス/適応力・へんげんじざい、タイプ相性、
  天候（晴/雨/砂/雪）、フィールド、多数の特性・持ち物、やけど、急所、
  ランク補正、壁、連続技。

### 再生成

```bash
cd mobile/test/fixtures
python3 generate_damage_cases.py 250    # CHAMP_EDGE_HOME で旧リポジトリ位置を指定可
```

## 性能

`calculateDamage` を 10,000 回連続実行した平均 **約 14.6 µs/回**
（≒ 0.015 ms）。spec の「100ms 未満」を大きく満たす。

## テストの実行

ダメージエンジンは純粋 Dart のため、Flutter/ネイティブ依存なしで検証できる。

```bash
cd mobile
dart run test/verify_damage.dart        # 一致検証 + 性能ベンチ（推奨・常時実行可）
```

`test/damage_calc_test.dart` は `flutter test` 用の同等テスト。ただし本リポジトリの
ローカル環境では次の 2 点が前提になる:

1. **Xcode ライセンス同意**: `sudo xcodebuild -license accept`
   （未同意だと推移的依存 `objective_c` のネイティブアセットビルドが失敗する）。
2. **DB アセット**: `pubspec.yaml` が参照する `assets/data/pokemon.db` を
   `mobile/assets/data/` に配置する必要がある（Change 1: クロスプラットフォーム
   フレームワークの DB 組込みタスク）。

> 補足: CommandLineTools しか使えない環境では、`xcrun`/`clang` を CLT へ向ける
> ラッパを PATH 前方に置くことでネイティブアセットビルドを通せる
> （`DEVELOPER_DIR=/Library/Developer/CommandLineTools`）。

## 将来の Rust 化

Dart 実装の性能は要件を大幅に満たしており（µs オーダー）、現時点で Rust 共有
ライブラリ化の必要性は無い。本ドキュメントと `damage_calc.dart` を仕様として残し、
将来 Web/デスクトップ展開で共通化が必要になった際の移行元とする。
