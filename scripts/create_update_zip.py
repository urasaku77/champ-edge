#!/usr/bin/env python3
"""配布用zipを作成する。

--full: 新規インストール用（全ファイル含む）
引数なし: アップデート用（battle.db除外）
"""
import os
import sys
import zipfile

sys.stdout.reconfigure(encoding="utf-8")

EXCLUDE_EXACT = {
    "_internal/database/battle.db",
}

SRC_DIR = os.path.join("dist", "champedge")


def should_exclude(arcname: str) -> bool:
    return arcname.replace("\\", "/") in EXCLUDE_EXACT


def make_zip(out_zip: str, full: bool):
    if not os.path.isdir(SRC_DIR):
        print(f"ERROR: {SRC_DIR} が見つかりません。先に build.bat を実行してください。")
        raise SystemExit(1)

    total = 0
    with zipfile.ZipFile(out_zip, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
        for root, _, files in os.walk(SRC_DIR):
            for file in files:
                arcname = os.path.relpath(
                    os.path.join(root, file), SRC_DIR
                )
                if not full and should_exclude(arcname.replace("\\", "/")):
                    print(f"  スキップ: {arcname}")
                    continue
                zf.write(os.path.join(root, file), arcname)
                total += 1

    size_mb = os.path.getsize(out_zip) / 1024 / 1024
    print(f"完了: {out_zip}  ({total} ファイル, {size_mb:.1f} MB)")


if __name__ == "__main__":
    full = "--full" in sys.argv
    out = os.path.join("dist", "champedge_full.zip" if full else "champedge_update.zip")
    make_zip(out, full)
