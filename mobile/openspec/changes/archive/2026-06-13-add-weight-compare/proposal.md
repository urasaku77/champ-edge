## Why

P3 第2弾。原典の「重さ比較」（`WeightComparing`）が未移植。さらに調査で **`BattlePokemon` が
`weight` をエンジンに渡しておらず、ヘビーボンバー/ヒートスタンプの重量比威力が常に最低の 40 で
計算されるバグ**が判明（エンジン側は対応済み・入力が常に 0）。原典は重さを基本情報欄にも表示する
（README L163）。

## What Changes

- `BattlePokemon` に `weight` を追加し、DB（pokemon_data.weight）から構築・フォルム切替で反映、
  JSON 永続化、`toAttacker`/`toDefender` でエンジンへ配管（**ヘビーボンバー/ヒートスタンプ修正**）。
- 既存の保存済みパーティ（weight 無し）には起動時に DB から補completion する。
- ドロワー「重さ比較」を実装：両 active の重さ（赤=重い/青=軽い・比較記号）と、互いをヘビーボンバー/
  ヒートスタンプで殴った場合の威力（重量比 <0.2→120 / <0.25→100 / <0.3→80 / <0.5→60 / else 40）を表示。
- 選択ポケモンの基本情報に重さ（kg）を表示する。

## Capabilities

### Modified Capabilities
- `battle-screen-ui`: 「重さ比較」要件を追加し、「選択ポケモンの基本情報表示」に重さ表示を追記する。

## Impact

- `mobile/lib/src/model/battle_pokemon.dart` / `data/poke_db.dart`（weight 配管）
- `mobile/lib/src/screens/weight_compare_dialog.dart`（新規）
- `mobile/lib/src/screens/home_screen.dart`（ドロワー起動・基本情報表示・weight 補完）
