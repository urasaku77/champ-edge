## Why

`add-waza-effects-ui` でランク変化・タイプ変更技まで対応したが、`waza.py` の other_effect 系
（**じこあんじ**＝相手のランクを自分にコピー、**スキルスワップ**＝特性入替、**コートチェンジ**＝
壁などの入替、**オーラぐるま**＝はらぺこ時あくタイプ化）と、**ポケモン切替時の一過性効果リセット**を
スコープ外にしていた。これらを対応して技効果ボタンの網羅性を上げる。

## What Changes

- 技効果ボタンに other_effect 系のトグルを追加:
  - **じこあんじ**: ON で相手の boosts を自分へコピー（解除で復元）。
  - **スキルスワップ**: ON で攻撃側↔防御側の特性を入替（解除で戻す）。
  - **コートチェンジ**: ON で壁・定数ダメージ・ステルスロックを攻守で入替（解除で戻す）。
  - **オーラぐるま**: ON で技タイプを あく として計算（でんき→あく、解除で戻す）。
- **ポケモン選択切替時に一過性効果をリセット**: 切替前に出していた active ポケモンの技トグルを
  すべて解除（適用していたランク/タイプ/特性/壁等を元に戻し、effectValue をクリア）。手動で設定した
  ランク等とは独立に、技トグル由来の変更のみを戻す。

## Capabilities

### Modified Capabilities
- `battle-screen-ui`: 「技の威力・回数効果ボタン」要件に other_effect 系トグルと切替時リセットを加える。

## Impact

- `mobile/lib/src/data/waza_effects.dart`（other_effect 系の種別・テーブル追加）
- `mobile/lib/src/model/battle_pokemon.dart`（boosts/ability/wall 等の退避フィールド、`MoveState` への
  技タイプ override）
- `mobile/lib/src/screens/home_screen.dart`（トグル適用/解除の分岐拡張、切替時リセット）
- テスト追加（コピー/入替/タイプ override/リセット）
