#!/usr/bin/env python3
"""Cloudflare Pages 配信用の静的ディレクトリ `public/` を生成する。

スマホ版アプリ (mobile/mobile/lib/src/data/ref_data.dart) は HOME 使用率 /
ランキング / シーズン / 構築記事データを、アプリ同梱アセットではなく
**ネット越し (Cloudflare Pages)** から取得して差し替える設計
(stale-while-revalidate)。その配信元を git 管理下のマスターから組み立てる。

アプリの取得 URL:
    _base = https://champ-edge-mobile.pages.dev/mobile/
    + assets/data/home/home_*.csv  /  assets/data/scrape/*.json
→ 配信ルート直下に `mobile/assets/data/...` を置く必要があるため、
  出力先は `public/mobile/assets/data/...`。

入力はすべて git 管理下のマスター (stats/, recog/) のみ。画像や cv2/numpy は
不要なので、Cloudflare Pages のビルド環境 (Python 標準ライブラリのみ) で動く。
`scripts/sync_to_mobile.py` の対応タスク (sync_home/ranking/season/kousei) と
同一の変換結果になるよう実装している。

使い方:
    python scripts/build_pages.py            # public/ を生成
    python scripts/build_pages.py --out dist # 出力先を変更
"""
import argparse
import json
import os
import shutil
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)


def _json_bytes(obj) -> bytes:
    return json.dumps(obj, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


def _write(path: str, data: bytes) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as f:
        f.write(data)
    print(f"  生成: {path} ({len(data)} bytes)")


def build_home(data_dir: str) -> int:
    """stats/home_*.csv -> mobile/assets/data/home/home_*.csv (そのままコピー)。"""
    n = 0
    for cat in ("doryoku", "motimono", "seikaku", "tokusei", "waza"):
        src = f"stats/home_{cat}.csv"
        if not os.path.exists(src):
            print(f"  ! src なし、スキップ: {src}")
            continue
        dst = f"{data_dir}/home/home_{cat}.csv"
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copyfile(src, dst)
        print(f"  生成: {dst}")
        n += 1
    return n


def build_ranking(data_dir: str) -> int:
    """stats/ranking.txt -> scrape/ranking.json。pid のゼロ埋め除去 (0445-00 -> 0445-0)。"""
    src = "stats/ranking.txt"
    if not os.path.exists(src):
        print(f"  ! src なし、スキップ: {src}")
        return 0
    pids = [l.strip() for l in open(src, encoding="utf-8").read().splitlines() if l.strip()]
    pids = [f"{p.split('-')[0]}-{int(p.split('-')[1])}" for p in pids]
    _write(f"{data_dir}/scrape/ranking.json", _json_bytes(pids))
    return 1


def build_season(data_dir: str) -> int:
    """recog/season.json -> scrape/season.json。年月日フィールドを ISO 文字列へ。"""
    src = "recog/season.json"
    if not os.path.exists(src):
        print(f"  ! src なし、スキップ: {src}")
        return 0
    data = json.load(open(src, encoding="utf-8"))
    dst = [{
        "name": e["name"],
        "from": f"{e['from_year']}-{e['from_month']:02d}-{e['from_date']:02d}",
        "to": f"{e['to_year']}-{e['to_month']:02d}-{e['to_date']:02d}",
    } for e in data]
    _write(f"{data_dir}/scrape/season.json", _json_bytes(dst))
    return 1


def build_kousei(data_dir: str) -> int:
    """stats/ranking.json -> scrape/kousei.json。parties フラット化・URL 重複排除・
    icons->pokemons リネーム・title は空文字。"""
    src = "stats/ranking.json"
    if not os.path.exists(src):
        print(f"  ! src なし、スキップ: {src}")
        return 0
    data = json.load(open(src, encoding="utf-8"))
    seen, dst = set(), []
    for entry in data:
        for party in entry.get("parties", []):
            url = party.get("url", "")
            if not url or url in seen:
                continue
            seen.add(url)
            dst.append({"title": "", "url": url, "pokemons": party.get("icons", [])})
    _write(f"{data_dir}/scrape/kousei.json", _json_bytes(dst))
    return 1


def write_headers(out_dir: str) -> None:
    """Cloudflare Pages の _headers。配信ファイルは短い TTL で常に最新追従させる
    (アプリ側も 24h TTL を持つが、サーバ側は更新を素早く反映させたい)。"""
    headers = (
        "/mobile/assets/data/*\n"
        "  Cache-Control: public, max-age=300, must-revalidate\n"
        "  Access-Control-Allow-Origin: *\n"
    )
    _write(f"{out_dir}/_headers", headers.encode("utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--out", default="public", help="出力ルート (default: public)")
    args = parser.parse_args()

    out_dir = args.out
    # クリーンビルド (古い配信物を残さない)。
    if os.path.isdir(out_dir):
        shutil.rmtree(out_dir)

    data_dir = f"{out_dir}/mobile/assets/data"
    print(f"== 配信ディレクトリ生成: {out_dir}/ ==")
    total = 0
    total += build_home(data_dir)
    total += build_ranking(data_dir)
    total += build_season(data_dir)
    total += build_kousei(data_dir)
    write_headers(out_dir)

    print(f"\n=== 完了: {total} ソースを配信用に変換 -> {out_dir}/ ===")
    return 0


if __name__ == "__main__":
    sys.exit(main())
