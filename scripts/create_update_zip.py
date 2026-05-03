#!/usr/bin/env python3
"""アップデート配布用zipを作成する。

ユーザーデータ（対戦DB・パーティCSV・HOME統計・キャプチャ設定）は除外し、
既存インストール先に展開しても上書きされないようにする。
"""
import os
import zipfile

# アップデートzipから除外するパス（_internal/ 以下の相対パスで指定）
# battle.db のみ除外（対戦履歴はユーザーデータのため上書き不可）
EXCLUDE_PREFIXES: list[str] = []
EXCLUDE_EXACT = {
    "_internal/database/battle.db",
}

SRC_DIR = os.path.join("dist", "champedge")
OUT_ZIP = os.path.join("dist", "champedge_update.zip")


def should_exclude(arcname: str) -> bool:
    path = arcname.replace("\\", "/")
    if path in EXCLUDE_EXACT:
        return True
    return any(
        path == prefix or path.startswith(prefix + "/")
        for prefix in EXCLUDE_PREFIXES
    )


def main():
    if not os.path.isdir(SRC_DIR):
        print(f"ERROR: {SRC_DIR} が見つかりません。先に build.bat を実行してください。")
        raise SystemExit(1)

    total = 0
    with zipfile.ZipFile(OUT_ZIP, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
        for root, dirs, files in os.walk(SRC_DIR):
            rel_root = os.path.relpath(root, SRC_DIR).replace("\\", "/")

            # 除外ディレクトリへの再帰を防ぐ
            dirs[:] = [
                d for d in dirs
                if not should_exclude(
                    (rel_root + "/" + d).lstrip("./")
                )
            ]

            for file in files:
                arcname = os.path.relpath(
                    os.path.join(root, file), SRC_DIR
                )
                if should_exclude(arcname.replace("\\", "/")):
                    print(f"  スキップ: {arcname}")
                    continue
                zf.write(os.path.join(root, file), arcname)
                total += 1

    size_mb = os.path.getsize(OUT_ZIP) / 1024 / 1024
    print(f"完了: {OUT_ZIP}  ({total} ファイル, {size_mb:.1f} MB)")


if __name__ == "__main__":
    main()
