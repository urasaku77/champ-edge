import os
import sys

# exeとして起動した場合、作業ディレクトリをバンドルフォルダ(_internal/)に設定する
# PyInstaller 6.x では bundled files は sys._MEIPASS (_internal/) 以下に配置される
if getattr(sys, 'frozen', False):
    # exeと同じフォルダをCWDにする（画像・設定ファイルを_internal/の外に置くため）
    os.chdir(os.path.dirname(sys.executable))

import tkinter
from tkinter.ttk import Style

from component.app import MainApp
from component.stage import Stage
from pokedata.pokemon import set_mega_enabled, set_terastal_enabled
from recog.recog import get_recog_value

set_terastal_enabled(get_recog_value("terastal_enabled"))
set_mega_enabled(get_recog_value("mega_enabled"))

app = MainApp()
stage = Stage(app)

style = Style()
style.configure("leftimage.TButton", compound=tkinter.LEFT)

app.mainloop()
