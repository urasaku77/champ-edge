# coding: utf-8
"""対戦分析画面のスクリーンショットのみを撮影する"""
import os
import sys
import time

os.chdir(r"e:\champ-edge")
sys.path.insert(0, r"e:\champ-edge")

import tkinter

from PIL import ImageGrab

from mypgl import analytics as mypgl_analytics

OUT = r"e:\champ-edge\image\readme"

root = tkinter.Tk()
root.withdraw()

dialog = mypgl_analytics.Analytics(master=root)
dialog.open()

dialog.season_var.set("カスタム")
dialog._on_season_select("カスタム")
dialog.from_year_var.set(2026)
dialog.from_month_var.set(3)
dialog.from_date_var.set(1)
dialog.to_year_var.set(2026)
dialog.to_month_var.set(5)
dialog.to_date_var.set(12)
dialog.update_result()

dialog.update_idletasks()
dialog.update()
time.sleep(1.5)
dialog.update_idletasks()
dialog.update()

x = dialog.winfo_rootx()
y = dialog.winfo_rooty()
w = dialog.winfo_width()
h = dialog.winfo_height()
path = f"{OUT}\\analysis.png"
ImageGrab.grab((x, y, x + w, y + h)).save(path)
print(f"saved: {path} ({w}x{h})")

dialog.destroy()
root.destroy()
