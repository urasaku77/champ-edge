#!/usr/bin/env python3
"""get_all_damages の前処理（テラバースト/シェルアームズ/めざめるダンス等）を
calc.py で計算し、Dart 検証用フィクスチャへ追記する。
RAW（前処理前）の技属性を記録し、Dart 側の前処理が一致することを確認する。"""
import json
import os
import sys

HOME = os.environ.get("CHAMP_EDGE_HOME", os.path.expanduser("~/Documents/champ-edge"))
sys.path.insert(0, HOME)
os.chdir(HOME)

from pokedata.calc import DamageCalc  # noqa: E402
from pokedata.const import Weathers, Fields, Types  # noqa: E402
from pokedata.pokemon import Pokemon  # noqa: E402
from pokedata.stats import Stats  # noqa: E402
from pokedata.waza import Waza, WazaBase  # noqa: E402

FIX = os.path.join(os.path.dirname(os.path.abspath(__file__)), "damage_cases.json")


def snapshot(p):
    t = [x.name for x in p.type]
    return {
        "name": p.name, "level": p.lv, "stats": p.get_all_stats(),
        "boosts": [0, p.rank.A, p.rank.B, p.rank.C, p.rank.D, p.rank.S],
        "type1": t[0], "type2": t[1] if len(t) > 1 else "なし",
        "tera": p.battle_terastype.name, "ability": p.ability,
        "abilityValue": p.ability_value, "item": p.item,
        "status": p.ailment.name, "weight": p.weight, "wall": p.wall.name,
    }


def raw_move_snap(name):
    """前処理前の技属性。"""
    w = Waza.ByWazaBase(WazaBase(name))
    return {
        "name": w.name, "type": w.type.name, "category": w.category,
        "power": w.power, "isTouch": w.is_touch, "target": w.target,
        "priority": w.priority, "hasEffect": w.has_effect,
        "addPower": w.add_power, "powerHosei": w.power_hosei,
        "multiHit": w.multi_hit, "critical": w.critical,
    }


def build(name, tera=None):
    p = Pokemon.by_name(name)
    d = Stats(0)
    d.set_values(a=32, b=32, c=32, d=32, s=32, h=32)
    p.doryoku = d
    if tera is not None:
        p.battle_terastype = tera
    return p


def case(att, dfn, move_name, weather=Weathers.なし, field=Fields.なし):
    msnap = raw_move_snap(move_name)
    att.set_waza(0, move_name)
    results = DamageCalc.get_all_damages(att, dfn, weather, field)
    res = next((r for r in results if r.waza and r.waza.name == move_name), None)
    if res is None or not res.is_damage:
        return None
    return {
        "attacker": snapshot(att), "defender": snapshot(dfn), "move": msnap,
        "field": {"weather": weather.name, "field": field.name},
        "expected": {"damages": res.damages, "min": res.min_damage,
                     "max": res.max_damage, "percentage": res.max_damage_per},
    }


def main():
    new = []
    dfn = build("カビゴン")
    # テラバースト（テラス=でんき）→ タイプでんき・分類A/C比
    a1 = build("ハバタクカミ", tera=Types.でんき)
    c = case(a1, dfn, "テラバースト")
    if c:
        new.append(c); print(f"テラバースト: type={c['move']['type']}(raw) max={c['expected']['max']}")
    # シェルアームズ（物理/特殊の高い方）
    a2 = build("ガブリアス")
    c = case(a2, dfn, "シェルアームズ")
    if c:
        new.append(c); print(f"シェルアームズ: max={c['expected']['max']}")
    # めざめるダンス → 自分のタイプ1
    a3 = build("ガブリアス")
    c = case(a3, dfn, "めざめるダンス")
    if c:
        new.append(c); print(f"めざめるダンス: max={c['expected']['max']}")
    # さばきのつぶて → 自分のタイプ1
    a4 = build("ガブリアス")
    c = case(a4, dfn, "さばきのつぶて")
    if c:
        new.append(c); print(f"さばきのつぶて: max={c['expected']['max']}")

    if not new:
        print("no cases generated"); return
    with open(FIX, encoding="utf-8") as f:
        cases = json.load(f)
    cases += new
    with open(FIX, "w", encoding="utf-8") as f:
        json.dump(cases, f, ensure_ascii=False, indent=1)
    print(f"appended {len(new)} preprocess cases -> total {len(cases)}")


if __name__ == "__main__":
    main()
