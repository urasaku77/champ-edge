#!/usr/bin/env python3
"""旧 champ-edge の `pokedata.calc` を駆動し、Dart ダメージエンジンの
基準テストデータ（damage_cases.json）を生成する開発ツール。

設計方針:
- `DamageCalc.__get_damage` を直接呼び、技・ポケモンの「変化前の解決済み属性」を
  記録する。これにより Dart エンジンへ渡す入力と完全一致し、結果も一致する。
- 旧リポジトリのパスは環境変数 CHAMP_EDGE_HOME で上書き可能（既定 ~/Documents/champ-edge）。

使い方:
    python3 generate_damage_cases.py            # 既定 200 件を生成
    CHAMP_EDGE_HOME=/path python3 generate_damage_cases.py 300
"""

import json
import os
import random
import sys

HOME = os.environ.get(
    "CHAMP_EDGE_HOME", os.path.expanduser("~/Documents/champ-edge")
)
sys.path.insert(0, HOME)
os.chdir(HOME)  # loader が相対パスで CSV/DB を開くため

from pokedata.calc import DamageCalc, DamageCalcResult  # noqa: E402
from pokedata.const import Ailments, Fields, Types, Walls, Weathers  # noqa: E402
from pokedata.pokemon import Pokemon  # noqa: E402
from pokedata.stats import Stats, StatsKey  # noqa: E402
from pokedata.waza import Waza, WazaBase  # noqa: E402

# 攻撃側候補（多様なタイプ・種族値）
ATTACKERS = [
    "ガブリアス", "カイリュー", "ハバタクカミ", "テツノブジン", "ウーラオス(いちげき)",
    "リザードン", "ギャラドス", "サーフゴー", "セグレイブ",
    "イーユイ", "パオジアン", "ディンルー", "テツノカイナ",
]
DEFENDERS = [
    "カビゴン", "ヘイラッシャ", "ハッサム", "ドオー", "ラウドボーン",
    "ミミッキュ", "ハピナス", "バンギラス", "モロバレル", "アーマーガア",
]
# 物理/特殊の素直なダメージ技（タイプ多様、特殊効果の少ないもの）
MOVES = [
    "じしん", "れいとうビーム", "かえんほうしゃ", "10まんボルト", "なみのり",
    "シャドーボール", "ムーンフォース", "りゅうのはどう", "じゃれつく", "アイアンヘッド",
    "はたきおとす", "インファイト", "ストーンエッジ", "サイコキネシス", "エナジーボール",
    "だいもんじ", "ハイドロポンプ", "かみくだく", "ばかぢから", "ヘドロばくだん",
    "つるぎのまい",  # 変化技（ダメージ無し）も混ぜる
]
NATURES = [
    "いじっぱり", "ひかえめ", "ようき", "おくびょう", "わんぱく", "しんちょう",
    "まじめ", "ずぶとい", "おだやか",
]
ITEMS = [
    "なし", "こだわりハチマキ", "こだわりメガネ", "いのちのたま", "たつじんのおび",
    "とつげきチョッキ", "しんかのきせき",
]
WEATHERS = [Weathers.なし, Weathers.晴れ, Weathers.雨, Weathers.砂嵐, Weathers.雪]
FIELDS = [Fields.なし, Fields.エレキ, Fields.サイコ, Fields.グラス, Fields.ミスト]
AILMENTS = [Ailments.なし, Ailments.やけど]
WALLS = [Walls.なし, Walls.リフレクター, Walls.ひかりのかべ, Walls.オーロラベール]
TERAS = [
    Types.なし, Types.なし, Types.ノーマル, Types.ほのお, Types.みず, Types.でんき,
    Types.くさ, Types.エスパー, Types.はがね, Types.フェアリー, Types.ステラ,
]


def _ev(rng):
    """0-32 スケールの努力値（攻撃/特攻/防御/特防/素早に振る）。"""
    return rng.choice([0, 16, 32])


