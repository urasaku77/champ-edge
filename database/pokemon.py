import sqlite3
from dataclasses import dataclass

from pokedata.const import Types
from pokedata.exception import remove_pokemon_name_from_party


@dataclass
class TypeEffective:
    at_type: Types
    df_type: Types
    value: float


class DB_pokemon:
    __db = sqlite3.connect("database/pokemon.db", check_same_thread=False)
    __db.row_factory = sqlite3.Row
    __type_effectives: list[TypeEffective] = []
    __pokemon_namelist: list[str] = []
    __pokemon_namelist_for_party: list[str] = []
    __waza_namedict: dict[str, str] = {}

    @staticmethod
    def get_pokemon_data_by_name(name: str):
        result = DB_pokemon.__select(
            "SELECT * FROM pokemon_data where name = ?", (name,)
        )
        return result[0]

    @staticmethod
    def get_pokemons_name_by_no(no: str):
        result = DB_pokemon.__select(
            "SELECT name FROM pokemon_data where no = ?", (no,)
        )
        return [row["name"] for row in result]

    @staticmethod
    def get_pokemon_data_by_pid(pid: str):
        no, form = pid.split("-")
        result = DB_pokemon.__select(
            "SELECT * FROM pokemon_data where no = ? and form = ?", (no, form)
        )
        return result[0]

    @staticmethod
    def get_pokemon_name_by_pid(pid: str):
        no, form = pid.split("-")
        result = DB_pokemon.__select(
            "SELECT name FROM pokemon_data where no = ? and form = ?", (no, form)
        )
        return result[0]["name"]

    @staticmethod
    def get_pokemon_pid_by_name(name: str) -> str:
        result = DB_pokemon.__select(
            "SELECT no || '-' || form pid FROM pokemon_data where name = ?", (name,)
        )
        return result[0]["pid"]

    @staticmethod
    def get_pokemon_namelist(form: bool = False) -> list[str]:
        if form:
            if len(DB_pokemon.__pokemon_namelist_for_party) == 0:
                sql = "SELECT name FROM pokemon_data WHERE name NOT LIKE 'メガ%' OR name = 'メガニウム'"
                for row in DB_pokemon.__select(sql):
                    DB_pokemon.__pokemon_namelist_for_party.append(row["name"])
                for pokemon in remove_pokemon_name_from_party:
                    if pokemon in DB_pokemon.__pokemon_namelist_for_party:
                        DB_pokemon.__pokemon_namelist_for_party.remove(pokemon)
            return DB_pokemon.__pokemon_namelist_for_party
        else:
            if len(DB_pokemon.__pokemon_namelist) == 0:
                sql = "SELECT name FROM pokemon_data"
                for row in DB_pokemon.__select(sql):
                    DB_pokemon.__pokemon_namelist.append(row["name"])
            return DB_pokemon.__pokemon_namelist

    @staticmethod
    def get_waza_data_by_name(name: str):
        result = DB_pokemon.__select(
            "SELECT * FROM waza_data where name = ?", (name,)
        )
        return result[0]

    @staticmethod
    def get_waza_namedict() -> dict[str, str]:
        if len(DB_pokemon.__waza_namedict) == 0:
            DB_pokemon.__create_waza_namedict()
        return DB_pokemon.__waza_namedict

    @staticmethod
    def __create_waza_namedict():
        import jaconv

        if len(DB_pokemon.__waza_namedict) == 0:
            sql = "SELECT name FROM waza_data"
            for row in DB_pokemon.__select(sql):
                DB_pokemon.__waza_namedict[jaconv.hira2kata(row["name"])] = row["name"]

    @staticmethod
    def get_type_effective(
        attack_type: Types, target_type: list[Types]
    ) -> list[TypeEffective]:
        if len(DB_pokemon.__type_effectives) == 0:
            for row in DB_pokemon.__select("SELECT * FROM type_effective"):
                DB_pokemon.__type_effectives.append(
                    TypeEffective(
                        at_type=Types[row["at_type"]],
                        df_type=Types[row["df_type"]],
                        value=row["value"],
                    )
                )
        return list(
            filter(
                lambda x: x.at_type == attack_type and x.df_type in target_type,
                DB_pokemon.__type_effectives,
            )
        )

    @staticmethod
    def get_item_effect(item_name: str) -> str:
        result = DB_pokemon.__select(
            "SELECT effect FROM item_data WHERE item_name = ?", (item_name,)
        )
        return result[0]["effect"] if result and result[0]["effect"] else ""

    @staticmethod
    def get_ability_effect(ability_name: str) -> str:
        result = DB_pokemon.__select(
            "SELECT effect FROM ability_data WHERE ability_name = ?", (ability_name,)
        )
        return result[0]["effect"] if result and result[0]["effect"] else ""

    @staticmethod
    def get_mega_forms_by_no(no: int) -> list[int]:
        """図鑑番号 no のメガシンカフォーム番号リスト (10-19) を昇順で返す"""
        return [
            row["form"]
            for row in DB_pokemon.__select(
                "SELECT form FROM pokemon_data WHERE no = ? AND form >= 10 AND form <= 19 ORDER BY form",
                (no,),
            )
        ]

    @staticmethod
    def __select(sql: str, params: tuple = ()) -> list:
        result = []
        cur = DB_pokemon.__db.cursor()
        cur.execute(sql, params)
        for row in cur:
            result.append(row)
        cur.close()
        return result
