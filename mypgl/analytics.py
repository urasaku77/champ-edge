import datetime
import json
import re
import tkinter

from PIL import Image, ImageTk

from database.battle import DB_battle
from mypgl.const import Const
from recog.recog import get_recog_value


class Analytics(tkinter.Toplevel):
    def __init__(self):
        super().__init__()
        self.title("対戦分析")

        before_recent_date = DB_battle.get_recent_date()[0]
        self.recent_date = (
            datetime.date(
                datetime.datetime.fromtimestamp(before_recent_date).year,
                datetime.datetime.fromtimestamp(before_recent_date).month,
                datetime.datetime.fromtimestamp(before_recent_date).day,
            )
            if before_recent_date is not None
            else datetime.datetime.today()
        )
        self.party_num = 0
        self.party_subnum = 0

        self.kp_list = []
        self.pokemon_list = []
        self.result_1_list = []
        self.result_2_list = []
        self.result_1_label_list = []
        self.result_2_label_list = []

        self.img_list = []
        self.canvas_list = []

        self.record_count_label = None
        self.whole_win_rate_label = None

        self.sort_condition_options = [("KP（選出/初手）", 0), ("勝率", 1)]
        self.sort_line_options = [("降順", False), ("昇順", True)]

        self.display_gui(self.recent_date)
        self.update_result()

        for i in range(50):
            rank_label = tkinter.Label(self, text=str(i + 1) + "位")
            rank_label.place(x=Const.list2[i][1] - 40, y=Const.list2[i][2])

    def open(self):
        self.focus_set()
        self.geometry("1280x720")

    def _load_seasons(self) -> list:
        try:
            with open("recog/season.json", "r", encoding="utf-8") as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return []

    def _on_season_select(self, name: str):
        is_custom = name == "カスタム"
        state = "normal" if is_custom else "disabled"
        for menu in [
            self.from_year_menu, self.from_month_menu, self.from_date_menu,
            self.to_year_menu, self.to_month_menu, self.to_date_menu,
        ]:
            menu.config(state=state)
        if not is_custom:
            season = next((s for s in self._seasons if s["name"] == name), None)
            if season is None:
                return
            self.from_year_var.set(season["from_year"])
            self.from_month_var.set(season["from_month"])
            self.from_date_var.set(season["from_date"])
            self.to_year_var.set(season["to_year"])
            self.to_month_var.set(season["to_month"])
            self.to_date_var.set(season["to_date"])

    def display_gui(self, search_date: datetime.datetime):
        self._seasons = self._load_seasons()
        season_names = ["カスタム"] + [s["name"] for s in self._seasons]
        season_label = tkinter.Label(self, text="シーズン")
        season_label.place(x=Const.searchX, y=Const.searchY - Const.searchDY)
        self.season_var = tkinter.StringVar(self, value="カスタム")
        season_menu = tkinter.OptionMenu(
            self, self.season_var, *season_names, command=self._on_season_select
        )
        season_menu.place(x=Const.searchX, y=Const.searchY)

        self.time9_bln = tkinter.BooleanVar()
        self.time9_bln.set(True)
        time9_check = tkinter.Checkbutton(
            self, variable=self.time9_bln, text="開始日を11時以降にする"
        )
        time9_check.place(x=Const.searchX + 120, y=Const.searchY - Const.searchDY)

        self.time23_bln = tkinter.BooleanVar()
        self.time23_bln.set(True)
        time23_check = tkinter.Checkbutton(
            self, variable=self.time23_bln, text="終了日を11時までにする"
        )
        time23_check.place(x=Const.searchX + 320, y=Const.searchY - Const.searchDY)

        rank_label = tkinter.Label(self, text="パーティ絞り込み")
        rank_label.place(x=Const.searchX, y=Const.searchY + Const.searchDY * 2)

        self.from_year_var = tkinter.IntVar(self)
        self.from_year_var.set(int(search_date.year))
        self.from_year_menu = tkinter.OptionMenu(self, self.from_year_var, *Const.yearList)
        self.from_year_menu.place(x=Const.searchX + 120, y=Const.searchY)
        self.from_month_var = tkinter.IntVar(self)
        self.from_month_var.set(int(search_date.month))
        self.from_date_var = tkinter.IntVar(self)
        self.from_date_var.set(13 if search_date.day > 13 else 1)
        self.from_month_menu = tkinter.OptionMenu(
            self, self.from_month_var, *Const.monthList
        )
        self.from_month_menu.place(x=Const.searchX + 190, y=Const.searchY)
        self.from_date_menu = tkinter.OptionMenu(self, self.from_date_var, *Const.dateList)
        self.from_date_menu.place(x=Const.searchX + 240, y=Const.searchY)

        mack_label = tkinter.Label(self, text=" ~ ", font=Const.titleFont)
        mack_label.place(x=Const.searchX + 290, y=Const.searchY)

        self.to_year_var = tkinter.IntVar(self)
        self.to_year_var.set(int(search_date.year))
        self.to_year_menu = tkinter.OptionMenu(self, self.to_year_var, *Const.yearList)
        self.to_year_menu.place(x=Const.searchX + 320, y=Const.searchY)
        self.to_month_var = tkinter.IntVar(self)
        self.to_month_var.set(int(search_date.month))
        self.to_date_var = tkinter.IntVar(self)
        self.to_date_var.set(int(search_date.day))
        self.to_month_menu = tkinter.OptionMenu(self, self.to_month_var, *Const.monthList)
        self.to_month_menu.place(x=Const.searchX + 390, y=Const.searchY)
        self.to_date_menu = tkinter.OptionMenu(self, self.to_date_var, *Const.dateList)
        self.to_date_menu.place(x=Const.searchX + 450, y=Const.searchY)

        num_label = tkinter.Label(self, text="番号")
        num_label.place(x=Const.searchX, y=Const.searchY + Const.searchDY * 3)
        self.num_txt = tkinter.Entry(self, width=Const.txtboxWidth)
        self.num_txt.place(x=Const.searchX + 40, y=Const.searchY + Const.searchDY * 3)
        sub_num_label = tkinter.Label(self, text="連番")
        sub_num_label.place(x=Const.searchX + 90, y=Const.searchY + Const.searchDY * 3)
        self.sub_num_txt = tkinter.Entry(self, width=Const.txtboxWidth)
        self.sub_num_txt.place(
            x=Const.searchX + 130, y=Const.searchY + Const.searchDY * 3
        )

        # --- 伝説絞り込み機能（未使用） ---
        # self.regend_filter_bln = tkinter.BooleanVar()
        # self.regend_filter_bln.set(False)
        # self.regend_filter_btn = tkinter.Checkbutton(
        #     self,
        #     variable=self.regend_filter_bln,
        #     text="伝説絞込",
        #     command=self.set_regend,
        # )
        # self.regend_filter_btn.place(
        #     x=Const.searchX + 200, y=Const.searchY + Const.searchDY * 2.7
        # )
        # self.regends_dict = {
        #     "コライドン": "1007-0",
        #     "ミライドン": "1008-0",
        #     "黒バドレックス": "898-2",
        #     "ザシアン（王）": "888-1",
        #     "テラパゴス": "1024-0",
        #     "ホウオウ": "250-0",
        #     "ルギア": "249-0",
        #     "ルナアーラ": "792-0",
        #     "白バドレックス": "898-1",
        #     "ムゲンダイナ": "890-0",
        #     "カイオーガ": "382-0",
        #     "レックウザ": "384-0",
        #     "日食ネクロズマ": "800-1",
        #     "黒キュレム": "646-2",
        #     "ザマゼンタ（王）": "889-1",
        #     "グラードン": "383-0",
        #     "白キュレム": "646-1",
        #     "ソルガレオ": "791-0",
        #     "月食ネクロズマ": "800-2",
        #     "レシラム": "643-0",
        #     "ゼクロム": "644-0",
        #     "ギラティナ（アナザー）": "487-0",
        #     "ギラティナ（オリジン）": "487-1",
        #     "ディアルガ": "483-0",
        #     "ディアルガ（オリジン）": "483-1",
        #     "パルキア": "484-0",
        #     "パルキア（オリジン）": "484-1",
        #     "ザシアン": "888-0",
        #     "ザマゼンタ": "889-0",
        #     "ミュウツー": "150-0",
        #     "キュレム": "646-0",
        #     "ネクロズマ": "800-0",
        #     "バドレックス": "898-0",
        # }
        # self.regend_num = tkinter.StringVar()
        # self.regend_num.set("0")
        # self.selected_regend = tkinter.StringVar()
        # self.selected_regend.set(list(self.regends_dict.keys())[0])
        # self.regends_filter = tkinter.OptionMenu(
        #     self,
        #     self.selected_regend,
        #     *list(self.regends_dict.keys()),
        #     command=self.set_regend,
        # )
        # self.regends_filter.place(
        #     x=Const.searchX + 270, y=Const.searchY + Const.searchDY * 2.6
        # )
        self.regend_num = tkinter.StringVar()
        self.regend_num.set("0")
        # --- ここまで ---

        self.rule = tkinter.IntVar()
        self.rule.set(get_recog_value("rule"))
        rb_single = tkinter.Radiobutton(
            self, text="シングル", variable=self.rule, value=1
        )
        rb_single.place(x=Const.searchX + 120, y=Const.searchY + Const.searchDY * 2)
        rb_double = tkinter.Radiobutton(
            self, text="ダブル", variable=self.rule, value=2
        )
        rb_double.place(x=Const.searchX + 190, y=Const.searchY + Const.searchDY * 2)
        search_button = tkinter.Button(
            self,
            text="検索",
            command=self.update_result,
        )
        search_button.place(
            x=Const.searchX + 550, y=Const.searchY + Const.searchDY * 2.7
        )
        self.title_var = tkinter.StringVar()
        self.title_var.set("ＫＰと勝率")
        self.main_title_label = tkinter.Button(
            self,
            textvariable=self.title_var,
            font=Const.titleFont,
            state="disable",
            command=self.change_mode,
        )
        sort_condition_frame = tkinter.Frame(self)
        self.sort_condition_var = tkinter.IntVar()
        self.sort_condition_var.set(0)
        for text, value in self.sort_condition_options:
            rb = tkinter.Radiobutton(
                sort_condition_frame,
                text=text,
                variable=self.sort_condition_var,
                value=value,
                command=self.change_sort_condition,
            )
            rb.grid(sticky="w")
        sort_condition_frame.place(x=Const.searchX + 130, y=Const.kpStartY - 60)
        sort_line_frame = tkinter.Frame(self)
        self.sort_line_var = tkinter.BooleanVar()
        self.sort_line_var.set(True)
        for text, value in self.sort_line_options:
            rb = tkinter.Radiobutton(
                sort_line_frame,
                text=text,
                variable=self.sort_line_var,
                value=value,
                command=self.change_sort_condition,
            )
            rb.grid(sticky="w")
        sort_line_frame.place(x=Const.searchX + 270, y=Const.kpStartY - 60)
        self.main_title_label.place(x=Const.kpStartX, y=Const.kpStartY - 60)
        self.subtitle_var = tkinter.StringVar()
        self.subtitle_var.set("直近使用したパーティ")
        self.sub_title_label = tkinter.Label(
            self, textvariable=self.subtitle_var, font=Const.titleFont
        )
        self.sub_title_label.place(x=Const.myPartyStartX, y=Const.myPartyStartY - 30)

        if self._seasons:
            self.season_var.set(self._seasons[0]["name"])
            self._on_season_select(self._seasons[0]["name"])

    # --- 伝説絞り込み機能（未使用） ---
    # def set_regend(self, *args):
    #     if self.regend_filter_bln.get():
    #         self.regends_filter.config(state="normal")
    #         self.regend_num.set(self.selected_regend.get())
    #     else:
    #         self.regends_filter.config(state="disabled")
    #         self.regend_num.set("0")
    # --- ここまで ---

    def update_result(self):
        self.from_date, self.to_date = DB_battle.chenge_date_from_datetime_to_unix(
            self.from_year_var.get(),
            self.from_month_var.get(),
            self.from_date_var.get(),
            self.to_year_var.get(),
            self.to_month_var.get(),
            self.to_date_var.get(),
            self.time9_bln.get(),
            self.time23_bln.get(),
        )
        self.delete_result_page()
        self.sort_condition_var.set(0)
        self.sort_line_var.set(True)
        self.party_num = (
            int(self.num_txt.get())
            if self.num_txt.get() is not None and self.num_txt.get() != ""
            else 0
        )
        self.party_subnum = (
            int(self.sub_num_txt.get())
            if self.sub_num_txt.get() is not None and self.sub_num_txt.get() != ""
            else 0
        )
        self.title_var.set("ＫＰと勝率")
        self.main_title_label["state"] = (
            "disable" if self.party_num == 0 and self.party_subnum == 0 else "normal"
        )
        _kp_result = DB_battle.calc_kp(
            self.from_date,
            self.to_date,
            self.rule.get(),
            self.party_num,
            self.party_subnum,
            self.regends_dict[self.regend_num.get()]
            if self.regend_num.get() != "0"
            else "0",
        )
        self.pokemon_list = [item[0] for item in _kp_result]
        self.result_1_list = [item[1] for item in _kp_result]
        self.result_2_list = DB_battle.get_win_rate(
            self.pokemon_list,
            self.from_date,
            self.to_date,
            self.rule.get(),
            self.party_num,
            self.party_subnum,
            self.regends_dict[self.regend_num.get()]
            if self.regend_num.get() != "0"
            else "0",
        )

        self.record_count = DB_battle.count_record(
            self.from_date,
            self.to_date,
            self.rule.get(),
            self.party_num,
            self.party_subnum,
            self.regends_dict[self.regend_num.get()]
            if self.regend_num.get() != "0"
            else "0",
        )
        self.win_count = DB_battle.count_win(
            self.from_date,
            self.to_date,
            self.rule.get(),
            self.party_num,
            self.party_subnum,
            self.regends_dict[self.regend_num.get()]
            if self.regend_num.get() != "0"
            else "0",
        )

        self.kp_list = list(self.pokemon_list)
        self.change_sort_condition()
        self.record_count_label = tkinter.Label(
            self,
            text="対戦数：" + str(self.record_count[0]),
            font=Const.titleFont,
        )
        self.record_count_label.place(x=Const.myPartyStartX + 50, y=Const.searchY)
        whole_win_rate = (
            self.win_count[0] * 100 / self.record_count[0]
            if self.record_count[0] != 0
            else 0
        )
        self.whole_win_rate_label = tkinter.Label(
            self,
            text=str("勝率：" + "{:.1f}".format(whole_win_rate)) + "%",
            font=Const.titleFont,
        )
        self.whole_win_rate_label.place(
            x=Const.myPartyStartX + 50, y=Const.searchY + Const.searchDY * 2
        )
        self.display_party_detail()

    def display_result_1(self):
        if self.title_var.get() == "ＫＰと勝率":
            for i in range(len(self.result_1_list)):
                if i > 49:
                    break
                result_1_label = tkinter.Label(
                    self,
                    text=str(
                        "{:.1f}".format(
                            (
                                int(self.result_1_list[i])
                                * 100
                                / int(self.record_count[0])
                            )
                        )
                    )
                    + "%",
                )
                result_1_label.place(x=Const.list2[i][1] - 40, y=Const.list2[i][2] + 20)
                self.result_1_label_list.append(result_1_label)
        else:
            for i in range(len(self.result_1_list)):
                if i > 49:
                    break
                result_1_label = tkinter.Label(
                    self,
                    text=str("{:.1f}".format(self.result_1_list[i] * 100)) + "%",
                )
                result_1_label.place(x=Const.list2[i][1] - 40, y=Const.list2[i][2] + 20)
                self.result_1_label_list.append(result_1_label)

    def display_result_2(self):
        for i in range(len(self.result_2_list)):
            if i > 49:
                break
            result_2_label = tkinter.Label(
                self, text=str("{:.1f}".format(self.result_2_list[i] * 100)) + "%"
            )
            result_2_label.place(x=Const.list2[i][1] - 40, y=Const.list2[i][2] + 40)
            self.result_2_label_list.append(result_2_label)
            i = i + 1

    def display_image(self):
        i = 0
        for pokemon in self.pokemon_list:
            if len(pokemon[0]) < 1:
                break
            img = Image.open(Const.createPass(pokemon))
            img = img.resize((40, 40))
            img = ImageTk.PhotoImage(img)
            canvas = tkinter.Canvas(self, width=50, height=50)
            canvas.place(x=Const.list2[i][1], y=Const.list2[i][2] + 10)
            canvas.create_image(5, 5, image=img, anchor=tkinter.NW)
            self.img_list.append(img)
            self.canvas_list.append(canvas)
            i = i + 1
            if i > 49:
                break

    def change_sort_condition(self):
        self.delete_result()
        new_result_list = list(
            zip(
                self.pokemon_list,
                self.result_1_list,
                self.result_2_list,
                strict=False,
            )
        )

        name_order_dict = {name: index for index, name in enumerate(self.kp_list)}
        if self.sort_condition_var.get() == 0:
            new_result_list.sort(
                key=lambda x: (x[1], x[2], name_order_dict[x[0]]),
                reverse=self.sort_line_var.get(),
            )
        elif self.sort_condition_var.get() == 1:
            new_result_list.sort(
                key=lambda x: (x[2], x[1], name_order_dict[x[0]]),
                reverse=self.sort_line_var.get(),
            )

        self.pokemon_list = [item[0] for item in new_result_list]
        self.result_1_list = [item[1] for item in new_result_list]
        self.result_2_list = [item[2] for item in new_result_list]

        self.display_result_1()
        self.display_result_2()
        self.display_image()

    def change_mode(self):
        if self.title_var.get() == "ＫＰと勝率":
            self.title_var.set("選出と勝率")
            self.result_1_list = DB_battle.get_oppo_chosen_rate(
                self.pokemon_list,
                self.from_date,
                self.to_date,
                self.rule.get(),
                self.party_num,
                self.party_subnum,
                self.regends_dict[self.regend_num.get()]
                if self.regend_num.get() != "0"
                else "0",
            )
            self.result_2_list = DB_battle.get_oppo_chosen_and_win_rate(
                self.pokemon_list,
                self.from_date,
                self.to_date,
                self.rule.get(),
                self.party_num,
                self.party_subnum,
                self.regends_dict[self.regend_num.get()]
                if self.regend_num.get() != "0"
                else "0",
            )

        elif self.title_var.get() == "選出と勝率":
            self.title_var.set("初手と勝率")
            self.result_1_list = DB_battle.get_oppo_first_chosen_rate(
                self.pokemon_list,
                self.from_date,
                self.to_date,
                self.rule.get(),
                self.party_num,
                self.party_subnum,
                self.regends_dict[self.regend_num.get()]
                if self.regend_num.get() != "0"
                else "0",
            )
            self.result_2_list = DB_battle.get_oppo_first_chosen_and_win_rate(
                self.pokemon_list,
                self.from_date,
                self.to_date,
                self.rule.get(),
                self.party_num,
                self.party_subnum,
                self.regends_dict[self.regend_num.get()]
                if self.regend_num.get() != "0"
                else "0",
            )

        elif self.title_var.get() == "初手と勝率":
            self.title_var.set("ＫＰと勝率")
            _kp_result = DB_battle.calc_kp(
                self.from_date,
                self.to_date,
                self.rule.get(),
                self.party_num,
                self.party_subnum,
                self.regends_dict[self.regend_num.get()]
                if self.regend_num.get() != "0"
                else "0",
            )
            self.pokemon_list = [item[0] for item in _kp_result]
            self.result_1_list = [item[1] for item in _kp_result]

            self.result_2_list = DB_battle.get_win_rate(
                self.pokemon_list,
                self.from_date,
                self.to_date,
                self.rule.get(),
                self.party_num,
                self.party_subnum,
                self.regends_dict[self.regend_num.get()]
                if self.regend_num.get() != "0"
                else "0",
            )
        self.change_sort_condition()

    def display_party_detail(self):
        party_canvas = tkinter.Canvas(self, width=350, height=600)
        party_canvas.place(x=0, y=Const.myPartyStartY)

        if self.party_num != 0 and self.party_subnum != 0:
            pokemon_list = DB_battle.get_my_party(
                self.party_num,
                self.party_subnum,
                self.regends_dict[self.regend_num.get()]
                if self.regend_num.get() != "0"
                else "0",
            )
            if pokemon_list != -1:
                win_rate_list = DB_battle.get_win_rate_per_pokemon(
                    list(pokemon_list[0]),
                    self.from_date,
                    self.to_date,
                    self.rule.get(),
                    self.party_num,
                    self.party_subnum,
                    self.regends_dict[self.regend_num.get()]
                    if self.regend_num.get() != "0"
                    else "0",
                )
                chosen_rate_list = DB_battle.get_chosen_rate(
                    list(pokemon_list[0]),
                    self.from_date,
                    self.to_date,
                    self.rule.get(),
                    self.party_num,
                    self.party_subnum,
                    self.regends_dict[self.regend_num.get()]
                    if self.regend_num.get() != "0"
                    else "0",
                )
                chosen_and_win_rate_list = DB_battle.get_chosen_and_win_rate(
                    list(pokemon_list[0]),
                    self.from_date,
                    self.to_date,
                    self.rule.get(),
                    self.party_num,
                    self.party_subnum,
                    self.regends_dict[self.regend_num.get()]
                    if self.regend_num.get() != "0"
                    else "0",
                )
                first_chosen_rate_list = DB_battle.get_first_chosen_rate(
                    list(pokemon_list[0]),
                    self.from_date,
                    self.to_date,
                    self.rule.get(),
                    self.party_num,
                    self.party_subnum,
                    self.regends_dict[self.regend_num.get()]
                    if self.regend_num.get() != "0"
                    else "0",
                )
                first_chosen_and_win_rate_list = (
                    DB_battle.get_first_chosen_and_win_rate(
                        list(pokemon_list[0]),
                        self.from_date,
                        self.to_date,
                        self.rule.get(),
                        self.party_num,
                        self.party_subnum,
                        self.regends_dict[self.regend_num.get()]
                        if self.regend_num.get() != "0"
                        else "0",
                    )
                )
                self.subtitle_var.set("パーティ詳細")
                for i in range(len(list(pokemon_list[0]))):
                    img = Image.open(Const.createPass(pokemon_list[0][i]))
                    img = img.resize((40, 40))
                    img = ImageTk.PhotoImage(img)
                    canvas = tkinter.Canvas(self, width=50, height=50)
                    canvas.place(
                        x=Const.myPartyDetailList[0][0],
                        y=Const.myPartyDetailList[i][1],
                    )
                    canvas.create_image(5, 5, image=img, anchor=tkinter.NW)
                    self.img_list.append(img)
                    party_num_label = tkinter.Label(
                        self,
                        text="勝率："
                        + "{:.1f}".format(win_rate_list[i] * 100)
                        + "%\n選出率："
                        + "{:.1f}".format(chosen_rate_list[i] * 100)
                        + "%ー選出時勝率："
                        + "{:.1f}".format(chosen_and_win_rate_list[i] * 100)
                        + "%\n初手選出率："
                        + "{:.1f}".format(first_chosen_rate_list[i] * 100)
                        + "%ー初手選出時勝率："
                        + "{:.1f}".format(first_chosen_and_win_rate_list[i] * 100)
                        + "%",
                    )
                    party_num_label.place(
                        x=Const.myPartyDetailList[0][0] + 50,
                        y=Const.myPartyDetailList[i][1],
                    )
            else:
                self.display_my_party()

        elif self.party_num != 0:
            pokemon_list = DB_battle.get_my_party(
                self.party_num,
                self.party_subnum,
                self.regends_dict[self.regend_num.get()]
                if self.regend_num.get() != "0"
                else "0",
            )
            if pokemon_list != -1:
                win_rate_list = DB_battle.get_win_rate_per_pokemon(
                    list(pokemon_list[0]),
                    self.from_date,
                    self.to_date,
                    self.rule.get(),
                    self.party_num,
                    0,
                    self.regends_dict[self.regend_num.get()]
                    if self.regend_num.get() != "0"
                    else "0",
                )
                chosen_rate_list = DB_battle.get_chosen_rate(
                    list(pokemon_list[0]),
                    self.from_date,
                    self.to_date,
                    self.rule.get(),
                    self.party_num,
                    0,
                    self.regends_dict[self.regend_num.get()]
                    if self.regend_num.get() != "0"
                    else "0",
                )
                chosen_and_win_rate_list = DB_battle.get_chosen_and_win_rate(
                    list(pokemon_list[0]),
                    self.from_date,
                    self.to_date,
                    self.rule.get(),
                    self.party_num,
                    0,
                    self.regends_dict[self.regend_num.get()]
                    if self.regend_num.get() != "0"
                    else "0",
                )
                first_chosen_rate_list = DB_battle.get_first_chosen_rate(
                    list(pokemon_list[0]),
                    self.from_date,
                    self.to_date,
                    self.rule.get(),
                    self.party_num,
                    0,
                    self.regends_dict[self.regend_num.get()]
                    if self.regend_num.get() != "0"
                    else "0",
                )
                first_chosen_and_win_rate_list = (
                    DB_battle.get_first_chosen_and_win_rate(
                        list(pokemon_list[0]),
                        self.from_date,
                        self.to_date,
                        self.rule.get(),
                        self.party_num,
                        0,
                        self.regends_dict[self.regend_num.get()]
                        if self.regend_num.get() != "0"
                        else "0",
                    )
                )
                self.subtitle_var.set("パーティ詳細")
                for i in range(len(list(pokemon_list[0]))):
                    img = Image.open(Const.createPass(pokemon_list[0][i]))
                    img = img.resize((40, 40))
                    img = ImageTk.PhotoImage(img)
                    canvas = tkinter.Canvas(self, width=50, height=50)
                    canvas.place(
                        x=Const.myPartyDetailList[0][0],
                        y=Const.myPartyDetailList[i][1],
                    )
                    canvas.create_image(5, 5, image=img, anchor=tkinter.NW)
                    self.img_list.append(img)
                    party_num_label = tkinter.Label(
                        self,
                        text="勝率："
                        + "{:.1f}".format(win_rate_list[i] * 100)
                        + "%\n選出率："
                        + "{:.1f}".format(chosen_rate_list[i] * 100)
                        + "%ー選出時勝率："
                        + "{:.1f}".format(chosen_and_win_rate_list[i] * 100)
                        + "%\n初手選出率："
                        + "{:.1f}".format(first_chosen_rate_list[i] * 100)
                        + "%ー初手選出時勝率："
                        + "{:.1f}".format(first_chosen_and_win_rate_list[i] * 100)
                        + "%",
                    )
                    party_num_label.place(
                        x=Const.myPartyDetailList[0][0] + 50,
                        y=Const.myPartyDetailList[i][1],
                    )
            else:
                self.display_my_party()
        else:
            self.display_my_party()

    def display_my_party(self):
        self.subtitle_var.set("直近使用したパーティ")
        pokemon_list = DB_battle.get_my_recent_party()
        for i in range(len(pokemon_list)):
            party_num = f"{pokemon_list[i][6]}-{pokemon_list[i][7]}"
            for j in range(7):
                if j == 6:
                    party_num_label = tkinter.Label(
                        self, text=party_num, font=Const.titleFont
                    )
                    party_num_label.place(
                        x=Const.myPartyPointList[i * 7 + j][0],
                        y=Const.myPartyPointList[i * 7 + j][1],
                    )
                else:
                    img = Image.open(Const.createPass(pokemon_list[i][j]))
                    img = img.resize((40, 40))
                    img = ImageTk.PhotoImage(img)
                    canvas = tkinter.Canvas(self, width=50, height=50)
                    canvas.place(
                        x=Const.myPartyPointList[i * 7 + j][0],
                        y=Const.myPartyPointList[i * 7 + j][1],
                    )
                    canvas.create_image(5, 5, image=img, anchor=tkinter.NW)
                    self.img_list.append(img)

    def delete_result_page(self):
        if self.record_count_label is not None:
            self.record_count_label.destroy()
        if self.whole_win_rate_label is not None:
            self.whole_win_rate_label.destroy()
        for kpLabel in self.result_1_label_list:
            kpLabel.destroy()
        self.result_1_label_list = []
        for win_rate_label in self.result_2_label_list:
            win_rate_label.destroy()
        self.result_2_label_list = []
        for canvas in self.canvas_list:
            canvas.delete("all")
        self.canvas_list = []

    def delete_result(self):
        for kp_label in self.result_1_label_list:
            kp_label.destroy()
        self.result_1_label_list = []
        for win_rate_label in self.result_2_label_list:
            win_rate_label.destroy()
        self.result_2_label_list = []

    def zero_pad_number(self, s):
        # 正規表現で最初の数字部分を抽出
        match = re.match(r"(\d{1,4})-\d", s)
        if match:
            number = match.group(1)
            # 4桁に0埋め
            padded_number = number.zfill(4)
            # 元の文字列と置換
            return s.replace(number, padded_number, 1)
        return s
