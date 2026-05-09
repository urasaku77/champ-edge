import asyncio
import base64
import glob
import os
from pathlib import Path

import cv2
import numpy as np
import pyocr
from PIL import Image

from pokedata.exception import unrecognizable_pokemon
from pokedata.pokemon import Pokemon
from recog.coodinate import ConfCoordinate
from recog.obs import Obs
from recog.recog import get_recog_value


class Capture:
    def __init__(self):
        self.coords = ConfCoordinate()
        self.path_tesseract = get_recog_value("tesseract_path")

        # sensyutu(選出画面)→rate(レート確認)→battle(対戦開始待ち)
        self.phase = "sensyutu"
        self.banme = 0
        self.sensyutu_num = 3 if get_recog_value("rule") == 1 else 4
        self.is_panipani = get_recog_value("panipani_auto")
        self.party_recognized = False
        self.pokecrop_imgs: list[Image.Image] = []

    # Websocket接続
    def connect_websocket(self):
        try:
            self.loop = asyncio.get_event_loop()
            self.obs = Obs(
                self.loop, get_recog_value("port"), get_recog_value("password")
            )
            self.phase = "sensyutu"
            self.party_recognized = False
            return True
        except Exception:
            return False

    # Websocket切断
    def disconnect_websocket(self):
        try:
            self.loop.run_until_complete(self.obs.break_request())
            return True
        except Exception:
            return False

    # キャプチャ画像取得
    def get_screenshot(self):
        responseData = self.loop.run_until_complete(
            self.obs.get_screenshot(get_recog_value("source_name"))
        )
        screenshotBase64 = responseData.responseData["imageData"].split(",")[1]
        img_binary = base64.b64decode(screenshotBase64)
        jpg = np.frombuffer(img_binary, dtype=np.uint8)
        self.img = cv2.imdecode(jpg, cv2.IMREAD_COLOR)

    # キャプチャ画像保存
    def save_screenshot(self, coordName, savePath):
        coord = self.coords.dicCoord[coordName]
        img1 = self.img[coord.top : coord.bottom, coord.left : coord.right]
        cv2.imwrite(savePath, img1)

    # フェーズに応じて画像認識処理
    def image_recognize(self):
        match self.phase:
            case "sensyutu":
                return self.recognize_sensyutu()
            case "rate":
                return self.recognize_rate()
            case "battle":
                return self.recognize_battle()

    # 選出画面検知
    def chose_pokemon(self):
        return self.is_exist_image(
            "image/recogImg/situation/recogSensyutu.jpg", 0.8, "sensyutu"
        )

    # ①選出フェーズ: 相手パーティ解析＋選出番号取得、対戦準備中画面を検知したらrateへ移行
    def recognize_sensyutu(self):
        self.get_screenshot()
        if self.chose_pokemon():
            result = None
            if not self.party_recognized:
                oppo_tn = self.recognize_oppo_tn()
                party = self.recognize_oppo_party()
                self.party_recognized = True
                result = (party, oppo_tn)
            banme_list = [
                self.recognize_chosen_num(banme) for banme in range(self.sensyutu_num)
            ]
            if self.is_panipani and banme_list != [-1] * self.sensyutu_num:
                self.create_my_chosen_image(
                    banme_list, len(banme_list) - banme_list.count(-1)
                )
            return result if result is not None else banme_list
        else:
            if self.is_exist_image(
                "image/recogImg/situation/recogSensyutu.jpg", 0.55, "sensyutu_end"
            ):
                self.phase = "rate"
            return None

    # ②レートフェーズ: rate.jpgを検知してoporate1座標からOCRでレート取得、battleへ移行
    def recognize_rate(self):
        self.get_screenshot()
        if self.is_exist_image("image/recogImg/situation/rate.jpg", 0.8, "rate"):
            coord = self.coords.dicCoord["oporate1"]
            img = self.img[coord.top : coord.bottom, coord.left : coord.right]
            rate_str = self.ocr_full(img).strip()
            try:
                rate = int(rate_str)
                self.phase = "battle"
                return rate
            except ValueError:
                return None
        return None

    # ③バトルフェーズ: recogBattle.jpgをbattle座標から検知、タイマー起動トリガー
    def recognize_battle(self):
        self.get_screenshot()
        if self.is_exist_image(
            "image/recogImg/situation/recogBattle.jpg", 0.8, "battle"
        ):
            self.phase = "sensyutu"
            self.party_recognized = False
            return True
        return False

    # 選出取得（手動キャプチャ用）
    def recognize_chosen_capture(self):
        try:
            self.get_screenshot()
            oppo_tn = self.recognize_oppo_tn()
            party = self.recognize_oppo_party()
            return (party, oppo_tn)
        except Exception:
            return None

    # 相手パーティの解析
    def recognize_oppo_party(self):
        if self.is_panipani:
            self.save_screenshot("myPokemon", "image/outputImg/myPokemon.jpg")
            self.save_screenshot("opoPokemon", "image/outputImg/opoPokemon.jpg")
            self.set_my_party_img()
            self._save_pokecrop_base()

        pokemonImages = glob.glob("image/pokemon/*")
        coordsList = [
            "opoPoke1",
            "opoPoke2",
            "opoPoke3",
            "opoPoke4",
            "opoPoke5",
            "opoPoke6",
        ]
        pokemonlist: list[Pokemon] = [Pokemon()] * 6

        for coord in range(len(coordsList)):
            oppo = self.is_exist_image_max(pokemonImages, 0.45, coordsList[coord])
            if oppo != "":
                oppo_shaped = self.shape_poke_num(oppo)
                oppo_pokemon = Pokemon.by_pid(oppo_shaped, True)
                if oppo_pokemon.base_name in unrecognizable_pokemon:
                    oppo_pokemon.form_selected = False
                pokemonlist[coord] = oppo_pokemon
        return pokemonlist

    # 相手のTN解析
    def recognize_oppo_tn(self):
        coord = self.coords.dicCoord["opoTn"]
        img = self.img[coord.top : coord.bottom, coord.left : coord.right]
        tn = self.ocr_full(img)
        return tn.replace(" ", "")

    # OBS表示用の自分パーティ画像取得
    def set_my_party_img(self):
        coord = self.coords.dicCoord["mySensyutu"]
        self.myPartyImg = self.img[coord.top : coord.bottom, coord.left : coord.right]

    # 自分の選出番号を取得
    def recognize_chosen_num(self, banme):
        banme_num = banme + 1
        paths = [f"image\\recogImg\\sensyutu\\banme\\num{banme_num}.jpg"]
        alt = f"image\\recogImg\\sensyutu\\banme\\num{banme_num}a.jpg"
        if os.path.exists(alt):
            paths.append(alt)
        for num in range(6):
            for path in paths:
                if self.is_exist_image(path, 0.85, "banme" + str(num + 1)):
                    return num
        return -1

    # OBS表示用の自分選出画像作成
    def create_my_chosen_image(self, sensyutuPoke, count):
        if self.banme == count:
            return
        self.banme = count
        full_img = Image.fromarray(cv2.cvtColor(self.img, cv2.COLOR_BGR2RGB))
        c0 = self.coords.dicCoord["pokecrop1"]
        crop_w = c0.right - c0.left
        crop_h = c0.bottom - c0.top
        dst = Image.new("RGB", (crop_w * count, crop_h))
        selected = {num for num in sensyutuPoke if num != -1}
        i = 0
        for num in sensyutuPoke:
            if num == -1:
                dst.save("image/outputImg/outputSensyutu.jpg", quality=95)
                self._write_sensyutu_big(selected)
                return
            c = self.coords.dicCoord[f"pokecrop{num + 1}"]
            crop = full_img.crop((c.left, c.top, c.right, c.bottom))
            dst.paste(crop, (crop_w * i, 0))
            i += 1
        dst.save("image/outputImg/outputSensyutu.jpg", quality=95)
        self._write_sensyutu_big(selected)

    # pokecrop1~6をクロップして保存、全て30%透明のBig画像を作成
    def _save_pokecrop_base(self):
        full = Image.fromarray(cv2.cvtColor(self.img, cv2.COLOR_BGR2RGB)).convert(
            "RGBA"
        )
        self.pokecrop_imgs = [
            full.crop(
                (
                    self.coords.dicCoord[f"pokecrop{i}"].left,
                    self.coords.dicCoord[f"pokecrop{i}"].top,
                    self.coords.dicCoord[f"pokecrop{i}"].right,
                    self.coords.dicCoord[f"pokecrop{i}"].bottom,
                )
            )
            for i in range(1, 7)
        ]
        self._write_sensyutu_big(set())

    # selectedに含まれるインデックスを100%、それ以外を70%透明でBig画像を保存
    def _write_sensyutu_big(self, selected: set):
        if not self.pokecrop_imgs:
            return
        w = self.pokecrop_imgs[0].width
        h = self.pokecrop_imgs[0].height
        dst = Image.new("RGBA", (w * 6, h), (0, 0, 0, 0))
        for i, crop in enumerate(self.pokecrop_imgs):
            img = crop.copy()
            if i not in selected:
                r, g, b, _ = img.split()
                alpha = Image.new("L", img.size, int(255 * 0.70))
                img = Image.merge("RGBA", (r, g, b, alpha))
            dst.paste(img, (w * i, 0), img)
        # JPEGはアルファ非対応のため黒背景に合成して保存
        bg = Image.new("RGB", dst.size, (0, 0, 0))
        bg.paste(dst, mask=dst.split()[3])
        bg.save("image/outputImg/outputSensyutuBig.jpg", quality=95)

    # テンプレートマッチング(最大のみ)
    _clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))

    @staticmethod
    def _load_pokemon_template(image_path: str) -> np.ndarray | None:
        """アルファ付きPNGの透明部分を本体平均輝度で埋めてグレースケール化する。
        透明ピクセルをゼロ平均引き後に0にすることで、本体形状のみで相関を取れる。"""
        raw = cv2.imread(image_path, cv2.IMREAD_UNCHANGED)
        if raw is None:
            return None
        if raw.ndim == 3 and raw.shape[2] == 4:
            alpha = raw[:, :, 3]
            gray = cv2.cvtColor(raw[:, :, :3], cv2.COLOR_BGR2GRAY)
            body_mask = alpha >= 10
            if body_mask.any():
                body_mean = int(gray[body_mask].mean())
                gray[~body_mask] = body_mean
            return gray
        if raw.ndim == 3:
            return cv2.cvtColor(raw, cv2.COLOR_BGR2GRAY)
        return raw

    def is_exist_image_max(self, temp_imgge_name, accuracy, coord_name):
        coord = self.coords.dicCoord[coord_name]
        img1 = self.img[coord.top : coord.bottom, coord.left : coord.right]
        gray = cv2.cvtColor(img1, cv2.COLOR_BGR2GRAY)
        gray_clahe = self._clahe.apply(gray)
        max_val_list: list[float] = []
        for image in temp_imgge_name:
            try:
                temp = self._load_pokemon_template(image)
                if temp is None:
                    max_val_list.append(0.0)
                    continue
                temp = cv2.resize(temp, None, None, 1.06, 1.06)
                match = cv2.matchTemplate(gray, temp, cv2.TM_CCOEFF_NORMED)
                _, max_val, _, _ = cv2.minMaxLoc(match)
                temp_clahe = self._clahe.apply(temp)
                match_c = cv2.matchTemplate(
                    gray_clahe, temp_clahe, cv2.TM_CCOEFF_NORMED
                )
                _, max_val_c, _, _ = cv2.minMaxLoc(match_c)
                max_val_list.append(max(max_val, max_val_c))
            except Exception:
                max_val_list.append(0.0)

        if max_val_list and max(max_val_list) >= accuracy:
            return temp_imgge_name[max_val_list.index(max(max_val_list))]
        else:
            return ""

    # テンプレートマッチング
    def is_exist_image(self, temp_imgge_name, accuracy, coord_name):
        result = False
        coord = self.coords.dicCoord[coord_name]
        img1 = self.img[coord.top : coord.bottom, coord.left : coord.right]
        temp = cv2.imread(temp_imgge_name)
        if temp is None:
            print(temp_imgge_name + "が見つかりません")
            return False

        gray = cv2.cvtColor(img1, cv2.COLOR_BGR2GRAY)
        temp = cv2.cvtColor(temp, cv2.COLOR_BGR2GRAY)

        match = cv2.matchTemplate(gray, temp, cv2.TM_CCOEFF_NORMED)
        loc = np.where(match >= accuracy)
        for _pt in zip(*loc[::-1], strict=False):
            result = True
        return result

    # ポケモンの画像ファイル名からPIDを取得 (例: "image/pokemon/0003-11.png" → "3-11")
    def shape_poke_num(self, origin: str):
        try:
            stem = Path(origin).stem  # "0003-11"
            no, sep, form = stem.partition("-")
            return f"{int(no)}-{form}" if sep else f"{int(no)}-0"
        except Exception:
            return ""

    # 全体OCR
    def ocr_full(self, base_img):
        try:
            if self.path_tesseract not in os.environ["PATH"].split(os.pathsep):
                os.environ["PATH"] += os.pathsep + self.path_tesseract
            tools = pyocr.get_available_tools()
            tool = tools[0]
            img = cv2.cvtColor(base_img, cv2.COLOR_BGR2RGB)
            threshold_value = 85
            gray = img.copy()
            img[gray < threshold_value] = 0
            img[gray >= threshold_value] = 255
            img = Image.fromarray(img)
            txt = tool.image_to_string(img, lang="jpn")
            return txt
        except Exception as e:
            print(e)
            return ""
