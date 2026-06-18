# 設計：クラウド基盤・ストアリリース（A）

## 0. 前提・方針
- コスト最優先。**個人運用で月額ほぼ0円**を目標。招待制＝少人数前提なので無料枠で十分賄える見込み。
- クライアント側スクレイピングはしない（サーバ集約データを取得するだけ）。横画面・iOS/Android。
- **無料（広告・課金なし）方針**。非公式ファンメイドツールとして免責表記を明記。

### 確定事項（ユーザー回答 2026-06-14）
- アプリ表示名：**ChampEdge**（iOS `CFBundleDisplayName`/`CFBundleName`、Android `android:label`）。
- bundle id / applicationId：**`io.github.urasaku77.champedge`**（GitHubユーザー名ベース。ドメイン所有不要・公開後不変）。
- アイコン：旧 champ-edge の `image/favicon.ico`（王冠＋モンスターボール＋金星章）を流用し、紺色背景でフラット化して全サイズ生成。
- 参照データ配信：**案2＝プライベートリポジトリ + Cloudflare Pages 無料ホスティング**（公開リードオンリーURL）。
- ユーザーデータ保存：**ローカル保存を基本（端末が正・source of truth）**。対戦記録・保存パーティ・アプリ設定はローカルに完結。
- **クラウド同期（Google Drive）は P4（後回し）**。リリース基盤には含めず、希望者向けの任意機能として後から追加（案A＝本人 Google Drive、§1-C）。当面はローカル保存のみで運用。
- 招待・ユーザー管理：**管理者（作成者）主導の allowlist 方式**。管理者が利用希望者の Gmail を聞き、その人向けに招待コードを発行→利用者は Google（iPhone は Apple 可）でサインイン＋コード入力→**管理者側で氏名・ユーザーID(UID) を一元管理**。認証は Google/Apple、ユーザー一覧の管理はこちらで実施。
- 課金：無料・広告なし。

## 1. 無料枠でどこまでできるか（要点）

### 1-A. 参照データ配信（HOME使用率・構築記事・ランキング・シーズン）＝読み取り専用・全員共通
最も安いのは**静的ファイル配信**。候補と無料枠：
- **案2＝プライベートリポジトリ + Cloudflare Pages（採用）**：データ用のソースは**非公開**のまま、Cloudflare Pages がそれをビルド/公開して**公開リードオンリーURL**（`https://<project>.pages.dev/...` または独自サブドメイン）を発行。**完全無料・CDNキャッシュ・帯域無制限**。リポジトリを非公開にできるのが jsDelivr（公開repo必須）との違い。
  - 料金：**$0**（Cloudflare Pages 無料プラン。ビルド月500回・帯域無制限）。
  - `RefData._base` を Pages の公開URLに差し替える。データ更新＝プライベートrepoへ push → Pages が自動デプロイ。
  - 自動取得は**配信URL確定後に有効化**（現状は同梱データ既定＋手動更新）。
- 代替：GitHub + jsDelivr（公開repo必須のため不採用）、Firebase Hosting（10GB/月、可）。
→ **結論：参照データは 案2（Private repo + Cloudflare Pages）で $0。** 既に `RefData` で配信レイヤ実装済み（取得→キャッシュ→同梱フォールバック）。スクレイピングのバッチは将来 GitHub Actions（private 無料枠 2,000分/月）で定期実行→データ commit→Pages 自動公開、で $0 運用可。

### 1-B. 認証（Apple/Google）＋招待制
- **Firebase Authentication 無料枠**：Google/Apple サインインは**無料・人数上限なし**（電話番号SMSのみ有料）。→ 招待制の少人数なら**$0**。
- **管理者主導の allowlist**（§3）：`invites`（対象メール向けコード）と `users`（氏名・UID・メール）を **Firestore に最小限**置く。Firestore 無料枠（Spark）：保存1GB・読み取り5万/日・書き込み2万/日。発行・検証は1ユーザー数回程度なので**余裕で$0**。
- ユーザー一覧の管理は当面 Firebase コンソール手動でも可。自動化は管理者専用の最小ツール（$0）。

