import tkinter

from PIL import Image, ImageTk

from pokedata.const import Types

blank_images = {}


def get_blank_image(size: tuple[int, int]):
    size_key: str = str(size[0]) + "x" + str(size[1])
    if size_key in blank_images:
        return blank_images[size_key]
    else:
        blank_image = tkinter.PhotoImage(width=size[0], height=size[1])
        blank_images[size_key] = blank_image
        return blank_image


def get_pokemon_icon(pid: str, size: tuple[int, int] = None):
    try:
        no, _, form = pid.partition("-")
        filename = f"{int(no):04d}-{form}.png"
        return _load_image("image/pokemon/" + filename, size)
    except Exception:
        return get_blank_image(size or (30, 30))


def get_type_icon(t: Types, size: tuple[int, int] = (20, 20)):
    return _load_image("image/typeicon/" + t.name + ".png", size)


def get_menu_icon(filename: str):
    return _load_image("image/menu/" + filename + ".png")


def _load_image(filepath: str, size: tuple[int, int] = None):
    img = Image.open(filepath)

    if size is not None:
        img_resize = img.resize(size)
        return ImageTk.PhotoImage(img_resize)
    else:
        return ImageTk.PhotoImage(img)
