# Mac 引き渡し: Mobile アセット同期実装 + TestFlight アップロード

> このドキュメントの使い方: Mac で `champ-edge` リポジトリを最新の main にした状態で Claude Code を起動し、**このファイルの内容を全文コピーしてそのままプロンプト送信** してください。

---

## あなたへの依頼

PC 版 (Windows / Python) で進めてきたスマホ版 (Flutter / Dart) のモノレポ統合の続きを Mac で完遂してください。具体的には:

1. `scripts/sync_to_mobile.py` を変換ロジック込みで全面書き直し
2. 旧 `mobile/assets/` の削除
3. sync 動作確認 (`mobile/mobile/assets/` に正しい構造で生成される)
4. 生成物の `.gitignore` 化 + `git rm --cached`
5. Flutter prebuild フック (`mobile/mobile/scripts/prebuild.sh`) の追加
6. `flutter analyze` + `flutter test` でテスト
7. iOS ビルド + TestFlight アップロード

途中でコミットして良い (タスク単位で区切る)。push までは行う。TestFlight にアップロード完了したら作業終了。

---

## 現状サマリ

### リポジトリ
- URL: `https://github.com/urasaku77/champ-edge`
- 構造: PC 版 (Python/Tkinter) がリポジトリ root、スマホ版 (Flutter/Dart) は `mobile/` に git subtree で統合済み
- 直近 12 コミット (2026-06-18 セッション) で実施済み:
  - 新メガシンカ16件の `database/pokemon.db` 登録
  - 新特性 (ほのおのたてがみ、うなぎのぼり) のダメ計対応 (Python `pokedata/calc.py`, `pokemon.py` + Dart `mobile/mobile/lib/src/service/damage/`)
  - シーズン M-3 (2026-06-17〜07-08) を `recog/season.json` に追加
  - 画像39件 (`image/pokemon/`) 追加
  - 同期スクリプト初版 (※旧 `mobile/assets/` 向けで間違い、今回書き直し対象) を `scripts/sync_to_mobile.py` に追加

### 関連 Issue
- **#26**: PC版とモバイル版のアセット構成不整合の整理 (本作業の元イシュー、全アセット対応表あり)
- **#25**: スマホ版移植要件

### 重要な前提
- **PC 版は不変** で進める (既存配布 exe が動かなくなるリスク回避)
- Mobile はまだリリース前 (TestFlight が初配布)
- 全 Mobile アセットは PC データから変換生成可能

---

## アセット変換仕様 (sync_to_mobile.py で実装すること)

### 構造
- **PC マスター**: `database/`, `image/`, `recog/`, `stats/` (リポジトリ root)
- **Mobile アセット**: `mobile/mobile/assets/` (Flutter の `pubspec.yaml` が参照)
- **旧 `mobile/assets/`**: 削除対象 (Flutter は参照していない、PC データの旧コピー)

### 変換マッピング

| Mobile 出力先 | PC ソース | 変換ロジック |
|---|---|---|
| `mobile/mobile/assets/data/pokemon.db` | `database/pokemon.db` | コピーのみ |
| `mobile/mobile/assets/data/home/home_*.csv` (5件: doryoku, motimono, seikaku, tokusei, waza) | `stats/home_*.csv` | コピーのみ |
| `mobile/mobile/assets/data/scrape/ranking.json` | `stats/ranking.txt` | text→JSON 配列、pid 形式変換 `0445-00` → `0445-0` (form 部分を `int()` してから str 化) |
| `mobile/mobile/assets/data/scrape/season.json` | `recog/season.json` | フィールド構造変換 |
| `mobile/mobile/assets/data/scrape/kousei.json` | `stats/ranking.json` | `parties[]` のフラット化、URL 重複排除、`icons` → `pokemons` リネーム、`title` は空文字 |
| `mobile/mobile/assets/pokemon/*.png` | `image/pokemon/*.png` | 同一フォルダ構造、ファイル名そのまま |

### 各変換の詳細仕様

#### ranking.txt → ranking.json
```
入力 (stats/ranking.txt):
  0445-00
  1018-00
  0730-00
  ...

出力 (mobile/mobile/assets/data/scrape/ranking.json):
  ["0445-0", "1018-0", "0730-0", ...]
```
変換コード:
```python
pids = [l.strip() for l in open("stats/ranking.txt").read().splitlines() if l.strip()]
pids = [f"{p.split('-')[0]}-{int(p.split('-')[1])}" for p in pids]  # ゼロ埋め除去
json.dump(pids, open("mobile/mobile/assets/data/scrape/ranking.json", "w"))
```

