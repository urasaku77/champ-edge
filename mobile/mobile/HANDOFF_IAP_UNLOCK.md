# 引継ぎ: App Store リジェクト対応（IAP解放 ＋ 無料版の汎用計算機化）

最終更新: 2026-07-02 / ブランチ: `feature/iap-unlock`（origin へ push 済）

このドキュメントだけで別セッションから作業を再開できるようにまとめている。

---

## 0. 背景（なぜこの作業をしているか）

App Store 審査リジェクト（2026-06-27 / Submission `0dd3aad5-6d77-4db9-95d9-9c28660829c4` / version 1.0(32)）で以下3点を指摘された。

1. **Guideline 3.1.1（IAP）**: 自前の招待コードで機能解放しているのはNG。IAP以外の解放機構は不可。
2. **Guideline 4.1(c)（Copycats）**: サブタイトルに他社ブランド名「ポケモン」が含まれる。
3. **Guideline 2.1（Information Needed）**: デモ用コードが期限切れでフル機能を確認できなかった。

---

## 1. 確定した方針（ユーザーとの合意事項）

- **課金方式**: 非消費型IAP（買い切り）＋ **Apple純正プロモコード**。自前招待コードは全廃。
  解放は StoreKit の購入 / 復元 / `presentCodeRedemptionSheet`（コード引き換え）でのみ行う。
  → プロモコード配布なら手数料0・追加コスト0（年会費$99のみ）。ただしASCで「有料App契約＋口座/税情報」登録が前提（無料手続き）。
- **商品ID**: `io.github.urasaku77.champedge.full_unlock`（バンドルID `io.github.urasaku77.champedge` に揃えた・非消費型）
- **隠しモード = 案①（控えめ）**: 設定画面に小さく「フル機能 / コードをお持ちの方」導線を置く。
  メイン画面には出さない。完全秘密（案②③）は Guideline 2.3.1（隠し機能）リスクで不採用。
  **重要**: 「Appleに隠す」のはNG。ユーザーに目立たせないのはOK。→ App Review情報で必ず開示する。
- **機能境界（当初）**:
  - 無料: 完全手動のダメージ計算のみ
  - 有料（`unlocked`）: パーティ管理 / ボックス / 対戦履歴 / 対戦分析 / 対戦記録 / OCR取込 /
    バトルデータ表示（HOME使用率・類似パーティ検索）/ バトルデータ自動補完 / クラウド連携
- **★方針転換（最新・未実装）**: 無料版から**ポケモン要素を完全排除**したい（動機: A=任天堂に目をつけられたくない, C=アプリ内ポケモン表示の著作権不安）。
  → **無料 = 汎用の数値ダメージ計算機（ポケモンのスプライト/名前/DB無し）**、**有料 = 現行のポケモンDBを後乗せした HomeScreen**。
  これは「別アプリに変身」ではなく「同一の計算機能への機能追加（正当なIAP）」として通す。**審査情報での開示が必須**。

---

## 2. 実装済みの状態（コミット `631476e`）

`flutter analyze` クリア・**全348テスト合格**・`flutter build ipa` 成功（build **1.0.0+33**, `build/ios/ipa/ChampEdge.ipa` 77.3MB, **未アップロード**）。

### 新規ファイル
- `lib/src/data/entitlement_service.dart` — 解放状態管理。`EntitlementService.instance`（ChangeNotifier）。
  - `unlocked` getter / `init()`（永続フラグ読込→ストア初期化→purchaseStream購読）/ `buy()` / `restore()` / `redeemCode()`（iOS `presentCodeRedemptionSheet`）
  - 解放フラグは `AppSettings.unlocked` に永続化（`app_settings.json`）
- `lib/src/screens/unlock_sheet.dart` — `showUnlockSheet(context)`。購入 / コードを利用 / 復元 の3ボタン（StoreKit経由）。

