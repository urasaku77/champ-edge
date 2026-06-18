## Why

特性の自動発動（いかく/スキルリンク/トレース）は対応したが、**メタモンのへんしん**（登場時に相手を
丸ごとコピー）が未対応。メタモンは実戦で使われるため、選択時に相手の種族値（HP は メタモンの 48 を維持）・
タイプ・特性・技をコピーし、ダメージ計算に反映する。

## What Changes

- **メタモン**を選択（登場）したとき、相手の active ポケモンの名前・種族値（H=48 維持、A〜S は相手をコピー）・
  タイプ・特性・技をコピーして自分に反映する。場を離れる（切替）とメタモンの状態に復元する。
- 復元のため `BattlePokemon` に状態スナップショット（`snapshot`/`applySnapshot`、JSON ベース）を追加する。

## Capabilities

### Modified Capabilities
- `battle-screen-ui`: 「特性による天候・フィールドの自動反映」要件にメタモンのへんしんを加える。

## Impact

- `mobile/lib/src/model/battle_pokemon.dart`（transformBackup・snapshot/applySnapshot）
- `mobile/lib/src/screens/home_screen.dart`（_applyAppearAbility/_resetAppearAbility にメタモン）
- テスト：snapshot/applySnapshot 復元
