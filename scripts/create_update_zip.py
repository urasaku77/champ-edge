#!/usr/bin/env python3
"""配布用zipを作成する。

--full : 新規インストール用（全ファイル含む）
引数なし: アップデート用（ユーザーデータ除外）

ユーザーデータ（上書き不可）:
  _internal/database/battle.db
  _internal/party/csv/
  _internal/party/txt/
  _internal/party/table/
"""
import os
import sys
import zipfile

sys.stdout.reconfigure(encoding="utf-8")

SRC_DIR = os.path.join("dist", "champedge")

# アップデート時に上書きしてはいけないユーザーデータ
_EXCLUDE_EXACT = {
    "_internal/database/battle.db",
}
_EXCLUDE_PREFIXES = [
    "_internal/party/csv",
    "_internal/party/txt",
    "_internal/party/table",
]


def _should_exclude(arcname: str) -> bool:
    path = arcname.replace("\\", "/")
    if path in _EXCLUDE_EXACT:
        return True
    return any(path == p or path.startswith(p + "/") for p in _EXCLUDE_PREFIXES)


def make_zip(out_zip: str, full: bool):
    if not os.path.isdir(SRC_DIR):
        print(f"ERROR: {SRC_DIR} が見つかりません。先にビルドを実行してください。")
        raise SystemExit(1)

    total = 0
    with zipfile.ZipFile(out_zip, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
        for root, _, files in os.walk(SRC_DIR):
            for file in files:
                arcname = os.path.relpath(
                    os.path.join(root, file), SRC_DIR
                )
                if not full and _should_exclude(arcname.replace("\\", "/")):
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
