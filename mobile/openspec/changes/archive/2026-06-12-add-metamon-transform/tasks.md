# タスク: add-metamon-transform

## 1. モデル

- [x] 1.1 `BattlePokemon` に `transformBackup` と `snapshot()`/`applySnapshot(json)` を追加（JSON ベースで復元）

## 2. へんしん適用・復元（home_screen.dart）

- [x] 2.1 `_applyAppearAbility`：メタモン選択時に相手をコピー（H=48維持、A〜S・タイプ・特性・技）
- [x] 2.2 `_resetAppearAbility`：切替で transformBackup から復元

## 3. 検証

- [x] 3.1 テスト追加：snapshot/applySnapshot の復元（party_json_test）
- [x] 3.2 analyze クリーン・全293テストパス・ビルド＆再起動
- [x] 3.3 spec/tasks 同期