### 変更ファイル
- `lib/main.dart` — 起動時に `EntitlementService.instance.init()`。Firebase初期化は撤去（クラウド利用時に遅延初期化）。
- `lib/src/app.dart` — `home: const HomeScreen()`（旧 AuthGate 撤廃）。**★方針転換で後述 RootScreen に差し替える予定**。
- `lib/src/data/app_settings.dart` — `bool unlocked` フィールド＋ load/save に追加。
- `lib/src/screens/cloud_account_screen.dart` — 招待/allowlist/admin を全除去。Firebase遅延初期化。サインイン（Google/Apple）＋ Driveバックアップ/復元のみ。誰でもサインインで使える。
- `lib/src/screens/settings_screen.dart` — 最下部に控えめな「フル機能 / コードをお持ちの方」導線（`showUnlockSheet`）。クラウドアカウント項目と HOMEデータ更新は `_ent.unlocked` のときのみ表示。
- `lib/src/screens/home_screen.dart` — `EntitlementService` を購読し、以下を `_unlocked` でガード:
  - 中央メニュー: 「バトルデータ（相手）」「類似パーティ検索」「対戦記録」を未解放で非表示（`_centerMenu`）
  - ドロワー: パーティ編集/ボックス編集/対戦履歴/対戦分析を未解放で非表示（`_buildMenuDrawer`）。素早さ比較/重さ比較/設定は無料
  - 自分パネル長押し（使用中パーティ表示）/ 相手パネル長押し・ダブルタップ（OCR取込）を未解放で無効化
  - 自動補完 `_fillFromHome` / `_normalizeOpponentMoves` / 自動類似検索 `_maybeAutoSimilar` は未解放で早期リターン
- `pubspec.yaml` — `in_app_purchase: ^3.2.0` / `in_app_purchase_storekit: ^0.4.0` 追加。version `1.0.0+33`。
- `ios/Podfile.lock` — pod 追加分。

### 削除ファイル
- `lib/src/data/invite_service.dart` / `lib/src/screens/admin_screen.dart` / `lib/src/screens/auth_gate.dart`

> 注: 方針転換（無料=汎用計算機）を実装すると、未解放ユーザーは HomeScreen 自体を見なくなるため、home_screen 内のガードは大半が防御的（冗長だが無害）になる。残置でよい。

---

## 3. ★次にやること: 無料版の汎用計算機化（未実装・メイン残作業）

### 3.1 設計方針
ダメージエンジンの低レベルAPIが **DB非依存の純粋な数値計算** なので、これを使って無料の汎用計算機を作る。
ポケモンのスプライト/名前/DBは一切使わない。タイプ名（ほのお/みず/でんき…）は一般名詞で商標非該当なので使用可。

- エンジン: `DamageCalc.calculateDamage(AttackerState, DefenderState, MoveState, FieldState)`
  （`lib/src/service/damage_engine.dart` が re-export。実装は `lib/src/service/damage/`）
- 入出力モデル: `lib/src/service/damage/models.dart`
  - `AttackerState` / `DefenderState`（`CombatantState`）: `level`(既定50), `stats`=[H,A,B,C,D,S](6要素必須), `boosts`(ランク6要素), `type1`/`type2`, `ability`, `item`, `status`(Ailment), `wall`(Wall), `charging` ほか
    - `DefenderState.hp` = stats[H]
  - `MoveState`: `name`, `type`(PokeType), `category`(MoveCategory 物理/特殊/変化), `power`, `isTouch`, `multiHit`(-1単発), `critical` ほか
  - `FieldState`: `weather`(Weather), `field`(Field)
  - `DamageResult`: `damages`(16通り昇順), `minDamage`, `maxDamage`, `percentage`(対HP%), `isDamage`
- enum定義: `lib/src/service/damage/poke_types.dart`
  - `PokeType`（none + 18タイプ, `.jp`で日本語名）, `Weather`(なし/晴れ/雨/砂嵐/雪), `Field`(なし/エレキ/サイコ/グラス/ミスト), `Wall`(なし/リフレクター/ひかりのかべ/オーロラベール), `Ailment`(なし/やけど…), `MoveCategory`(物理/特殊/変化)

### 3.2 作るもの
1. **`lib/src/screens/generic_calc_screen.dart`（新規）** — 無料の汎用計算機。入力フォーム:
   - 攻撃側: 攻撃実数値（分類が物理→A, 特殊→C に対応する1値でOK）, レベル(既定50), タイプ1/2(STAB用), ランク, 急所
   - 技: 威力, タイプ, 分類(物理/特殊), 接触, 連続回数(任意)
   - 防御側: HP実数値, 防御実数値(物理→B, 特殊→D), タイプ1/2, ランク, 壁, 状態異常(やけど等)
   - 場: 天候, フィールド
   - 出力: 最小〜最大ダメージ, 対HP%, 確定n発 など
   - `stats` は6要素必須なので、使わない枠は 0 か適当な実数値で埋める（H,B/D は防御側で使用、A/C は攻撃側で使用）
   - 「メニュー」から `SettingsScreen` へ遷移できるようにする（← ここに解放導線があるため必須）
