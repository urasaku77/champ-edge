# 設定画面（アプリ設定）

## Why

旧 champ-edge の「アプリ設定」に相当する設定画面が未実装だった。ドロワーの「設定」を実体化し、
ルール表示・動作モードをローカルに永続化する（将来クラウド同期に載せ替え可能な作り）。

## What Changes

- 新 capability **app-settings** を追加：
  - **ルール**：シングル/ダブル（シングルのみ選択可・ダブルは P4）、ギミック反映 メガ/Z技/ダイマックス（メガのみ選択可・他は P4）。
  - **動作モード**：類似パーティ自動検索（既定オフ）、相手選出の自動登録（常時オン・固定表示）。
  - ローカル JSON 永続化（`app_settings.json`）。
- ドロワー「設定」から開く。

## Impact

- New spec: app-settings
- Affected code: data/app_settings.dart（新規）, screens/settings_screen.dart（新規）, screens/home_screen.dart（導線・起動時 load）。
- OCR/キャプチャ・認証/クラウド・BGM 等はバックエンド/リリース待ちのため本設定の対象外（P4）。
