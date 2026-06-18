# champ-edge-mobile

ポケモン Champions スマートフォン版対戦補助アプリ。

現行デスクトップ版 [`champ-edge`](../champ-edge/) を、スマートフォン版ポケモン Champions のリリースに合わせて iOS / Android 向けに移植したモバイルアプリ。

## ステータス

- フェーズ: **Phase 1 (MVP) — 要件定義 / 仕様策定中**
- 開発手法: [OpenSpec](https://github.com/Fission-AI/OpenSpec) による仕様駆動開発
- 関連イシュー: [champ-edge#25](https://github.com/urasaku77/champ-edge/issues/25)

## スコープ (Phase 1 / MVP)

- ポケモン / 技 / 特性 / 持ち物のデータ参照
- ダメージ計算エンジン（テラスタル・特殊技仕様含む）
- パーティ編集・保存（複数パーティ管理）
- HOME 使用率の表示・反映
- 天候・フィールドの設定
- 画像認識（OCR）による相手パーティ・選出・TN・レートの自動取込
- スクリーンショット自動取込 UX
- 招待制ユーザ認証とクラウド同期基盤

詳細は `openspec/project.md` を参照。

## プラットフォーム

- iOS / Android（クロスプラットフォーム）
- 横画面（ランドスケープ）基本

## 既存資産

旧リポジトリ `champ-edge` の以下を移植:

- ダメージ計算ロジック仕様 (`pokedata/calc.py` 他)
- ポケモン / 技 / 特性 / 持ち物マスタデータ (`database/pokemon.db`)
- 対戦記録 DB スキーマ (`database/battle.py`)
- 画像アセット (`image/`)
- HOME 使用率データ (`stats/home_*.csv`)

## ライセンス

非公開（個人開発）。
