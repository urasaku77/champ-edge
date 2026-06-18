## Why

P3 第4弾（旧 P1 残）。原典は条件付き特性の**有効/無効や値**を `ABILITY_VALUES`（pokedata/const.py）で
切り替えられる（ふかしのこぶし・かんつうドリルはデフォルト無効、有効で×1/4。マルチスケイル等は
デフォルト有効）。モバイルの**エンジンは `abilityValue` 対応済み**だが、`BattlePokemon.toAttacker/
toDefender` が値を渡しておらず**常に空＝条件付き特性が一切効いていない実バグ**（マルチスケイル・
しんりょく系・スナイパー・そうだいしょう・こだいかっせい等すべて）。

## What Changes

- 原典 `ABILITY_VALUES` を Dart へ移植（`ability_values.dart`、先頭値＝デフォルト）。
- `BattlePokemon.abilityValue` を追加：**特性を変更するとその特性のデフォルト値へ自動リセット**
  （原典 `set_default_ability_value` と同一）。JSON 永続化。`toAttacker`/`toDefender` でエンジンへ配管。
- 特性チップの長押し詳細に**値の切替チップ**（有効/無効、そうだいしょう 1.0/1.1/1.2、
  こだいかっせい/クォークチャージ なし/A/B/C/D/S、とうそうしん 1.0/1.25/0.75）を表示。
- 値を持つ特性はチップに現在値を `[値]` で併記する。

## Capabilities

### Modified Capabilities
- `battle-screen-ui`: 「特性・持ち物の編集」に特性値（有効/無効等）の切替を追記する。

## Impact

- `mobile/lib/src/data/ability_values.dart`（新規）
- `mobile/lib/src/model/battle_pokemon.dart`（abilityValue・setter リセット・配管）
- `mobile/lib/src/screens/home_screen.dart`（詳細ダイアログの値切替・チップ併記）
