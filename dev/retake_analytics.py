# coding: utf-8
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
    print("[1/1] 対戦分析")
    from mypgl import analytics as mypgl_analytics
    dialog = mypgl_analytics.Analytics()
    dialog.open()
    dialog.update_idletasks()
    dialog.update()
    time.sleep(1.0)
    dialog.update_idletasks()
    dialog.update()
    grab_window(dialog, f"{OUT}\\analysis.png")
    dialog.destroy()
    print("完了")
    app.destroy()


app.after(1500, run)
app.mainloop()
print("Done")
