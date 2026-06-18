## Why

P2 第1弾。原典の対戦記録（database/battle.py の battle テーブル）を移植し、対戦結果を保存できるように
する。これが対戦履歴・分析（P2-3/4）と類似パーティ検索（P2-5）のデータ基盤になる。あわせて、分析の
自分パーティ別絞り込みに必要な**パーティ番号/連番/タイトル**を導入する。

## What Changes

- **書き込み可能な battle.db（sqflite）**をアプリ領域に作成し、原典と同一スキーマの `battle` テーブルを移植
  （日時/ルール/勝敗/お気に入り/相手TN/相手レート/メモ/自分パーティ番号・連番/両者ポケモン6体/両者選出4枠）。
- **対戦記録の登録**：中央列の「対戦記録」アイコンからダイアログを開き、相手TN・レート・メモ・お気に入りを
  手動入力（TN/レートの OCR 自動入力は P4 保留）、勝ち/分け/負けで保存する。匿名ボタンで TN を「トレーナー」に。
  ポケモン・選出は現在の盤面（両パーティと選出）から取り込む。
- **自分パーティの番号/連番/タイトル**：パーティ編集（自分）に番号・連番・タイトル欄を追加し永続化。
  記録時に番号/連番を保存する（分析の絞り込みキー）。

## Capabilities

### Added Capabilities
- `battle-record`: 対戦記録の保存とパーティ番号付けの要件群。

## Impact

- `mobile/lib/src/model/battle_record.dart`（新規）／`mobile/lib/src/data/battle_db.dart`（新規・sqflite）
- `mobile/lib/src/screens/battle_record_dialog.dart`（新規）
- `mobile/lib/src/data/party_store.dart`（パーティ番号メタの永続化）
- `mobile/lib/src/screens/home_screen.dart`（記録アイコン・番号入力・起動時 DB open）
