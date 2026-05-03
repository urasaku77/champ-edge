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

        # party(相手パーティ待ち)→chosen(対戦画面待ち)→一旦終了
        self.phase = "wait"
        self.banme = 0
        self.sensyutu_num = 3 if get_recog_value("rule") == 1 else 4
        self.is_panipani = get_recog_value("panipani_auto")

    # Websocket接続
    def connect_websocket(self):
        try:
            self.loop = asyncio.get_event_loop()
            self.obs = Obs(
                self.loop, get_recog_value("port"), get_recog_value("password")
            )
            self.phase = "wait"
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
            case "wait":
                return self.recognize_rank()
            case "party":
                return self.recognize_chosen_capture()
            case "chosen":
                chosen = self.started_battle()
                if chosen:
                    self.phase = "wait"
                    return chosen
                elif self.chose_pokemon():
                    banme_list = [
                        self.recognize_chosen_num(banme)
                        for banme in range(self.sensyutu_num)
                    ]
                    if self.is_panipani and banme_list != [-1] * self.sensyutu_num:
                        self.create_my_chosen_image(
                            banme_list, len(banme_list) - banme_list.count(-1)
                        )
                    return banme_list

    # 選出画面検知
    def chose_pokemon(self):
        return self.is_exist_image(
            "recog/recogImg/situation/recogSensyutu.jpg", 0.8, "sensyutu"
        )

    # 選出画面解析
    def recognize_chosen_capture(self) -> tuple[list[Pokemon], str]:
        self.get_screenshot()
        if self.chose_pokemon():
            self.phase = "chosen"
            oppo_tn = self.recognize_oppo_tn()
            return (self.recognize_oppo_party(), oppo_tn)

    # 各順位を取得する
    def recognize_rank(self):
        self.get_screenshot()
        opoRank = -1
        # myRank = -1

        recogResult = self.is_exist_image(
            "recog/recogImg/situation/juni.jpg", 0.8, "juni"
        )
        recogChosen = self.chose_pokemon()
        if recogResult:
            opoKuraiCoord = self.get_coordinate_for_recognize(
                "recog/recogImg/other/kurai.jpg", 0.8, "kurai"
            )
            if opoKuraiCoord != [-1, -1, -1, -1]:
                opoRank = self.recognize_opo_rank(opoKuraiCoord)
                self.phase = "party"
            # myKuraiCoord = self.get_coordinate_for_recognize(
            #     "recog/recogImg/other/myKurai.jpg", 0.7, "myKurai"
            # )

            # if myKuraiCoord == [-1, -1, -1, -1]:
            #     myRank = -1
            # else:
            #     myRank = self.recognize_my_rank(myKuraiCoord)

            # if myRank == -1 and opoRank == -1:
            #     opoRateCoord = self.get_coordinate_for_recognize(
            #         "recog/recogImg/situation/rate.jpg", 0.8, "kurai"
            #     )
            #     if opoRateCoord == [-1, -1, -1, -1]:
            #         opoRank = -1
            #     else:
            #         opoRank = self.recognize_opo_rate(opoRateCoord)

            #     myRank = self.recognize_my_rate()
        elif recogChosen:
            self.phase = "party"
        return opoRank

    # 相手の順位を取得する
    def recognize_opo_rank(self, kuraiCoord):
        coord = self.coords.dicCoord["kurai"]

        digit = 1
        rank = 0
        blNumExist = True
        blRank = False
        recLeft = coord.left + kuraiCoord[0] - 35
        recRight = coord.left + kuraiCoord[0] + 5
        while blNumExist:
            self.coords.add_coord("opoNum", coord.top, coord.bottom, recLeft, recRight)
            for i in range(10):
                if self.is_exist_image(
                    "recog/recogImg/num/opo/" + str(i) + ".jpg", 0.8, "opoNum"
                ):
                    rank = rank + digit * i
                    blRank = True
                    break
                if i == 9:
                    blNumExist = False
            digit = digit * 10
            recLeft = recLeft - 30
            recRight = recRight - 30

        if not blRank:
            return -1
        return rank

    # 相手のレートを取得する（仲間大会など）
    def recognize_opo_rate(self, rateCoord):
        coord = self.coords.dicCoord["kurai"]

        digit = 1000
        rate = 0

        recLeft = coord.left + rateCoord[2] - 10
        recRight = coord.left + rateCoord[2] + 35
        while digit >= 1:
            self.coords.add_coord("opoRate", coord.top, coord.bottom, recLeft, recRight)
            for i in range(10):
                if self.is_exist_image(
                    "recog/recogImg/num/opo/" + str(i) + ".jpg", 0.8, "opoRate"
                ):
                    if rate == -1:
                        rate = digit * i
                    else:
                        rate = rate + digit * i
                    break
            digit = digit / 10
            recLeft = recLeft + 30
            recRight = recRight + 30

        if rate == 0:
            return -1
        return int(rate) * -1

    # 自分の順位を取得する
    def recognize_my_rank(self, kuraiCoord):
        if kuraiCoord == [-1, -1, -1, -1]:
            return -1
        coord = self.coords.dicCoord["myKurai"]
        digit = 1
        rank = 0
        blRank = False
        blNumExist = True
        recLeft = coord.left + kuraiCoord[0] - 47
        recRight = coord.left + kuraiCoord[0] + 5

        while blNumExist:
            self.coords.add_coord("myNum", coord.top, coord.bottom, recLeft, recRight)
            match = 0
            num = 0
            for i in range(10):
                numImg = cv2.imread("recog/recogImg/num/my/" + str(i) + ".jpg")
                result = self.is_exist_image_for_my_sensyutsu(numImg, self.img, "myNum")
                if result > 0.85:
                    rank = rank + digit * i
                    blRank = True
                    break
                if match < result:
                    match = result
                    num = i

                if i == 9:
                    if match < 0.7:
                        blNumExist = False
                    else:
                        blRank = True
                        rank = rank + digit * num
            digit = digit * 10
            recLeft = recLeft - 41
            recRight = recRight - 41
            if not blRank:
                return -1
        return rank

    # 自分のレートを取得する（仲間大会など）
    def recognize_my_rate(self):
        coord = self.coords.dicCoord["myRate"]
        digit = 1
        rank = 0
        blRank = False
        recLeft = coord.left
        recRight = coord.left + 40
        for j in range(4):
            self.coords.add_coord("Rate", coord.top, coord.bottom, recLeft, recRight)
            match = 0
            num = 0
            for i in range(10):
                numImg = cv2.imread("recog/recogImg/num/opo/" + str(i) + ".jpg")
                result = self.is_exist_image_for_my_sensyutsu(numImg, self.img, "Rate")

                if result > 0.85:
                    rank = rank + digit * i
                    blRank = True
                    break
                if match < result:
                    match = result
                    num = i

                if i == 9:
                    if match < 0.7:
                        return -1
                    else:
                        blRank = True
                        rank = rank + digit * num

            digit = digit * 10
            recLeft = recLeft - 31
            recRight = recRight - 31
            if not blRank:
                return -1
        return rank * -1

    # 相手パーティの解析
    def recognize_oppo_party(self):
        if self.is_panipani:
            # OBS表示用のキャプチャ取得
            self.save_screenshot("myPokemon", "recog/outputImg/myPokemon.jpg")
            self.save_screenshot("opoPokemon", "recog/outputImg/opoPokemon.jpg")
            self.set_my_party_img()

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
            oppo = self.is_exist_image_max(pokemonImages, 0.7, coordsList[coord])
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
        paths = [f"recog\\recogImg\\sensyutu\\banme\\num{banme_num}.jpg"]
        alt = f"recog\\recogImg\\sensyutu\\banme\\num{banme_num}a.jpg"
        if os.path.exists(alt):
            paths.append(alt)
        for num in range(6):
            for path in paths:
                if self.is_exist_image(path, 0.85, "banme" + str(num + 1)):
                    return num
        return -1

    # OBS表示用の自分選出画像作成
    def create_my_chosen_image(self, sensyutuPoke, count):
        img = Image.fromarray(cv2.cvtColor(self.myPartyImg, cv2.COLOR_BGR2RGB))
        if self.banme == count:
            return
        self.banme = count
        i = 0
        dst = Image.new("RGB", (575 * (count) + 1, 106))
        for num in sensyutuPoke:
            if num == -1:
                dst.save("recog/outputImg/outputSensyutu.jpg", quality=95)
                return
            outputImg = img.crop((0, 0 + 115 * num, 570, 105 + 115 * num))
            dst.paste(outputImg, (0 + 570 * i, 0))
            i = i + 1
        dst.save("recog/outputImg/outputSensyutu.jpg", quality=95)

    # 対戦開始画面を検知
    def started_battle(self):
        self.get_screenshot()
        return self.is_exist_image(
            "recog/recogImg/situation/recogBattle.jpg", 0.8, "aitewomiru"
        )

    # テンプレートマッチング(最大のみ)
    def is_exist_image_max(self, temp_imgge_name, accuracy, coord_name):
        coord = self.coords.dicCoord[coord_name]
        img1 = self.img[coord.top : coord.bottom, coord.left : coord.right]
        gray = cv2.cvtColor(img1, cv2.COLOR_RGB2GRAY)
        max_val_list: list[float] = []
        for image in temp_imgge_name:
            try:
                temp = cv2.imread(image, cv2.IMREAD_GRAYSCALE)
                temp = cv2.resize(temp, None, None, 1.06, 1.06)
                match = cv2.matchTemplate(gray, temp, cv2.TM_CCOEFF_NORMED)
                _, max_val, _, _ = cv2.minMaxLoc(match)
                max_val_list.append(max_val)
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

        gray = cv2.cvtColor(img1, cv2.COLOR_RGB2GRAY)
        temp = cv2.cvtColor(temp, cv2.COLOR_RGB2GRAY)

        match = cv2.matchTemplate(gray, temp, cv2.TM_CCOEFF_NORMED)
        loc = np.where(match >= accuracy)
        for _pt in zip(*loc[::-1], strict=False):
            result = True
        return result

    # テンプレートマッチング（順位取得用）
    def is_exist_image_for_my_sensyutsu(self, temp, capImg, coordName):
        coord = self.coords.dicCoord[coordName]
        img1 = capImg[coord.top : coord.bottom, coord.left : coord.right]
        gray = cv2.cvtColor(img1, cv2.COLOR_RGB2GRAY)
        temp = cv2.cvtColor(temp, cv2.COLOR_RGB2GRAY)
        match = cv2.matchTemplate(temp, gray, cv2.TM_CCOEFF_NORMED)
        return max(list(map(lambda x: max(x), match)))

    # 座標を取得（順位取得用）
    def get_coordinate_for_recognize(self, tempImgName, accuracy, coordName):
        coord = self.coords.dicCoord[coordName]
        img1 = self.img[coord.top : coord.bottom, coord.left : coord.right]
        temp = cv2.imread(tempImgName)
        coordinate = [-1, -1, -1, -1]
        if temp is None:
            print(tempImgName + "が見つかりません")
            return coordinate
        h, w, a = temp.shape
        gray = cv2.cvtColor(img1, cv2.COLOR_RGB2GRAY)
        temp = cv2.cvtColor(temp, cv2.COLOR_RGB2GRAY)
        th, gray = cv2.threshold(gray, 240, 255, cv2.THRESH_TOZERO)
        th, temp = cv2.threshold(temp, 240, 255, cv2.THRESH_TOZERO)
        match = cv2.matchTemplate(gray, temp, cv2.TM_CCOEFF_NORMED)

        min_value, max_value, min_pt, max_pt = cv2.minMaxLoc(match)
        pt = min_pt
        loc = np.where(match >= accuracy)
        for pt in zip(*loc[::-1], strict=False):
            coordinate = pt
            coordinate = coordinate + (coordinate[0] + w, coordinate[1] + h)
            break
        return coordinate

    # ポケモンの画像ファイル名からPIDを取得 (例: "image/pokemon/0003-11.png" → "3-11")
    def shape_poke_num(self, origin: str):
        try:
            stem = Path(origin).stem        # "0003-11"
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
            # 閾値の設定
            threshold_value = 85
            # 配列の作成（output用）
            gray = img.copy()
            # 実装(numpy)
            img[gray < threshold_value] = 0
            img[gray >= threshold_value] = 255
            img = Image.fromarray(img)
            txt = tool.image_to_string(img, lang="jpn")
            return txt
        except Exception as e:
            print(e)
            return ""
