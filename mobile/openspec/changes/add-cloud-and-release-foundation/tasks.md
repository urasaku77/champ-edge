# Tasks

## 1. 参照データ配信レイヤ（実装済み）
- [x] 1.1 `RefData`（取得→キャッシュ→同梱フォールバックの stale-while-revalidate、TTL、手動 force）
- [x] 1.2 `ScrapeData`/`HomeStats` を `RefData.loadString` 経由に
- [x] 1.3 設定画面に「参照データを更新」手動ボタン
- [x] 1.4 Android INTERNET 権限を追加
- [x] 1.5 自動取得は配信元準備まで無効（同梱データ既定）。flutter analyze/test 通過

## 2. 設計（design.md・本変更は設計のみ）
- [x] 2.1 無料枠分析（Firebase Spark / Google Drive appDataFolder / 静的CDN）
- [x] 2.2 認証（Apple/Google）＋招待制（招待コード→allowlist）設計
- [x] 2.3 ユーザーデータ同期（Google Drive 案A／Firestore 案B）設計＋抽象化方針
- [x] 2.4 ストアリリース計画（アカウント・bundle id/名称・掲載文・権限・プライバシー・CI・段取り）

## 3. クライアント整備（実装側で対応可能）
- [x] 3.1 アプリ表示名 ChampEdge を適用（iOS Info.plist・Android label）
- [x] 3.2 bundle id / applicationId を `io.github.urasaku77.champedge` に変更
- [x] 3.3 アプリアイコンを旧 champ-edge favicon から生成し iOS/Android 全サイズへ配置
- [x] 3.4 プライバシーポリシー（`docs/privacy.html`）作成（JP/EN・免責）

## 4. リリース基盤（次フェーズ・要ユーザー環境）
- [ ] 4.1 Cloudflare Pages プロジェクト作成（参照データ＋`docs/privacy.html` 配信）→ 公開URL確定 → `RefData._base` 差し替え＋自動取得有効化＋プライバシーURL確定
- [ ] 4.2 Firebase 認証（Google／iPhone は Apple）＋管理者主導 allowlist（invites/users 管理）実装
  - [x] 4.2a Firestore セキュリティルール（users〔role で管理者兼用〕/invites・自己昇格防止）＋ firebase.json ＋ 管理者運用ガイド（FIREBASE_ADMIN.md）を先行作成
  - [x] 4.2b FlutterFire 組込（firebase_core/auth/cloud_firestore/google_sign_in）・firebase_options・iOS URLスキーム・Android google-services/minSdk23
  - [x] 4.2c 起動時ゲート（AuthGate）：Googleサインイン→招待コード→allowlist通過までTop非表示。オフラインは確認済みローカル記録でフォールバック。analyze/test通過・起動ゲート実機表示確認
  - [x] 4.2d 実機での Google サインイン疎通＝本番Firebaseで サインイン→allowlist→Top 到達を確認（Firestoreルール反映＋管理者ブートストラップ済）
  - [x] 4.2e ゲート堅牢化：Firebase初期化失敗/接続不能(オフライン新規端末)で行き止まりにせず再試行画面を提示（AllowStatus 3値化・ロックアウト防止）
  - [x] 4.2g 管理者メニュー（アプリ内）：招待コード発行/一覧/削除・ユーザー一覧/無効化（設定→クラウドアカウント→管理者メニュー、role==admin のみ）
  - [x] 4.2f Apple サインイン（クライアント実装）：AuthService.signInWithApple(AppleAuthProvider)・ゲートにAppleボタン(iOSのみ)・Runner.entitlements(Sign in with Apple)＋pbxproj配線。iOSビルド/ゲート表示 確認済み
  - [x] 4.2i 招待をコード照合のみに変更（メール一致撤廃・Appleメール非公開対応）＋発行時に表示名入力→users.name 採用＋設定画面に名前表示。iOS は Google＋Apple 併記（Google推奨）
  - [ ] 4.2h Apple サインイン疎通（要：Apple DeveloperでApp IDにSign in with Apple有効＋Firebaseで Apple プロバイダ有効＋実機/Apple ID）
- [ ] 4.3 Apple/Google アカウント取得 → CI/署名 → 内部テスト → ストア申請

## 5. クラウド同期（Google Drive）＝優先度引き上げ（スクショ対応の次）
- [x] 5.1 手動バックアップ/復元（MVP）：`DriveSync`（drive.appdata 認可＋REST：multipart作成/PATCH更新/get）＋`SyncService`（Documents配下 app_settings.json/battle.db/parties/** を base64 スナップショット化→Drive保存/復元、復元時 battle.db close→上書き→open＋設定reload）＋クラウドアカウント画面に「バックアップ/復元」ボタン＋最終バックアップ時刻。analyze/329テスト通過
  - [ ] 5.1a Drive 疎通確認（要：GCPでGoogle Drive API有効化＋OAuth同意画面に drive.appdata・テストユーザー登録、実機/Google認可）
  - [ ] 5.2 自動同期（起動時pull/変更時push）＋複数端末マージ（最終更新優先＋記録ID重複排除）は後続。現状は手動・スナップショット全体上書き（last-write-wins）