### 1-C. ユーザーデータ保存と同期
**基本＝ローカル保存（端末が正）**。以下は常にローカル JSON に保存し、オフラインでも完結：
- **対戦記録**（履歴・勝敗・選出・メモ）
- **保存パーティ／ボックス**（登録ポケモン・努力値・技・持ち物・特性等）
- **アプリ設定**（`app_settings.json`：ルール/メガ有効・類似検索トグル等）＋使用中パーティ参照

**クラウド同期（P4・後回し）**：希望ユーザーのみ、本人 Google Drive（appDataFolder）へ上記ローカル JSON をミラーリング（バックアップ／機種変更引き継ぎ目的）。リリース基盤には含めず、ローカル完結を先行させ、同期はP4でオプション追加。
- **同期しないもの**：参照データ（HOME使用率・構築記事・ランキング＝全員共通で配信から取得、§1-A）、CDNキャッシュ、認証トークン。

同期の実装方式（任意機能なので将来）：
- **案A：各ユーザーの Google Drive（appDataFolder）に保存**＝**バックエンド$0**。
  - 端末↔個人Driveで同期。アプリ専用の不可視フォルダ（appDataFolder）に JSON を置く。サーバ運用ゼロ。
  - 長所：完全無料・プライバシー良好（本人のDrive）。短所：Apple ユーザーの同期は iCloud 別途 or Google ログイン必須。共有/集計は不可（個人データのみ）。
- **案B：Firestore にユーザーごと保存**。
  - Spark 無料枠：上記の通り。1ユーザーの対戦記録（数百〜数千件）なら読み書きとも無料枠に収まる。
  - 長所：認証と一体・将来の集計（みんなの使用率等）に発展可。短所：件数が多いと読み取り回数に注意（ページング/集計キャッシュで回避）。
→ **推奨：当面は案A（Google Drive・$0）でユーザーデータ同期**、将来「全体集計」を作るなら案B/サーバへ移行。
  ただしユーザー回答は「まずローカルで良い」なので、**同期は抽象化層（SyncBackend インターフェース）だけ用意し、実装は後**。

### 1-D. まとめ（無料での到達点）
- 参照データ配信：**$0**（実装済み、要データ公開）。
- 認証＋招待制：**$0**（Firebase Auth + 最小 Firestore allowlist、少人数）。
- ユーザー同期：**$0**（Google Drive appDataFolder）。将来集計はFirestore/サーバで段階課金。
→ **招待制・個人規模なら全体 $0 で Phase1 のクラウド要件を満たせる見込み。** 規模拡大時のみ Firestore/Functions の従量課金。

## 2. アーキテクチャ（推奨）
- 参照データ：GitHub(データ) → jsDelivr → `RefData`（キャッシュ＋フォールバック）→ ScrapeData/HomeStats。実装済み。
- 認証：Firebase Auth（Apple/Google）。初回に招待コードを Firestore allowlist で検証し、ユーザーを有効化。
- ユーザー同期：`SyncBackend` 抽象（保存/取得/最終更新）。実装＝GoogleDriveSyncBackend（appDataFolder）。LocalOnly を既定にし、ログイン後に有効化。
- オフライン優先：ローカルが常に正、起動/手動で pull/push（last-write-wins ＋ 端末別マージは記録IDで重複排除）。

## 3. 認証・招待フロー（管理者主導の allowlist）
方針：**運用は全員 Google（Gmail）でログイン**（後述の Google Drive 連携を1アカウントで完結させるため）。**iOS は App Store 4.8 対応で Google＋Apple を併記**（Google 推奨・Apple は審査要件＆希望者用）、**Android は Google のみ**。**ユーザー一覧（氏名・UID）は管理者が一元管理**。利用希望者は管理者から招待コードを受け取って初回登録する。
- 注意：プロバイダが違うと UID も別。運用を Google に統一することで、同一人物が複数端末でも同一アカウント＝同一データ（Drive 連携）にできる。

### 管理者（作成者）側
1. 利用希望者から **Gmail アドレス**を聞く。
2. 管理ツール（後述）で**その Gmail 向けの招待コードを発行**（Firestore `invites/{code}`：対象メール・発行日時・未使用フラグ・任意の有効期限）。コードを本人へ伝える。
3. 利用者が登録を完了すると、管理者側の**ユーザー一覧（`users/{uid}`：氏名・メール・登録日時）**に反映され、ここで一覧確認・無効化（allowlist から除外）ができる。

