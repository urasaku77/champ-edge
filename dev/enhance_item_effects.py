"""
fetch_item_effects.py で生成した CSV の効果テキストを
「日本語フレーバーテキストベース + 英語proseの数値を反映」に変換するスクリプト。

前提: dev/item_effects_check.csv が存在すること
出力: dev/item_effects_enhanced.csv
"""

import csv
import re
import sys

sys.stdout.reconfigure(encoding="utf-8")

INPUT_CSV = "dev/item_effects_check.csv"
OUTPUT_CSV = "dev/item_effects_enhanced.csv"


# ─────────────────────────────────────────────────────
# 英語proseから数値を抽出するヘルパー
# ─────────────────────────────────────────────────────

def extract_pct_increase(en: str) -> str | None:
    """X% increase / boosts by X% / increases by X% → '1.Xxx倍' """
    m = re.search(r"(?:increase[s]?|raise[s]?|boost[s]?)\b.+?by (\d+)%", en, re.I)
    if m:
        pct = int(m.group(1))
        val = 1 + pct / 100
        s = f"{val:.2f}".rstrip("0").rstrip(".")
        return f"{s}倍"
    m = re.search(r"(\d+(?:\.\d+)?)× ?(?:Defense|Special Defense|Attack|Speed|damage)", en, re.I)
    if m:
        return f"{m.group(1)}倍"
    m = re.search(r"to (\d+(?:\.\d+)?)×", en, re.I)
    if m:
        return f"{m.group(1)}倍"
    return None


def extract_damage_pct(en: str) -> str | None:
    """do X% more damage / X% extra damage / X% more damage → '1.Xxx倍' """
    m = re.search(r"(\d+)% (?:more|extra) damage", en, re.I)
    if m:
        pct = int(m.group(1))
        val = 1 + pct / 100
        s = f"{val:.2f}".rstrip("0").rstrip(".")
        return f"{s}倍"
    m = re.search(r"inflict[s]? (\d+)% extra damage", en, re.I)
    if m:
        pct = int(m.group(1))
        val = 1 + pct / 100
        s = f"{val:.2f}".rstrip("0").rstrip(".")
        return f"{s}倍"
    return None


def extract_fraction(en: str, context: str = "") -> str | None:
    """HP関連の分数を抽出（小数点を含む括弧表記をスキップ）"""
    # "restore 1/16" "loses 1/10" "at 1/2 max HP" など
    if context == "recover":
        m = re.search(r"restore[s]? (\d+/\d+)", en, re.I)
        if m:
            return m.group(1)
        m = re.search(r"recover[s]? (\d+/\d+)", en, re.I)
        if m:
            return m.group(1)
        # "1/16 (6.25%) holder's max HP"
        m = re.search(r"(\d+/\d+) \(\d+\.?\d*%\)", en)
        if m:
            return m.group(1)
    if context == "cost":
        m = re.search(r"lose[s]? (\d+/\d+)[^%]*HP", en, re.I)
        if m:
            return m.group(1)
    if context == "contact":
        m = re.search(r"deal[s]? (\d+/\d+)[^%]*(?:max )?HP", en, re.I)
        if m:
            return m.group(1)
        m = re.search(r"(\d+/\d+) of [a-z ]* max HP", en, re.I)
        if m:
            return m.group(1)
    return None


def extract_chance_pct(en: str) -> str | None:
    m = re.search(r"\((\d+(?:\.\d+)?)%\) chance", en, re.I)
    if m:
        return f"{m.group(1)}%"
    m = re.search(r"(\d+)% chance", en, re.I)
    if m:
        return f"{m.group(1)}%"
    return None


def extract_turns(en: str) -> str | None:
    m = re.search(r"lasts? (\d+) (?:rounds?|turns?)", en, re.I)
    if m:
        return f"{m.group(1)}ターン"
    return None


