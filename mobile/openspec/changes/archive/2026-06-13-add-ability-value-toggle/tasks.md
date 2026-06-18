# タスク: add-ability-value-toggle

## 1. データ・モデル

- [x] 1.1 `ability_values.dart`：原典 ABILITY_VALUES を移植（先頭値＝デフォルト）
- [x] 1.2 `BattlePokemon.abilityValue`：特性変更でデフォルトへ自動リセット（setter）・JSON 永続化
- [x] 1.3 `toAttacker`/`toDefender` でエンジンへ配管

## 2. UI

- [x] 2.1 特性詳細ダイアログに値切替チップ（即時反映）
- [x] 2.2 値を持つ特性はチップに `[値]` を併記

## 3. 検証

- [x] 3.1 テスト：デフォルト値・特性変更リセット・JSON 往復・ふかしのこぶし×1/4・マルチスケイル半減
- [x] 3.2 analyze クリーン・全テストパス・spec/tasks 同期