def build_pokemon(name, rng, *, is_attacker):
    p = Pokemon.by_name(name)
    p.seikaku = rng.choice(NATURES)
    # 努力値
    dory = Stats(0)
    dory.set_values(
        h=_ev(rng), a=_ev(rng), b=_ev(rng), c=_ev(rng), d=_ev(rng), s=_ev(rng)
    )
    p.doryoku = dory
    # ランク（-2〜+2 をたまに付与）
    rank = Stats(0)
    for k in [StatsKey.A, StatsKey.B, StatsKey.C, StatsKey.D, StatsKey.S]:
        if rng.random() < 0.25:
            rank[k] = rng.randint(-2, 2)
    p.rank = rank
    # 持ち物
    p.item = rng.choice(ITEMS)
    # テラス
    tera = rng.choice(TERAS)
    if tera != Types.なし:
        p.battle_terastype = tera
    # やけど（攻撃側のみ意味があるが両方に付けても可）
    if is_attacker:
        p.ailment = rng.choice(AILMENTS)
    return p


def snapshot(p):
    types = [t.name for t in p.type]
    return {
        "name": p.name,
        "level": p.lv,
        "stats": p.get_all_stats(),
        "boosts": [
            0, p.rank.A, p.rank.B, p.rank.C, p.rank.D, p.rank.S
        ],
        "type1": types[0],
        "type2": types[1] if len(types) > 1 else "なし",
        "tera": p.battle_terastype.name,
        "ability": p.ability,
        "abilityValue": p.ability_value,
        "item": p.item,
        "status": p.ailment.name,
        "weight": p.weight,
        "wall": p.wall.name,
    }


def move_snapshot(waza: Waza):
    return {
        "name": waza.name,
        "type": waza.type.name,
        "category": waza.category,
        "power": waza.power,
        "isTouch": waza.is_touch,
        "target": waza.target,
        "priority": waza.priority,
        "hasEffect": waza.has_effect,
        "addPower": waza.add_power,
        "powerHosei": waza.power_hosei,
        "multiHit": waza.multi_hit,
        "critical": waza.critical,
    }


def generate(n):
    rng = random.Random(20260609)
    cases = []
    attempts = 0
    while len(cases) < n and attempts < n * 10:
        attempts += 1
        a = build_pokemon(rng.choice(ATTACKERS), rng, is_attacker=True)
        d = build_pokemon(rng.choice(DEFENDERS), rng, is_attacker=False)
        d.wall = rng.choice(WALLS)
        move_name = rng.choice(MOVES)
        crit = rng.random() < 0.2
        weather = rng.choice(WEATHERS)
        field = rng.choice(FIELDS)

        try:
            wb = WazaBase(move_name)
            wb.critical = crit
            waza = Waza.ByWazaBase(wb)
        except (IndexError, KeyError):
            continue

        # 変化前の属性を記録
        move_attrs = move_snapshot(waza)
        a_snap = snapshot(a)
        d_snap = snapshot(d)

        # 変化技はダメージ無し
        if waza.category == "変化":
            cases.append({
                "attacker": a_snap,
                "defender": d_snap,
                "move": move_attrs,
                "field": {"weather": weather.name, "field": field.name},
                "expected": {
                    "damages": [],
                    "min": 0,
                    "max": 0,
                    "percentage": 0.0,
                },
            })
            continue

        damages = DamageCalc._DamageCalc__get_damage(
            attacker=a, defender=d, waza=waza,
            weather=weather, field=field, double_params=None,
        )
        if damages is None:
            continue
        res = DamageCalcResult(attacker=a, defender=d, waza=waza, damages=damages)
        cases.append({
            "attacker": a_snap,
            "defender": d_snap,
            "move": move_attrs,
            "field": {"weather": weather.name, "field": field.name},
            "expected": {
                "damages": damages,
                "min": res.min_damage,
                "max": res.max_damage,
                "percentage": res.max_damage_per,
            },
        })
    return cases


def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 200
    cases = generate(n)
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "damage_cases.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump(cases, f, ensure_ascii=False, indent=1)
    dmg = sum(1 for c in cases if c["expected"]["damages"])
    print(f"generated {len(cases)} cases ({dmg} damaging) -> {out}")


if __name__ == "__main__":
    main()
