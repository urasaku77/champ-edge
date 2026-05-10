import csv
import re

from pokedata.exception import base_names


def get_party_csv() -> str:
    with open("party/setting.txt", "r", encoding="utf-8") as txt:
        file = txt.read()
        txt.close()
    return "party/csv/" + file


def get_party_data(file_path: str = "default") -> list[list[str]]:
    file = file_path
    if file_path == "default":
        file = get_party_csv()
    try:
        with open(file, encoding="cp932") as pt_csv:
            data = [x for x in csv.reader(pt_csv)]
            data = data[1:7]
            return data
    except FileNotFoundError as e:
        raise FileNotFoundError(f"CSVファイルが見つかりません: {file}") from e
    except (UnicodeDecodeError, UnicodeError) as e:
        raise ValueError(f"CSVファイルのエンコードが正しくありません（cp932形式が必要）: {file}") from e
    except csv.Error as e:
        raise ValueError(f"CSVファイルの形式が正しくありません: {e}") from e


def get_home_data(name: str, file_path: str):
    for base_name in base_names:
        if base_name in name:
            name = base_name
    data_list: list[list[str]] = []
    try:
        with open(file_path, encoding="utf-8") as csv_file:
            data = [x for x in csv.reader(csv_file)]
            for i in range(len(data)):
                if data[i][0] == name:
                    data_list.append([data[i][1], data[i][2]])
    except FileNotFoundError:
        pass
    return data_list


_DORYOKU_NUM_RE = re.compile(r"[HABCDS](\d+)")


def get_top_home_doryoku(name: str) -> str | None:
    """HOME努力値データのうち、合計が66になる最上位のものを返す。なければNone。"""
    for doryoku_text, _pct in get_home_data(name, "./stats/home_doryoku.csv"):
        if sum(int(v) for v in _DORYOKU_NUM_RE.findall(doryoku_text)) == 66:
            return doryoku_text
    return None


def get_default_data(name: str) -> list[str]:
    with open("party/csv/default.csv", encoding="sjis") as csv_file:
        default_data = [x for x in csv.reader(csv_file)]
        lst = [x for x in default_data if x[0] == name]
        return lst[0] if len(lst) else []
