## Context

技効果は `waza_effects.dart` に `WazaEffect`（kind: none/multiHit/addPower/powerHosei）として移植済み。
`BattleMove.effectValue`（null=既定）で現在値を保持し、`_MoveRow` の効果ボタンで循環、`toMoveState` で
`MoveState.multiHit/addPower/powerHosei` に渡している。エンジンはランク（boosts）・タイプ・各種補正に
対応済み。本 change はこの枠組みを buff/debuff・other・type-change へ広げる。

旧 `waza.py` の該当テーブル:
- `self_buff_values`/`self_debuff_values`: 技名→ "AS+1" のような **複数能力・段数** の文字列。
- `opponent_buff_values`/`opponent_debuff_values`: 同形式だが対象が相手。
- `other_effect_values`: 技名→(候補リスト, 既定値)。例 きょけんとつげき=("","受×2")、オーラぐるま=("まんぷく","はらぺこ")。
- タイプ変更技（みずびたし/もえつきる/でんこうそうげき）は `waza.py` の TYPE 分類 + `stage.py` 側の適用。

## Goals / Non-Goals

**Goals:**
- ランク変化技（自分/相手）をボタンで 1 回分適用/解除でき、`boosts` に反映してダメージへ効く。
- きょけんとつげき「受×2」・オーラぐるま「はらぺこ/まんぷく」・じこあんじ等のトグルを反映。
- タイプ変更技で防御/攻撃側タイプを書き換え、相性に反映。
- ポケモン選択切替で一過性効果をリセット（appear 相当）。

**Non-Goals:**
- テラス依存技（テラバースト等）と テラスUI は別 change（`reintroduce-tera`）。
- スキルリンク等の特性自動発動は別 change（`add-ability-auto-effects`）。
- 連続技の「1ターンに複数回ランクが乗る」等の厳密シミュレーションはしない（1 回分適用に留める）。

## Decisions

- **WazaEffect の拡張**: `WazaEffectKind` に `selfRank` / `opponentRank` / `toggle` / `typeChange` を追加。
  - ランク系は「適用する boosts 差分（[A,B,C,D,S] の増減）」を値として持つ（"AS+1" → A+1,S+1 をパース）。
  - toggle 系は ON/OFF の 2 値。other_effect の複数候補は当面 ON/OFF に簡約（きょけんとつげき/オーラぐるま）。
  - typeChange は「対象（self/opponent）と変更後タイプ（または除去）」を持つ。
- **適用先**: ランク変化は「使用ポケモン＝攻撃側」基準だが、対象が self か opponent かで
  attacker/defender の boosts に適用。UI は技を持つポケモン視点で「相手のランクを下げる」も表現する。
- **一過性状態の保持**: 技に紐づくのではなく、適用結果（boosts/type/受×2 フラグ）を
  `BattlePokemon` 側の既存フィールド（boosts/type1/type2）と新フラグ（例 `incomingDamageX2`）に反映。
  ボタンの「適用済み」表示は、`BattleMove` の `effectValue`（ON/OFF やランク適用済みフラグ）で管理。
- **リセット**: `onTapPoke`（ポケモン選択切替）時に、一過性フラグ（受×2 等）と当該ランク適用を戻す
  かは要検討。旧アプリは appear でリセット。まずは「ボタン再タップで解除」を基本とし、切替リセットは
  最小限（受×2 等のフラグのみ）に。

## Risks / Trade-offs

- `waza.py` の文字列（"ACS+2 BD-1" 等）パースの網羅。テーブル移植時にテストで担保する。
- ランク適用の「対象が相手」の UI 表現が分かりにくい可能性 → ラベル色/向きで区別。
- other_effect を ON/OFF に簡約するため、原典の細かな分岐（じこあんじの有効/無効など）と差が出る箇所は
  tasks で個別に確認する。
