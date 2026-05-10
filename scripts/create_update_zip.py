#!/usr/bin/env python3
"""配布用zipを作成する。

--full : 新規インストール用（全ファイル含む）
引数なし: アップデート用（ユーザーデータ除外）

zip構造:
  champedge.exe        ← exeファイル
  _internal/           ← Pythonライブラリ群（PyInstallerが生成）
  image/               ← ポケモン画像
  database/            ← DBファイル
  stats/               ← 統計データ
  recog/               ← テンプレート画像・設定
  party/               ← パーティ設定
  version.txt
"""
import os
import sys
import zipfile

sys.stdout.reconfigure(encoding="utf-8")

BUILD_DIR = os.path.join("dist", "champedge")

# スキャン対象のルート（ファイルまたはディレクトリ）
# 各ディレクトリ内の新規ファイルは自動的にzipに含まれる
# 含めたくないものは _UPDATE_EXCLUDE / _ALWAYS_EXCLUDE に追加する
_DATA_ROOTS = [
    "version.txt",
    "README.pdf",
    "image",
    "database",
    "stats",
    "recog",
    "party",
]

# フルインストール・アップデート共通で除外するパス
_ALWAYS_EXCLUDE = {
    "image/readme",
}

# アップデート時に除外するユーザーデータ（zip内パスのプレフィックス）
_UPDATE_EXCLUDE = {
    "database/battle.db",
    "stats",
    "party/csv",
    "party/txt",
    "party/table",
    "party/setting.txt",
    "recog/capture.json",
    "recog/setting.json",
    "image/outputImg",
}


def _excluded(arc: str, full: bool) -> bool:
    path = arc.replace("\\", "/")
    if any(path == e or path.startswith(e + "/") for e in _ALWAYS_EXCLUDE):
        return True
    if full:
        return False
    return any(path == e or path.startswith(e + "/") for e in _UPDATE_EXCLUDE)


def _add_entry(zf: zipfile.ZipFile, src: str, arc_base: str, full: bool) -> int:
    if os.path.isfile(src):
        if _excluded(arc_base, full):
            print(f"  スキップ: {arc_base}")
            return 0
        zf.write(src, arc_base)
        return 1
    if os.path.isdir(src):
        total = 0
        for root, _, files in os.walk(src):
            for file in files:
                abs_path = os.path.join(root, file)
                rel = os.path.relpath(abs_path, src).replace("\\", "/")
                arc = f"{arc_base}/{rel}"
                if _excluded(arc, full):
                    print(f"  スキップ: {arc}")
                    continue
                zf.write(abs_path, arc)
                total += 1
        return total
    print(f"  エラー: 見つかりません: {src}")
    raise FileNotFoundError(f"必要ファイルが見つかりません: {src}")


def make_zip(out_zip: str, full: bool):
    if not os.path.isdir(BUILD_DIR):
        print(f"ERROR: {BUILD_DIR} が見つかりません。先にビルドを実行してください。")
        raise SystemExit(1)

    total = 0
    with zipfile.ZipFile(out_zip, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
        # PyInstaller成果物（exe + _internal/）
        for root, _, files in os.walk(BUILD_DIR):
            for file in files:
                abs_path = os.path.join(root, file)
                arc = os.path.relpath(abs_path, BUILD_DIR).replace("\\", "/")
                zf.write(abs_path, arc)
                total += 1

        # 外部データファイル（exeと同階層）
        for root in _DATA_ROOTS:
            total += _add_entry(zf, root, root, full)

    size_mb = os.path.getsize(out_zip) / 1024 / 1024
    print(f"完了: {out_zip}  ({total} ファイル, {size_mb:.1f} MB)")


if __name__ == "__main__":
    full = "--full" in sys.argv
    out = os.path.join("dist", "champedge_full.zip" if full else "champedge_update.zip")
    make_zip(out, full)
