# タスク: decide-cross-platform-framework

## モバイル共通

- [x] iOS と Android を対象とした Flutter プロジェクトのひな形を作成する
- [x] iOS と Android をランドスケープ優先で動作するよう設定する
- [x] `assets/data/pokemon.db` を Flutter プロジェクトに組み込み、Dart から開けて読み取れることを確認する
- [x] ローカルストレージ用に `drift` / `sqflite` を評価し、Phase 1 で採用するライブラリを決定する
- [x] `~/Documents/champ-edge/pokedata/calc.py` の最小限のダメージ計算フローを Dart に移植し、実行時間を測定する
- [x] パーティ参照や検索画面の共有 UI コンポーネントと状態管理モジュールを Flutter で作成する
- [x] パーティデータ、わざ詳細、HOME 使用率などのオフライン読取に対応するローカルデータキャッシュ層を追加する
- [x] Flutter アーキテクチャとプラットフォーム統合ポイントを README や設計ノートに文書化する

## iOS 固有

- [x] スクリーンショット自動取込と OCR 用の iOS プラットフォームチャネルのスタブを追加する
- [x] ランドスケープモードでの写真・スクリーンショット権限およびカメラ権限の扱いを確認する
- [x] スクショ→画像データ受け渡しの実機検証は後続 `decide-ocr-implementation` へ移管（スマホ版ゲーム未リリースのため保留）

## Android 固有

- [x] スクリーンショット自動取込と OCR 用の Android プラットフォームチャネルのスタブを追加する
- [x] Android のストレージ/カメラ権限・背景スクショ取得の挙動確認は後続 `decide-ocr-implementation` へ移管（リリース待ち保留）
- [x] Android ネイティブフックからの画像受け取り確認も同上（後続 OCR change へ移管）

## 検証 / テスト

- [x] iOS シミュレータ（iPhone 17 / iOS 26.3）で Flutter プロジェクトが起動・動作することを確認（Android 実機/エミュは OCR 着手時にあわせて検証）
- [x] ダメージ計算の性能チェックを追加（`damage_calc_test.dart` ベンチ：約0.028ms/回 ＜100ms）
- [x] ネットワーク無効でも参照データ（DB/サンプル）でオフライン動作することを確認
- [x] スマートフォン横画面で対戦画面 UI が収まることをシミュレータで確認

## 次の意思決定

- [x] `decide-damage-engine-language` を提案・作成済み（Dart 採用・250/250 検証）
- [x] `decide-ocr-implementation` の提案は OCR 着手時（スマホ版ゲームリリース後）に行う