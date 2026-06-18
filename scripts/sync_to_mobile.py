#!/usr/bin/env python3
"""PC マスターデータ (database/, image/, recog/, stats/) から、
スマホ版 (Flutter) が参照する `mobile/mobile/assets/` を生成・同期する。

PC 版を唯一のマスターとし、Mobile アセットはここから変換生成する
(Issue #26)。ルール変更・シーズン更新・新ポケモン画像追加などの後、
あるいは Flutter ビルド前 (scripts/prebuild.sh 経由) に実行する。

使い方:
  python scripts/sync_to_mobile.py        # 同期実行
  python scripts/sync_to_mobile.py --dry  # 差分のみ表示 (書き換えなし)
"""
import argparse
import filecmp
import json
import os
import shutil
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)

# Flutter が参照するアセットルート (pubspec.yaml は二重 mobile/ 配下)。
DST = "mobile/mobile/assets"


# ---- 共通ヘルパ ----------------------------------------------------------

def _write_if_changed(dst: str, data: bytes, dry: bool) -> bool:
    """内容が変わるときだけ書き込む。戻り値: 更新したか。"""
    if os.path.exists(dst) and open(dst, "rb").read() == data:
        return False
    print(f"  {'(dry) ' if dry else ''}更新: {dst}")
    if not dry:
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        with open(dst, "wb") as f:
            f.write(data)
    return True


def _copy_if_changed(src: str, dst: str, dry: bool) -> bool:
    """ファイルをコピー (内容差分があるときだけ)。戻り値: 更新したか。"""
    if not os.path.exists(src):
        print(f"  ! src なし、スキップ: {src}")
        return False
    if os.path.exists(dst) and filecmp.cmp(src, dst, shallow=False):
        return False
    print(f"  {'(dry) ' if dry else ''}更新: {src} -> {dst}")
    if not dry:
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copy2(src, dst)
    return True


def _json_bytes(obj) -> bytes:
    return json.dumps(obj, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


# ---- 各同期タスク --------------------------------------------------------

def sync_db(dry: bool) -> int:
    print("\n== database/pokemon.db -> assets/data/pokemon.db ==")
    return int(_copy_if_changed("database/pokemon.db",
                                f"{DST}/data/pokemon.db", dry))


def sync_home(dry: bool) -> int:
    print("\n== stats/home_*.csv -> assets/data/home/ ==")
    n = 0
    for cat in ("doryoku", "motimono", "seikaku", "tokusei", "waza"):
        n += int(_copy_if_changed(f"stats/home_{cat}.csv",
                                  f"{DST}/data/home/home_{cat}.csv", dry))
    return n


def sync_ranking(dry: bool) -> int:
    """stats/ranking.txt -> scrape/ranking.json。pid のゼロ埋め除去 (0445-00 -> 0445-0)。"""
    print("\n== stats/ranking.txt -> assets/data/scrape/ranking.json ==")
    src = "stats/ranking.txt"
    if not os.path.exists(src):
        print(f"  ! src なし、スキップ: {src}")
        return 0
    pids = [l.strip() for l in open(src, encoding="utf-8").read().splitlines() if l.strip()]
    pids = [f"{p.split('-')[0]}-{int(p.split('-')[1])}" for p in pids]
    return int(_write_if_changed(f"{DST}/data/scrape/ranking.json", _json_bytes(pids), dry))


def sync_season(dry: bool) -> int:
    """recog/season.json -> scrape/season.json。年月日フィールドを ISO 文字列へ。"""
    print("\n== recog/season.json -> assets/data/scrape/season.json ==")
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
    return int(_write_if_changed(f"{DST}/data/scrape/season.json", _json_bytes(dst), dry))


def sync_kousei(dry: bool) -> int:
    """stats/ranking.json -> scrape/kousei.json。parties をフラット化・URL 重複排除・
    icons->pokemons リネーム・title は空文字。"""
    print("\n== stats/ranking.json -> assets/data/scrape/kousei.json ==")
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
    return int(_write_if_changed(f"{DST}/data/scrape/kousei.json", _json_bytes(dst), dry))


def sync_images(dry: bool) -> int:
    """image/pokemon/*.png -> assets/pokemon/ (ミラー)。PC に無い余剰は削除。"""
    print("\n== image/pokemon/*.png -> assets/pokemon/ ==")
    src_dir, dst_dir = "image/pokemon", f"{DST}/pokemon"
    if not os.path.isdir(src_dir):
        print(f"  ! src なし、スキップ: {src_dir}")
        return 0
    if not dry:
        os.makedirs(dst_dir, exist_ok=True)
    src_files = {f for f in os.listdir(src_dir) if f.endswith(".png")}
    dst_files = ({f for f in os.listdir(dst_dir) if f.endswith(".png")}
                 if os.path.isdir(dst_dir) else set())
    n = 0
    for f in sorted(src_files):
        n += int(_copy_if_changed(os.path.join(src_dir, f),
                                  os.path.join(dst_dir, f), dry))
    for f in sorted(dst_files - src_files):  # PC に無い余剰を削除 (ミラー)
        print(f"  {'(dry) ' if dry else ''}削除(余剰): {dst_dir}/{f}")
        if not dry:
            os.remove(os.path.join(dst_dir, f))
        n += 1
    return n


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--dry", action="store_true", help="差分のみ表示、書き換えない")
    args = parser.parse_args()

    total = 0
    for task in (sync_db, sync_home, sync_ranking, sync_season, sync_kousei, sync_images):
        total += task(args.dry)

    print(f"\n=== 完了: 変更 {total} 件{'  (dry-run)' if args.dry else ''} ===")
    return 0


if __name__ == "__main__":
    sys.exit(main())