#### recog/season.json → scrape/season.json
```
入力 (recog/season.json):
  [{"name": "M-3", "from_year": 2026, "from_month": 6, "from_date": 17,
    "to_year": 2026, "to_month": 7, "to_date": 8}, ...]

出力 (mobile/mobile/assets/data/scrape/season.json):
  [{"name": "M-3", "from": "2026-06-17", "to": "2026-07-08"}, ...]
```
変換コード:
```python
src = json.load(open("recog/season.json", encoding="utf-8"))
dst = [{
    "name": e["name"],
    "from": f"{e['from_year']}-{e['from_month']:02d}-{e['from_date']:02d}",
    "to":   f"{e['to_year']}-{e['to_month']:02d}-{e['to_date']:02d}",
} for e in src]
json.dump(dst, open(".../season.json", "w", encoding="utf-8"), ensure_ascii=False)
```

#### stats/ranking.json → scrape/kousei.json
```
入力 (stats/ranking.json):
  [{"pid": "0445-00", "parties": [
     {"url": "https://x.com/...", "icons": ["212-0", "937-0", ...6体]},
     ...
   ]}, ...]

出力 (mobile/mobile/assets/data/scrape/kousei.json):
  [{"title": "", "url": "https://x.com/...", "pokemons": ["212-0", ...6体]}, ...]
```
変換コード:
```python
src = json.load(open("stats/ranking.json", encoding="utf-8"))
seen, dst = set(), []
for entry in src:
    for party in entry.get("parties", []):
        url = party.get("url", "")
        if not url or url in seen: continue
        seen.add(url)
        dst.append({"title": "", "url": url, "pokemons": party.get("icons", [])})
json.dump(dst, open(".../kousei.json", "w", encoding="utf-8"), ensure_ascii=False)
```

### 触らない Mobile アセット
- `mobile/mobile/assets/README.md`
- (もし他に Mobile 固有の静的ファイルがあれば残す。`assets/` 配下を grep で確認すること)

---

## 実装手順

### Step 1: scripts/sync_to_mobile.py 全面書き直し

既存ファイルは旧 `mobile/assets/` 向けで間違い。完全に書き換える。要件:
- `--dry` オプションで差分のみ表示 (書き換えなし)
- 同期先は `mobile/mobile/assets/` (二重 `mobile/`)
- 上記の変換ロジック全部を実装
- 画像は `image/pokemon/*.png` を `mobile/mobile/assets/pokemon/` にコピー
- 既存ファイルが同一内容ならスキップ (filecmp.cmp で判定)

### Step 2: 旧 mobile/assets/ 削除
```
git rm -r mobile/assets/
```

### Step 3: sync 実行と検証
```
python scripts/sync_to_mobile.py --dry  # 差分確認
python scripts/sync_to_mobile.py        # 実行
```
検証:
- `mobile/mobile/assets/data/pokemon.db` が `database/pokemon.db` と同一
- `mobile/mobile/assets/data/home/` に CSV 5 件
- `mobile/mobile/assets/data/scrape/ranking.json` が `["xxx-y", ...]` 形式
- `mobile/mobile/assets/data/scrape/season.json` に M-3 が含まれる
- `mobile/mobile/assets/data/scrape/kousei.json` がフラットなリスト
- `mobile/mobile/assets/pokemon/` に PNG 315 枚 (PC の `image/pokemon/` と同数)

### Step 4: gitignore + git rm --cached

`mobile/.gitignore` に追加:
```gitignore
# 生成物 (scripts/sync_to_mobile.py で PC データから生成)
mobile/assets/data/pokemon.db
mobile/assets/data/home/
mobile/assets/data/scrape/ranking.json
mobile/assets/data/scrape/season.json
mobile/assets/pokemon/
```

※ `mobile/assets/data/scrape/kousei.json` も自動生成だが、空配列でもOKなら除外。要判断 (上記変換でちゃんと生成されるはずなので gitignore でよい)。

untrack:
```
git rm --cached mobile/mobile/assets/data/pokemon.db
git rm -r --cached mobile/mobile/assets/data/home/
git rm --cached mobile/mobile/assets/data/scrape/ranking.json
git rm --cached mobile/mobile/assets/data/scrape/season.json
git rm -r --cached mobile/mobile/assets/pokemon/
```

(kousei.json も自動生成にするなら同じく `git rm --cached`)

### Step 5: prebuild フック

`mobile/mobile/scripts/prebuild.sh` を作成:
```bash
#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../.."
python3 ../../scripts/sync_to_mobile.py
echo "✅ prebuild: assets synced"
```
権限: `chmod +x mobile/mobile/scripts/prebuild.sh`

README ([mobile/mobile/README.md](mobile/mobile/README.md)) に追記:
```
## ビルド前の準備
`flutter build` または `flutter run` の前に以下を実行してください:
    ./scripts/prebuild.sh
PC データ (../../database/, ../../image/, etc.) から assets/ を生成します。
```

