# champ-edge-mobile Flutter プロジェクト

このフォルダは Phase 1 MVP 向けの Flutter サンプルプロジェクト骨子です。

## 目的

- iOS / Android 両対応のクロスプラットフォーム開発基盤を用意する
- 既存の `assets/data/pokemon.db` を Flutter から参照できるようにする
- ランドスケープ UI の前提で、ネイティブ機能のプラットフォームチャネルを準備する
- ダメージ計算エンジンの Dart 版実装を開始する

## 構成

- `pubspec.yaml` - Flutter プロジェクトの依存定義
- `lib/main.dart` - アプリのエントリポイント
- `lib/src/app.dart` - アプリ本体の Widget
- `lib/src/screens/home_screen.dart` - 初期ホーム画面
- `lib/src/data/local_database.dart` - SQLite データベース初期化および読み取り
- `lib/src/service/damage_engine.dart` - ダメージ計算エンジンのひな型
- `lib/src/platform/platform_channels.dart` - ネイティブ連携メソッドのスタブ

## ビルド前の準備 (assets 生成)

`assets/` は PC マスター (`../../database/`, `../../image/`, `../../recog/`, `../../stats/`)
から生成される (Issue #26)。git 管理対象外なので、`flutter build` / `flutter run` の前に
必ず以下を実行して `assets/` を生成・更新すること。

```bash
./scripts/prebuild.sh    # = python3 ../../scripts/sync_to_mobile.py
```

## 実行

Flutter が導入されている環境では、以下のコマンドで実行できます。

```bash
cd mobile
./scripts/prebuild.sh    # 先に assets を生成
flutter pub get
flutter run
```

## 注意

`assets/data/pokemon.db` はリポジトリ上部の `assets/data` にあります。
`pubspec.yaml` でこのファイルをアセット登録し、アプリ起動時にローカルコピーを作成して読み込みます。
