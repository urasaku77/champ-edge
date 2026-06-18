## Why

P2 第3弾。対戦記録を集計して相手の傾向を見る対戦分析画面（旧 champ-edge の対戦分析画面の移植）。

## What Changes

- ドロワーメニュー「対戦分析」から全画面の分析画面を開く。
- **絞り込み**：期間・自分パーティ番号/連番。**対戦数・勝率**を表示。
- **表示モード3択**：KPと勝率／選出と勝率／初手と勝率。相手ポケモンごとに主指標（KP=出現数／選出率／
  初手選出率）と勝率（出現時／選出時／初手時）を表示。
- **操作パネル**：ソート（件数/勝率）・降順/昇順・値の表示形式（%／分数／両方）・**メガ統合**（メガ前後を
  同一集計）・表示件数（50/100）。
- 集計ロジックは UI 非依存の `battle_analysis.dart` に分離（テスト可能）。
- 注：原典の「使用率順」「トップN絞り」は `stats/ranking.txt`（全体使用率ランキング）依存で、モバイルには
  該当データが無いため本フェーズでは対象外（HOME ランキング整備時に追加）。

## Capabilities

### Modified Capabilities
- `battle-record`: 対戦分析の集計・表示要件を追加する。

## Impact

- `mobile/lib/src/service/battle_analysis.dart`（新規・集計）
- `mobile/lib/src/screens/battle_analysis_screen.dart`（新規）
- `mobile/lib/src/screens/home_screen.dart`（ドロワー「対戦分析」起動）
