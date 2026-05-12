# coding: utf-8
import os, sys
os.chdir(r"e:\champ-edge")
sys.path.insert(0, r"e:\champ-edge")

import tkinter
from PIL import ImageGrab

root = tkinter.Tk()
root.withdraw()


def grab(widget, path):
    widget.update_idletasks()
    x = widget.winfo_rootx()
    y = widget.winfo_rooty()
    w = widget.winfo_width()
    h = widget.winfo_height()
    ImageGrab.grab((x, y, x + w, y + h)).save(path)
    print(f"saved: {path}")


def step1_seikaku():
    from component.frames.common import SeikakuPopup
    popup = SeikakuPopup(root, lambda _: None)
    popup.geometry("+200+200")

    def shot():
        grab(popup, r"e:\champ-edge\image\readme\seikaku.png")
        popup.destroy()
        root.after(300, step2_party)

    popup.after(600, shot)


def step2_party():
    from party.party import PartyEditor
    editor = PartyEditor()
    editor.geometry("+100+100")

    def shot():
        grab(editor, r"e:\champ-edge\image\readme\party.png")
        editor.destroy()
        root.after(100, root.quit)

    editor.after(800, shot)


root.after(300, step1_seikaku)
root.mainloop()
print("Done")
