# coding: utf-8
"""
全画面スクリーンショット撮影スクリプト
- サンプルデータが登録された状態でアプリを起動
- 対戦画面でポケモンを選択して基本情報・HOME情報を表示
- 各ポップアップ・サブ画面を順次キャプチャ
- image/readme/ に保存
"""
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

def grab_window(widget, path, extra_wait=0):
    """ウィジェットのスクリーンショットを保存する"""
    widget.update_idletasks()
    widget.update()
    if extra_wait:
        widget.after(extra_wait)
    x = widget.winfo_rootx()
    y = widget.winfo_rooty()
    w = widget.winfo_width()
    h = widget.winfo_height()
    ImageGrab.grab((x, y, x + w, y + h)).save(path)
    print(f"  saved: {path}")


# ---------- ステップ関数群 ----------

def step_load_parties(app, stage):
    """自分パーティをCSVから、相手パーティを手動でロード"""
    # 自分パーティ（setting.txt → 2-1_テスト.csv）
    stage.load_party(0)

    # 相手パーティを手動設定（HOME技データをロードして技名・使用率を表示）
    from pokedata.pokemon import Pokemon
    opp_names = ["ガブリアス", "ミミッキュ", "ドラパルト", "ドドゲザン", "アーマーガア", "カイリュー"]
    opp_party = []
    for name in opp_names:
        p = Pokemon.by_name(name)
        p.form_selected = True
        p.set_waza_from_home()
        opp_party.append(p)
    stage.set_party(1, opp_party)
    print("  両パーティロード完了")


def step_select_pokemons(app, stage):
    """自分側マスカーニャ・相手側ガブリアスを選択してダメージ計算発動、両者3体ずつ選出"""
    # 自分側: index 0 (マスカーニャ)
    app.party_frames[0].on_push_pokemon_button(0)
    # 相手側: index 0 (ガブリアス) - HOME情報も自動ロード
    app.party_frames[1].on_push_pokemon_button(0)
    # 両者の選出を先頭3体に設定
    stage.set_chosen(0, [0, 1, 2])
    stage.set_chosen(1, [0, 1, 2])
    print("  ポケモン選択・選出設定完了")


def step_shot_battle(app, stage):
    """メイン対戦画面をキャプチャ"""
    app.update_idletasks()
    app.update()
    time.sleep(0.5)
    grab_window(app, f"{OUT}\\menu-battle.png")


def step_shot_seikaku(app, stage):
    """性格選択ポップアップをキャプチャ"""
    from component.frames.common import SeikakuPopup
    popup = SeikakuPopup(app, lambda _: None)
    popup.geometry(f"+{app.winfo_x() + 200}+{app.winfo_y() + 200}")
    popup.update_idletasks()
    popup.update()
    time.sleep(0.3)
    grab_window(popup, f"{OUT}\\seikaku.png")
    popup.destroy()


def step_shot_speed(app, stage):
    """素早さ比較ポップアップをキャプチャ"""
    from component.parts.dialog import SpeedComparing
    pokemons = [
        app.active_poke_frames[0]._pokemon,
        app.active_poke_frames[1]._pokemon,
    ]
    if pokemons[0].no == -1 or pokemons[1].no == -1:
        print("  ポケモン未選択のためスキップ")
        return
    dialog = SpeedComparing()
    dialog.set_pokemon(pokemons)
    dialog.geometry(f"+{app.winfo_x() + 50}+{app.winfo_y() + 50}")
    dialog.update_idletasks()
    dialog.update()
    time.sleep(0.3)
    grab_window(dialog, f"{OUT}\\speed.png")
    dialog.destroy()


def step_shot_weight(app, stage):
    """重さ比較ポップアップをキャプチャ"""
    from component.parts.dialog import WeightComparing
    pokemons = [
        app.active_poke_frames[0]._pokemon,
        app.active_poke_frames[1]._pokemon,
    ]
    if pokemons[0].no == -1 or pokemons[1].no == -1:
        print("  ポケモン未選択のためスキップ")
        return
    dialog = WeightComparing()
    dialog.set_pokemon(pokemons)
    dialog.geometry(f"+{app.winfo_x() + 50}+{app.winfo_y() + 50}")
    dialog.update_idletasks()
    dialog.update()
    time.sleep(0.3)
    grab_window(dialog, f"{OUT}\\weight.png")
    dialog.destroy()


def step_shot_party(app, stage):
    """パーティ編集画面をキャプチャ"""
    from party.party import PartyEditor
    editor = PartyEditor(capture=None)
    editor.geometry(f"+{app.winfo_x()}+{app.winfo_y()}")
    editor.update_idletasks()
    editor.update()
    time.sleep(0.8)
    editor.update_idletasks()
    editor.update()
    grab_window(editor, f"{OUT}\\party.png")
    editor.destroy()


