# タスク: add-waza-special-effects

## 1. 効果テーブル（waza_effects.dart）

- [x] 1.1 `WazaEffectKind` に `copyBoosts`（じこあんじ）/ `swapAbility`（スキルスワップ）/
  `swapField`（コートチェンジ）/ `moveTypeChange`（オーラぐるま）を追加
- [x] 1.2 各技を登録：じこあんじ / スキルスワップ / コートチェンジ / オーラぐるま（→あく）

## 2. モデル・適用ロジック

- [x] 2.1 `BattlePokemon` に boosts 退避（じこあんじ用）を追加（既存 typeBackup と同様）
- [x] 2.2 `BattleMove.toMoveState` に技タイプ override（オーラぐるま ON であくタイプ）を反映
- [x] 2.3 トグル適用/解除ロジック：
  - copyBoosts：自分 boosts を退避→相手 boosts をコピー／解除で復元
  - swapAbility：攻撃側↔防御側 ability を入替（自己逆）
  - swapField：wall / constantDamage / hasStealthRock を攻守入替（自己逆）

## 3. UI・切替リセット（home_screen.dart）

- [x] 3.1 効果ボタンの分岐・ラベル/色を other_effect 系に拡張（ON で塗りつぶし）
- [x] 3.2 タップで適用/解除し再計算
- [x] 3.3 ポケモン選択切替（onTapPoke）時、切替前 active の全技トグルを解除しリセットする
  `_resetMoveToggles(attacker, defender)` を実装

## 4. 検証

- [x] 4.1 テスト追加：スキルスワップで特性入替・オーラぐるまでタイプあく化・じこあんじでランクコピー・
  コートチェンジで壁入替・切替リセット
- [x] 4.2 `flutter analyze` クリーン・全テストパス・シミュレータで表示/動作確認
- [x] 4.3 spec/tasks 同期
