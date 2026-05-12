import dataclasses
import datetime
import sqlite3
from time import time
from typing import Optional

from component.frames.common import ChosenFrame, PartyFrame
from component.frames.whole import RecordFrame
from pokedata.exception import check_pokemon_form, unrecognizable_pokemon_no
from recog.recog import get_recog_value


@dataclasses.dataclass
class Battle:
    id: Optional[int]
    date: Optional[int]
    rule: Optional[int]
    result: Optional[int]
    favorite: Optional[int]
    opponent_tn: Optional[str]
    opponent_rate: Optional[int]
    battle_memo: Optional[str]
    player_party_num: Optional[int]
    player_party_subnum: Optional[int]
    player_pokemon1: Optional[str]
    player_pokemon2: Optional[str]
    player_pokemon3: Optional[str]
    player_pokemon4: Optional[str]
    player_pokemon5: Optional[str]
    player_pokemon6: Optional[str]
    opponent_pokemon1: Optional[str]
    opponent_pokemon2: Optional[str]
    opponent_pokemon3: Optional[str]
    opponent_pokemon4: Optional[str]
    opponent_pokemon5: Optional[str]
    opponent_pokemon6: Optional[str]
    player_choice1: Optional[str]
    player_choice2: Optional[str]
    player_choice3: Optional[str]
    player_choice4: Optional[str]
    opponent_choice1: Optional[str]
    opponent_choice2: Optional[str]
    opponent_choice3: Optional[str]
    opponent_choice4: Optional[str]

    def set_battle(
        record_frame: RecordFrame,
        party_frames: list[PartyFrame],
        chosen_frames: list[ChosenFrame],
    ):
        from pokedata.loader import get_party_csv

        file = get_party_csv().split("party/csv/")[1]

        return Battle(
            None,
            int(time()),
            get_recog_value("rule"),
            record_frame.result,
            record_frame.favo.get(),
            record_frame.tn.get(),
            record_frame.rank.get(),
            record_frame.memo.get("1.0", "end-1c"),
            file.split("-")[0],
            file.split("-")[1].split("_")[0],
            check_pokemon_form(party_frames[0].pokemon_list[0].pid),
            check_pokemon_form(party_frames[0].pokemon_list[1].pid),
            check_pokemon_form(party_frames[0].pokemon_list[2].pid),
            check_pokemon_form(party_frames[0].pokemon_list[3].pid),
            check_pokemon_form(party_frames[0].pokemon_list[4].pid),
            check_pokemon_form(party_frames[0].pokemon_list[5].pid),
            check_pokemon_form(party_frames[1].pokemon_list[0].pid),
            check_pokemon_form(party_frames[1].pokemon_list[1].pid),
            check_pokemon_form(party_frames[1].pokemon_list[2].pid),
            check_pokemon_form(party_frames[1].pokemon_list[3].pid),
            check_pokemon_form(party_frames[1].pokemon_list[4].pid),
            check_pokemon_form(party_frames[1].pokemon_list[5].pid),
            check_pokemon_form(chosen_frames[0].pokemon_list[0].pid),
            check_pokemon_form(chosen_frames[0].pokemon_list[1].pid),
            check_pokemon_form(chosen_frames[0].pokemon_list[2].pid),
            check_pokemon_form(chosen_frames[0].pokemon_list[3].pid)
            if get_recog_value("rule") == 2
            else "-1",
            check_pokemon_form(chosen_frames[1].pokemon_list[0].pid),
            check_pokemon_form(chosen_frames[1].pokemon_list[1].pid),
            check_pokemon_form(chosen_frames[1].pokemon_list[2].pid),
            check_pokemon_form(chosen_frames[1].pokemon_list[3].pid)
            if get_recog_value("rule") == 2
            else "-1",
        )