# ─────────────────────────────────────────────────────
# アイテム名ごとの固定変換テーブル
# キー: item_name_db, 値: (ja_pattern, replacement) のリスト
# ─────────────────────────────────────────────────────

ITEM_SPECIFIC: dict[str, list[tuple[str, str]]] = {
    "こだわりハチマキ":  [("攻撃はあがる", "攻撃が1.5倍になる")],
    "こだわりメガネ":   [("特攻はあがる", "特攻が1.5倍になる")],
    "こだわりスカーフ":  [("素早さはあがる", "素早さが1.5倍になる")],
    "ちからのハチマキ":  [("物理技の威力が少しあがる", "物理技の威力が1.1倍になる")],
    "ものしりメガネ":   [("特殊技の威力が少しあがる", "特殊技の威力が1.1倍になる")],
    "たつじんのおび":   [("技の威力が少しあがる", "技の威力が1.2倍になる")],
    "いのちのたま":     [("技の威力があがる", "技の威力が1.3倍になる"),
                        ("ＨＰが少し減って", "ＨＰが最大HPの1/10減って")],
    "たべのこし":       [("少しずつ回復する", "最大HPの1/16ずつ回復する")],
    "くろいヘドロ":     [("少しずつＨＰを回復", "最大HPの1/16ずつＨＰを回復"),
                        ("少しずつ回復", "最大HPの1/16ずつ回復")],
    "しんかのきせき":   [("防御と特防があがる", "防御と特防が1.5倍になる")],
    "とつげきチョッキ":  [("特防があがるが変化技をだせなくなる", "特防が1.5倍になるが変化技をだせなくなる")],
    "じゃくてんほけん":  [("攻撃と特攻がそれぞれぐーんとあがる", "攻撃と特攻がそれぞれ2段階あがる")],
    "ゴツゴツメット":   [("相手にもダメージを与える", "相手も最大HPの1/6のダメージを受ける")],
    "しめつけバンド":   [("ダメージが増える", "ダメージが2倍になる")],
    "おうじゃのしるし":  [("ひるませることがある", "10%の確率でひるませる")],
    "きあいのハチマキ":  [("耐えることがある", "10%の確率で耐えることができる")],
    "せんせいのツメ":   [("相手より先に行動できることがある", "18.75%の確率で相手より先に行動できる")],
    "メトロノーム":     [("威力があがる。やめると威力はもどる", "威力が1回ごとに10%ずつあがる（最大2倍）。やめると威力はもどる")],
    "こうかくレンズ":   [("技の命中率が少しあがる", "技の命中率が1.1倍になる")],
    "ひかりのこな":     [("技が命中しにくくなる", "技の命中率が11%下がる")],
    "ひかりのねんど":   [("いつもより長く続く", "8ターン続く（通常より長く）"),
                        ("長く続くようになる", "8ターン続くようになる")],
    "つめたいいわ":     [("いつもよりあられの", "8ターンあられの")],
    "さらさらいわ":     [("いつもよりすなあらしの", "8ターンすなあらしの")],
    "あついいわ":      [("いつもよりはれの", "8ターンはれの")],
    "しめったいわ":     [("いつもよりあめの", "8ターンあめの")],
    "グランドコート":   [("フィールドの効果が長く続く", "フィールドの効果が8ターン続く")],
    # タイプ強化アイテム（威力があがる → 1.2倍）
    "ぎんのこな":      [("タイプの技の威力があがる", "タイプの技の威力が1.2倍になる")],
    "くろいメガネ":    [("タイプの技の威力があがる", "タイプの技の威力が1.2倍になる")],
    "くろおび":        [("タイプの技の威力があがる", "タイプの技の威力が1.2倍になる")],
    "じしゃく":        [("タイプの技の威力があがる", "タイプの技の威力が1.2倍になる")],
    "しんぴのしずく":   [("タイプの技の威力があがる", "タイプの技の威力が1.2倍になる")],
    "するどいくちばし": [("タイプの技の威力があがる", "タイプの技の威力が1.2倍になる")],
    "どくバリ":        [("タイプの技の威力があがる", "タイプの技の威力が1.2倍になる")],
    "とけないこおり":   [("タイプの技の威力があがる", "タイプの技の威力が1.2倍になる")],
    "のろいのおふだ":   [("タイプの技の威力があがる", "タイプの技の威力が1.2倍になる")],
    "もくたん":        [("タイプの技の威力があがる", "タイプの技の威力が1.2倍になる")],
    "シルクのスカーフ":  [("タイプの技の威力があがる", "タイプの技の威力が1.2倍になる")],
    "かたいいし":      [("タイプの技の威力があがる", "タイプの技の威力が1.2倍になる")],
    "メタルコート":     [("タイプの技の威力があがる", "タイプの技の威力が1.2倍になる")],
    # フィラのみ系（HP1/8回復）
    "フィラのみ":      [("ＨＰを回復する", "ＨＰを最大HPの1/8回復する")],
    "ウイのみ":        [("ＨＰを回復する", "ＨＰを最大HPの1/8回復する")],
    "マゴのみ":        [("ＨＰを回復する", "ＨＰを最大HPの1/8回復する")],
    "バンジのみ":      [("ＨＰを回復する", "ＨＰを最大HPの1/8回復する")],
    "イアのみ":        [("ＨＰを回復する", "ＨＰを最大HPの1/8回復する")],
    # ピンチきのみ系（発動HP閾値）
    "チイラのみ":      [("ピンチのとき自分の攻撃があがる", "ＨＰが1/4以下のとき自分の攻撃が1段階あがる")],
    "カムラのみ":      [("ピンチのとき自分の素早さがあがる", "ＨＰが1/4以下のとき自分の素早さが1段階あがる")],
    "サンのみ":        [("ピンチのとき攻撃が急所に当たりやすくなる", "ＨＰが1/4以下のとき急所ランクが1段階あがる")],
    # でんきだま
    "でんきだま":      [("攻撃と特攻の威力があがる", "攻撃と特攻がそれぞれ2倍になる")],
}