### Step 6: Flutter テスト

```
cd mobile/mobile
./scripts/prebuild.sh    # アセット生成
flutter pub get
flutter analyze          # 静的解析
flutter test             # ユニットテスト
```
すべて pass することを確認。エラーがあれば修正してから先へ。

### Step 7: iOS ビルド + TestFlight アップロード

#### 前提
- Mac + Xcode (最新)
- Flutter 3.44.2 以降 (`mobile/.github/workflows/ci.yml` で固定されているバージョン)
- Apple Developer アカウント (App Store Connect アクセス必要)
- プロビジョニングプロファイル + 署名証明書
- App Store Connect で本アプリの登録済み (bundle id は `mobile/mobile/ios/Runner/Info.plist` を確認)

#### 手順
```
cd mobile/mobile
./scripts/prebuild.sh                        # アセット最新化
flutter pub get
flutter build ios --release --no-codesign    # 一旦コードサイン抜きでビルド検証
```

エラーなければ Xcode で:
```
open ios/Runner.xcworkspace
```

Xcode で:
1. Runner プロジェクトを選択 → Signing & Capabilities タブ
2. Team を選択 (Apple Developer アカウント)
3. Bundle Identifier 確認
4. メニュー: Product → Archive
5. Organizer ウィンドウで Distribute App
6. App Store Connect → Upload
7. TestFlight に上がるのを待つ (通常 5-15 分)

完了したら TestFlight 側でビルドが Processing → 配布可能 になる。

### コミット方針
タスク単位で区切る (一気にやらない):
- Step 1〜3: `chore: sync_to_mobile.py を Flutter assets 構造向けに全面書き直し`
- Step 4: `chore: mobile/mobile/assets/ 生成物を gitignore 化`
- Step 5: `chore: Flutter ビルド前 prebuild フック追加`
- Step 6 で何か直したら個別コミット
- Step 7 では (iOS ビルド設定変更があれば) 個別コミット

最後に push。

---

## 参考情報

### Dart コードの該当箇所
- アセット読み込み: `mobile/mobile/lib/src/data/ref_data.dart`, `scrape_data.dart`, `home_stats.dart`
- ダメ計 (新特性対応済): `mobile/mobile/lib/src/service/damage/damage_calc.dart`, `move_tables.dart`, `models.dart`
- pubspec.yaml の assets 宣言: `mobile/mobile/pubspec.yaml`

### Mobile が読む asset パス (Flutter rootBundle 経由)
```
assets/data/pokemon.db
assets/data/home/home_doryoku.csv
assets/data/home/home_motimono.csv
assets/data/home/home_seikaku.csv
assets/data/home/home_tokusei.csv
assets/data/home/home_waza.csv
assets/data/scrape/ranking.json
assets/data/scrape/season.json
assets/data/scrape/kousei.json
assets/pokemon/{pid}.png   # pid 形式: "{no:04d}-{form}" (form 1桁、例: "0026-11", "0025-0")
```

### Cloudflare Pages 配信
`ref_data.dart` で `champ-edge-mobile.pages.dev/mobile/` から daily フェッチしているが、**Mobile は未リリース・ユーザー無し** のため当面気にしなくて良い。リリース前に Pages 配信設定を新リポジトリ向けに切り替える別タスク (Issue 化 or #26 に追記推奨)。

### memory に既に記録済みの情報 (Claude が参照する)
- `project_monorepo_workflow.md`: モノレポ運用の全体像 + Dart 側と PC 側の対応関係
- `project_new_mega_procedure.md`: 新メガ追加手順
- `project_new_ability_handling.md`: 新特性対応 + Dart 側反映の対応表
- `reference_pokedb_tokyo.md`: データソース取得方法

### memory の更新依頼
Step 4〜5 が完了したら memory `project_monorepo_workflow.md` の以下を更新してほしい:
- 「将来的に gitignore + ビルド時生成へ移行するのが理想」と書いてある部分を「移行済み」に修正
- prebuild フックの存在と使い方を追記

---

## 完了条件
- [ ] `scripts/sync_to_mobile.py` が新仕様で動作する (`--dry` 含め)
- [ ] `mobile/assets/` (旧コピー) が削除されている
- [ ] `mobile/mobile/assets/` が gitignore 化され、prebuild で生成される
- [ ] `flutter analyze` + `flutter test` が pass
- [ ] iOS Archive 成功
- [ ] TestFlight に新ビルドがアップロードされ Processing 完了
- [ ] push 済み
- [ ] memory `project_monorepo_workflow.md` 更新済み

完了したら結果をユーザーに簡潔に報告すること (どのコミットを push したか、TestFlight ビルド番号、テスト結果)。

---

**以上。実装に着手してください。**
