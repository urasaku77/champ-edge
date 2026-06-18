#!/usr/bin/env python3
"""PC 側データを mobile/assets/ に同期する。

ルール変更・シーズン更新・新ポケモン画像追加などの後に実行すると、
スマホ版 (Flutter) が参照する assets/ を最新状態に揃える。

使い方:
  python scripts/sync_to_mobile.py        # 同期実行
  python scripts/sync_to_mobile.py --dry  # 差分確認のみ
"""
import argparse
import filecmp
import os
import shutil
import sys

os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# (PC 側パス, mobile 側パス, 種別 file/dir)
MAPPINGS: list[tuple[str, str, str]] = [
    ("database/pokemon.db",            "mobile/assets/data/pokemon.db",            "file"),
    ("image/pokemon",                  "mobile/assets/image/pokemon",              "dir"),
    ("image/typeicon",                 "mobile/assets/image/typeicon",             "dir"),
    ("image/menu",                     "mobile/assets/image/menu",                 "dir"),
    ("image/other",                    "mobile/assets/image/other",                "dir"),
    ("image/favicon.ico",              "mobile/assets/image/favicon.ico",          "file"),
    ("stats/home_doryoku.csv",         "mobile/assets/data/stats/home_doryoku.csv","file"),
    ("stats/home_motimono.csv",        "mobile/assets/data/stats/home_motimono.csv","file"),
    ("stats/home_seikaku.csv",         "mobile/assets/data/stats/home_seikaku.csv","file"),
    ("stats/home_tokusei.csv",         "mobile/assets/data/stats/home_tokusei.csv","file"),
    ("stats/home_waza.csv",            "mobile/assets/data/stats/home_waza.csv",   "file"),
    ("stats/ranking.json",             "mobile/assets/data/stats/ranking.json",    "file"),
    ("stats/ranking.txt",              "mobile/assets/data/stats/ranking.txt",     "file"),
    ("stats/season.txt",               "mobile/assets/data/stats/season.txt",      "file"),
    ("stats/last_update.txt",          "mobile/assets/data/stats/last_update.txt", "file"),
    ("stats/last_update_battle.txt",   "mobile/assets/data/stats/last_update_battle.txt", "file"),
]


def _sync_file(src: str, dst: str, dry: bool) -> tuple[int, int]:
    """ファイル1件を同期。戻り値: (更新件数, スキップ件数)"""
    if not os.path.exists(src):
        print(f"  ! src なし、スキップ: {src}")
        return 0, 0
    if os.path.exists(dst) and filecmp.cmp(src, dst, shallow=False):
        return 0, 1
    print(f"  {'(dry) ' if dry else ''}更新: {src} -> {dst}")
    if not dry:
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copy2(src, dst)
    return 1, 0


def _sync_dir(src: str, dst: str, dry: bool) -> tuple[int, int]:
    """ディレクトリ配下を再帰同期。ファイル単位で差分判定。"""
    if not os.path.isdir(src):
        print(f"  ! src なし、スキップ: {src}")
        return 0, 0
    updated = skipped = 0
    for root, _, files in os.walk(src):
        rel_root = os.path.relpath(root, src)
        dst_root = dst if rel_root == "." else os.path.join(dst, rel_root)
        for name in files:
            s = os.path.join(root, name)
            d = os.path.join(dst_root, name)
            u, sk = _sync_file(s, d, dry)
            updated += u
            skipped += sk
    return updated, skipped


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry", action="store_true", help="差分のみ表示、書き換えない")
    args = parser.parse_args()

    total_updated = total_skipped = 0
    for src, dst, kind in MAPPINGS:
        print(f"\n== {src} -> {dst} ==")
        if kind == "file":
            u, sk = _sync_file(src, dst, args.dry)
        else:
            u, sk = _sync_dir(src, dst, args.dry)
        total_updated += u
        total_skipped += sk

    print(f"\n=== 完了: 更新 {total_updated} 件 / 同一 {total_skipped} 件{'  (dry-run)' if args.dry else ''} ===")
    return 0


if __name__ == "__main__":
    sys.exit(main())