def step_shot_box(app, stage):
    """ボックス管理画面をキャプチャ"""
    from component.parts.dialog import BoxDialog
    dialog = BoxDialog()
    dialog.geometry(f"+{app.winfo_x()}+{app.winfo_y()}")
    dialog.update_idletasks()
    dialog.update()
    time.sleep(0.5)
    dialog.update_idletasks()
    dialog.update()
    grab_window(dialog, f"{OUT}\\box.png")
    dialog.destroy()


def step_shot_record(app, stage):
    """対戦履歴画面をキャプチャ"""
    from mypgl import record as mypgl_record
    dialog = mypgl_record.Record()
    dialog.open()
    dialog.update_idletasks()
    dialog.update()
    time.sleep(0.8)
    dialog.update_idletasks()
    dialog.update()
    grab_window(dialog, f"{OUT}\\record.png")
    dialog.destroy()


def step_shot_analytics(app, stage):
    """対戦分析画面をキャプチャ"""
    from mypgl import analytics as mypgl_analytics
    dialog = mypgl_analytics.Analytics()
    dialog.open()
    dialog.update_idletasks()
    dialog.update()
    time.sleep(0.8)
    dialog.update_idletasks()
    dialog.update()
    grab_window(dialog, f"{OUT}\\analysis.png")
    dialog.destroy()


def step_shot_capture_setting(app, stage):
    """キャプチャ設定ダイアログをキャプチャ"""
    from recog.recog import CaptureSetting
    dialog = CaptureSetting()
    dialog.geometry(f"+{app.winfo_x() + 100}+{app.winfo_y() + 100}")
    dialog.update_idletasks()
    dialog.update()
    time.sleep(0.3)
    grab_window(dialog, f"{OUT}\\setting_capture.png")
    dialog.destroy()


def step_shot_mode_setting(app, stage):
    """モード切替ダイアログをキャプチャ"""
    from recog.recog import ModeSetting
    dialog = ModeSetting()
    dialog.geometry(f"+{app.winfo_x() + 100}+{app.winfo_y() + 100}")
    dialog.update_idletasks()
    dialog.update()
    time.sleep(0.3)
    grab_window(dialog, f"{OUT}\\setting_mode.png")
    dialog.destroy()


def step_shot_double_mode(app, stage):
    """ダブルモードフレームを単独ウィンドウで表示してキャプチャ"""
    from component.frames.whole import DoubleFrame
    win = tkinter.Toplevel(app)
    win.title("ダブルモード")
    win.resizable(False, False)
    frame = DoubleFrame(win)
    frame.pack(padx=10, pady=10)
    win.geometry(f"+{app.winfo_x() + 100}+{app.winfo_y() + 100}")
    win.update_idletasks()
    win.update()
    time.sleep(0.3)
    grab_window(win, f"{OUT}\\double_mode.png")
    win.destroy()


# ---------- メインシーケンス ----------

STEP_DELAY = 600   # ms between steps

def run_all_steps(app, stage):
    steps = [
        ("パーティロード",      lambda: step_load_parties(app, stage)),
        ("ポケモン選択",        lambda: step_select_pokemons(app, stage)),
        ("対戦画面",            lambda: step_shot_battle(app, stage)),
        ("性格ポップアップ",    lambda: step_shot_seikaku(app, stage)),
        ("素早さ比較",          lambda: step_shot_speed(app, stage)),
        ("重さ比較",            lambda: step_shot_weight(app, stage)),
        ("パーティ編集",        lambda: step_shot_party(app, stage)),
        ("ボックス管理",        lambda: step_shot_box(app, stage)),
        ("対戦履歴",            lambda: step_shot_record(app, stage)),
        ("対戦分析",            lambda: step_shot_analytics(app, stage)),
        ("キャプチャ設定",      lambda: step_shot_capture_setting(app, stage)),
        ("モード切替",          lambda: step_shot_mode_setting(app, stage)),
        ("ダブルモード",        lambda: step_shot_double_mode(app, stage)),
    ]

    def execute(idx):
        if idx >= len(steps):
            print("\n全スクリーンショット完了！アプリを終了します")
            app.destroy()
            return
        name, fn = steps[idx]
        print(f"[{idx+1}/{len(steps)}] {name}")
        try:
            fn()
        except Exception as e:
            import traceback
            print(f"  エラー: {e}")
            traceback.print_exc()
        app.after(STEP_DELAY, lambda: execute(idx + 1))

    # 最初のステップを開始（アプリ起動後少し待つ）
    app.after(1500, lambda: execute(0))


app = MainApp()
# 自動アップデートチェック無効化（スクリーンショット中に邪魔なダイアログが出ないように）
# __init__ 内で after(1000, self._auto_check_update) が登録済みなので
# メソッドを差し替えてコールバック実行時に何もしないようにする
app._auto_check_update = lambda: None
app._auto_update_battle_data = lambda: None

stage = Stage(app)

style = Style()
style.configure("leftimage.TButton", compound=tkinter.LEFT)

run_all_steps(app, stage)

app.mainloop()
print("Done")
