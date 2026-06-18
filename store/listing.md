# ストア掲載文ドラフト（App Store / Google Play）

非公式ファンメイドツール。申請前に商標・ガイドライン最終確認。プライバシーポリシー：
https://champ-edge-mobile.pages.dev/docs/privacy

- アプリ名：**ChampEdge**
- カテゴリ：ユーティリティ（または スポーツ/ゲーム関連ツール）
- 年齢レーティング：全年齢想定（暴力・課金・広告なし）。Google Play コンテンツレーティング質問票は「なし」中心で回答。
- 価格：無料・広告なし・アプリ内課金なし

---

## 日本語

### サブタイトル（App Store・30字以内）
ポケモン対戦のダメージ計算＆記録

### 短い説明（Google Play・80字以内）
ポケモン対戦用の高精度ダメージ計算機。パーティ編集・対戦記録・分析までこれ一つ。

### 説明文
ChampEdge は、ポケモン対戦のための高精度ダメージ計算ツールです。横画面に最適化し、
対戦中でも素早く正確に計算できます。

主な機能
・高精度ダメージ計算（特性・持ち物・天候・フィールド・壁・急所・状態・各種特殊技に対応）
・確定数表示（乱数の幅をわかりやすく）
・パーティ編集・保存／ボックス管理（努力値・技・持ち物・特性まで個別編集）
・HOME使用率を反映した入力補助（技・持ち物・特性・性格・努力値の候補）
・対戦記録・履歴・分析（勝率／選出率／KP、シーズン別・期間別の集計）
・類似パーティ検索／素早さ比較・重さ比較・加算ツール・タイマー・カウンター

本アプリは非公式のファンメイドツールです。任天堂株式会社・株式会社ポケモン・
株式会社ゲームフリークおよびその関連会社とは一切関係ありません。

### キーワード（App Store・カンマ区切り100字以内）
ポケモン,対戦,ダメージ計算,ダメ計,構築,パーティ,努力値,使用率,対戦記録,分析

---

## English

### Subtitle (App Store, <=30 chars)
Damage calc & battle tracker

### Short description (Google Play, <=80 chars)
Accurate Pokémon battle damage calculator with party editing and match analysis.

### Description
ChampEdge is an accurate damage calculator for competitive Pokémon battles.
Optimized for landscape, it lets you calculate quickly and precisely mid-battle.

Features
- Accurate damage calc (abilities, items, weather, terrain, screens, crits, status, and special moves)
- Guaranteed-hit counts to read damage rolls at a glance
- Party editing & saving / box management (per-Pokémon EVs, moves, item, ability)
- Input assist based on HOME usage rates (moves, items, abilities, natures, EVs)
- Battle records, history, and analysis (win rate, selection rate, KP; by season/period)
- Similar-party search, speed & weight comparison, adder tool, timer, counter

This is an unofficial, fan-made tool. It is not affiliated with Nintendo,
The Pokémon Company, or GAME FREAK.

### Keywords (App Store, comma-separated, <=100 chars)
pokemon,battle,damage calculator,damage calc,team,party,EV,usage,record,analysis

---

## 申請メモ（要対応）

### スクリーンショット仕様（提出時に release ビルドで撮影）
横画面（ランドスケープ）。DEBUG バナーは `debugShowCheckedModeBanner:false` で非表示済み。
- **撮る画面（推奨5枚）**：①Top（ダメージ計算・確定数）②パーティ編集（個別編集）③対戦履歴 ④対戦分析（勝率/選出率）⑤ツール（素早さ/重さ比較・加算）
- **App Store 必須サイズ**：6.7"（iPhone 16/15 Pro Max 等）・6.5"（iPhone 11 Pro Max 等）・iPad 12.9"
- **Google Play**：携帯（最低2枚・各16:9 or 9:16）＋ 任意でタブレット
- 撮影手順：`flutter run --release -d <各シミュレータ>` → 各画面で `xcrun simctl io <udid> screenshot`（横向きは `sips -r 90`）

### ストア設定
- App Store：Sign in with Apple は他社ログイン併用時に必須（実装は Apple フェーズ）。プライバシー「データ収集なし」申告。年齢 4+。
- Google Play：データ安全フォーム（個人データ収集なし・端末内保存・任意で本人クラウド）。コンテンツレーティング質問は「なし」中心。
- プライバシーポリシーURL：`https://champ-edge-mobile.pages.dev/docs/privacy`
- 著作権・商標：説明文末尾の非公式・免責表記を保持。ポケモン画像/名称の権利は各権利者に帰属。

> 掲載文（上記 JP/EN）は確定。スクリーンショットの実アセットのみ提出時に撮影する。
