## Why

対戦履歴・分析の原典機能の取りこぼし。原典は期間をシーズン（`season.json`）で一括選択できたが、モバイルは
日付ピッカーのみ。また分析の「直近使用パーティ」表示、編集での日時・パーティ番号の修正も漏れていた。

## What Changes

- **期間プリセット選択**を履歴・分析に追加（全期間/今日/今週/今月/過去30日/過去90日/カスタム）。選択で
  from/to を一括設定。日付ピッカー操作で自動的にカスタムへ。シーズン名リスト（M-2 等）はスクレイプ依存の
  ため、実用上同等のクイック期間で代替（季節データはスクレイピングデータ整備時に追加）。
- **直近使用パーティ表示**を分析サマリに追加（最新記録の自分パーティ）。
- **履歴の編集ダイアログに 日時・P番号・連番**の修正を追加（既存の勝敗/TN/レート/メモ/お気に入り/
  ポケモンに加えて）。

## Capabilities

### Modified Capabilities
- `battle-record`: 対戦履歴・分析の期間プリセット・直近パーティ・編集項目を更新する。

## Impact

- `mobile/lib/src/screens/period_preset.dart`（新規）
- `mobile/lib/src/screens/battle_history_screen.dart` / `battle_analysis_screen.dart`
- `mobile/lib/src/model/battle_record.dart`（date を編集可能に）
