# クラウド基盤・ストアリリースの基礎（A）

## Why

Issue #25 の Phase1 は「クラウド正本＋端末キャッシュ＋招待制＋認証」を前提とする。今はローカル完結のため、
(1) 参照データ（HOME使用率・構築記事・ランキング・シーズン）のクラウド配信、(2) 認証（Apple/Google）＋招待制、
(3) ユーザーデータ同期、(4) App Store / Google Play リリース、の基礎を用意する。

ユーザー方針（2026-06-14 確認）：**コスト最優先**（無料枠でどこまで可能かを重視。難しければ Google Drive 等の
無料クラウドも検討）。認証は **Apple＋Google＋招待コード**。近期の必須は **HOME使用率・構築記事をクラウド取得**。
ストアはアカウント未取得・アプリ名/ID 未定のため**計画から**。

## What Changes

- **実装（本変更で完了）**：参照データ配信レイヤ `RefData`（クラウド取得→キャッシュ→同梱フォールバックの
  stale-while-revalidate）。`ScrapeData`/`HomeStats` がこれ経由で読む。設定画面に手動更新。Android INTERNET 権限。
  ※自動取得は配信元（クリーンデータの公開）準備後に有効化。
- **設計（design.md・本変更では設計のみ）**：
  - 無料枠分析（Firebase Spark / Google Drive appDataFolder / 静的CDN）と推奨アーキテクチャ。
  - 認証（Sign in with Apple＋Google）＋招待制（招待コード→allowlist）。
  - ユーザーデータ同期（対戦記録・パーティ/ボックス・設定。Google Drive 方式を第一候補に）。
  - ストアリリース計画（アカウント取得・bundle id/アプリ名・掲載文・権限文言・プライバシー方針・CI・段取り）。

## Impact

- Spec: scrape-data（クラウド配信を追記）。design.md に backend/auth/sync/release を記載。
- Code: data/ref_data.dart（新規）、scrape_data.dart / home_stats.dart（RefData 経由）、settings_screen.dart（手動更新）、
  AndroidManifest（INTERNET）。
- 実デプロイ（バックエンド構築・ストア申請・署名）は環境・アカウント整備後に別途。
