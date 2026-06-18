# 対戦履歴/分析の強化とダメージ計算UIの整合（実装反映）

## Why

当セッションで実装した次の挙動が既存スペックに未反映で齟齬が出ている。実装に合わせてスペックを同期する。

- 対戦履歴/分析：引分の明示、勝率の算出根拠、シーズン名表示、連番絞り込み、並び替え、ランク日替り境界（11時）、履歴一覧の自分/相手パーティ＋選出表示、自分パーティのポケモン別成績。
- 類似パーティ：サンプル構築記事プレースホルダの除去と空状態。
- ダメージ計算UI：相手技の物理/特殊5枠正規化（変化技除外＋HOME補完）、まきびしの登場時ハザード、ステータス表長押しでのランク一括クリア。

## What Changes

- **battle-record**：「対戦履歴の閲覧と絞り込み」「対戦分析」「類似パーティ検索」要件を実装に合わせて更新し、「自分パーティのポケモン別成績」要件を追加。
- **battle-screen-ui**：相手技の正規化・まきびし・ランク一括クリアの要件を追加。

## Impact

- Affected specs: battle-record, battle-screen-ui
- Affected code（実装済み）: battle_history_screen.dart, battle_analysis_screen.dart, period_preset.dart, service/battle_analysis.dart, similar_party_dialog.dart, data/battle_db.dart, screens/home_screen.dart, model/battle_pokemon.dart
- 挙動の後方互換：既存の絞り込み・集計は維持しつつ項目を追加（破壊的変更なし）。
