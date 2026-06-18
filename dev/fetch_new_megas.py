# coding: utf-8
"""新メガシンカ情報をchamps.pokedb.tokyoから取得してDBに登録するスクリプト"""
import html
import json
import os
import re
import sqlite3
import urllib.request
from io import BytesIO

from PIL import Image

os.chdir(r"e:\champ-edge")

# 対象ポケモン (図鑑No) と、サイト側のメガフォーム番号 → DBフォーム番号 のマッピング
# サイトでは Mega は form_no=1 (XYがある場合は 2, 3) で表現される
# DBでは Mega X = 11, Mega Y = 12, シングルメガ = 11
TARGETS = [
    # (no, [(site_form_no, db_form_no)])
    (26,  [(2, 11), (3, 12)]),  # ライチュウ (X, Y)
    (254, [(1, 11)]),            # ジュカイン
    (257, [(1, 11)]),            # バシャーモ
    (260, [(1, 11)]),            # ラグラージ
    (303, [(1, 11)]),            # クチート
    (376, [(1, 11)]),            # メタグロス
    (398, [(1, 11)]),            # ムクホーク
    (545, [(1, 11)]),            # ペンドラー
    (560, [(1, 11)]),            # ズルズキン
    (604, [(1, 11)]),            # シビルドン
    (668, [(2, 11)]),            # カエンジシ (form 01 はメスフォーム)
    (687, [(1, 11)]),            # カラマネロ
    (689, [(1, 11)]),            # ガメノデス
    (691, [(1, 11)]),            # ドラミドロ
    (870, [(1, 11)]),            # タイレーツ
]

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"

def fetch_page(no: int) -> dict:
    """個別ページから x-data のJSONをパースして forms 辞書を返す"""
    url = f"https://champs.pokedb.tokyo/pokemon/show/{no:04d}-00?season=3&rule=0"
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as r:
        content = r.read().decode("utf-8")
    m = re.search(r'pokemon-basis"[\s\S]*?x-data="pokemonShowBasis\((.*?)\)"', content)
    if not m:
        raise RuntimeError(f"x-data not found in page for no={no}")
    raw = m.group(1)
    unescaped = html.unescape(raw)
    data = json.loads(unescaped)
    return data["forms"]


def download_image(no: int, site_form: int, db_form: int):
    """画像を取得し 100x100 PNG として保存"""
    url = f"https://s3-ap-northeast-1.amazonaws.com/pokedb.tokyo/champs/assets/pokemon/icons_128/pokemon-{no:04d}-{site_form:02d}.png"
    save_path = f"image/pokemon/{no:04d}-{db_form}.png"
    if os.path.exists(save_path):
        print(f"  画像は既存: {save_path}")
        return
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as r:
        img_bytes = r.read()
    img = Image.open(BytesIO(img_bytes)).convert("RGBA")
    img = img.resize((100, 100), Image.LANCZOS)
    img.save(save_path)
    print(f"  画像保存: {save_path}")


def main():
    conn = sqlite3.connect("database/pokemon.db")
    cur = conn.cursor()

    inserted = []
    for no, megas in TARGETS:
        print(f"\n=== No.{no} の個別ページ取得 ===")
        forms = fetch_page(no)
        # サイト上のフォームキー: "0026-02" 形式
        for site_form, db_form in megas:
            key = f"{no:04d}-{site_form:02d}"
            if key not in forms:
                print(f"  サイトに {key} が存在しません。スキップ")
                continue
            fdata = forms[key]
            name = fdata["display_name"].replace("Ｘ", "X").replace("Ｙ", "Y")
            types = [t["name"] for t in fdata.get("types", [])]
            type1 = types[0] if len(types) >= 1 else ""
            type2 = types[1] if len(types) >= 2 else ""
            abilities = [a["name"] for a in fdata.get("abilities", [])]
            ability1 = abilities[0] if len(abilities) >= 1 else ""
            ability2 = abilities[1] if len(abilities) >= 2 else ""
            ability3 = abilities[2] if len(abilities) >= 3 else ""
            stats = fdata.get("stats", {})
            H = stats.get("hp",        {}).get("base", 0)
            A = stats.get("attack",    {}).get("base", 0)
            B = stats.get("defense",   {}).get("base", 0)
            C = stats.get("sp_attack", {}).get("base", 0)
            D = stats.get("sp_defense",{}).get("base", 0)
            S = stats.get("speed",     {}).get("base", 0)
            weight = float(fdata.get("weight", 0))
            # base_name は通常フォーム(00)から
            base_name = forms[f"{no:04d}-00"]["display_name"]
            form_name = "メガ進化"

            print(f"  {key} → DB form={db_form}: {name} | {type1}/{type2} | {ability1} | "
                  f"H{H}A{A}B{B}C{C}D{D}S{S} | {weight}kg")

            # 既存チェック
            cur.execute("SELECT 1 FROM pokemon_data WHERE no=? AND form=?", (no, db_form))
            if cur.fetchone():
                print(f"    既に DB に存在 (no={no}, form={db_form})。スキップ")
            else:
                cur.execute(
                    "INSERT INTO pokemon_data (no, form, name, base_name, form_name, H, A, B, C, D, S, "
                    "type1, type2, ability1, ability2, ability3, weight) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (no, db_form, name, base_name, form_name, H, A, B, C, D, S,
                     type1, type2, ability1, ability2, ability3, weight),
                )
                inserted.append((no, db_form, name))
                print("    DB に INSERT 完了")

            # 画像取得
            download_image(no, site_form, db_form)

    conn.commit()
    conn.close()

    print(f"\n=== 完了: {len(inserted)} 件挿入 ===")
    for r in inserted:
        print(f"  {r}")


if __name__ == "__main__":
    main()