### 利用者側（**起動時ゲート**・2026-06-14 ユーザー確定）
完全招待制：**Google サインイン＋招待コードを通過するまで Top 画面に入れない**（設定の任意項目ではなく起動ゲート）。実装＝`AuthGate`（`app.dart` の home）。
1. 起動 → `AuthGate` が認証状態を判定。
2. 未サインイン → **サインイン画面**（Google 推奨。iOS は Apple も併記＝審査用／Android は Google のみ）。
3. サインイン済みだが未登録 → **招待コード入力画面**。**コード照合のみ**で検証（未使用・有効。メール一致は不要＝Appleのメール非公開でも可）→ 使用済みに更新し `users/{uid}` を登録（トランザクション）。登録名は発行時に管理者が入れた `name`。
4. 登録済み（allowlist 通過）→ **Top 画面**。一度オンラインで確認できたらローカルにも記録し（`cloud_verified.txt`）、以降はオフライン起動でも締め出さない。初回はオンライン必須。
- 補足：審査時は審査員用に「審査用の招待コード」を申請メモで提供する。

### 管理ツール（軽量・$0想定）
- 当面は **Firebase コンソール** で `invites`/`users` を手動管理（コードはランダム文字列を手登録）でも運用可能。
- 自動化するなら **管理者専用の最小Web/CLI**（Functions or ローカルスクリプト）：メール入力→コード生成→ `invites` 追加、`users` 一覧表示・無効化。Firestore 無料枠で $0。

セキュリティルール要点：コレクションは `users`（allowlist＝存在で利用許可。`role` で管理者兼用）と `invites` の2つ（`admins` は廃止）。**招待はコード照合のみ**＝未使用コードをサインイン済みユーザーが消費（used/usedBy/usedAt のみ・トランザクションで1回）。メール一致は要求しない（Appleのメール非公開対応）。`users` 作成は本人 uid・**role='user' 固定**、本人更新は **role 変更不可**（自己昇格防止）。`role=='admin'` は Console でのみ付与。管理者のみ一覧全体の読取・招待発行/削除・ユーザー無効化が可能。発行時に `name`（表示名）を入れ、登録時 `users.name` に採用。

## 4. ストアリリース計画（アカウント未取得・名称未定 前提）
### 4-1. 事前準備（ユーザー作業）
- **Apple Developer Program**（年 $99）登録、**Google Play Developer**（初回 $25）登録。
- アプリ名：**ChampEdge**（確定。商標衝突は申請前に最終確認）。bundle id / applicationId：**`io.github.urasaku77.champedge`**（確定・適用済み）。
- プライバシーポリシー URL：**Cloudflare Pages に `docs/privacy.html` を同居**して公開（GitHub Pages は不要。配信を1つに集約）。

### 4-2. クライアント整備（実装側で対応可能・要 id/名称確定後）
- bundle id / applicationId 変更、アプリ表示名、アイコン（iOS/Android 全サイズ）、起動画面。
- 権限文言：iOS Info.plist（写真ライブラリ＝将来OCR用 `NSPhotoLibraryUsageDescription` 等）、Android（INTERNET 済、将来 READ_MEDIA_IMAGES）。
- iOS ATS（HTTPS のみ＝OK）。Sign in with Apple のケイパビリティ。
- バージョニング（pubspec `version`）、ビルド番号運用。

### 4-3. 申請物
- スクリーンショット（各デバイスサイズ・横画面）、説明文（JP/EN）、キーワード、年齢レーティング、カテゴリ（ユーティリティ/ゲーム関連）。
- App Store 審査：Sign in with Apple 必須（他社ログインがある場合）、機能が実在しクラッシュ無し、ガイドライン準拠。任天堂/ポケモンの知的財産表記に注意（非公式ツールの旨を明記、商標・画像利用の配慮）。
- Google Play：データ安全フォーム、対象年齢、コンテンツレーティング。

### 4-4. CI/配布（無料寄り）
- GitHub Actions（無料枠）で flutter build。TestFlight / Play 内部テストへ配布（fastlane）。署名証明書は要 Apple/Google アカウント。

