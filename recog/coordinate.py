import json


class Coordinate(object):
    """
    座標を扱うクラス
    """

    def __init__(self, top, bottom, left, right):
        self.top = top
        self.bottom = bottom
        self.left = left
        self.right = right

    def setCoordinate(self, top, bottom, left, right):
        self.top = top
        self.bottom = bottom
        self.left = left
        self.right = right


class ConfCoordinate(object):
    """
    ファイルから読み込んだ座標を持つクラス
    """

    def __init__(self):
        """
        Constructor
        """
        self.dicCoord = dict()
        self.read_conf_coord()

    def read_conf_coord(self):
        jsonLoad = open("recog/coordinate.json", "r")
        coordConfig = json.load(jsonLoad)

        for k, v in coordConfig.items():
            coord = Coordinate(v["top"], v["bottom"], v["left"], v["right"])

            self.dicCoord[k] = coord

    def add_coord(self, coordName, top, bottom, left, right):
        self.dicCoord[coordName] = Coordinate(top, bottom, left, right)
