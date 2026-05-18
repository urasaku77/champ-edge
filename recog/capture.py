import asyncio
import base64
import glob
import json
import os
import random
import re
import threading
import time
import unicodedata
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "1"

import cv2
import numpy as np
import pygame
import pyocr
import pyocr.builders
from PIL import Image

from pokedata.exception import unrecognizable_pokemon
from pokedata.pokemon import Pokemon
from recog.coordinate import ConfCoordinate
from recog.obs import Obs
from recog.recog import get_recog_value, get_tesseract_path


class Capture:
    def __init__(self):
        self.coords = ConfCoordinate()
        self.path_tesseract = get_tesseract_path()

        # フェーズ遷移:
        #   sensyutu(選出画面) BGM①
        #     → rate(レート確認) BGM①→②(選出終了3秒後)
        #     → battle(対戦開始待ち) BGM②
        #     → in_battle(対戦中) BGM②
        #     → wait(勝敗確定後) BGM①
        self.phase = "sensyutu"
        self.banme = 0
        self.sensyutu_num = 3 if get_recog_value("rule") == 1 else 4
        self.is_panipani = get_recog_value("panipani_auto")
        self.party_recognized = False
        self.pokecrop_imgs: list[Image.Image] = []
        self.on_party_start_progress = None  # callback(total: int)
        self.on_party_progress = None  # callback(current: int, total: int)

        self._bgm_enabled: bool = False
        self._bgm_mode: str = "file"
        self._bgm1_folder: str = ""
        self._bgm2_folder: str = ""
        self._obs_audio_source1: str = ""
        self._obs_audio_source2: str = ""
        self._bgm_playing: str = ""
        self._sensyutu_end_disappeared_time: float | None = None
        self._load_bgm_config()
        try:
            pygame.mixer.init()
        except Exception:
            pass

    _AUDIO_EXTENSIONS = {".mp3", ".wav", ".ogg", ".flac", ".aac", ".m4a"}

    def _load_bgm_config(self):
        try:
            with open("recog/bgm.json", "r", encoding="utf-8") as f:
                data = json.load(f)
            self._bgm_enabled = data.get("bgm_enabled", False)
            self._bgm_mode = data.get("bgm_mode", "file")
            self._bgm1_folder = data.get("bgm1_folder", "")
            self._bgm2_folder = data.get("bgm2_folder", "")
            self._obs_audio_source1 = data.get("obs_audio_source1", "")
            self._obs_audio_source2 = data.get("obs_audio_source2", "")
        except Exception:
            pass

    def _pick_random_bgm(self, folder: str) -> str:
        try:
            if not folder or not os.path.isdir(folder):
                return ""
            files = [
                f
                for f in os.listdir(folder)
                if os.path.splitext(f)[1].lower() in self._AUDIO_EXTENSIONS
            ]
            return os.path.join(folder, random.choice(files)) if files else ""
        except Exception:
            return ""

    def _switch_obs_audio(self, bgm_num: int):
        source1 = self._obs_audio_source1
        source2 = self._obs_audio_source2
        try:
            if bgm_num == 1:
                if source1:
                    self.loop.run_until_complete(self.obs.set_input_mute(source1, False))
                if source2 and source2 != source1:
                    self.loop.run_until_complete(self.obs.set_input_mute(source2, True))
            else:
                if source1 and source1 != source2:
                    self.loop.run_until_complete(self.obs.set_input_mute(source1, True))
                if source2:
                    self.loop.run_until_complete(self.obs.set_input_mute(source2, False))
            self._bgm_playing = f"bgm{bgm_num}"
            print(f"[BGM/OBS] switched to bgm{bgm_num}")
        except Exception as e:
            print(f"[BGM/OBS] error: {e}")

    def _switch_bgm(self, bgm_num: int):
        if not self._bgm_enabled:
            return
        if self._bgm_mode == "obs":
            self._switch_obs_audio(bgm_num)
            return
        folder = self._bgm1_folder if bgm_num == 1 else self._bgm2_folder
        path = self._pick_random_bgm(folder)
        if not path:
            return
        try:
            pygame.mixer.music.load(path)
            pygame.mixer.music.play(-1)
            pygame.mixer.music.set_volume(0.7)
            self._bgm_playing = f"bgm{bgm_num}"
            print(f"[BGM] playing bgm{bgm_num}: {path}")
        except Exception as e:
            print(f"[BGM] error: {e}")

    def start_bgm1(self):
        self._switch_bgm(1)

    # Websocket接続
    def connect_websocket(self):
        try:
            self.loop = asyncio.get_event_loop()
            self.obs = Obs(
                self.loop, get_recog_value("port"), get_recog_value("password")
            )
            self.phase = "sensyutu"
            self.party_recognized = False
            self._sensyutu_end_disappeared_time = None
            self._load_bgm_config()
            return True
        except Exception:
            return False

    # Websocket切断
    def disconnect_websocket(self):
        try:
            if self._bgm_enabled:
                if self._bgm_mode == "obs":
                    for src in {self._obs_audio_source1, self._obs_audio_source2}:
                        if src:
                            try:
                                self.loop.run_until_complete(self.obs.set_input_mute(src, True))
                            except Exception:
                                pass
                else:
                    try:
                        pygame.mixer.music.stop()
                    except Exception:
                        pass
            self.loop.run_until_complete(self.obs.break_request())
            self._bgm_playing = ""
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

    def image_recognize(self):
        match self.phase:
            case "sensyutu":
                return self.recognize_sensyutu()
            case "rate":
                return self.recognize_rate()
            case "battle":
                return self.recognize_battle()
            case "in_battle":
                return self.recognize_in_battle()
            case "wait":
                return self.recognize_wait()

    def chose_pokemon(self):
        return self.is_exist_image(
            "image/recogImg/situation/recogSensyutu.jpg", 0.8, "sensyutu"
        )

    # ①sensyutu: 相手パーティ解析・選出番号取得 → 対戦準備中画面でrateへ
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

    # ②rate: OCRでレート取得 → レート確認またはbattle画像検知でbattleへ / 選出終了3秒後にBGM②へ切り替え
    def recognize_rate(self):
        self.get_screenshot()

        # sensyutu_end が消えてから5秒後にBGM②へ切り替え
        if self.is_exist_image(
            "image/recogImg/situation/recogSensyutu.jpg", 0.55, "sensyutu_end"
        ):
            self._sensyutu_end_disappeared_time = None
        else:
            if self._sensyutu_end_disappeared_time is None:
                self._sensyutu_end_disappeared_time = time.time()
            elif (
                self._bgm_playing != "bgm2"
                and time.time() - self._sensyutu_end_disappeared_time >= 3.0
            ):
                self._switch_bgm(2)

        coord = self.coords.dicCoord["oporate1"]
        img = self.img[coord.top : coord.bottom, coord.left : coord.right]
        try:
            pil = Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
            rate_str = self._manga_ocr(pil).strip()
        except Exception:
            try:
                # manga_ocrが使えない場合（コンパイル版など）はTesseractで数字を読む
                if self.path_tesseract not in os.environ["PATH"].split(os.pathsep):
                    os.environ["PATH"] += os.pathsep + self.path_tesseract
                tools = pyocr.get_available_tools()
                gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
                gray = cv2.resize(gray, None, fx=3, fy=3, interpolation=cv2.INTER_CUBIC)
                _, binary = cv2.threshold(
                    gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU
                )
                binary = cv2.bitwise_not(binary)
                padded = cv2.copyMakeBorder(
                    binary, 20, 20, 20, 20, cv2.BORDER_CONSTANT, value=255
                )
                builder = pyocr.builders.TextBuilder(tesseract_layout=7)
                rate_str = tools[0].image_to_string(
                    Image.fromarray(padded), lang="eng", builder=builder
                )
            except Exception:
                rate_str = ""
        # 全角数字・全角ピリオドを半角に変換してからレートを抽出
        rate_clean = unicodedata.normalize("NFKC", re.sub(r"\s+", "", rate_str))
        m = re.search(r"\d{3,5}(?:\.\d+)?", rate_clean)
        if m:
            self.phase = "battle"
            if self._bgm_playing != "bgm2":
                self._switch_bgm(2)
            return float(m.group())
        if self.is_exist_image(
            "image/recogImg/situation/recogBattle.jpg", 0.8, "battle"
        ):
            self.phase = "battle"
            if self._bgm_playing != "bgm2":
                self._switch_bgm(2)
        return None

    # ③battle: recogBattle.jpg検知でin_battleへ → タイマー起動トリガー
    def recognize_battle(self):
        self.get_screenshot()
        if self.is_exist_image(
            "image/recogImg/situation/recogBattle.jpg", 0.8, "battle"
        ):
            self.phase = "in_battle"
            self.party_recognized = False
            if self._bgm_playing != "bgm2":
                self._switch_bgm(2)
            return True
        return False

    # ④in_battle: win.jpg検知でwaitへ → BGM①へ切り替え
    def recognize_in_battle(self):
        self.get_screenshot()
        if self.is_exist_image("image/recogImg/situation/win.jpg", 0.7, "winleft"):
            self.phase = "wait"
            self._switch_bgm(1)
            return "winleft"
        if self.is_exist_image("image/recogImg/situation/win.jpg", 0.7, "winright"):
            self.phase = "wait"
            self._switch_bgm(1)
            return "winright"
        return None

    # ⑤wait: BGM①再生中、次の選出画面を待機
    def recognize_wait(self):
        return "wait"

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

        if self.on_party_start_progress:
            self.on_party_start_progress(6)

        # 初回バトル時のみディスクから読み込んでキャッシュ、以降はメモリから参照
        for img_path in pokemonImages:
            self._get_pokemon_template_pair(img_path)

        _completed = [0]
        _lock = threading.Lock()

        def recognize_one(coord_idx: int) -> Pokemon:
            oppo = self.is_exist_image_max(pokemonImages, 0.45, coordsList[coord_idx])
            if oppo == "":
                pokemon = Pokemon()
            else:
                oppo_shaped = self.shape_poke_num(oppo)
                pokemon = Pokemon.by_pid(oppo_shaped, True)
                if pokemon.base_name in unrecognizable_pokemon:
                    pokemon.form_selected = False
            with _lock:
                _completed[0] += 1
                if self.on_party_progress:
                    self.on_party_progress(_completed[0], 6)
            return pokemon

        with ThreadPoolExecutor(max_workers=6) as executor:
            pokemonlist = list(executor.map(recognize_one, range(6)))

        return pokemonlist

    # 相手のTN解析
    def recognize_oppo_tn(self):
        if not get_recog_value("tn_ocr_enabled"):
            return ""
        coord = self.coords.dicCoord["opoTn"]
        img = self.img[coord.top : coord.bottom, coord.left : coord.right]
        tn = self.ocr_tn(img)
        return tn.replace(" ", "").replace("\n", "")

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
        os.makedirs("image/outputImg", exist_ok=True)
        bg.save("image/outputImg/outputSensyutuBig.jpg", quality=95)

    # テンプレートマッチング(最大のみ)
    _clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    # リサイズ+CLAHE済みテンプレートのクラスレベルキャッシュ（バトル間で再利用）
    _pokemon_template_cache: dict[str, tuple[np.ndarray, np.ndarray] | None] = {}

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

    @classmethod
    def _get_pokemon_template_pair(
        cls, image_path: str
    ) -> tuple[np.ndarray, np.ndarray] | None:
        """リサイズ+CLAHE済みのテンプレートペアをキャッシュから返す。"""
        if image_path not in cls._pokemon_template_cache:
            raw = cls._load_pokemon_template(image_path)
            if raw is None:
                cls._pokemon_template_cache[image_path] = None
            else:
                resized = cv2.resize(raw, None, None, 1.06, 1.06)
                cls._pokemon_template_cache[image_path] = (
                    resized,
                    cls._clahe.apply(resized),
                )
        return cls._pokemon_template_cache[image_path]

    def is_exist_image_max(self, temp_imgge_name, accuracy, coord_name):
        coord = self.coords.dicCoord[coord_name]
        img1 = self.img[coord.top : coord.bottom, coord.left : coord.right]
        gray = cv2.cvtColor(img1, cv2.COLOR_BGR2GRAY)
        gray_clahe = self._clahe.apply(gray)
        max_val_list: list[float] = []
        for image in temp_imgge_name:
            try:
                pair = self._get_pokemon_template_pair(image)
                if pair is None:
                    max_val_list.append(0.0)
                    continue
                temp, temp_clahe = pair
                match = cv2.matchTemplate(gray, temp, cv2.TM_CCOEFF_NORMED)
                _, max_val, _, _ = cv2.minMaxLoc(match)
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

    @property
    def _manga_ocr(self):
        if not hasattr(self, "_mocr"):
            from manga_ocr import MangaOcr

            self._mocr = MangaOcr()
        return self._mocr

    _TRAINER_NAME = "トレーナー"

    @staticmethod
    def _is_korean(text: str) -> bool:
        return any("가" <= ch <= "힣" or "ᄀ" <= ch <= "ᇿ" for ch in text)

    @staticmethod
    def _is_trainer_name(text: str) -> bool:
        import difflib

        return difflib.SequenceMatcher(None, text, "トレーナー").ratio() >= 0.65

    # TN専用OCR: manga-ocrで認識 → 韓国語/トレーナー判定 → 英語フォールバック
    def ocr_tn(self, base_img):
        try:
            pil = Image.fromarray(cv2.cvtColor(base_img, cv2.COLOR_BGR2RGB))
            result = self._manga_ocr(pil).strip()
            if result and result not in ("．．．", "..."):
                if self._is_korean(result):
                    return "韓国"
                if self._is_trainer_name(result):
                    return self._TRAINER_NAME
                return result
        except Exception:
            pass
        # manga_ocrが使えない or 結果が空の場合は英語TN向けTesseractフォールバック
        try:
            if self.path_tesseract not in os.environ["PATH"].split(os.pathsep):
                os.environ["PATH"] += os.pathsep + self.path_tesseract
            tools = pyocr.get_available_tools()
            tool = tools[0]
            gray = cv2.cvtColor(base_img, cv2.COLOR_BGR2GRAY)
            gray = cv2.resize(gray, None, fx=3, fy=3, interpolation=cv2.INTER_CUBIC)
            _, binary = cv2.threshold(gray, 160, 255, cv2.THRESH_BINARY)
            binary = cv2.bitwise_not(binary)
            padded = cv2.copyMakeBorder(
                binary, 20, 20, 20, 20, cv2.BORDER_CONSTANT, value=255
            )
            builder = pyocr.builders.TextBuilder(tesseract_layout=7)
            return tool.image_to_string(
                Image.fromarray(padded), lang="eng", builder=builder
            ).strip()
        except Exception as e:
            print(e)
            return ""

    # 全体OCR
    def ocr_full(self, base_img):
        try:
            if self.path_tesseract not in os.environ["PATH"].split(os.pathsep):
                os.environ["PATH"] += os.pathsep + self.path_tesseract
            tools = pyocr.get_available_tools()
            tool = tools[0]
            gray = cv2.cvtColor(base_img, cv2.COLOR_BGR2GRAY)
            _, binary = cv2.threshold(gray, 85, 255, cv2.THRESH_BINARY)
            img = Image.fromarray(binary)
            txt = tool.image_to_string(img, lang="jpn")
            return txt
        except Exception as e:
            print(e)
            return ""
