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
    opponent_rank: Optional[int]
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
    __db = sqlite3.connect("database/battle.db", check_same_thread=False)

    def register_battle(battle):
        cur = DB_battle.__db.cursor()

        cur.executemany(
            "INSERT INTO battle values(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (battle,),
        )
        cur.close()
        DB_battle.__db.commit()

    @staticmethod
    def get_battle_data_by_date(
        from_date: int,
        to_date: int,
        rule: int = 1,
        party_num=0,
        party_subnum=0,
        regend_num="0",
    ):
        # 動的条件の構築
        condition = f"date BETWEEN {from_date} and {to_date} and rule = {rule}"
        if party_num != 0:
            condition += f" and player_party_num = {party_num}"
        if party_subnum != 0:
            condition += f" and player_party_subnum = {party_subnum}"
        if regend_num != "0":
            condition += (
                f" and (opponent_pokemon1 = '{regend_num}' or opponent_pokemon2 = '{regend_num}' or "
                f"opponent_pokemon3 = '{regend_num}' or opponent_pokemon4 = '{regend_num}' or "
                f"opponent_pokemon5 = '{regend_num}' or opponent_pokemon6 = '{regend_num}')"
            )

        # SQL文の生成
        sql = f"SELECT * FROM battle WHERE {condition}"

        # 実行結果を取得
        result = DB_battle.__select(sql)
        return result

    @staticmethod
    def calc_kp(
        from_date, to_date, rule: int = 1, party_num=0, party_subnum=0, regend_num="0"
    ):
        # ベースとなるSQL文
        sql_base = """
            select pokemon, count(*) as kp
            from (
                select opponent_pokemon1 as pokemon
                from battle
                where date >= '{0}' and date <= '{1}' and rule = {2}
                {3}
                union ALL
                select opponent_pokemon2 as pokemon
                from battle
                where date >= '{0}' and date <= '{1}' and rule = {2}
                {3}
                union ALL
                select opponent_pokemon3 as pokemon
                from battle
                where date >= '{0}' and date <= '{1}' and rule = {2}
                {3}
                union ALL
                select opponent_pokemon4 as pokemon
                from battle
                where date >= '{0}' and date <= '{1}' and rule = {2}
                {3}
                union ALL
                select opponent_pokemon5 as pokemon
                from battle
                where date >= '{0}' and date <= '{1}' and rule = {2}
                {3}
                union ALL
                select opponent_pokemon6 as pokemon
                from battle
                where date >= '{0}' and date <= '{1}' and rule = {2}
                {3}
            )
            GROUP by pokemon
            ORDER by kp DESC
        """

        # 動的な条件を構築
        conditions = []

        # party_numが0でない場合に条件追加
        if party_num != 0:
            conditions.append(f"player_party_num = {party_num}")

        # party_subnumが0でない場合に条件追加
        if party_subnum != 0:
            conditions.append(f"player_party_subnum = {party_subnum}")

        # regend_numが"0"でない場合に条件追加 (文字列として扱う)
        if regend_num != "0":
            conditions.append(
                f"(opponent_pokemon1 = '{regend_num}' or opponent_pokemon2 = '{regend_num}' or "
                f"opponent_pokemon3 = '{regend_num}' or opponent_pokemon4 = '{regend_num}' or "
                f"opponent_pokemon5 = '{regend_num}' or opponent_pokemon6 = '{regend_num}')"
            )

        # 条件を結合
        where_clause = " and ".join(conditions)
        if where_clause:
            where_clause = " and " + where_clause  # `WHERE` に追加する形にする

        # SQL文を組み立て
        sql = sql_base.format(from_date, to_date, rule, where_clause)

        # SQLを実行して結果を返す
        result = DB_battle.__select(sql)
        return result

    @staticmethod
    def count_record(
        from_date, to_date, rule: int = 1, partyNum=0, partySubNum=0, regend_num="0"
    ):
        # 動的に条件を追加
        conditions = []
        if partyNum != 0:
            conditions.append(f"player_party_num = {partyNum}")
        if partySubNum != 0:
            conditions.append(f"player_party_subnum = {partySubNum}")
        if regend_num != "0":
            conditions.append(
                f"(opponent_pokemon1 = '{regend_num}' or opponent_pokemon2 = '{regend_num}' or "
                f"opponent_pokemon3 = '{regend_num}' or opponent_pokemon4 = '{regend_num}' or "
                f"opponent_pokemon5 = '{regend_num}' or opponent_pokemon6 = '{regend_num}')"
            )

        where_clause = " and ".join(conditions)
        if where_clause:
            where_clause = " and " + where_clause

        sql = f"select count(*) from battle where date >= '{from_date}' and date <= '{to_date}' and rule = {rule} {where_clause}"
        result = DB_battle.__select(sql)
        return result[0]

    @staticmethod
    def count_win(
        from_date, to_date, rule: int = 1, partyNum=0, partySubNum=0, regend_num="0"
    ):
        # 動的に条件を追加
        conditions = []
        if partyNum != 0:
            conditions.append(f"player_party_num = {partyNum}")
        if partySubNum != 0:
            conditions.append(f"player_party_subnum = {partySubNum}")
        if regend_num != "0":
            conditions.append(
                f"(opponent_pokemon1 = '{regend_num}' or opponent_pokemon2 = '{regend_num}' or "
                f"opponent_pokemon3 = '{regend_num}' or opponent_pokemon4 = '{regend_num}' or "
                f"opponent_pokemon5 = '{regend_num}' or opponent_pokemon6 = '{regend_num}')"
            )

        where_clause = " and ".join(conditions)
        if where_clause:
            where_clause = " and " + where_clause

        sql = f"select count(*) from battle where date >= '{from_date}' and date <= '{to_date}' and rule = {rule} and result = 1 {where_clause}"
        result = DB_battle.__select(sql)
        return result[0]

    @staticmethod
    def get_recent_date():
        sql = "select Max(date) From battle "
        result = DB_battle.__select(sql)
        return result[0]

    @staticmethod
    def get_my_recent_party():
        sql = "select player_pokemon1, player_pokemon2, player_pokemon3, player_pokemon4, player_pokemon5, player_pokemon6, player_party_num, player_party_subnum from battle where date in(select MAX(date) from battle group by player_pokemon1, player_pokemon2, player_pokemon3, player_pokemon4, player_pokemon5, player_pokemon6) order by date desc"
        result = DB_battle.__select(sql)
        del result[9:]
        return result

    @staticmethod
    def get_my_party(party_num=0, party_subnum=0, regend_num="0"):
        # SQL条件を動的に構築
        conditions = []

        # party_num が指定されている場合、条件に追加
        if party_num != 0:
            conditions.append(f"player_party_num = {party_num}")

        # party_subnum が指定されている場合、条件に追加
        if party_subnum != 0:
            conditions.append(f"player_party_subnum = {party_subnum}")

        # regend_num が指定されている場合、opponent_pokemon1~opponent_pokemon6 に追加
        if regend_num != "0":
            conditions.append(
                f"(opponent_pokemon1 = '{regend_num}' or opponent_pokemon2 = '{regend_num}' or "
                f"opponent_pokemon3 = '{regend_num}' or opponent_pokemon4 = '{regend_num}' or "
                f"opponent_pokemon5 = '{regend_num}' or opponent_pokemon6 = '{regend_num}')"
            )

        # WHERE句の動的構築
        where_clause = " and ".join(conditions)
        if where_clause:
            where_clause = " and " + where_clause

        # SQL文を作成
        sql = f"select player_pokemon1, player_pokemon2, player_pokemon3, player_pokemon4, player_pokemon5, player_pokemon6 from battle where 1=1 {where_clause}"

        # SQLを実行し、結果を取得
        result = DB_battle.__select(sql)

        # 結果をソートして処理
        sorted_result = set(tuple(sorted(t)) for t in result)
        result_list = list(sorted_result)

        # 一意な結果が1つならその結果を返す、それ以外は-1を返す
        if len(result_list) == 1:
            return result_list
        else:
            return -1

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
        winRateList = []

        for pokeName in pokemonList:
            # 動的に条件を追加
            conditions = []
            if partyNum != 0:
                conditions.append(f"player_party_num = {partyNum}")
            if partySubNum != 0:
                conditions.append(f"player_party_subnum = {partySubNum}")
            if regend_num != "0":
                conditions.append(
                    f"(opponent_pokemon1 = '{regend_num}' or opponent_pokemon2 = '{regend_num}' or "
                    f"opponent_pokemon3 = '{regend_num}' or opponent_pokemon4 = '{regend_num}' or "
                    f"opponent_pokemon5 = '{regend_num}' or opponent_pokemon6 = '{regend_num}')"
                )
            where_clause = " and ".join(conditions)
            if where_clause:
                where_clause = " and " + where_clause
            sql = f"select count(*) from battle where date >={from_date} and date <={to_date} and rule = {rule} {where_clause} and (opponent_pokemon1='{pokeName}' or opponent_pokemon2='{pokeName}' or opponent_pokemon3='{pokeName}' or opponent_pokemon4='{pokeName}' or opponent_pokemon5='{pokeName}' or opponent_pokemon6='{pokeName}')"

            cur.execute(sql)
            matchNum = cur.fetchone()

            sql = f"select count(*) from battle where date >={from_date} and date <={to_date} and rule = {rule} and result = 1 {where_clause} and (opponent_pokemon1='{pokeName}' or opponent_pokemon2='{pokeName}' or opponent_pokemon3='{pokeName}' or opponent_pokemon4='{pokeName}' or opponent_pokemon5='{pokeName}' or opponent_pokemon6='{pokeName}')"
            cur.execute(sql)
            winNum = cur.fetchone()

            if matchNum[0] == 0:
                winRateList.append(0)
            else:
                winRateList.append(winNum[0] / matchNum[0])

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
        sensyutuRateList = []

        for pokeName in pokemonList:
            # 基本のパラメータリスト
            conditions = []
            if partyNum != 0:
                conditions.append(f"player_party_num = {partyNum}")
            if partySubNum != 0:
                conditions.append(f"player_party_subnum = {partySubNum}")
            if regend_num != "0":
                conditions.append(
                    f"(opponent_pokemon1 = '{regend_num}' or opponent_pokemon2 = '{regend_num}' or "
                    f"opponent_pokemon3 = '{regend_num}' or opponent_pokemon4 = '{regend_num}' or "
                    f"opponent_pokemon5 = '{regend_num}' or opponent_pokemon6 = '{regend_num}')"
                )
            where_clause = " and ".join(conditions)
            if where_clause:
                where_clause = " and " + where_clause

            # 対戦回数を取得
            sql = f"select count(*) from battle where date >= {from_date} and date <= {to_date} and rule = {rule} {where_clause} and (opponent_pokemon1 = '{pokeName}' or opponent_pokemon2 = '{pokeName}' or opponent_pokemon3 = '{pokeName}' or opponent_pokemon4 = '{pokeName}' or opponent_pokemon5 = '{pokeName}' or opponent_pokemon6 = '{pokeName}')"
            cur.execute(sql)
            matchNum = cur.fetchone()

            # 選択回数を取得
            sql = f"select count(*) from battle where date >= {from_date} and date <= {to_date} and rule = {rule} {where_clause} and (opponent_choice1 = '{pokeName}' or opponent_choice2 = '{pokeName}' or opponent_choice3 = '{pokeName} or opponent_choice4 = '{pokeName}')"
            cur.execute(sql)
            winNum = cur.fetchone()

            if matchNum[0] == 0:
                sensyutuRateList.append(0)
            else:
                sensyutuRateList.append(winNum[0] / matchNum[0])

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
        sensyutuRateList = []

        for pokeName in pokemonList:
            # 条件を動的に構築
            conditions = []
            if partyNum != 0:
                conditions.append(f"player_party_num = {partyNum}")
            if partySubNum != 0:
                conditions.append(f"player_party_subnum = {partySubNum}")
            if regend_num != "0":
                conditions.append(
                    f"(opponent_pokemon1 = '{regend_num}' or opponent_pokemon2 = '{regend_num}' or "
                    f"opponent_pokemon3 = '{regend_num}' or opponent_pokemon4 = '{regend_num}' or "
                    f"opponent_pokemon5 = '{regend_num}' or opponent_pokemon6 = '{regend_num}')"
                )

            # WHERE句の動的構築
            where_clause = " and ".join(conditions)
            if where_clause:
                where_clause = " and " + where_clause

            # 選出回数を取得
            sql = f"select count(*) from battle where date >= {from_date} and date <= {to_date} and rule = {rule} {where_clause} and (opponent_pokemon1 = '{pokeName}' or opponent_pokemon2 = '{pokeName}' or opponent_pokemon3 = '{pokeName}' or opponent_pokemon4 = '{pokeName}' or opponent_pokemon5 = '{pokeName}' or opponent_pokemon6 = '{pokeName}')"
            cur.execute(sql)
            matchNum = cur.fetchone()

            # 先発回数を取得
            sql = f"select count(*) from battle where date >= {from_date} and date <= {to_date} and rule = {rule} {where_clause} and opponent_choice1 = '{pokeName}'"
            cur.execute(sql)
            firstNum = cur.fetchone()

            # 先発率を計算
            if matchNum[0] == 0:
                sensyutuRateList.append(0)
            else:
                sensyutuRateList.append(firstNum[0] / matchNum[0])

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
        winRateList = []

        for pokeName in pokemonList:
            # 基本のパラメータリスト
            conditions = []
            if partyNum != 0:
                conditions.append(f"player_party_num = {partyNum}")
            if partySubNum != 0:
                conditions.append(f"player_party_subnum = {partySubNum}")
            if regend_num != "0":
                conditions.append(
                    f"(opponent_pokemon1 = '{regend_num}' or opponent_pokemon2 = '{regend_num}' or "
                    f"opponent_pokemon3 = '{regend_num}' or opponent_pokemon4 = '{regend_num}' or "
                    f"opponent_pokemon5 = '{regend_num}' or opponent_pokemon6 = '{regend_num}')"
                )
            where_clause = " and ".join(conditions)
            if where_clause:
                where_clause = " and " + where_clause

            # 選出回数を取得
            sql = f"select count(*) from battle where date >= {from_date} and date <= {to_date} and rule = {rule} {where_clause} and (opponent_choice1 = '{pokeName}' or opponent_choice2 = '{pokeName}' or opponent_choice3 = '{pokeName}' or opponent_choice4 = '{pokeName}')"
            cur.execute(sql)
            matchNum = cur.fetchone()

            # 勝利回数を取得
            sql = f"select count(*) from battle where date >= {from_date} and date <= {to_date} and rule = {rule} {where_clause} and result = 1 and (opponent_choice1 = '{pokeName}' or opponent_choice2 = '{pokeName}' or opponent_choice3 = '{pokeName}' or opponent_choice4 = '{pokeName}')"
            cur.execute(sql)
            winNum = cur.fetchone()

            if matchNum[0] == 0:
                winRateList.append(0)
            else:
                winRateList.append(winNum[0] / matchNum[0])

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
        winRateList = []

        for pokeName in pokemonList:
            # 条件を動的に構築
            conditions = []
            if partyNum != 0:
                conditions.append(f"player_party_num = {partyNum}")
            if partySubNum != 0:
                conditions.append(f"player_party_subnum = {partySubNum}")
            if regend_num != "0":
                conditions.append(
                    f"(opponent_pokemon1 = '{regend_num}' or opponent_pokemon2 = '{regend_num}' or "
                    f"opponent_pokemon3 = '{regend_num}' or opponent_pokemon4 = '{regend_num}' or "
                    f"opponent_pokemon5 = '{regend_num}' or opponent_pokemon6 = '{regend_num}')"
                )

            # WHERE句の動的構築
            where_clause = " and ".join(conditions)
            if where_clause:
                where_clause = " and " + where_clause

            # 選出回数を取得
            sql = f"select count(*) from battle where date >= {from_date} and date <= {to_date} and rule = {rule} {where_clause} and opponent_choice1 = '{pokeName}'"
            cur.execute(sql)
            matchNum = cur.fetchone()

            # 勝利回数を取得
            sql = f"select count(*) from battle where date >= {from_date} and date <= {to_date} and rule = {rule} {where_clause} and result = 1 and opponent_choice1 = '{pokeName}'"
            cur.execute(sql)
            winNum = cur.fetchone()

            # 勝率を計算
            if matchNum[0] == 0:
                winRateList.append(0)
            else:
                winRateList.append(winNum[0] / matchNum[0])

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
        winRateList = []

        for pokeName in party_list:
            # 条件の初期化
            condition = f"date >= {from_date} and date <= {to_date} and rule = {rule}"

            # 条件の追加
            if partyNum != 0:
                condition += f" and player_party_num = {partyNum}"
            if partySubnum != 0:
                condition += f" and player_party_subnum = {partySubnum}"
            if regend_num != "0":
                condition += (
                    f" and (opponent_pokemon1 = '{regend_num}' or opponent_pokemon2 = '{regend_num}' or "
                    f"opponent_pokemon3 = '{regend_num}' or opponent_pokemon4 = '{regend_num}' or "
                    f"opponent_pokemon5 = '{regend_num}' or opponent_pokemon6 = '{regend_num}')"
                )

            # マッチ数のSQL
            sql_match = (
                f"select count(*) from battle where {condition} and "
                f"(player_choice1 = '{pokeName}' or player_choice2 = '{pokeName}' or player_choice3 = '{pokeName}' or player_choice4 = '{pokeName}')"
            )
            cur.execute(sql_match)
            matchNum = cur.fetchone()

            # 勝利数のSQL
            sql_win = (
                f"select count(*) from battle where {condition} and result = 1 and "
                f"(player_choice1 = '{pokeName}' or player_choice2 = '{pokeName}' or player_choice3 = '{pokeName}' or player_choice4 = '{pokeName}')"
            )
            cur.execute(sql_win)
            winNum = cur.fetchone()

            # 勝率計算
            if matchNum[0] == 0:
                winRateList.append(0)
            else:
                winRateList.append(winNum[0] / matchNum[0])

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

        # 条件の初期化
        condition = f"date >= {from_date} and date <= {to_date} and rule = {rule}"

        # 動的に条件を追加
        if partyNum != 0:
            condition += f" and player_party_num = {partyNum}"
        if partySubNum != 0:
            condition += f" and player_party_subnum = {partySubNum}"
        if regend_num != "0":
            condition += (
                f" and (opponent_pokemon1 = '{regend_num}' or opponent_pokemon2 = '{regend_num}' or "
                f"opponent_pokemon3 = '{regend_num}' or opponent_pokemon4 = '{regend_num}' or "
                f"opponent_pokemon5 = '{regend_num}' or opponent_pokemon6 = '{regend_num}')"
            )

        # 総バトル数を取得
        sql_battle_count = f"select count(*) from battle where {condition}"
        cur.execute(sql_battle_count)
        battleCount = cur.fetchone()

        if battleCount[0] == 0:
            return [0] * len(party_list)  # バトルがない場合はすべて0を返す

        sensyutuRateList = []

        # 各ポケモンの選出率を計算
        for pokeName in party_list:
            sql_sensyutu_count = (
                f"select count(*) from battle where {condition} and "
                f"(player_choice1 = '{pokeName}' or player_choice2 = '{pokeName}' or player_choice3 = '{pokeName}' or player_choice4 = '{pokeName}')"
            )
            cur.execute(sql_sensyutu_count)
            sensyutuCount = cur.fetchone()

            # 選出率を計算してリストに追加
            sensyutuRate = (
                sensyutuCount[0] / battleCount[0] if battleCount[0] != 0 else 0
            )
            sensyutuRateList.append(sensyutuRate)

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
        winRateList = []

        # 基本条件
        condition = f"date >= {from_date} and date <= {to_date} and rule = {rule}"

        # 動的条件追加
        if partyNum != 0:
            condition += f" and player_party_num = {partyNum}"
        if partySubNum != 0:
            condition += f" and player_party_subnum = {partySubNum}"
        if regend_num != "0":
            condition += (
                f" and (opponent_pokemon1 = '{regend_num}' or opponent_pokemon2 = '{regend_num}' or "
                f"opponent_pokemon3 = '{regend_num}' or opponent_pokemon4 = '{regend_num}' or "
                f"opponent_pokemon5 = '{regend_num}' or opponent_pokemon6 = '{regend_num}')"
            )

        # 各ポケモンごとの選出率と勝率を計算
        for pokeName in party_list:
            # 試合数取得
            sql_match_count = (
                f"select count(*) from battle where {condition} and "
                f"(player_choice1 = '{pokeName}' or player_choice2 = '{pokeName}' or player_choice3 = '{pokeName}' or player_choice4 = '{pokeName}')"
            )
            cur.execute(sql_match_count)
            matchNum = cur.fetchone()

            # 勝利数取得
            sql_win_count = (
                f"select count(*) from battle where {condition} and result = 1 and "
                f"(player_choice1 = '{pokeName}' or player_choice2 = '{pokeName}' or player_choice3 = '{pokeName}' or player_choice4 = '{pokeName}')"
            )
            cur.execute(sql_win_count)
            winNum = cur.fetchone()

            # 勝率計算
            if matchNum[0] == 0:
                winRateList.append(0)
            else:
                winRateList.append(winNum[0] / matchNum[0])

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

        # 基本条件
        condition = f"date >= {from_date} and date <= {to_date} and rule = {rule}"

        # 動的条件追加
        if partyNum != 0:
            condition += f" and player_party_num = {partyNum}"
        if partySubNum != 0:
            condition += f" and player_party_subnum = {partySubNum}"
        if regend_num != "0":
            condition += (
                f" and (opponent_pokemon1 = '{regend_num}' or opponent_pokemon2 = '{regend_num}' or "
                f"opponent_pokemon3 = '{regend_num}' or opponent_pokemon4 = '{regend_num}' or "
                f"opponent_pokemon5 = '{regend_num}' or opponent_pokemon6 = '{regend_num}')"
            )

        # 全体の試合数を取得
        sql_battle_count = f"select count(*) from battle where {condition}"
        cur.execute(sql_battle_count)
        battleCount = cur.fetchone()

        if battleCount[0] == 0:
            return [0] * len(party_list)  # 試合がない場合は全て0を返す

        # 選出率リスト
        sensyutuRateList = []

        # 各ポケモンごとの先発回数を取得
        for pokeName in party_list:
            sql_chosen_count = f"select count(*) from battle where {condition} and player_choice1 = '{pokeName}'"
            cur.execute(sql_chosen_count)
            sensyutuCount = cur.fetchone()

            # 選出率計算
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
        winRateList = []

        # 動的条件の構築
        condition = f"date >= {from_date} and date <= {to_date} and rule = {rule}"
        if partyNum != 0:
            condition += f" and player_party_num = {partyNum}"
        if partySubNum != 0:
            condition += f" and player_party_subnum = {partySubNum}"
        if regend_num != "0":
            condition += (
                f" and (opponent_pokemon1 = '{regend_num}' or opponent_pokemon2 = '{regend_num}' or "
                f"opponent_pokemon3 = '{regend_num}' or opponent_pokemon4 = '{regend_num}' or "
                f"opponent_pokemon5 = '{regend_num}' or opponent_pokemon6 = '{regend_num}')"
            )

        # 各ポケモンごとの選出率と勝率の計算
        for pokeName in party_list:
            # 選出数を取得
            sql_match_count = f"select count(*) from battle where {condition} and player_choice1 = '{pokeName}'"
            cur.execute(sql_match_count)
            matchNum = cur.fetchone()

            # 勝利数を取得
            sql_win_count = f"select count(*) from battle where {condition} and result = 1 and player_choice1 = '{pokeName}'"
            cur.execute(sql_win_count)
            winNum = cur.fetchone()

            # 勝率の計算
            if matchNum[0] == 0:
                winRateList.append(0)
            else:
                winRateList.append(winNum[0] / matchNum[0])

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
    ):
        if time9Bl:
            from_date = int(
                datetime.datetime(fromYear, fromMonth, fromDate, 11, 0, 0).timestamp()
            )
        else:
            from_date = int(
                datetime.datetime(fromYear, fromMonth, fromDate).timestamp()
            )
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
        # 完全一致のレコードを削除
        return [item for item in result_all if item not in result_full]

    @staticmethod
    def __select(sql: str, param: tuple = ()) -> list:
        result = []
        cur = DB_battle.__db.cursor()
        cur.execute(sql, param)
        for row in cur:
            result.append(row)
        return result
