# タスク: add-weight-compare

## 1. weight 配管（バグ修正）

- [x] 1.1 `BattlePokemon.weight` 追加・JSON 永続化・`toAttacker`/`toDefender` でエンジンへ渡す
- [x] 1.2 `buildPokemon`/`formChange` で DB の weight を反映、`weightOf(pid)` 追加
- [x] 1.3 既存保存パーティの weight=0 を起動時に DB から補完

## 2. UI

- [x] 2.1 `weight_compare_dialog.dart`：重さ比較ポップアップ（赤青・比較記号・ヘビーボンバー威力）
- [x] 2.2 ドロワー「重さ比較」から起動
- [x] 2.3 基本情報に重さ（kg）を表示

## 3. 検証

- [x] 3.1 重量比威力のユニットテスト＋ヘビーボンバーのエンジン反映テスト
- [x] 3.2 analyze クリーン・全テストパス・spec/tasks 同期