class DB_battle:
    _init_sql = """
        CREATE TABLE IF NOT EXISTS battle (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date INTEGER,
            rule INTEGER,
            result INTEGER,
            favorite INTEGER,
            opponent_tn TEXT,
            opponent_rate TEXT,
            battle_memo TEXT,
            player_party_num TEXT,
            player_party_subnum TEXT,
            player_pokemon1 TEXT,
            player_pokemon2 TEXT,
            player_pokemon3 TEXT,
            player_pokemon4 TEXT,
            player_pokemon5 TEXT,
            player_pokemon6 TEXT,
            opponent_pokemon1 TEXT,
            opponent_pokemon2 TEXT,
            opponent_pokemon3 TEXT,
            opponent_pokemon4 TEXT,
            opponent_pokemon5 TEXT,
            opponent_pokemon6 TEXT,
            player_choice1 TEXT,
            player_choice2 TEXT,
            player_choice3 TEXT,
            player_choice4 TEXT,
            opponent_choice1 TEXT,
            opponent_choice2 TEXT,
            opponent_choice3 TEXT,
            opponent_choice4 TEXT
        )
    """

    try:
        __db = sqlite3.connect("database/battle.db", check_same_thread=False)
        __db.execute(_init_sql)
        __db.commit()
    except Exception as _e:
        import tkinter.messagebox as _mb
        _mb.showerror("起動エラー", f"対戦データベースを開けませんでした。\n{_e}")
        import sys as _sys
        _sys.exit(1)

    # 相手パーティ6枠のいずれかに一致する条件（プレースホルダー版）
    _OPPO_POKE_ANY = (
        "(opponent_pokemon1 = ? OR opponent_pokemon2 = ? OR "
        "opponent_pokemon3 = ? OR opponent_pokemon4 = ? OR "
        "opponent_pokemon5 = ? OR opponent_pokemon6 = ?)"
    )

    def register_battle(battle):
        cur = DB_battle.__db.cursor()

        cur.executemany(
            "INSERT INTO battle values(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (battle,),
        )
        cur.close()
        DB_battle.__db.commit()

    @staticmethod
    def delete_latest():
        cur = DB_battle.__db.cursor()
        cur.execute("DELETE FROM battle WHERE id = (SELECT MAX(id) FROM battle)")
        DB_battle.__db.commit()
        cur.close()

    @staticmethod
    def delete_by_date_range(from_date: int, to_date: int, rule: int, party_num=0, party_subnum=0):
        parts = ["date >= ?", "date <= ?", "rule = ?"]
        params: list = [from_date, to_date, rule]
        if party_num != 0:
            parts.append("player_party_num = ?")
            params.append(party_num)
        if party_subnum != 0:
            parts.append("player_party_subnum = ?")
            params.append(party_subnum)
        cur = DB_battle.__db.cursor()
        cur.execute(f"DELETE FROM battle WHERE {' AND '.join(parts)}", tuple(params))
        DB_battle.__db.commit()
        cur.close()

    @staticmethod
    def get_battle_data_by_date(
        from_date: int,
        to_date: int,
        rule: int = 1,
        party_num=0,
        party_subnum=0,
        regend_num="0",
    ):
        where, params = DB_battle._build_base_where(
            from_date, to_date, rule, party_num, party_subnum, regend_num
        )
        return DB_battle.__select(f"SELECT * FROM battle WHERE {where}", tuple(params))

    @staticmethod
    def calc_kp(
        from_date, to_date, rule: int = 1, party_num=0, party_subnum=0, regend_num="0"
    ):
        extra_parts: list[str] = []
        extra_params: list = []
        if party_num != 0:
            extra_parts.append("player_party_num = ?")
            extra_params.append(party_num)
        if party_subnum != 0:
            extra_parts.append("player_party_subnum = ?")
            extra_params.append(party_subnum)
        if regend_num != "0":
            extra_parts.append(DB_battle._OPPO_POKE_ANY)
            extra_params.extend([regend_num] * 6)

        extra_where = (" AND " + " AND ".join(extra_parts)) if extra_parts else ""
        union_sql = " UNION ALL ".join(
            f"SELECT opponent_pokemon{i} AS pokemon FROM battle "
            f"WHERE date >= ? AND date <= ? AND rule = ?{extra_where}"
            for i in range(1, 7)
        )
        sql = (
            f"SELECT pokemon, count(*) AS kp FROM ({union_sql}) "
            "GROUP BY pokemon ORDER BY kp DESC"
        )
        branch_params = [from_date, to_date, rule] + extra_params
        return DB_battle.__select(sql, tuple(branch_params * 6))

    @staticmethod
    def count_record(
        from_date, to_date, rule: int = 1, partyNum=0, partySubNum=0, regend_num="0"
    ):
        where, params = DB_battle._build_base_where(
            from_date, to_date, rule, partyNum, partySubNum, regend_num
        )
        result = DB_battle.__select(
            f"SELECT count(*) FROM battle WHERE {where}", tuple(params)
        )
        return result[0]

    @staticmethod
    def count_win(
        from_date, to_date, rule: int = 1, partyNum=0, partySubNum=0, regend_num="0"
    ):
        where, params = DB_battle._build_base_where(
            from_date, to_date, rule, partyNum, partySubNum, regend_num
        )
        result = DB_battle.__select(
            f"SELECT count(*) FROM battle WHERE {where} AND result = ?",
            tuple(params + [1]),
        )
        return result[0]

    @staticmethod
    def get_recent_date():
        sql = "select Max(date) From battle "
        result = DB_battle.__select(sql)
        return result[0]

    @staticmethod
    def get_my_recent_party():
        sql = (
            "select player_pokemon1, player_pokemon2, player_pokemon3, "
            "player_pokemon4, player_pokemon5, player_pokemon6, "
            "player_party_num, player_party_subnum "
            "from battle where date in("
            "select MAX(date) from battle group by "
            "player_pokemon1, player_pokemon2, player_pokemon3, "
            "player_pokemon4, player_pokemon5, player_pokemon6"
            ") order by date desc"
        )
        result = DB_battle.__select(sql)
        del result[9:]
        return result

    @staticmethod
    def get_my_party(party_num=0, party_subnum=0, regend_num="0"):
        parts = ["1=1"]
        params: list = []
        if party_num != 0:
            parts.append("player_party_num = ?")
            params.append(party_num)
        if party_subnum != 0:
            parts.append("player_party_subnum = ?")
            params.append(party_subnum)
        if regend_num != "0":
            parts.append(DB_battle._OPPO_POKE_ANY)
            params.extend([regend_num] * 6)

        sql = (
            "SELECT player_pokemon1, player_pokemon2, player_pokemon3, "
            "player_pokemon4, player_pokemon5, player_pokemon6 "
            "FROM battle WHERE " + " AND ".join(parts)
        )
        result = DB_battle.__select(sql, tuple(params))
        sorted_result = set(tuple(sorted(t)) for t in result)
        result_list = list(sorted_result)
        return result_list if len(result_list) == 1 else -1

    @staticmethod
    def get_win_rate(
        pokemonList,
        from_date,
        to_date,
        rule: int = 1,
        partyNum=0,
        partySubNum=0,
        regend_num="0",
    ):
        cur = DB_battle.__db.cursor()
        base_where, base_params = DB_battle._build_base_where(
            from_date, to_date, rule, partyNum, partySubNum, regend_num
        )
        winRateList = []
        for pokeName in pokemonList:
            cur.execute(
                f"SELECT count(*) FROM battle WHERE {base_where} AND {DB_battle._OPPO_POKE_ANY}",
                tuple(base_params + [pokeName] * 6),
            )
            matchNum = cur.fetchone()
            cur.execute(
                f"SELECT count(*) FROM battle WHERE {base_where} AND result = ? AND {DB_battle._OPPO_POKE_ANY}",
                tuple(base_params + [1] + [pokeName] * 6),
            )
            winNum = cur.fetchone()
            winRateList.append(0 if matchNum[0] == 0 else winNum[0] / matchNum[0])
        return winRateList

    @staticmethod
    def get_oppo_chosen_rate(
        pokemonList,
        from_date,
        to_date,
        rule: int = 1,
        partyNum=0,
        partySubNum=0,
        regend_num="0",
    ):
        cur = DB_battle.__db.cursor()
        base_where, base_params = DB_battle._build_base_where(
            from_date, to_date, rule, partyNum, partySubNum, regend_num
        )
        _OPPO_CHOICE_ANY = (
            "(opponent_choice1 = ? OR opponent_choice2 = ? OR "
            "opponent_choice3 = ? OR opponent_choice4 = ?)"
        )
        sensyutuRateList = []
        for pokeName in pokemonList:
            cur.execute(
                f"SELECT count(*) FROM battle WHERE {base_where} AND {DB_battle._OPPO_POKE_ANY}",
                tuple(base_params + [pokeName] * 6),
            )
            matchNum = cur.fetchone()
            cur.execute(
                f"SELECT count(*) FROM battle WHERE {base_where} AND {_OPPO_CHOICE_ANY}",
                tuple(base_params + [pokeName] * 4),
            )
            winNum = cur.fetchone()
            sensyutuRateList.append(
                0 if matchNum[0] == 0 else winNum[0] / matchNum[0]
            )
        return sensyutuRateList

    @staticmethod
    def get_oppo_first_chosen_rate(
        pokemonList,
        from_date,
        to_date,
        rule: int = 1,
        partyNum=0,
        partySubNum=0,
        regend_num="0",
    ):
        cur = DB_battle.__db.cursor()
        base_where, base_params = DB_battle._build_base_where(
            from_date, to_date, rule, partyNum, partySubNum, regend_num
        )
        sensyutuRateList = []
        for pokeName in pokemonList:
            cur.execute(
                f"SELECT count(*) FROM battle WHERE {base_where} AND {DB_battle._OPPO_POKE_ANY}",
                tuple(base_params + [pokeName] * 6),
            )
            matchNum = cur.fetchone()
            cur.execute(
                f"SELECT count(*) FROM battle WHERE {base_where} AND opponent_choice1 = ?",
                tuple(base_params + [pokeName]),
            )
            firstNum = cur.fetchone()
            sensyutuRateList.append(
                0 if matchNum[0] == 0 else firstNum[0] / matchNum[0]
            )
        return sensyutuRateList

    @staticmethod
    def get_oppo_chosen_and_win_rate(
        pokemonList,
        from_date,
        to_date,
        rule: int = 1,
        partyNum=0,
        partySubNum=0,
        regend_num="0",
    ):
        cur = DB_battle.__db.cursor()
        base_where, base_params = DB_battle._build_base_where(
            from_date, to_date, rule, partyNum, partySubNum, regend_num
        )
        _OPPO_CHOICE_ANY = (
            "(opponent_choice1 = ? OR opponent_choice2 = ? OR "
            "opponent_choice3 = ? OR opponent_choice4 = ?)"
        )
        winRateList = []
        for pokeName in pokemonList:
            cur.execute(
                f"SELECT count(*) FROM battle WHERE {base_where} AND {_OPPO_CHOICE_ANY}",
                tuple(base_params + [pokeName] * 4),
            )
            matchNum = cur.fetchone()
            cur.execute(
                f"SELECT count(*) FROM battle WHERE {base_where} AND result = ? AND {_OPPO_CHOICE_ANY}",
                tuple(base_params + [1] + [pokeName] * 4),
            )
            winNum = cur.fetchone()
            winRateList.append(0 if matchNum[0] == 0 else winNum[0] / matchNum[0])
        return winRateList

    @staticmethod
    def get_oppo_first_chosen_and_win_rate(
        pokemonList,
        from_date,
        to_date,
        rule: int = 1,
        partyNum=0,
        partySubNum=0,
        regend_num="0",
    ):
        cur = DB_battle.__db.cursor()
        base_where, base_params = DB_battle._build_base_where(
            from_date, to_date, rule, partyNum, partySubNum, regend_num
        )
        winRateList = []
        for pokeName in pokemonList:
            cur.execute(
                f"SELECT count(*) FROM battle WHERE {base_where} AND opponent_choice1 = ?",
                tuple(base_params + [pokeName]),
            )
            matchNum = cur.fetchone()
            cur.execute(
                f"SELECT count(*) FROM battle WHERE {base_where} AND result = ? AND opponent_choice1 = ?",
                tuple(base_params + [1, pokeName]),
            )
            winNum = cur.fetchone()
            winRateList.append(0 if matchNum[0] == 0 else winNum[0] / matchNum[0])
        return winRateList

    @staticmethod
    def get_win_rate_per_pokemon(
        party_list,
        from_date,
        to_date,
        rule: int = 1,
        partyNum=0,
        partySubnum=0,
        regend_num="0",
    ):
        cur = DB_battle.__db.cursor()
        base_where, base_params = DB_battle._build_base_where(
            from_date, to_date, rule, partyNum, partySubnum, regend_num
        )
        _PLAYER_CHOICE_ANY = (
            "(player_choice1 = ? OR player_choice2 = ? OR "
            "player_choice3 = ? OR player_choice4 = ?)"
        )
        winRateList = []
        for pokeName in party_list:
            cur.execute(
                f"SELECT count(*) FROM battle WHERE {base_where} AND {_PLAYER_CHOICE_ANY}",
                tuple(base_params + [pokeName] * 4),
            )
            matchNum = cur.fetchone()
            cur.execute(
                f"SELECT count(*) FROM battle WHERE {base_where} AND result = ? AND {_PLAYER_CHOICE_ANY}",
                tuple(base_params + [1] + [pokeName] * 4),
            )
            winNum = cur.fetchone()
            winRateList.append(0 if matchNum[0] == 0 else winNum[0] / matchNum[0])
        return winRateList

    @staticmethod
    def get_chosen_rate(
        party_list,
        from_date,
        to_date,
        rule: int = 1,
        partyNum=0,
        partySubNum=0,
        regend_num="0",
    ):
        cur = DB_battle.__db.cursor()
        base_where, base_params = DB_battle._build_base_where(
            from_date, to_date, rule, partyNum, partySubNum, regend_num
        )
        _PLAYER_CHOICE_ANY = (
            "(player_choice1 = ? OR player_choice2 = ? OR "
            "player_choice3 = ? OR player_choice4 = ?)"
        )
        cur.execute(
            f"SELECT count(*) FROM battle WHERE {base_where}", tuple(base_params)
        )
        battleCount = cur.fetchone()
        if battleCount[0] == 0:
            return [0] * len(party_list)

        sensyutuRateList = []
        for pokeName in party_list:
            cur.execute(
                f"SELECT count(*) FROM battle WHERE {base_where} AND {_PLAYER_CHOICE_ANY}",
                tuple(base_params + [pokeName] * 4),
            )
            sensyutuCount = cur.fetchone()
            sensyutuRateList.append(sensyutuCount[0] / battleCount[0])
        return sensyutuRateList

    @staticmethod
    def get_chosen_and_win_rate(
        party_list,
        from_date,
        to_date,
        rule: int = 1,
        partyNum=0,
        partySubNum=0,
        regend_num="0",
    ):
        cur = DB_battle.__db.cursor()
        base_where, base_params = DB_battle._build_base_where(
            from_date, to_date, rule, partyNum, partySubNum, regend_num
        )
        _PLAYER_CHOICE_ANY = (
            "(player_choice1 = ? OR player_choice2 = ? OR "
            "player_choice3 = ? OR player_choice4 = ?)"
        )
        winRateList = []
        for pokeName in party_list:
            cur.execute(
                f"SELECT count(*) FROM battle WHERE {base_where} AND {_PLAYER_CHOICE_ANY}",
                tuple(base_params + [pokeName] * 4),
            )
            matchNum = cur.fetchone()
            cur.execute(
                f"SELECT count(*) FROM battle WHERE {base_where} AND result = ? AND {_PLAYER_CHOICE_ANY}",
                tuple(base_params + [1] + [pokeName] * 4),
            )
            winNum = cur.fetchone()
            winRateList.append(0 if matchNum[0] == 0 else winNum[0] / matchNum[0])
        return winRateList

    @staticmethod
    def get_first_chosen_rate(
        party_list,
        from_date,
        to_date,
        rule: int = 1,
        partyNum=0,
        partySubNum=0,
        regend_num="0",
    ):
        cur = DB_battle.__db.cursor()
        base_where, base_params = DB_battle._build_base_where(
            from_date, to_date, rule, partyNum, partySubNum, regend_num
        )
        cur.execute(
            f"SELECT count(*) FROM battle WHERE {base_where}", tuple(base_params)
        )
        battleCount = cur.fetchone()
        if battleCount[0] == 0:
            return [0] * len(party_list)

        sensyutuRateList = []
        for pokeName in party_list:
            cur.execute(
                f"SELECT count(*) FROM battle WHERE {base_where} AND player_choice1 = ?",
                tuple(base_params + [pokeName]),
            )
            sensyutuCount = cur.fetchone()
            sensyutuRateList.append(sensyutuCount[0] / battleCount[0])
        return sensyutuRateList

    @staticmethod
    def get_first_chosen_and_win_rate(
        party_list,
        from_date,
        to_date,
        rule: int = 1,
        partyNum=0,
        partySubNum=0,
        regend_num="0",
    ):
        cur = DB_battle.__db.cursor()
        base_where, base_params = DB_battle._build_base_where(
            from_date, to_date, rule, partyNum, partySubNum, regend_num
        )
        winRateList = []
        for pokeName in party_list:
            cur.execute(
                f"SELECT count(*) FROM battle WHERE {base_where} AND player_choice1 = ?",
                tuple(base_params + [pokeName]),
            )
            matchNum = cur.fetchone()
            cur.execute(
                f"SELECT count(*) FROM battle WHERE {base_where} AND result = ? AND player_choice1 = ?",
                tuple(base_params + [1, pokeName]),
            )
            winNum = cur.fetchone()
            winRateList.append(0 if matchNum[0] == 0 else winNum[0] / matchNum[0])
        return winRateList

    @staticmethod
    def chenge_date_from_datetime_to_unix(
        fromYear: int,
        fromMonth: int,
        fromDate: int,
        toYear: int,
        toMonth: int,
        toDate: int,
        time9Bl: bool,
        time23Bl: bool = False,
    ):
        if time9Bl:
            from_date = int(
                datetime.datetime(fromYear, fromMonth, fromDate, 11, 0, 0).timestamp()
            )
        else:
            from_date = int(
                datetime.datetime(fromYear, fromMonth, fromDate).timestamp()
            )
        if time23Bl:
            to_date = int(
                datetime.datetime(toYear, toMonth, toDate, 10, 59, 59).timestamp()
            )
        else:
            to_date = int(
                datetime.datetime(toYear, toMonth, toDate, 23, 59, 59).timestamp()
            )
        return from_date, to_date

    @staticmethod
    def record_search_full(pokelist: list[str]):
        paramList = tuple(pokelist)
        sql = "SELECT * FROM battle WHERE opponent_pokemon1=? AND opponent_pokemon2=? AND opponent_pokemon3=? AND opponent_pokemon4=? AND opponent_pokemon5=? AND opponent_pokemon6 =?;"
        result1 = DB_battle.__select(sql, paramList)

        for no in unrecognizable_pokemon_no:
            if str(no) + "-0" in pokelist or str(no) + "-1" in pokelist:
                paramList = (
                    [
                        str(no) + "-1" if item == str(no) + "-0" else item
                        for item in pokelist
                    ]
                    if str(no) + "-0" in pokelist
                    else [
                        str(no) + "-0" if item == str(no) + "-1" else item
                        for item in pokelist
                    ]
                )
                result2 = DB_battle.__select(sql, paramList)
                result1.extend(result2)

        return list(set(result1))

    @staticmethod
    def record_search(pokelist: list[str]):
        paramList = tuple(pokelist)
        result_full = DB_battle.record_search_full(pokelist)

        sql = "SELECT * FROM battle WHERE (opponent_pokemon1 IN (?, ?, ?, ?, ?, ?)) AND (opponent_pokemon2 IN (?, ?, ?, ?, ?, ?)) AND (opponent_pokemon3 IN (?, ?, ?, ?, ?, ?)) AND (opponent_pokemon4 IN (?, ?, ?, ?, ?, ?)) AND (opponent_pokemon5 IN (?, ?, ?, ?, ?, ?)) AND (opponent_pokemon6 IN (?, ?, ?, ?, ?, ?)) AND (SELECT COUNT(DISTINCT col) FROM (SELECT opponent_pokemon1 AS col FROM battle UNION ALL SELECT opponent_pokemon2 AS col FROM battle UNION ALL SELECT opponent_pokemon3 AS col FROM battle UNION ALL SELECT opponent_pokemon4 AS col FROM battle UNION ALL SELECT opponent_pokemon5 AS col FROM battle UNION ALL SELECT opponent_pokemon6 AS col FROM battle) AS subquery WHERE col IN (?, ?, ?, ?, ?, ?)) = 6;"
        result_all_1 = DB_battle.__select(sql, paramList * 7)

        for no in unrecognizable_pokemon_no:
            if str(no) + "-0" in pokelist or str(no) + "-1" in pokelist:
                paramList = (
                    [
                        str(no) + "-1" if item == str(no) + "-0" else item
                        for item in pokelist
                    ]
                    if str(no) + "-0" in pokelist
                    else [
                        str(no) + "-0" if item == str(no) + "-1" else item
                        for item in pokelist
                    ]
                )
                result_all_2 = DB_battle.__select(sql, paramList * 7)
                result_all_1.extend(result_all_2)

        result_all = list(set(result_all_1))
        return [item for item in result_all if item not in result_full]

    @staticmethod
    def _build_base_where(
        from_date, to_date, rule, party_num=0, party_subnum=0, regend_num="0"
    ) -> tuple[str, list]:
        parts = ["date >= ?", "date <= ?", "rule = ?"]
        params: list = [from_date, to_date, rule]
        if party_num != 0:
            parts.append("player_party_num = ?")
            params.append(party_num)
        if party_subnum != 0:
            parts.append("player_party_subnum = ?")
            params.append(party_subnum)
        if regend_num != "0":
            parts.append(DB_battle._OPPO_POKE_ANY)
            params.extend([regend_num] * 6)
        return " AND ".join(parts), params

    @staticmethod
    def __select(sql: str, param: tuple = ()) -> list:
        result = []
        cur = DB_battle.__db.cursor()
        cur.execute(sql, param)
        for row in cur:
            result.append(row)
        return result
