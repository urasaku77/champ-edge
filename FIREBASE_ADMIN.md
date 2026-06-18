# Firebase 管理者向けガイド（招待制 allowlist）

champ-edge mobile の認証・招待・ユーザー管理の運用メモ。実装は OpenSpec
`add-cloud-and-release-foundation`（design.md §3）に対応。

## 構成（無料 Spark / Cloud Functions 不使用）
- 認証：Firebase Authentication（Google／iPhone は Apple を後で追加）
- データ：Firestore（コレクションは2つ。管理者は users.role に一本化）
  - `users/{uid}` … 登録ユーザー一覧（＝ allowlist）。存在＝利用許可。
    `{ name, email, createdAt, inviteCode?, role: 'admin' | 'user' }`。`role=='admin'` が管理者。
  - `invites/{code}` … 招待コード（対象 Gmail 向け・1回限り）
- セキュリティルール：`firestore.rules`（利用者は自分の `role` を変更不可＝自己昇格防止）

## 初期セットアップ（1回だけ）
1. Firebase プロジェクト作成、iOS/Android アプリ登録（bundle id `io.github.urasaku77.champedge`）。
2. Authentication → Google を有効化。
3. Firestore 作成（ロケーション `asia-northeast1`）。
4. セキュリティルールを反映（どちらか）：
   - Console：Firestore → ルール に `firestore.rules` の内容を貼り付けて公開、または
   - CLI：`npm i -g firebase-tools` → `firebase login` → `firebase deploy --only firestore:rules`
5. **管理者ブートストラップ**：自分が一度アプリで Google サインイン →
   Authentication → Users に出る自分の UID をコピー →
   Firestore `users/{自分のUID}` を Console で手動作成：
   `name`(任意 例 `admin`) / `email`(自分のGmail) / `createdAt`(任意) / **`role` = `admin`**。
   ※管理者昇格はルール上クライアントから不可なので必ず Console から設定する。

## 招待運用（コード照合のみ）
照合は **招待コード（一回限りの秘密トークン）だけ**で行う。メール一致は不要なので、
相手が Google でも Apple（メール非公開でも）でも、コードを入れれば登録できる。
登録時の表示名は、発行時に管理者が入れた `name` が採用される。

**アプリ内（推奨）**：設定 → クラウドアカウント → 管理者メニュー → 「表示名」と
「メール（任意メモ）」を入れて発行 → 表示されたコードを本人へ直接共有。
本人はアプリでサインイン（iOS=Google/Apple, Android=Google）→ コード入力 → 登録完了。

**Console で手動発行する場合**：`invites/{ランダムコード}` を作成し、
- `name`（string）… 表示名（登録時に users.name へ採用）
- `email`（string, 任意）… 誰宛か分かるメモ（照合には使わない）
- `used`（bool）… `false`
- `createdBy`/`createdAt`/`expiresAt(任意)`

**一覧確認・無効化**：アプリの管理者メニュー、または Console の `users` で確認。
利用停止は `users/{uid}` を削除（allowlist から除外）。

## Android SHA-1（Google ログインに必要）
Google サインインは Firebase に署名証明書の SHA-1 登録が必要。
Firebase Console → プロジェクト設定 → 自分の Android アプリ → 「フィンガープリントを追加」。

- **デバッグ用（開発機の debug.keystore・内部テストまで）**
  - SHA-1：`B0:85:B0:FC:36:AC:67:58:E7:53:F8:5D:0A:FC:4F:D5:B4:C0:D2:2D`
  - ※この値は開発機ごとに異なる。取得：
    `keytool -list -v -keystore ~/.android/debug.keystore -alias androiddebugkey -storepass android -keypass android`
- **リリース用（ストア配布の署名鍵）**：リリース keystore 作成後にその SHA-1 を追加（後日）。
  Play App Signing 利用時は Play Console 側の SHA-1 も登録する。

## Apple サインイン（iOS）の有効化手順
クライアント実装（AppleAuthProvider・Appleボタン・Sign in with Apple ケイパビリティ）は済。
動作させるには以下のコンソール設定が必要：
1. **Apple Developer** → Certificates, IDs & Profiles → Identifiers → App ID
   `io.github.urasaku77.champedge` を開き **「Sign In with Apple」を有効化**して保存。
2. **Firebase Console** → Authentication → Sign-in method → **Apple を有効化**。
   - ネイティブ iOS のみなら追加設定は最小。Android/Web でも Apple を使う場合は
     Services ID・Key（.p8）・Team ID の設定が必要（当面 iOS のみなら不要）。
3. テストは **実機 or Apple ID を設定したシミュレータ**で。App Store 審査では
   他社ログイン（Google）併用時に Apple サインイン提供が必須（ガイドライン 4.8）。

## Google Drive バックアップ（任意機能）の有効化
クライアント実装済み（クラウドアカウント画面の「バックアップ/復元」）。本人の Drive の
アプリ専用領域（appDataFolder）へ対戦記録・パーティ・設定を保存/復元する。動作には以下：
1. **Google Cloud Console**（Firebase と同じプロジェクト `champedge`）→ APIとサービス →
   **Google Drive API を有効化**。
2. **OAuth 同意画面** → スコープに `.../auth/drive.appdata` を追加。
   - `drive.appdata` は機微スコープ扱い。**「テスト」モード＋テストユーザー登録**なら審査なしで利用可。
     一般公開時はアプリ審査（verification）が必要になる場合あり（招待制・少人数なら当面テストモード運用で可）。
3. 利用者はアプリ「バックアップ」初回タップ時に **Drive 利用許可（Google 認可）** を求められる。
   - Apple サインインのユーザーはここで別途 Google 認可が必要（運用は Google ログイン推奨）。

## 自動化（任意・後日）
発行・一覧・無効化を Console 手動でなく行いたくなったら、管理者専用の最小ツール
（ローカル CLI もしくは限定 Web。いずれも $0）を実装可能。Cloud Functions は
Blaze（従量課金）必須のため使わない方針。

## 補足・既知のトレードオフ
- 認可は **招待コードの秘匿**に依存（8桁ランダム・1回限り・直接手渡し。一般的な招待コードと同等）。
  ルール上 `users` 作成は「本人 uid・role=user 固定」で許可するが、実際の利用許可は
  「未使用コードの消費」を経て行う（アプリ UI はコード必須）。`users` 一覧で異常を検知・削除可能。
  厳密化が必要になれば管理者レビュー、または将来 Functions 検討。
- メール一致は廃止（コード照合のみ）。これにより Apple の「メール非公開」でも登録できる。
