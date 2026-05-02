import csv

from pokedata.exception import base_names


def get_party_csv() -> str:
    with open("party/setting.txt", "r") as txt:
        file = txt.read()
        txt.close()
    return "party/csv/" + file


def get_party_data(file_path: str = "default") -> list[list[str]]:
    file = file_path
    if file_path == "default":
        file = get_party_csv()
    with open(file, encoding="cp932") as pt_csv:
        data = [x for x in csv.reader(pt_csv)]
        data = data[1:7]
        return data


def get_home_data(name: str, file_path: str):
    for base_name in base_names:
        if base_name in name:
            name = base_name
    data_list: list[list[str]] = []
    with open(file_path, encoding="utf-8") as csv_file:
        data = [x for x in csv.reader(csv_file)]
        for i in range(len(data)):
            if data[i][0] == name:
                data_list.append([data[i][1], data[i][2]])
    return data_list


def get_default_data(name: str) -> list[str]:
    with open("party/csv/default.csv", encoding="sjis") as csv_file:
        default_data = [x for x in csv.reader(csv_file)]
        lst = [x for x in default_data if x[0] == name]
        return lst[0] if len(lst) else []
