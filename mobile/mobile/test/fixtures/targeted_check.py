#!/usr/bin/env python3
"""砂嵐×岩(特防1.5倍) / 雪×氷(防御1.5倍) を calc.py で直接確認し、
Dart 検証用フィクスチャ(damage_cases.json)へ追記する。"""
import json
import os
import sys

HOME = os.environ.get("CHAMP_EDGE_HOME", os.path.expanduser("~/Documents/champ-edge"))
sys.path.insert(0, HOME)
os.chdir(HOME)

from pokedata.calc import DamageCalc, DamageCalcResult  # noqa: E402
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


def move_snap(w):
    return {
        "name": w.name, "type": w.type.name, "category": w.category,
        "power": w.power, "isTouch": w.is_touch, "target": w.target,
        "priority": w.priority, "hasEffect": w.has_effect,
        "addPower": w.add_power, "powerHosei": w.power_hosei,
        "multiHit": w.multi_hit, "critical": w.critical,
    }


def build(name, ability=None, item="なし"):
    p = Pokemon.by_name(name)
    d = Stats(0)
    d.set_values(a=32, b=32, c=32, d=32, s=32, h=32)  # 適当な実数値で固定
    p.doryoku = d
    if ability:
        p.ability = ability
    p.item = item
    return p


def case(att, dfn, move_name, weather, field=Fields.なし):
    wb = WazaBase(move_name)
    waza = Waza.ByWazaBase(wb)
    msnap = move_snap(waza)
    a_snap, d_snap = snapshot(att), snapshot(dfn)
    # 防御力（補正確認用）を取り出す
    dp = DamageCalc._DamageCalc__get_defence_power(
        attacker=att, defender=dfn, waza=waza, weather=weather,
        field=field, double_params=None)
    damages = DamageCalc._DamageCalc__get_damage(
        attacker=att, defender=dfn, waza=waza, weather=weather,
        field=field, double_params=None)
    res = DamageCalcResult(attacker=att, defender=dfn, waza=waza, damages=damages)
    return {
        "attacker": a_snap, "defender": d_snap, "move": msnap,
        "field": {"weather": weather.name, "field": field.name},
        "expected": {"damages": damages, "min": res.min_damage,
                     "max": res.max_damage, "percentage": res.max_damage_per},
    }, dp


def main():
    new = []
    # --- 砂嵐 × 岩(バンギラス) に特殊技。砂嵐で特防1.5倍 → ダメージ減 ---
    att_s = build("ハバタクカミ", item="なし")
    dfn_rock = build("バンギラス")  # いわ/あく → 砂嵐で特防1.5倍
    c_no, dp_no = case(att_s, dfn_rock, "シャドーボール", Weathers.なし)
    c_ss, dp_ss = case(att_s, dfn_rock, "シャドーボール", Weathers.砂嵐)
    print(f"[砂嵐×岩 特防] 防御力 なし={dp_no} 砂嵐={dp_ss} (比 {dp_ss/dp_no:.3f}) "
          f"→ 期待1.5倍, ダメージ max なし={c_no['expected']['max']} "
          f"砂嵐={c_ss['expected']['max']}")
    new += [c_no, c_ss]

    # --- 雪 × 氷(ラプラス) に物理技。雪で防御1.5倍 → ダメージ減 ---
    att_p = build("ガブリアス")
    dfn_ice = build("ラプラス")  # みず/こおり → 雪で防御1.5倍
    c2_no, dp2_no = case(att_p, dfn_ice, "じしん", Weathers.なし)
    c2_sn, dp2_sn = case(att_p, dfn_ice, "じしん", Weathers.雪)
    print(f"[雪×氷 防御] 防御力 なし={dp2_no} 雪={dp2_sn} (比 {dp2_sn/dp2_no:.3f}) "
          f"→ 期待1.5倍, ダメージ max なし={c2_no['expected']['max']} "
          f"雪={c2_sn['expected']['max']}")
    new += [c2_no, c2_sn]

    # 既存フィクスチャへ追記
    with open(FIX, encoding="utf-8") as f:
        cases = json.load(f)
    cases += new
    with open(FIX, "w", encoding="utf-8") as f:
        json.dump(cases, f, ensure_ascii=False, indent=1)
    print(f"appended {len(new)} targeted cases -> total {len(cases)}")


if __name__ == "__main__":
    main()
