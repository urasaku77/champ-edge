from __future__ import annotations

import math
from decimal import Decimal
from typing import Optional

from database.pokemon import DB_pokemon
from pokedata.const import ABILITY_VALUES, Ailments, Types, Walls
from pokedata.exception import changeble_form_in_battle, get_next_form
from pokedata.nature import get_default_doryoku, get_seikaku_hosei
from pokedata.stats import Stats, StatsKey
from pokedata.waza import Waza, WazaBase

_terastal_enabled: bool = True
_mega_enabled: bool = True


def set_terastal_enabled(enabled: bool):
    global _terastal_enabled
    _terastal_enabled = enabled


def set_mega_enabled(enabled: bool):
    global _mega_enabled
    _mega_enabled = enabled


class Pokemon:
    def __init__(self, db_data=None):
        self.__no: int = -1
        self.__form: int = -1
        self.__base_form: int = -1
        self.__form_selected: bool = True
        self.__name: str = ""
        self.__lv: int = 50
        self.__base_name: str = ""
        self.__form_name: str = ""
        self.__syuzoku: Stats = Stats(0)
        self.__kotai: Stats = Stats(31)
        self.__doryoku: Stats = Stats(0)
        self.__rank: Stats = Stats(0)
        self.__seikaku: str = "まじめ"
        self.__item: str = "なし"
        self.__type: list[Types] = []
        self.__terastype: Types = Types.なし
        self.__battle_terastype: Types = Types.なし
        self.__abilities: list[str] = []
        self.__ability: str = ""
        self.__base_ability: str = ""
        self.__ability_value: str = ""
        self.__ailment: Ailments = Ailments.なし
        self.__charging: bool = False
        self.__wall: Walls = Walls.なし
        self.__waza_list: list[Optional[WazaBase]] = [None for _ in range(10)]
        self.__waza_rate_list: list[Optional[float]] = [0.0 for _ in range(10)]
        self.__weight: float = 0.0
        self.__memo: str = ""
        self.__statechanged_handler: Optional[callable] = None

        if db_data is not None:
            self.__no = db_data["no"]
            self.__form = db_data["form"]
            self.__base_form = db_data["form"]
            self.__name = db_data["name"]
            self.__base_name: str = db_data["base_name"]
            self.__form_name: str = db_data["form_name"]
            self.__syuzoku.set_values(
                h=db_data["H"],
                a=db_data["A"],
                b=db_data["B"],
                c=db_data["C"],
                d=db_data["D"],
                s=db_data["S"],
            )
            self.__type.append(Types[db_data["type1"]])
            if db_data["type2"] and db_data["type2"].strip():
                self.__type.append(Types[db_data["type2"]])
            for key in ["ability1", "ability2", "ability3"]:
                if db_data[key] and db_data[key].strip():
                    self.__abilities.append(db_data[key])
            self.set_ability_from_home()
            self.__ability: str = self.__abilities[0]
            self.__base_ability: str = self.__abilities[0]
            self.__weight: float = db_data["weight"]
            self.__item: str = self.fixed_item(self.__name)
            self.__terastype: Types = self.fixed_terastype(self.__name)

    def __getitem__(self, key: StatsKey) -> int:
        match key:
            case StatsKey.H:
                return self.__get_stats(StatsKey.H)
            case StatsKey.A | StatsKey.B | StatsKey.C | StatsKey.D | StatsKey.S:
                value = self.__get_stats(key)
                return value

    @staticmethod
    def by_name(name: str, default=False) -> Pokemon:
        pokemon = Pokemon(DB_pokemon.get_pokemon_data_by_name(name))
        if default:
            pokemon.set_default_data()
        return pokemon

    @staticmethod
    def by_pid(pid: str, default=False) -> Pokemon:
        pokemon = Pokemon(DB_pokemon.get_pokemon_data_by_pid(pid))
        if default:
            pokemon.set_default_data()
        return pokemon

    @staticmethod
    def fixed_item(name: str) -> str:
        if name == "オーガポン(水)":
            return "いどのめん"
        elif name == "オーガポン(炎)":
            return "かまどのめん"
        elif name == "オーガポン(岩)":
            return "いしずえのめん"
        elif name == "ザシアン(王)":
            return "くちたけん"
        elif name == "ザマゼンタ(王)":
            return "くちたたて"
        elif name == "アルセウス(かくとう)":
            return "こぶしのプレート"
        elif name == "アルセウス(ひこう)":
            return "あおぞらプレート"
        elif name == "アルセウス(どく)":
            return "もうどくプレート"
        elif name == "アルセウス(じめん)":
            return "だいちのプレート"
        elif name == "アルセウス(いわ)":
            return "がんせきプレート"
        elif name == "アルセウス(むし)":
            return "たまむしプレート"
        elif name == "アルセウス(ゴースト)":
            return "もののけプレート"
        elif name == "アルセウス(はがね)":
            return "こうてつプレート"
        elif name == "アルセウス(ほのお)":
            return "ひのたまプレート"
        elif name == "アルセウス(みず)":
            return "しずくプレート"
        elif name == "アルセウス(くさ)":
            return "みどりのプレート"
        elif name == "アルセウス(でんき)":
            return "いかずちプレート"
        elif name == "アルセウス(エスパー)":
            return "ふしぎのプレート"
        elif name == "アルセウス(こおり)":
            return "つららのプレート"
        elif name == "アルセウス(ドラゴン)":
            return "りゅうのプレート"
        elif name == "アルセウス(あく)":
            return "こわもてプレート"
        elif name == "アルセウス(フェアリー)":
            return "せいれいプレート"
        else:
            return "なし"

    @staticmethod
    def fixed_terastype(name: str) -> Types:
        if name == "オーガポン":
            return Types.くさ
        elif name == "オーガポン(水)":
            return Types.みず
        elif name == "オーガポン(炎)":
            return Types.ほのお
        elif name == "オーガポン(岩)":
            return Types.いわ
        else:
            return Types.なし

    # region プロパティ
    @property
    def no(self) -> int:
        return self.__no

    @property
    def form(self) -> int:
        return self.__form

    @property
    def form_selected(self) -> bool:
        return self.__form_selected

    @form_selected.setter
    def form_selected(self, value: bool):
        self.__form_selected = value

    @property
    def pid(self) -> str:
        return str(self.__no) + "-" + str(self.__form)

    @property
    def icon(self) -> str:
        form = self.__form if self.__form != -1 else 0
        return f"image/pokemon/{self.__no:04d}-{form}.png"

    @property
    def name(self) -> str:
        return self.__name

    @property
    def base_name(self) -> str:
        return self.__base_name

    @property
    def type(self) -> list[Types]:
        return self.__type

    @property
    def terastype(self) -> Types:
        if self.__name == "オーガポン":
            return Types.くさ
        elif self.__name == "オーガポン(水)":
            return Types.みず
        elif self.__name == "オーガポン(炎)":
            return Types.ほのお
        elif self.__name == "オーガポン(岩)":
            return Types.いわ
        else:
            return self.__terastype

    @terastype.setter
    def terastype(self, value: Types):
        self.__terastype = value

    @property
    def battle_terastype(self) -> Types:
        if not _terastal_enabled:
            return Types.なし
        return self.__battle_terastype

    @battle_terastype.setter
    def battle_terastype(self, value: Types):
        self.__battle_terastype = value
        if "オーガポン" in self.__name:
            stats: Stats = Stats(0)
            key = StatsKey(5)
            if "水" in self.__name:
                key = StatsKey(4)
            elif "炎" in self.__name:
                key = StatsKey(1)
            elif "岩" in self.__name:
                key = StatsKey(2)
            if value == Types.なし:
                self.ability = self.__abilities[0]
                self.rank = stats
            else:
                self.ability = "おもかげやどし"
                for k in StatsKey:
                    if k == key:
                        stats[k] = 1
                    else:
                        stats[k] = 0
                self.rank = stats
        self.statechanged()

    @property
    def lv(self) -> int:
        return self.__lv

    @property
    def syuzoku(self) -> Stats:
        return self.__syuzoku

    @property
    def kotai(self) -> Stats:
        return self.__kotai

    @kotai.setter
    def kotai(self, value) -> None:
        self.__kotai.set_values_from_stats(value)
        self.statechanged()

    @property
    def doryoku(self) -> Stats:
        return self.__doryoku

    @doryoku.setter
    def doryoku(self, value) -> None:
        self.__doryoku.set_values_from_stats(value)
        self.statechanged()

    @property
    def rank(self) -> Stats:
        return self.__rank

    @rank.setter
    def rank(self, value: Stats) -> None:
        self.__rank = value
        self.statechanged()

    @property
    def seikaku(self) -> str:
        return self.__seikaku

    @seikaku.setter
    def seikaku(self, value) -> None:
        self.__seikaku = value
        self.statechanged()

    @property
    def item(self) -> str:
        return self.__item

    @item.setter
    def item(self, value) -> None:
        self.__item = value
        self.statechanged()

    @property
    def ability(self) -> str:
        return self.__ability

    @ability.setter
    def ability(self, value) -> None:
        self.__ability = value
        self.__base_ability = value
        self.set_default_ability_value()
        self.statechanged()

    @property
    def base_ability(self) -> str:
        return self.__base_ability

    def apply_trace(self, value: str) -> None:
        """トレース特性によるコピー。base_abilityを変更しない。"""
        self.__ability = value
        self.set_default_ability_value()

    @property
    def ailment(self) -> Ailments:
        return self.__ailment

    @ailment.setter
    def ailment(self, value: Ailments) -> None:
        self.__ailment = value
        self.statechanged()

    @property
    def charging(self) -> bool:
        return self.__charging

    @charging.setter
    def charging(self, value: bool) -> None:
        self.__charging = value
        self.statechanged()

    @property
    def wall(self) -> Walls:
        return self.__wall

    @wall.setter
    def wall(self, value: Walls) -> None:
        self.__wall = value
        self.statechanged()

    @property
    def abilities(self) -> list[str]:
        return self.__abilities

    @property
    def rankedA(self) -> int:
        return self.get_ranked_stats(StatsKey.A)

    @property
    def rankedB(self) -> int:
        return self.get_ranked_stats(StatsKey.B)

    @property
    def rankedC(self) -> int:
        return self.get_ranked_stats(StatsKey.C)

    @property
    def rankedD(self) -> int:
        return self.get_ranked_stats(StatsKey.D)

    @property
    def rankedS(self) -> int:
        return self.get_ranked_stats(StatsKey.S)

    @property
    def ability_value(self) -> str:
        return self.__ability_value

    @ability_value.setter
    def ability_value(self, value: str):
        self.__ability_value = value
        self.statechanged()

    @property
    def ability_enable(self) -> bool:
        return self.__ability_value == "有効"

    @property
    def waza_list(self) -> list[WazaBase]:
        return self.__waza_list

    @property
    def waza_rate_list(self) -> list[float]:
        return self.__waza_rate_list

    @property
    def weight(self) -> float:
        return self.__weight

    @property
    def memo(self) -> str:
        return self.__memo

    @memo.setter
    def memo(self, value) -> None:
        self.__memo = value

    @property
    def status_text(self) -> str:
        return "-".join([str(self.__get_stats(x)) for x in StatsKey])

    @property
    def marked_status_text(self) -> str:
        text = ""
        for key in StatsKey:
            value = get_seikaku_hosei(self.__seikaku, key)
            if value == 1.1:
                text += (
                    "[color=#ffc0cb]" + str(self.get_ranked_stats(key)) + "[/color]-"
                )
            elif value == 0.9:
                text += (
                    "[color=#add8e6]" + str(self.get_ranked_stats(key)) + "[/color]-"
                )
            else:
                text += str(self.get_ranked_stats(key)) + "-"
        return text[:-1]

    @property
    def to_string(self) -> str:
        return "{0}@{1} {2}".format(self.name, self.item, self.status_text)

    @property
    def statechanged_handler(self) -> callable:
        return self.__statechanged_handler

    @property
    def next_form_pid(self) -> Optional[str]:
        # バトル中フォルムチェンジ（メロエッタ・イルカマン・テラパゴス）
        result = get_next_form(self.pid)
        if result is not None:
            return result

        # メガシンカ: DB の form 10-19 を動的にサイクル
        # 通常フォーム(0, 5等) → 11 → 12 → 通常フォームに戻る
        mega_forms = DB_pokemon.get_mega_forms_by_no(self.__no)
        if not mega_forms or not _mega_enabled:
            return None
        if self.__form not in mega_forms:
            return f"{self.__no}-{mega_forms[0]}"
        if self.__form in mega_forms:
            idx = mega_forms.index(self.__form)
            if idx + 1 < len(mega_forms):
                return f"{self.__no}-{mega_forms[idx + 1]}"
            return f"{self.__no}-{self.__base_form}"
        return None

    @property
    def next_form_icon(self) -> str:
        form_pid = self.next_form_pid
        if form_pid is None:
            return ""
        no, _, form = form_pid.partition("-")
        return f"image/pokemon/{int(no):04d}-{form}.png"

    @property
    def changeable_icon(self) -> str:
        return (
            "image/other/change.png"
            if self.__no in changeble_form_in_battle
            else ""
        )

    @statechanged_handler.setter
    def statechanged_handler(self, handler: Optional[callable]):
        self.__statechanged_handler = handler

    @property
    def is_empty(self) -> bool:
        return self.__no == -1

    @property
    def is_flying(self) -> bool:
        return (
            (Types.ひこう in self.__type)
            or self.__ability == "ふゆう"
            or self.__item == "ふうせん"
        )

    # endregion

    # 実数値（努力値は0-32スケール、1単位=2の実数値寄与）
    def __get_stats(self, key: StatsKey) -> int:
        if key == StatsKey.H:
            value = (
                (self.__syuzoku[key] * 2)
                + self.kotai[key]
                + self.doryoku[key] * 2
            )
            return math.floor(value * self.__lv / 100) + 10 + self.__lv
        else:
            value = (
                (self.__syuzoku[key] * 2)
                + self.kotai[key]
                + self.doryoku[key] * 2
            )
            value = math.floor(value * self.__lv / 100) + 5
            value = math.floor(value * get_seikaku_hosei(self.__seikaku, key))
            return value

    # 全実数値
    def get_all_stats(self) -> list[int]:
        stats: list[int] = []
        for _i, key in enumerate([x for x in StatsKey]):
            value = self.__get_stats(key)
            stats.append(value)
        return stats

    # 実数値(ランク補正込み)
    def __get_ranked_stats(self, key: StatsKey) -> int:
        before_stats = self.__get_stats(key)
        value = before_stats
        if key != StatsKey.H:
            rank = self.__rank[key]
            if rank > 0:
                value = math.floor(before_stats / 2 * (2 + rank))
            elif rank < 0:
                value = math.floor(before_stats / (2 - rank) * 2)
            else:
                value = before_stats
        else:
            value = before_stats
        return value

    # 全実数値(ランク補正込み)
    def get_all_ranked_stats(self) -> list[int]:
        ranked_stats: list[int] = []
        for _i, key in enumerate([x for x in StatsKey]):
            value = self.__get_ranked_stats(key)
            ranked_stats.append(value)
        return ranked_stats

    # 最も高い実数値のキーを返す（こだいかっせい、クォークチャージ用）
    def __get_best_stats_key(self) -> StatsKey:
        max_key = StatsKey.A
        max_value = self.__get_stats(StatsKey.A)
        for key in [StatsKey.B, StatsKey.C, StatsKey.D, StatsKey.S]:
            value = self.__get_stats(key)
            if max_value < value:
                max_key = key
                max_value = value
        return max_key

    # 実数値(ランク補正込み)
    def get_ranked_stats(self, key: StatsKey) -> int:
        stats = self[key]
        rank = self.__rank[key]
        if rank > 0:
            stats = math.floor(stats / 2 * (2 + rank))
        elif rank < 0:
            stats = math.floor(stats / (2 - rank) * 2)
        return stats

    # デフォルトデータ設定
    def set_default_data(self):
        self.set_top_data_from_home()
        self.set_default_doryoku_from_home()
        self.set_ability_from_home()
        self.set_waza_from_home()
        if self.seikaku == "まじめ":
            from pokedata.loader import get_default_data

            data = get_default_data(self.name)
            self.set_load_data(
                data, use_data=True if self.__waza_list[0] is None else False
            )

    # CSV読み込みデータの設定
    def set_load_data(self, data, use_data: bool, load_kotai: bool = True):
        if len(data):
            if load_kotai:
                self.__kotai.set_values_from_string(data[1])
            self.__doryoku.set_values_from_string(data[2])
            self.__seikaku = data[3]
            self.__item = data[4]
            self.__ability = data[5]
            self.__base_ability = data[5]
            self.__terastype = Types[data[6]] if data[6] != "" else Types.なし
            self.__memo = data[7]
            if use_data:
                for i in range(11):
                    if i + 8 < len(data):
                        self.__waza_list[i] = WazaBase(data[i + 8])

    # HOMEデータから技を10個読み取り
    def set_waza_from_home(self):
        from pokedata.loader import get_home_data

        waza_data = get_home_data(self.name, "./stats/home_waza.csv")
        for i in range(len(waza_data) if len(waza_data) <= 10 else 10):
            self.__waza_list[i] = WazaBase(waza_data[i][0])
            self.__waza_rate_list[i] = waza_data[i][1]

    # HOMEデータからとくせいを使用率順に並び替え
    def set_ability_from_home(self):
        abilities_data = []
        from pokedata.loader import get_home_data

        ability_data = get_home_data(self.name, "./stats/home_tokusei.csv")
        for i in range(len(ability_data)):
            if ability_data[i][0] in self.__abilities:
                abilities_data.append(ability_data[i][0])
        if len(abilities_data) != 0:
            self.__abilities = abilities_data

    # HOMEデータで一番使用率が高いものをセット
    def set_top_data_from_home(self):
        from pokedata.loader import get_home_data

        item_data = get_home_data(self.name, "./stats/home_motimono.csv")
        self.item = item_data[0][0] if len(item_data) != 0 else "なし"
        seikaku_data = get_home_data(self.name, "./stats/home_seikaku.csv")
        self.seikaku = seikaku_data[0][0] if len(seikaku_data) != 0 else "まじめ"
        teras_data = get_home_data(self.name, "./stats/home_terastal.csv")
        self.terastype = (
            Types.get(teras_data[0][0]) if len(teras_data) != 0 else Types.なし
        )

    def set_default_doryoku_from_home(self):
        from pokedata.loader import get_top_home_doryoku
        doryoku_text = get_top_home_doryoku(self.name)
        if doryoku_text is not None:
            self.__doryoku.init_values(0)
            self.__doryoku.set_values_from_string(doryoku_text)

    def set_default_doryoku_from_seikaku(self):
        doryoku = get_default_doryoku(self.seikaku, self.syuzoku)
        self.doryoku = doryoku

    # タイプ相性値
    # テラスタイプがある場合、そのタイプで算出
    def get_type_effective(
        self,
        waza: Waza,
        ability: str,
        attacker_terastype: Types = Types.なし,
        defender_terastype: Types = Types.なし,
    ) -> float:
        value = Decimal(1.0)
        types: list[Types] = (
            self.type
            if self.battle_terastype == Types.なし
            or self.battle_terastype == Types.ステラ
            else [self.battle_terastype]
        )
        for type_effective in DB_pokemon.get_type_effective(waza.type, types):
            if waza.name == "フリーズドライ" and type_effective.df_type == Types.みず:
                value = value * Decimal(2.0)
            elif (
                waza.name == "サウザンアロー" and type_effective.df_type == Types.じめん
            ):
                value = value * Decimal(2.0)
            elif (
                (ability == "しんがん" or ability == "きもったま")
                and (waza.type == Types.ノーマル or waza.type == Types.かくとう)
                and type_effective.df_type == Types.ゴースト
            ):
                value = value * Decimal(1.0)
            else:
                value = value * Decimal(type_effective.value)
        if (
            (waza.name == "テラバースト")
            and self.battle_terastype == Types.ステラ
            and not defender_terastype == Types.なし
        ):
            value = Decimal(2.0)
        if (
            waza.name == "テラクラスター"
            and not attacker_terastype == Types.なし
            and not defender_terastype == Types.なし
        ):
            value = Decimal(2.0)

        return float(value)

    # 技の編集
    def set_waza(self, index: int, waza_name: str):
        if len(waza_name) == 0:
            self.__waza_list[index] = None
        elif index < len(self.__waza_list):
            self.__waza_list[index] = WazaBase(waza_name)
        else:
            self.__waza_list.append(WazaBase(waza_name))
        self.statechanged()

    # 対象のタイプを持っているか（テラスタイプの場合含む）
    def has_type(self, _type: Types) -> bool:
        if self.battle_terastype is not None and self.battle_terastype != Types.なし:
            return _type == self.__battle_terastype
        else:
            return _type in self.__type

    # 値が変化した時の通知
    def statechanged(self):
        if self.__statechanged_handler is not None:
            self.__statechanged_handler()

    def form_change(self):
        form_id = self.next_form_pid
        if form_id is not None:
            next_form = Pokemon.by_pid(form_id)
            self.__name = next_form.name
            self.__form = next_form.__form
            self.__form_name = next_form.__form_name
            self.__syuzoku.set_values_from_stats(next_form.syuzoku)
            self.__weight = next_form.__weight
            self.__type = list(next_form.type)
            self.__abilities = list(next_form.abilities)
            self.__ability = next_form.ability
            self.statechanged()

    def on_stage(self):
        self.__rank = Stats(init_value=0)
        self.set_default_ability_value()

    def set_default_ability_value(self):
        for k, v in ABILITY_VALUES.items():
            if self.__ability == k:
                self.__ability_value = v[0]
