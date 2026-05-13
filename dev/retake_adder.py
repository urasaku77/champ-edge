# coding: utf-8
"""加算ツールウィンドウのスクリーンショット"""
import os
import sys
import time

os.chdir(r"e:\champ-edge")
sys.path.insert(0, r"e:\champ-edge")

import tkinter
from tkinter.ttk import Style

from PIL import ImageGrab

from component.app import MainApp
from component.stage import Stage
from pokedata.pokemon import set_mega_enabled, set_terastal_enabled
from recog.recog import get_recog_value

set_terastal_enabled(get_recog_value("terastal_enabled"))
set_mega_enabled(get_recog_value("mega_enabled"))

OUT = r"e:\champ-edge\image\readme"


def grab_window(widget, path):
    widget.update_idletasks()
    widget.update()
    x = widget.winfo_rootx()
    y = widget.winfo_rooty()
    w = widget.winfo_width()
    h = widget.winfo_height()
    ImageGrab.grab((x, y, x + w, y + h)).save(path)
    print(f"  saved: {path}")


app = MainApp()
app._auto_check_update = lambda: None
app._auto_update_battle_data = lambda: None
stage = Stage(app)
style = Style()
style.configure("leftimage.TButton", compound=tkinter.LEFT)


def run():
    # パーティロード
    stage.load_party(0)
    from pokedata.pokemon import Pokemon
    opp_names = ["ガブリアス", "ミミッキュ", "ドラパルト", "ドドゲザン", "アーマーガア", "カイリュー"]
    opp_party = []
    for name in opp_names:
        p = Pokemon.by_name(name)
        p.form_selected = True
        opp_party.append(p)
    stage.set_party(1, opp_party)

    # ポケモン選択（ダメージ計算を走らせる）
    app.party_frames[0].on_push_pokemon_button(0)
    app.party_frames[1].on_push_pokemon_button(0)
    app.update_idletasks()
    app.update()
    time.sleep(0.5)

    # WazaDamageListFrame[0] (自分側) から現在の技名と計算結果を取得して加算ツールを開く
    waza_frame = app._waza_damage_frames[0]
    items = []
    for i, cbx in enumerate(waza_frame._cbx_list):
        name = cbx.get().strip()
        if name:
            result = (
                waza_frame._current_results[i]
                if i < len(waza_frame._current_results)
                else None
            )
            items.append((name, result))

    print(f"  技数: {len(items)}")
    if not items:
        print("  技が取得できません、スキップ")
        app.destroy()
        return

    from component.frames.common import MultiWazaDamageWindow
    win = MultiWazaDamageWindow(app, items)
    win.geometry(f"+{app.winfo_x() + 200}+{app.winfo_y() + 300}")
    win.update_idletasks()
    win.update()
    time.sleep(0.3)

    # 数技ボタンを押してダメージを累積表示させる
    if len(items) >= 1:
        win._press_move(0)
    if len(items) >= 1:
        win._press_move(0)
    if len(items) >= 3:
        win._press_move(2)
    # 回復ボタンも一つ押す
    win._press_heal("オボンのみ", __import__("fractions").Fraction(1, 4))

    win.update_idletasks()
    win.update()
    time.sleep(0.3)

    grab_window(win, f"{OUT}\\adder.png")
    win.destroy()
    print("完了")
    app.destroy()


app.after(1500, run)
app.mainloop()
print("Done")
