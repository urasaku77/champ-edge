## Why

スクレイピングデータ依存機能を、仮データ（アプリ同梱 seed）で先行実装する。データの取得（更新）は
別物として切り分け、機能本体は**ローカルキャッシュを読むだけ**にする（原典同様。将来サーバー集約で更新）。

## What Changes

- **ScrapeData**（ローカルキャッシュ層）を新設。`assets/data/scrape/{ranking,season,kousei}.json` の seed を
  読み込む。各機能はここを読むだけ。更新機構（API/バンドル更新）は別タスク（未実装）。
- **使用率順ソート・トップN絞り**（分析）：ranking を使い、ソート3択（件数順/勝率順/使用率順）と
  トップに絞る（OFF/10/30/50）を実装。
- **シーズン選択**（履歴・分析）：season を使い、シーズンドロップダウンで from/to を一括設定（プリセットと併存）。
- **構築記事ベース検索の実データ**（類似パーティ）：kousei seed を照合対象に追加（手動登録 DB 分と併用）。

## Capabilities

### Added Capabilities
- `scrape-data`: スクレイピング由来データのローカルキャッシュと、それに依存する機能の要件。

## Impact

- `mobile/assets/data/scrape/*.json`（seed）／`pubspec.yaml`（assets）
- `mobile/lib/src/data/scrape_data.dart`（新規）
- `mobile/lib/src/screens/battle_analysis_screen.dart`（使用率順/トップN/シーズン）
- `mobile/lib/src/screens/battle_history_screen.dart`（シーズン）
- `mobile/lib/src/screens/similar_party_dialog.dart`（kousei seed 照合）
- `mobile/lib/src/screens/period_preset.dart`（SeasonDropdown）
