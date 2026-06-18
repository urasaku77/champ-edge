# タスク: add-effect-detail-popup

## 1. データ取得（poke_db.dart）

- [x] 1.1 `abilityEffect(name)`：`ability_data` から effect を取得
- [x] 1.2 `itemEffect(name)`：`item_data` から effect を取得

## 2. UI（home_screen.dart）

- [x] 2.1 `_editChip` に onLongPress を追加（任意）
- [x] 2.2 特性チップ長押し → 効果詳細ダイアログ（名前＋effect。データ無しは「効果情報なし」）
- [x] 2.3 持ち物チップ長押し → 効果詳細ダイアログ

## 3. 検証

- [x] 3.1 analyze クリーン・全テストパス・ビルド＆再起動で長押し表示を確認
- [x] 3.2 spec/tasks 同期（へんげんじざい/リベロのタイプ手動設定は既存タイプ編集で代替と明記）
