import datetime
import sys

if sys.platform == "darwin":
    _FONT_FAMILY = "Hiragino Sans"
elif sys.platform == "win32":
    _FONT_FAMILY = "メイリオ"
else:
    _FONT_FAMILY = "Noto Sans CJK JP"


class Const(object):
    """
    classdocs
    """

    dbName = "database/battle.db"
    list2 = []
    kpStartX = 400
    kpStartY = 210
    kpMargin = 10
    kpMojiDX = 25
    kpPictureDX = 55
    kpPictureDY = 65
    myPartyStartX = 10
    myPartyStartY = 180
    myPartyMargin = 5
    myPartyDX = 45
    myPartyDY = 50
    myPartyDetailDY = 70
    myPartyPointList = []
    myPartyDetailList = []
    for i in range(6):
        myPartyDetailList.append((myPartyStartX, myPartyStartY + i * myPartyDetailDY))
    for i in range(9):
        for j in range(7):
            myPartyPointList.append(
                (myPartyStartX + j * myPartyDX, myPartyStartY + i * myPartyDY)
            )
    for i in range(5):
        for j in range(10):
            list2.append(
                (
                    j,
                    kpStartX + j * (kpPictureDX + kpMargin + kpMojiDX),
                    kpStartY + i * (kpPictureDY + kpMargin),
                )
            )
    #            list2=[(0,0,0),(1,60,0),(2,120,0),(3,180,0),(4,240,0),(5,300,0),(6,360,0),(7,420,0),(8,480,0),(9,540,0),(10,0,60),(11,60,60),(12,120,60),(13,180,60),(14,240,60),(15,300,60),(16,360,60),(17,420,60),(18,480,60),(19,540,60),(20,0,120),(21,60,120),(22,120,120),(23,180,120),(24,240,120),(25,300,120),(26,360,120),(27,420,120),(28,480,120),(29,540,120)]
    searchX = 400
    searchY = 60
    searchDY = 20
    txtboxWidth = 5
    yearList = list(range(2026, datetime.date.today().year + 2))
    monthList = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12]
    dateList = [
        1,
        2,
        3,
        4,
        5,
        6,
        7,
        8,
        9,
        10,
        11,
        12,
        13,
        14,
        15,
        16,
        17,
        18,
        19,
        20,
        21,
        22,
        23,
        24,
        25,
        26,
        27,
        28,
        29,
        30,
        31,
    ]
    kikanLabelY = 7
    titleLabelY = 140
    titleFont = (_FONT_FAMILY, 14, "bold")
    bigFont = (_FONT_FAMILY, 12)
    smallFont = (_FONT_FAMILY, 7)
    DB_CHOICE_X = 1100
    DB_CHOICE_Y = 130
    allBattleHistoryButtonX = 20
    allBattleHistoryButtonY = 650
    outlineX = 400
    outlineY = 5
    outlineEndX = 400
    outlineEndY = 670
    summaryStartX = 250
    textStartY = 17
    imageStartY = 3
    summaryX = 10
    myPokemonX = 120
    battleCountY = 10
    myPokemonStartY = 100
    koumokuY = 205
    battleTimeX = 300
    mysensyutuX = 415
    winLoseX = 620
    opoPokemonX = 660
    opposensyutuX = 965
    outline2X = 950
    tnX = 1145
    tnDX = 30
    rankX = 1270
    rankDX = 30
    memoX = 1600
    battleDataY = 5
    battleDataDY = 45
    pokemonImageY = 230
    myPokemonY = []
    for i in range(6):
        myPokemonY.append(myPokemonStartY + i * 60)

    @staticmethod
    def createPass(pid: str) -> str:
        no, _, form = pid.partition("-")
        return f"image/pokemon/{int(no):04d}-{form}.png"