2. **`RootScreen`（新規 or app.dart 内）** — `EntitlementService` を購読し、
   `unlocked ? HomeScreen() : GenericCalcScreen()` を返す。`app.dart` の `home:` をこれに差し替え。
   コード引き換えで `unlocked` が true になると notifyListeners → 自動で HomeScreen へ切替。
3. `HomeScreen` は「解放後のポケモン計算機」として維持（現行のまま。中のガードは残置で無害）。

### 3.3 コンプラ上の必須事項（重要）
- **App Review情報に必ず開示**（2.3.1回避）:
  - フル機能は「設定 → フル機能 / コードをお持ちの方 → コードを利用」で解放されること
  - 解放するとポケモンDB（スプライト/種族値/HOME使用率/自動補完）が追加されること
  - **レビュー用プロモコードを1枚記載**（2.1対応）
- **購入導線を残す**（IAPが「購入可能」でないと再リジェクトリスク）。unlock_sheet の購入ボタンは維持。
- 無料の汎用計算機は **それ単体で実用的** であること（4.2 最低限の機能）。数値計算として成立していればOK。

### 3.4 レビュー情報 記載例
```
・本アプリのダメージ計算（数値入力）は無料で利用できます。
・「設定 → フル機能 / コードをお持ちの方 → コードを利用」から、
  ポケモンのデータ（種族値・使用率など）を使った拡張機能を解放できます。
・レビュー用プロモコード: XXXX-XXXX
```

---

## 4. 配信（TestFlight）: 中断中

- ビルド済み IPA: `mobile/mobile/build/ios/ipa/ChampEdge.ipa`（build 1.0.0+33）
- アップロードスクリプト: `mobile/mobile/upload_testflight.sh <ISSUER_ID>`
  - APIキー: `~/.appstoreconnect/private_keys/AuthKey_8FHTL4N8T9.p8` / KEY_ID=`8FHTL4N8T9`（自動使用）
  - **ISSUER_ID が未取得でブロック中**。App Store Connect → ユーザーとアクセス → 統合(Integrations) → App Store Connect API → **Issuer ID**（UUID）をユーザーから取得して渡す。
- **注意**: 方針転換（無料=汎用計算機）を実装するなら、build 33 はアップロードせず、実装後に **version を +34 以上に上げて再ビルド** してから配信すること。

---

## 5. ユーザー側の手作業（コード不可・ASC）
1. **有料App契約に同意 ＋ 銀行口座・税務情報を登録**（IAP有効化に必須・無料）
2. **非消費型IAP作成**: 商品ID `io.github.urasaku77.champedge.full_unlock` / 表示名・価格Tier設定（¥0不可・最低額でOK）
3. IAP商品を**このバージョンの審査に紐付けて提出**（紐付け忘れると3.1.1対応が未完）
4. **プロモコード発行**（最大100枚/バージョン・無料）→ 配布 ＆ レビュー用に1枚をReview情報へ
5. **メタデータ修正**: アプリ名/サブタイトルから「ポケモン」削除（4.1c）。露出を下げたいならアイコン/スクショ/説明文もポケモン要素排除＋「非公式ファンメイド・任天堂/ポケモン社とは無関係」明記

---

## 6. ブランチ / コミット状況
- `main`: `89438b5`（UX改善: 使用中パーティ確認＋努力値エディタ種族値/実数値表示）push済
- `feature/iap-unlock`: `631476e`（IAP解放実装一式）push済 ← **現在ここで作業**
- 未コミットの scratch: リポジトリ root の `dev/ev_mock.html` / `dev/ev_mock_shot.png` / `dev/poke_db_unblock_probe.py`（コミット対象外）

## 7. 検証コマンド
```
cd mobile/mobile
bash scripts/prebuild.sh          # アセット同期（PCマスター→assets/）
flutter pub get
flutter analyze
flutter test
flutter build ipa                 # 署名は設定済み。build/ios/ipa/ChampEdge.ipa 生成
```

## 8. 関連メモリ
- `appstore-iap-unlock-plan`（プロジェクトメモリ・本作業の要約）
- `no-auto-device-build`（build/配信は明示指示時のみ。今回は配信まで許可済だが方針転換のため中断）
