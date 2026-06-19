# Cloudflare Pages 配信セットアップ（HOME等の参照データ配信）

スマホ版アプリは HOME 使用率 / ランキング / シーズン / 構築記事データを、
アプリ同梱アセットではなく **Cloudflare Pages から取得**して差し替える
（`mobile/mobile/lib/src/data/ref_data.dart`、stale-while-revalidate）。

旧リポジトリからこのモノレポへ統合した際に Cloudflare Pages の Git 接続が切れ、
配信データが新ルール解禁前で凍結 → 新ポケモンの HOME 情報が表示されなくなった。
以下で同じ仕組みを復活させる。

## 仕組み

```
stats/home_*.csv, stats/ranking.txt/json, recog/season.json   ← git 管理マスター
        │  (push / CI: update_data.yml が stats/ をコミット)
        ▼
GitHub: urasaku77/champ-edge (main)
        │  Cloudflare Pages が push を検知して自動ビルド
        ▼
build: python3 scripts/build_pages.py  →  public/mobile/assets/data/...
        ▼
配信: https://champ-edge-mobile.pages.dev/mobile/assets/data/home/home_waza.csv ...
        ▼
アプリが起動時に取得しキャッシュ（端末側 24h TTL）
```

- `scripts/build_pages.py` は git 管理下のマスターのみから配信物を生成（標準ライブラリのみ・画像不要）。
- 出力 `public/` はビルド生成物なので `.gitignore` 済み（Cloudflare 側のビルドで都度生成）。

## ダッシュボードでの再接続（1回だけ）

Cloudflare ダッシュボード → **Workers & Pages** →
既存プロジェクト `champ-edge-mobile`（あれば）を開く。無ければ
**Create application → Pages → Connect to Git** で新規作成。

設定値:

| 項目 | 値 |
|---|---|
| Production branch | `main` |
| Framework preset | `None` |
| Build command | `python3 scripts/build_pages.py` |
| Build output directory | `public` |
| Root directory | （空＝リポジトリルート） |

- 接続先リポジトリ: `urasaku77/champ-edge`
- 既存プロジェクトの場合は **Settings → Builds & deployments** で
  「Connected Git repository」をこのリポジトリに張り替え、上記 Build 設定を反映。
- 環境変数は不要（Python 標準ライブラリのみ）。Pages のビルド環境には Python3 が同梱。

設定後、**Retry deployment / 任意の push** で初回ビルドが走る。

## 動作確認

```bash
# ローカルでビルド物を確認
python3 scripts/build_pages.py
find public -type f

# デプロイ後、配信に新ポケモンが入っているか
curl -s https://champ-edge-mobile.pages.dev/mobile/assets/data/home/home_waza.csv | grep -c '^サーフゴー,'
# → 0 以外なら OK（旧データだと 0）
```

アプリ側は端末キャッシュに 24h TTL があるため、配信更新後の反映は
次回以降の起動＋TTL 経過後。即時確認したい場合は端末アプリを再インストール
（`ref_cache` を消す）すると配信を取り直す。

## 更新フロー（以後の運用）

- 通常: ローカルバッチ or CI(`.github/workflows/update_data.yml`)が `stats/` を
  更新コミット → main へ push → Cloudflare が自動ビルド＆デプロイ。
- 追加作業は不要。`build_pages.py` が常に最新の `stats/` から配信物を作る。