### 4-5. 段取り（推奨順）
1. アプリ名・bundle id 確定 → クライアント整備（id/アイコン/権限/プライバシーURL）。
2. Apple/Google アカウント取得。
3. 参照データ公開（push or データrepo）→ RefData 自動取得を有効化。
4. 認証＋招待（Firebase）→ 内部テスト配布。
5. ユーザー同期（Google Drive）→ ベータ。
6. ストア申請。

## 5. 残課題・要ユーザー作業（確定済みは §0）
- **Cloudflare Pages のプロジェクト作成**（参照データ＋`docs/privacy.html` を配信）→ 公開URL確定 → `RefData._base` 差し替え＋自動取得有効化／プライバシーURL確定。
- **Apple Developer / Google Play デベロッパー アカウント取得**（署名・申請に必須）。
- Firebase プロジェクト作成（Auth＋Firestore：`users`〔allowlist・role で管理者兼用〕／`invites`）。
- 将来「全体集計」が必要になった場合のみ案B/サーバへ拡張（現状は案A・$0）。

## 6. あなた（管理者）が準備すること（手順・優先順）
すべて無料枠で完結。**コスト発生はストア申請のアカウント費のみ**（Apple 年$99 / Google 初回$25）。

**3サービスの役割（混同しないこと）**：
- **GitHub**＝ソース置き場（リポジトリ本体）。
- **Cloudflare Pages**＝静的ファイル配信。**参照データ(JSON/CSV) と プライバシーポリシーHTML を両方ここに載せる**。
- **Firebase**＝認証＋ユーザー一覧（招待管理）。ファイル配信はしない。
- **GitHub Pages は不要**：プライバシーポリシーは Cloudflare Pages に同居させるため、配信先を1つに集約する。

### フェーズ0：今すぐ・無料（クラウド基盤）
1. **Cloudflare アカウント**（無料）作成。
   - Pages → 「Connect to Git」→ 配信用 repo（参照データ JSON/CSV ＋ `docs/privacy.html`）を接続 → デプロイ。→ 発行された `https://<project>.pages.dev` を私に共有 → `RefData._base` を差し替え＋自動取得を有効化。`https://<project>.pages.dev/privacy.html` がプライバシーポリシー公開URL（ストア申請に使用）。
   - ※配信元は既存 `champ-edge-mobile` の `mobile/assets/data` ＋ `docs/` をそのまま接続する形でも可（別の専用repoでも可）。どちらにするか決めてください。
2. **Firebase アカウント／プロジェクト**（無料 Spark）作成。
   - Authentication で **Google** を有効化（iPhone向けに **Apple** も後で）。
   - Firestore を作成（`users` / `invites` コレクション用。管理者は `users.role`）。
   - あなたのGoogleアカウントUIDを「管理者」として控える（管理用ルールで使用）。
   - 設定ファイル（`google-services.json`／`GoogleService-Info.plist`）を私に渡す → クライアント組込。

### フェーズ1：招待運用（フェーズ0完了後）
3. 利用希望者の **Gmail を聞く** → （当面）Firebase コンソールで `invites` に「対象メール＋ランダムコード」を1件追加 → コードを本人へ連絡。
   - 自動化したくなったら、管理者専用の最小ツール（コード発行・一覧）を私が用意。
4. 登録された利用者は `users` 一覧で確認・無効化可能（氏名・メール・UID）。

### フェーズ2：ストア申請（アプリを公開する段階）
5. **Apple Developer Program**（年$99）登録 → 証明書/プロビジョニング、Sign in with Apple 有効化、TestFlight。
6. **Google Play Developer**（初回$25）登録 → アプリ作成、データ安全フォーム、内部テスト。
7. 申請物（スクショ横画面・説明文JP/EN・年齢レーティング・カテゴリ）を準備 → 審査提出。

### 私（実装側）が担当
- クライアント実装（認証UI・招待コード入力・同期トグル・管理ツール）、`RefData` 切替、CI、申請物の下書き、ストアメタデータ作成補助。
- あなたから渡る情報待ち：①Cloudflare PagesのURL ②Firebase設定ファイル＋管理者UID ③データ用repoの方針。
