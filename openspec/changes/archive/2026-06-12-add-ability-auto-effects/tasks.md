# タスク: add-ability-auto-effects

## 1. モデル

- [x] 1.1 `BattlePokemon` にいかく/トレース用の退避フィールド（intimidateActive / traceBackup）を追加
- [x] 1.2 `BattleMove.toMoveState` に skillLink パラメータを追加（連続技を 5 回で計算）

## 2. 登場時適用・切替リセット（home_screen.dart）

- [x] 2.1 `_applyAppearAbility(p, opp)`：いかく＝相手攻撃-1、トレース＝相手特性コピー
- [x] 2.2 `_resetAppearAbility(p, opp)`：いかく復元・トレース特性復元
- [x] 2.3 onTapPoke：切替前に reset、切替後に apply（既存の天候特性反映と併用）
- [x] 2.4 ダメージ計算で attacker がスキルリンクなら `toMoveState(skillLink: true)` を渡す

## 3. 検証

- [x] 3.1 テスト追加：スキルリンクで multiHit=5・いかくで相手攻撃ランク-1・トレースで特性コピー
- [x] 3.2 analyze クリーン・全テストパス・ビルド＆再起動
- [x] 3.3 spec/tasks 同期（メタモン/特性有効無効は後続と明記）
