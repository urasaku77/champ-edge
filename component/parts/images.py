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


def _form_candidates(no_int: int):
    import glob as _glob
    import os as _os
    return sorted(
        _glob.glob(f"image/pokemon/{no_int:04d}-*.png"),
        key=lambda p: int(_os.path.splitext(_os.path.basename(p))[0].partition("-")[2] or 0),
    )


def get_pokemon_icon(pid: str, size: tuple[int, int] = None):
    import os as _os
    try:
        no, _, form = pid.partition("-")
        no_int = int(no)
        exact_path = f"image/pokemon/{no_int:04d}-{form}.png"
        if _os.path.isfile(exact_path):
            return _load_image(exact_path, size)
        candidates = _form_candidates(no_int)
        if candidates:
            return _load_image(candidates[0], size)
    except Exception:
        pass
    return get_blank_image(size or (30, 30))


def resolve_pid_by_image(pid: str) -> str:
    """画像ファイルが存在しないフォームの場合、実際に画像があるフォームのpidを返す。"""
    import os as _os
    try:
        no, _, form = pid.partition("-")
        no_int = int(no)
        if _os.path.isfile(f"image/pokemon/{no_int:04d}-{form}.png"):
            return pid
        candidates = _form_candidates(no_int)
        if candidates:
            import os as _os2
            stem = _os2.path.splitext(_os2.path.basename(candidates[0]))[0]
            _, _, actual_form = stem.partition("-")
            return f"{no_int}-{actual_form}"
    except Exception:
        pass
    return pid


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