def apply_numbers(ja: str, en: str, item_name: str) -> str:
    result = ja

    # アイテム固有の変換テーブルを先に適用
    for pat, rep in ITEM_SPECIFIC.get(item_name, []):
        result = re.sub(pat, rep, result)

    return result


def is_mega_stone(name: str) -> bool:
    return name.endswith("ナイト") or name.endswith("ナイトX") or name.endswith("ナイトY")


def main():
    with open(INPUT_CSV, encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))

    print(f"入力: {INPUT_CSV} ({len(rows)}件)")
    print(f"出力: {OUTPUT_CSV}")
    print("-" * 60)

    output_rows = []
    enhanced = 0
    unchanged = 0

    for row in rows:
        name = row["item_name_db"]
        source = row.get("source", "")
        effect_ja = row.get("effect_ja", "")
        effect_en = row.get("effect_en", "")

        if row["matched"] != "OK" or source not in ("prose_en", "flavor") or not effect_ja:
            output_rows.append({**row, "effect_enhanced": effect_ja})
            unchanged += 1
            continue

        enhanced_text = apply_numbers(effect_ja, effect_en, name)

        if enhanced_text != effect_ja:
            print(f"ENHANCED [{name}]")
            print(f"  before: {effect_ja}")
            print(f"  after : {enhanced_text}")
            enhanced += 1
        else:
            unchanged += 1

        output_rows.append({**row, "effect_enhanced": enhanced_text})

    fieldnames = [k for k in rows[0].keys() if k != "effect_enhanced"] + ["effect_enhanced"]
    with open(OUTPUT_CSV, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(output_rows)

    print("-" * 60)
    print(f"完了: 数値組み込み={enhanced}, 変更なし/スキップ={unchanged}")
    print(f"CSV出力: {OUTPUT_CSV}")


if __name__ == "__main__":
    main()
