"""
PokeAPI の GitHub CSV データからアイテム効果を取得してCSVに出力するスクリプト。
DB登録前の確認用。

方法:
  PokeAPI の生CSV（GitHub）を一括ダウンロードし、日本語名でマッチング。
  個別APIコールは不要なので高速。

出力: dev/item_effects_check.csv
  - item_id, item_name_db, item_name_api, matched, effect
"""

import csv
import io
import sqlite3
import sys
import urllib.request

sys.stdout.reconfigure(encoding="utf-8")

GITHUB_RAW = "https://raw.githubusercontent.com/PokeAPI/pokeapi/master/data/v2/csv"
OUTPUT_CSV = "dev/item_effects_check.csv"

# PokeAPI 言語ID
# 1=ja, 9=en, 11=ja-Hrkt
JA_LANG_IDS = {"1", "11"}
EN_LANG_ID = "9"

# バージョングループID優先順（新しいものほど前）
PREFERRED_VERSION_GROUP_IDS = ["25", "20", "17", "15", "14"]

# メガストーン判定（効果テキストはフレーバーテキストのままでよい）
def is_mega_stone(name: str) -> bool:
    return name.endswith("ナイト") or name.endswith("ナイトX") or name.endswith("ナイトY")


def fetch_csv(url: str) -> list[dict]:
    print(f"  ダウンロード: {url}")
    req = urllib.request.Request(url, headers={"User-Agent": "champ-edge-dev/1.0"})
    with urllib.request.urlopen(req, timeout=30) as res:
        text = res.read().decode("utf-8")
    reader = csv.DictReader(io.StringIO(text))
    return list(reader)


def build_ja_name_map(item_names: list[dict]) -> dict[str, str]:
    """pokeapi_item_id -> 日本語名 のマップを構築。ja-Hrkt(11)を優先。"""
    result: dict[str, str] = {}
    for row in item_names:
        if row["local_language_id"] not in JA_LANG_IDS:
            continue
        iid = row["item_id"]
        name = row["name"]
        # 11(ja-Hrkt) があれば上書きして優先
        if iid not in result or row["local_language_id"] == "11":
            result[iid] = name
    return result


def build_flavor_map(flavor_rows: list[dict]) -> dict[str, str]:
    """pokeapi_item_id -> 日本語効果テキスト のマップを構築。新バージョン優先。"""
    # {item_id: {version_group_id: text}}
    tmp: dict[str, dict[str, str]] = {}
    for row in flavor_rows:
        if row["language_id"] not in JA_LANG_IDS:
            continue
        iid = row["item_id"]
        vgid = row["version_group_id"]
        text = row["flavor_text"].replace("\n", "").replace("­", "").replace("　", "")
        tmp.setdefault(iid, {})[vgid] = text

    result: dict[str, str] = {}
    for iid, vg_map in tmp.items():
        for vgid in PREFERRED_VERSION_GROUP_IDS:
            if vgid in vg_map:
                result[iid] = vg_map[vgid]
                break
        if iid not in result:
            # 優先バージョンになければ最後のキーを使う
            result[iid] = list(vg_map.values())[-1]
    return result


def build_prose_map(prose_rows: list[dict]) -> tuple[dict[str, str], dict[str, str]]:
    """
    item_prose.csv から pokeapi_id -> (日本語short_effect, 英語short_effect) のマップを構築。
    日本語が存在しない場合は英語にフォールバック。
    """
    ja_map: dict[str, str] = {}
    en_map: dict[str, str] = {}
    for row in prose_rows:
        iid = row["item_id"]
        lang = row["local_language_id"]
        text = row.get("short_effect", "").replace("\n", "").replace("  ", " ").strip()
        if not text:
            text = row.get("effect", "").replace("\n", "").replace("  ", " ").strip()
        if lang in JA_LANG_IDS and text:
            if iid not in ja_map or lang == "11":
                ja_map[iid] = text
        elif lang == EN_LANG_ID and text:
            en_map[iid] = text
    return ja_map, en_map


def main():
    # --- DB からアイテム一覧取得 ---
    conn = sqlite3.connect("database/pokemon.db")
    cur = conn.cursor()
    cur.execute("SELECT item_id, item_name FROM item_data ORDER BY item_id")
    db_items = cur.fetchall()
    conn.close()
    print(f"DBアイテム数: {len(db_items)}")

    # --- PokeAPI CSV を一括取得 ---
    print("PokeAPI CSV をダウンロード中...")
    item_names_rows = fetch_csv(f"{GITHUB_RAW}/item_names.csv")
    flavor_rows = fetch_csv(f"{GITHUB_RAW}/item_flavor_text.csv")
    prose_rows = fetch_csv(f"{GITHUB_RAW}/item_prose.csv")

    # --- マッピング構築 ---
    api_id_to_ja: dict[str, str] = build_ja_name_map(item_names_rows)
    api_id_to_flavor: dict[str, str] = build_flavor_map(flavor_rows)
    api_id_to_prose_ja, api_id_to_prose_en = build_prose_map(prose_rows)
    ja_to_api_id: dict[str, str] = {v: k for k, v in api_id_to_ja.items()}

    print(f"PokeAPI アイテム総数: {len(api_id_to_ja)}")
    ja_prose_count = len(api_id_to_prose_ja)
    en_prose_count = len(api_id_to_prose_en)
    print(f"prose日本語: {ja_prose_count}件 / 英語: {en_prose_count}件")
    print("-" * 60)

    rows = []
    matched = 0
    unmatched = 0

    for item_id, item_name_db in db_items:
        api_id = ja_to_api_id.get(item_name_db)
        if api_id:
            flavor_ja = api_id_to_flavor.get(api_id, "")
            if is_mega_stone(item_name_db):
                effect = flavor_ja
                effect_en = ""
                source = "flavor"
            else:
                if api_id in api_id_to_prose_ja:
                    effect = api_id_to_prose_ja[api_id]
                    effect_en = api_id_to_prose_en.get(api_id, "")
                    source = "prose_ja"
                elif api_id in api_id_to_prose_en:
                    effect = flavor_ja   # 日本語フレーバーを effect に保持
                    effect_en = api_id_to_prose_en[api_id]
                    source = "prose_en"
                else:
                    effect = flavor_ja
                    effect_en = ""
                    source = "flavor"
            status = "OK"
            matched += 1
            print(f"OK[{source:8}] id={item_id} {item_name_db!r} | ja={effect[:25]!r} | en={effect_en[:25]!r}")
        else:
            effect = ""
            effect_en = ""
            status = "NOT_FOUND"
            source = ""
            unmatched += 1
            print(f"MISS id={item_id} {item_name_db!r}")

        rows.append({
            "item_id": item_id,
            "item_name_db": item_name_db,
            "api_id": api_id or "",
            "matched": status,
            "source": source,
            "effect_ja": effect,
            "effect_en": effect_en,
        })

    with open(OUTPUT_CSV, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(
            f, fieldnames=["item_id", "item_name_db", "api_id", "matched", "source", "effect_ja", "effect_en"]
        )
        writer.writeheader()
        writer.writerows(rows)

    print("-" * 60)
    print(f"完了: マッチ={matched}, 未マッチ={unmatched}")
    print(f"CSV出力: {OUTPUT_CSV}")


if __name__ == "__main__":
    main()
