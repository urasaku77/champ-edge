from typing import Optional

# フォルムチェンジ可能なポケモンの番号リスト
# バトル中フォルムチェンジ（メロエッタ・イルカマン・テラパゴス）
# ＋ メガシンカ対応（image/pokemon/ に form 11-12 が存在するポケモン）
changeble_form_in_battle = [
    648, 964, 1024,
    3, 6, 9, 15, 18, 36, 65, 71, 80, 94, 115, 121, 127, 130, 142,
    149, 154, 160, 181, 208, 212, 214, 227, 229, 248, 282, 302, 306,
    308, 310, 319, 323, 334, 354, 358, 359, 362, 428, 445, 448, 460,
    475, 478, 500, 530, 531, 609, 623, 652, 655, 658, 670, 678, 701,
    740, 780, 952, 970,
]

# 統計上同じポケモンとしてカウントしたいポケモンの番号リスト
same_pokemon_in_stats = [648, 888, 889, 964, 1024]

# パーティ選択時に表示させたくないポケモンリスト
remove_pokemon_name_from_party = [
    "メロエッタ(ステップ)",
    "イルカマン(マイティ)",
    "テラパゴス(テラスタル)",
    "テラパゴス(ステラ)",
]
# フォルムの違いはあるが、HOME上では区別されていないポケモンリスト
base_names = ["メロエッタ", "イルカマン", "イッカネズミ", "オーガポン", "テラパゴス"]

# 選出画面で判別付かないポケモンリスト
unrecognizable_pokemon = ["ウーラオス", "ザシアン", "ザマゼンタ"]

# 選出画面で判別付かないポケモン+途中で姿が変わるポケモンの番号
unrecognizable_pokemon_no = [648, 888, 889, 892, 964, 1024]

# 選出画面で判別付かないポケモンでHOME上区別がないポケモン
unrecognizable_and_same_pokemon_in_home = {
    "ザシアン": "きょじゅうざん",
    "ザマゼンタ": "きょじゅうだん",
}


def get_next_form(pid: str) -> Optional[str]:
    match pid:
        case "648-0":
            return "648-1"
        case "648-1":
            return "648-0"
        case "964-0":
            return "964-1"
        case "964-1":
            return "964-0"
        case "1024-0":
            return "1024-1"
        case "1024-1":
            return "1024-2"
        case "1024-2":
            return "1024-1"
        case _:
            return None


def check_pokemon_form(pid: str):
    if pid == "-1--1":
        return "-1"
    elif any(str(pokemon) in pid for pokemon in same_pokemon_in_stats):
        return pid[:-1] + "0"
    else:
        return pid
