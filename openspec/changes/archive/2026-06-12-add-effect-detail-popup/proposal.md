## Why

旧 champ-edge では特性・持ち物を**右クリックで効果詳細ポップアップ**を表示できた。モバイル版は
特性/持ち物チップのタップが「選択」に割り当てられているため、効果詳細を見る手段がない。
`pokemon.db` の `ability_data.effect` / `item_data.effect` に効果テキストが入っているので、これを
**長押し**で表示できるようにする。

## What Changes

- 基本情報カードの**特性チップを長押し**すると、その特性の効果詳細（`ability_data.effect`）を
  ダイアログ表示する。
- **持ち物チップを長押し**すると、その持ち物の効果詳細（`item_data.effect`）を表示する。
- ※へんげんじざい/リベロ時の防御タイプ手動設定は、既存の「タイプをタップで変更」で実現済みのため
  本 change では追加対応しない（注記のみ）。

## Capabilities

### Modified Capabilities
- `battle-screen-ui`: 「特性・持ち物の編集」要件に、長押しでの効果詳細ポップアップを加える。

## Impact

- `mobile/lib/src/data/poke_db.dart`（`abilityEffect(name)` / `itemEffect(name)` 追加）
- `mobile/lib/src/screens/home_screen.dart`（特性/持ち物チップに長押しで効果ダイアログ）
