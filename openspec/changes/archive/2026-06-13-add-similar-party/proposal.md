## Why

P2 第4弾（最後）。相手の選択パーティに一致する過去のパーティを、対戦履歴と構築記事から探す類似パーティ
検索（旧 champ-edge の SimilarParty / 類似パーティ）。

## What Changes

- 中央列の「類似パーティ検索」アイコンから結果ダイアログを開く。
- **マッチング**：相手パーティ6体と候補を照合し、**並びまで一致（exactOrder）／中身だけ同じ（sameSet）**を
  区別する（メガ統合つき）。判定は UI 非依存の `similar_party.dart` に分離（テスト可能）。
- **対戦履歴ベース**：過去の対戦記録の相手パーティ（重複排除）から一致を探す。
- **構築記事ベース**：`kousei` テーブル（タイトル・URL・6体）から一致を探し、**構築記事リンク**に飛べる。
  構築記事データはサーバー集約で投入する想定（現状は手動登録分。スクレイピングはクライアントで行わない）。

## Capabilities

### Modified Capabilities
- `battle-record`: 類似パーティ検索（対戦履歴・構築記事）要件を追加する。

## Impact

- `mobile/lib/src/service/similar_party.dart`（新規・照合）
- `mobile/lib/src/data/battle_db.dart`（kousei テーブル・allRecords/allKousei/addKousei）
- `mobile/lib/src/screens/similar_party_dialog.dart`（新規）
- `mobile/lib/src/screens/home_screen.dart`（類似パーティ検索アイコン配線）
