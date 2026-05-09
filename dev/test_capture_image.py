"""
OBS経由でキャプチャされた場合と同等の処理を、
デスクトップのIMG_7612.JPGを使って再現するテストスクリプト
"""
import glob as _glob
import os
import sys

os.chdir(r"e:\champ-edge")
sys.path.insert(0, r"e:\champ-edge")

import cv2
import numpy as np

from recog.coodinate import ConfCoordinate
from recog.recog import get_recog_value

IMAGE_PATH = r"C:\Users\okada\Desktop\IMG_7612.JPG"


class TestCapture:
    """OBS接続なしで静止画ファイルから認識を行うテスト用クラス"""

    def __init__(self, image_path: str):
        self.coords = ConfCoordinate()
        self.path_tesseract = get_recog_value("tesseract_path")
        self.phase = "sensyutu"
        self.banme = 0
        self.sensyutu_num = 3 if get_recog_value("rule") == 1 else 4
        self.is_panipani = True
        self.party_recognized = False

        self.img = cv2.imread(image_path)
        if self.img is None:
            raise FileNotFoundError(f"画像を読み込めません: {image_path}")

        os.makedirs("image/outputImg", exist_ok=True)

        h, w = self.img.shape[:2]
        print(f"[画像情報] サイズ: {w}x{h}px")

    def is_exist_image(self, temp_image_name, accuracy, coord_name):
        coord = self.coords.dicCoord[coord_name]
        img1 = self.img[coord.top : coord.bottom, coord.left : coord.right]
        temp = cv2.imread(temp_image_name)
        if temp is None:
            print(f"  テンプレ未発見: {temp_image_name}")
            return False

        gray = cv2.cvtColor(img1, cv2.COLOR_BGR2GRAY)
        temp_gray = cv2.cvtColor(temp, cv2.COLOR_BGR2GRAY)

        try:
            match = cv2.matchTemplate(gray, temp_gray, cv2.TM_CCOEFF_NORMED)
            _, max_val, _, _ = cv2.minMaxLoc(match)
            print(
                f"  テンプレマッチ [{coord_name}] {os.path.basename(temp_image_name)}: score={max_val:.3f} (閾値={accuracy})"
            )
            loc = np.where(match >= accuracy)
            return any(True for _ in zip(*loc[::-1], strict=False))
        except Exception as e:
            print(f"  マッチングエラー: {e}")
            return False

    _clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))

    def is_exist_image_max(self, temp_images, accuracy, coord_name):
        coord = self.coords.dicCoord[coord_name]
        img1 = self.img[coord.top : coord.bottom, coord.left : coord.right]
        gray = cv2.cvtColor(img1, cv2.COLOR_BGR2GRAY)
        gray_clahe = self._clahe.apply(gray)

        max_val_list = []
        for image in temp_images:
            try:
                temp = cv2.imread(image, cv2.IMREAD_GRAYSCALE)
                temp = cv2.resize(temp, None, None, 1.06, 1.06)
                match = cv2.matchTemplate(gray, temp, cv2.TM_CCOEFF_NORMED)
                _, max_val, _, _ = cv2.minMaxLoc(match)
                temp_clahe = self._clahe.apply(temp)
                match_c = cv2.matchTemplate(gray_clahe, temp_clahe, cv2.TM_CCOEFF_NORMED)
                _, max_val_c, _, _ = cv2.minMaxLoc(match_c)
                max_val_list.append(max(max_val, max_val_c))
            except Exception:
                max_val_list.append(0.0)

        if max_val_list and max(max_val_list) >= accuracy:
            best_idx = max_val_list.index(max(max_val_list))
            return temp_images[best_idx]
        return ""

    def save_screenshot(self, coord_name, save_path):
        coord = self.coords.dicCoord[coord_name]
        img1 = self.img[coord.top : coord.bottom, coord.left : coord.right]
        cv2.imwrite(save_path, img1)
        print(f"  保存: {save_path}")

    def set_my_party_img(self):
        # pokecrop方式では不要だがインタフェース互換のため残す
        pass

    def create_my_chosen_image(self, sensyutu_poke, count):
        from PIL import Image as PILImage

        # pokecrop1～6 座標（ぱにぱにツール config より）
        pokecrop_coords = [
            {"top": 160, "bottom": 260, "left": 130, "right": 590},
            {"top": 290, "bottom": 390, "left": 130, "right": 590},
            {"top": 420, "bottom": 520, "left": 130, "right": 590},
            {"top": 540, "bottom": 640, "left": 130, "right": 590},
            {"top": 666, "bottom": 766, "left": 130, "right": 590},
            {"top": 792, "bottom": 892, "left": 130, "right": 590},
        ]

        if self.banme == count:
            return
        self.banme = count

        full_img = PILImage.fromarray(cv2.cvtColor(self.img, cv2.COLOR_BGR2RGB))

        crop_w = 590 - 130  # 460px
        crop_h = 260 - 160  # 100px
        dst = PILImage.new("RGB", (crop_w * count, crop_h))

        i = 0
        for num in sensyutu_poke:
            if num == -1:
                dst.save("image/outputImg/outputSensyutu.jpg", quality=95)
                print("  保存: image/outputImg/outputSensyutu.jpg (途中で -1 検出)")
                return
            c = pokecrop_coords[num]
            crop = full_img.crop((c["left"], c["top"], c["right"], c["bottom"]))
            dst.paste(crop, (crop_w * i, 0))
            print(
                f"  pokecrop{num+1} ({c['left']},{c['top']})-({c['right']},{c['bottom']}) → 選出{i+1}枚目"
            )
            i += 1

        dst.save("image/outputImg/outputSensyutu.jpg", quality=95)
        print("  保存: image/outputImg/outputSensyutu.jpg")

    def recognize_chosen_num(self, banme):
        banme_num = banme + 1
        paths = [f"recog\\recogImg\\sensyutu\\banme\\num{banme_num}.jpg"]
        alt = f"recog\\recogImg\\sensyutu\\banme\\num{banme_num}a.jpg"
        if os.path.exists(alt):
            paths.append(alt)
        for num in range(6):
            for path in paths:
                if self.is_exist_image(path, 0.85, "banme" + str(num + 1)):
                    return num
        return -1

    def chose_pokemon(self):
        return self.is_exist_image(
            "image/recogImg/situation/recogSensyutu.jpg", 0.8, "sensyutu"
        )

    def recognize_rate(self):
        return self.is_exist_image("image/recogImg/situation/rate.jpg", 0.8, "rate")

    def recognize_battle(self):
        return self.is_exist_image(
            "image/recogImg/situation/recogBattle.jpg", 0.8, "battle"
        )

    def recognize_oppo_party(self):
        from pathlib import Path

        from pokedata.exception import unrecognizable_pokemon
        from pokedata.pokemon import Pokemon

        if self.is_panipani:
            self.save_screenshot("myPokemon", "image/outputImg/myPokemon.jpg")
            self.save_screenshot("opoPokemon", "image/outputImg/opoPokemon.jpg")
            self.set_my_party_img()

        pokemon_images = _glob.glob("image/pokemon/*")
        coords_list = [
            "opoPoke1",
            "opoPoke2",
            "opoPoke3",
            "opoPoke4",
            "opoPoke5",
            "opoPoke6",
        ]
        pokemon_list = [Pokemon()] * 6

        for i, coord_name in enumerate(coords_list):
            best = self.is_exist_image_max(pokemon_images, 0.45, coord_name)
            if best:
                stem = Path(best).stem
                no, sep, form = stem.partition("-")
                pid = f"{int(no)}-{form}" if sep else f"{int(no)}-0"
                poke = Pokemon.by_pid(pid, True)
                if poke.base_name in unrecognizable_pokemon:
                    poke.form_selected = False
                pokemon_list[i] = poke
                print(f"  [{coord_name}] 検知: {poke.name} (pid={pid}, score)")
            else:
                print(f"  [{coord_name}] 検知なし")
        return pokemon_list

    def recognize_oppo_tn(self):
        return "(OCRスキップ)"

    def run(self):
        print("\n===== キャプチャ認識テスト開始 =====")
        print(f"フェーズ: {self.phase}")
        print(f"ルール: {'シングル' if self.sensyutu_num == 3 else 'ダブル'}")

        print("\n--- 選出画面の検知 ---")
        is_sensyutu = self.chose_pokemon()
        print(f"=> 選出画面: {'検知あり' if is_sensyutu else '検知なし'}")

        print("\n--- レート画面の検知 ---")
        is_rate = self.recognize_rate()
        print(f"=> レート画面: {'検知あり' if is_rate else '検知なし'}")

        print("\n--- バトル開始画面の検知 ---")
        is_battle = self.recognize_battle()
        print(f"=> バトル開始: {'検知あり' if is_battle else '検知なし'}")

        if is_sensyutu:
            print("\n--- 相手パーティ解析 ---")
            party = self.recognize_oppo_party()
            detected = [p for p in party if p.no != -1]
            print(f"\n=> 検知ポケモン数: {len(detected)}/6")
            for p in detected:
                print(f"   - {p.name}")

            print("\n--- 選出番号解析 ---")
            banme_list = [
                self.recognize_chosen_num(b) for b in range(self.sensyutu_num)
            ]
            print(f"=> 選出番号リスト: {banme_list}")

            print("\n--- 選出画像生成 ---")
            if self.is_panipani and banme_list != [-1] * self.sensyutu_num:
                self.create_my_chosen_image(
                    banme_list, len(banme_list) - banme_list.count(-1)
                )

        print("\n===== テスト完了 =====")


if __name__ == "__main__":
    cap = TestCapture(IMAGE_PATH)
    cap.run()
