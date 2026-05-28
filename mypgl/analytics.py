import datetime
import json
import re
import tkinter

from PIL import Image, ImageTk

from database.battle import DB_battle
from mypgl.const import Const
from recog.recog import get_recog_value


class Analytics(tkinter.Toplevel):
    def __init__(self, master=None):
        super().__init__(master)
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
        self.kp_img_list = []
        self.canvas_list = []

        self.record_count_label = None
        self.whole_win_rate_label = None

        self.sort_condition_options = [("KP", 0), ("勝率", 1), ("使用率順", 2)]
        self.sort_line_options = [("降順", 0), ("昇順", 1)]
        self.mode_options = [
            ("ＫＰと勝率", "ＫＰと勝率"),
            ("選出と勝率", "選出と勝率"),
            ("初手と勝率", "初手と勝率"),
        ]
        self.display_mode_options = [("％表示", 0), ("分数表示", 1), ("両方表示", 2)]
        self.scroll_mode_options = [("スクロール表示", 0), ("全面表示", 1)]
        self.ranking_count_options = [("50位まで", 50), ("100位まで", 100)]
        self.merge_mega_var = tkinter.BooleanVar()
        self.merge_mega_var.set(True)
        self._mega_groups: dict = {}
        self._ranking_index = self._load_ranking_index()
        self.result_1_counts: list[tuple[int, int]] = []
        self.result_2_counts: list[tuple[int, int]] = []
        self._prev_sort_condition = 0
        self.rank_labels: list = []
        self._cell_positions: list[tuple[int, int, int]] = list(Const.list2)

        self.display_gui(self.recent_date)
        self._apply_cell_layout()
        self.update_result()

        for i in range(100):
            rank_label = tkinter.Label(self.kp_inner_frame, text=str(i + 1) + "位")
            self.rank_labels.append(rank_label)
        self._apply_rank_label_visibility()

    def open(self):
        self.focus_set()
        self.geometry("1280x720")

    def _apply_rank_label_visibility(self):
        count = self.ranking_count_var.get()
        for i, lbl in enumerate(self.rank_labels):
            if i < count:
                lbl.place(x=self._cell_positions[i][1] - 40, y=self._cell_positions[i][2])
            else:
                lbl.place_forget()

    def _apply_cell_layout(self):
        show_both = self.display_mode_var.get() == 2
        scroll_mode = self.scroll_mode_var.get() == 0
        if show_both:
            dx = 165
            full_window_width = 2080
        else:
            dx = Const.kpPictureDX + Const.kpMargin + Const.kpMojiDX
            full_window_width = 1280
        dy = Const.kpPictureDY + Const.kpMargin
        rows = 10
        cols = 10
        inner_width = 40 + cols * dx + 20

        self._cell_positions = []
        for i in range(rows):
            for j in range(cols):
                self._cell_positions.append(
                    (
                        j,
                        40 + j * dx,
                        i * dy,
                    )
                )

        ranking_count = self.ranking_count_var.get()
        shown_rows = 5 if ranking_count == 50 else 10

        if scroll_mode:
            window_width = 1280
            window_height = 720
        else:
            window_width = full_window_width
            window_height = Const.kpStartY + shown_rows * dy + 40

        self.geometry(f"{window_width}x{window_height}")

        canvas_w = window_width - (Const.kpStartX - 40) - 30
        canvas_h = window_height - Const.kpStartY - 30
        scroll_h = shown_rows * dy + 20
        full_visible_w = min(inner_width, canvas_w) if scroll_mode else inner_width
        full_visible_h = min(scroll_h, canvas_h) if scroll_mode else scroll_h
        self.kp_canvas_outer.configure(
            width=full_visible_w, height=full_visible_h
        )
        self.kp_canvas_outer.configure(scrollregion=(0, 0, inner_width, scroll_h))
        self.kp_inner_frame.configure(width=inner_width, height=scroll_h)

        if scroll_mode and inner_width > full_visible_w:
            self.kp_xscroll.place(
                x=Const.kpStartX - 40,
                y=Const.kpStartY + full_visible_h,
                width=full_visible_w,
            )
        else:
            self.kp_xscroll.place_forget()
        if scroll_mode and scroll_h > full_visible_h:
            self.kp_yscroll.place(
                x=Const.kpStartX - 40 + full_visible_w,
                y=Const.kpStartY,
                height=full_visible_h,
            )
        else:
            self.kp_yscroll.place_forget()

    def _on_ranking_count_change(self):
        self._apply_cell_layout()
        self._apply_rank_label_visibility()
        self.change_sort_condition()

    def _on_display_mode_change(self):
        self._apply_cell_layout()
        self._apply_rank_label_visibility()
        self._refresh_display()

    def _load_seasons(self) -> list:
        try:
            with open("recog/season.json", "r", encoding="utf-8") as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return []

    @staticmethod
    def _load_ranking_index() -> dict[str, int]:
        ranking: dict[str, int] = {}
        try:
            with open("stats/ranking.txt", encoding="utf-8") as f:
                for i, line in enumerate(f):
                    pid = line.strip()
                    if pid:
                        ranking[pid] = i + 1
        except FileNotFoundError:
            pass
        return ranking

    @staticmethod
    def _to_ranking_key(pid: str) -> str:
        if not pid:
            return pid
        parts = pid.split("-")
        if len(parts) < 2:
            return pid
        return f"{parts[0].zfill(4)}-{parts[-1].zfill(2)}"

    @staticmethod
    def _from_ranking_key(key: str) -> str:
        parts = key.split("-")
        if len(parts) < 2:
            return key
        no = parts[0].lstrip("0") or "0"
        form = parts[-1].lstrip("0") or "0"
        return f"{no}-{form}"

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
        rb_single.place(x=Const.searchX + 180, y=Const.searchY + Const.searchDY * 3)
        rb_double = tkinter.Radiobutton(
            self, text="ダブル", variable=self.rule, value=2
        )
        rb_double.place(x=Const.searchX + 250, y=Const.searchY + Const.searchDY * 3)
        search_button = tkinter.Button(
            self,
            text="検索",
            command=self.update_result,
        )
        search_button.place(
            x=Const.searchX + 510, y=Const.searchY + Const.searchDY * 2.7
        )

        self.title_var = tkinter.StringVar()
        self.title_var.set("ＫＰと勝率")
        mode_frame = tkinter.Frame(self)
        for text, value in self.mode_options:
            rb = tkinter.Radiobutton(
                mode_frame,
                text=text,
                variable=self.title_var,
                value=value,
                command=self.apply_mode,
            )
            rb.grid(sticky="w")
        mode_frame.place(x=Const.kpStartX, y=Const.controlRowY)
        sort_condition_frame = tkinter.Frame(self)
        self.sort_condition_var = tkinter.IntVar()
        self.sort_condition_var.set(0)
        for text, value in self.sort_condition_options:
            rb = tkinter.Radiobutton(
                sort_condition_frame,
                text=text,
                variable=self.sort_condition_var,
                value=value,
                command=self._on_sort_condition_change,
            )
            rb.grid(sticky="w")
        sort_condition_frame.place(x=Const.searchX + 130, y=Const.controlRowY)
        sort_line_frame = tkinter.Frame(self)
        self.sort_line_var = tkinter.IntVar()
        self.sort_line_var.set(1)
        for text, value in self.sort_line_options:
            rb = tkinter.Radiobutton(
                sort_line_frame,
                text=text,
                variable=self.sort_line_var,
                value=value,
                command=self.change_sort_condition,
            )
            rb.grid(sticky="w")
        sort_line_frame.place(x=Const.searchX + 270, y=Const.controlRowY)
        display_mode_frame = tkinter.Frame(self)
        self.display_mode_var = tkinter.IntVar()
        self.display_mode_var.set(0)
        for text, value in self.display_mode_options:
            rb = tkinter.Radiobutton(
                display_mode_frame,
                text=text,
                variable=self.display_mode_var,
                value=value,
                command=self._on_display_mode_change,
            )
            rb.grid(sticky="w")
        display_mode_frame.place(x=Const.searchX + 390, y=Const.controlRowY)
        scroll_mode_frame = tkinter.Frame(self)
        self.scroll_mode_var = tkinter.IntVar()
        self.scroll_mode_var.set(1)
        for text, value in self.scroll_mode_options:
            rb = tkinter.Radiobutton(
                scroll_mode_frame,
                text=text,
                variable=self.scroll_mode_var,
                value=value,
                command=self._on_display_mode_change,
            )
            rb.grid(sticky="w")
        scroll_mode_frame.place(x=Const.searchX + 490, y=Const.controlRowY)
        ranking_count_frame = tkinter.Frame(self)
        self.ranking_count_var = tkinter.IntVar()
        self.ranking_count_var.set(50)
        for text, value in self.ranking_count_options:
            rb = tkinter.Radiobutton(
                ranking_count_frame,
                text=text,
                variable=self.ranking_count_var,
                value=value,
                command=self._on_ranking_count_change,
            )
            rb.grid(sticky="w")
        ranking_count_frame.place(x=Const.searchX + 610, y=Const.controlRowY)
        self.merge_mega_check = tkinter.Checkbutton(
            self,
            text="メガ統合",
            variable=self.merge_mega_var,
            command=self.apply_mode,
        )
        self.merge_mega_check.place(x=Const.searchX + 720, y=Const.controlRowY)

        self.kp_canvas_outer = tkinter.Canvas(self, highlightthickness=0)
        self.kp_canvas_outer.place(x=Const.kpStartX - 40, y=Const.kpStartY)
        self.kp_xscroll = tkinter.Scrollbar(
            self, orient="horizontal", command=self.kp_canvas_outer.xview
        )
        self.kp_yscroll = tkinter.Scrollbar(
            self, orient="vertical", command=self.kp_canvas_outer.yview
        )
        self.kp_canvas_outer.configure(
            xscrollcommand=self.kp_xscroll.set,
            yscrollcommand=self.kp_yscroll.set,
        )
        self.kp_inner_frame = tkinter.Frame(self.kp_canvas_outer)
        self.kp_canvas_outer.create_window(
            (0, 0), window=self.kp_inner_frame, anchor="nw"
        )

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
        self.sort_line_var.set(1)
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
        _regend = (
            self.regends_dict[self.regend_num.get()]
            if self.regend_num.get() != "0"
            else "0"
        )
        self.record_count = DB_battle.count_record(
            self.from_date, self.to_date, self.rule.get(),
            self.party_num, self.party_subnum, _regend,
        )
        self.win_count = DB_battle.count_win(
            self.from_date, self.to_date, self.rule.get(),
            self.party_num, self.party_subnum, _regend,
        )
        _kp_result = DB_battle.calc_kp(
            self.from_date, self.to_date, self.rule.get(),
            self.party_num, self.party_subnum, _regend,
        )
        if self.merge_mega_var.get():
            _kp_result = self._merge_kp_results(_kp_result)
        else:
            self._mega_groups = {}
        self.pokemon_list = [item[0] for item in _kp_result]
        self.result_1_list = [item[1] for item in _kp_result]
        self.result_1_counts = [
            (kp, self.record_count[0]) for kp in self.result_1_list
        ]
        win_counts = DB_battle.get_win_counts(
            self._get_query_groups(),
            self.from_date, self.to_date, self.rule.get(),
            self.party_num, self.party_subnum, _regend,
        )
        self.result_2_counts = win_counts
        self.result_2_list = [n / d if d else 0 for n, d in win_counts]

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

    def _format_value(self, n: int, d: int) -> str:
        mode = self.display_mode_var.get()
        rate = (n * 100 / d) if d else 0
        if mode == 1:
            return f"{n}/{d}"
        if mode == 2:
            return f"{rate:.1f}% ({n}/{d})"
        return f"{rate:.1f}%"

    def display_result_1(self):
        show_both = self.display_mode_var.get() == 2
        x_off = 55 if show_both else -40
        y_off = 8 if show_both else 20
        limit = self.ranking_count_var.get()
        for i in range(len(self.result_1_list)):
            if i >= limit:
                break
            n, d = self.result_1_counts[i] if i < len(self.result_1_counts) else (0, 0)
            result_1_label = tkinter.Label(
                self.kp_inner_frame, text=self._format_value(n, d)
            )
            result_1_label.place(
                x=self._cell_positions[i][1] + x_off,
                y=self._cell_positions[i][2] + y_off,
            )
            self.result_1_label_list.append(result_1_label)

    def display_result_2(self):
        show_both = self.display_mode_var.get() == 2
        x_off = 55 if show_both else -40
        y_off = 32 if show_both else 40
        limit = self.ranking_count_var.get()
        for i in range(len(self.result_2_list)):
            if i >= limit:
                break
            n, d = self.result_2_counts[i] if i < len(self.result_2_counts) else (0, 0)
            result_2_label = tkinter.Label(
                self.kp_inner_frame, text=self._format_value(n, d)
            )
            result_2_label.place(
                x=self._cell_positions[i][1] + x_off,
                y=self._cell_positions[i][2] + y_off,
            )
            self.result_2_label_list.append(result_2_label)

    def _refresh_display(self):
        self.delete_result()
        self.display_result_1()
        self.display_result_2()
        self.display_image()

    def display_image(self):
        limit = self.ranking_count_var.get()
        i = 0
        for pokemon in self.pokemon_list:
            if len(pokemon[0]) < 1:
                break
            img = Image.open(Const.createPass(pokemon))
            img = img.resize((40, 40))
            img = ImageTk.PhotoImage(img)
            canvas = tkinter.Canvas(self.kp_inner_frame, width=50, height=50)
            canvas.place(x=self._cell_positions[i][1], y=self._cell_positions[i][2] + 10)
            canvas.create_image(5, 5, image=img, anchor=tkinter.NW)
            self.kp_img_list.append(img)
            self.canvas_list.append(canvas)
            i = i + 1
            if i >= limit:
                break

    def _merge_kp_results(self, kp_result):
        """メガシンカフォーム（form 10-19）のKPを基本フォームに統合する。"""
        merged_kp: dict[str, int] = {}
        mega_groups: dict[str, list[str]] = {}
        for pid, kp in kp_result:
            parts = pid.split("-")
            try:
                form = int(parts[-1]) if len(parts) >= 2 else -1
                base_id = f"{parts[0]}-0" if 10 <= form <= 19 else pid
            except ValueError:
                base_id = pid
            if base_id not in merged_kp:
                merged_kp[base_id] = 0
                mega_groups[base_id] = []
            merged_kp[base_id] += kp
            mega_groups[base_id].append(pid)
        self._mega_groups = mega_groups
        return sorted(merged_kp.items(), key=lambda x: x[1], reverse=True)

    def _get_query_groups(self):
        """DB クエリ用のポケモンリストを返す。メガ統合 ON 時はグループ（リスト）に展開する。"""
        if self.merge_mega_var.get() and self._mega_groups:
            return [self._mega_groups.get(pid, [pid]) for pid in self.pokemon_list]
        return list(self.pokemon_list)

    def _on_sort_condition_change(self):
        new_sc = self.sort_condition_var.get()
        if self._prev_sort_condition == 2 and new_sc != 2:
            self._prev_sort_condition = new_sc
            self.apply_mode()
            return
        self._prev_sort_condition = new_sc
        self.change_sort_condition()

    def change_sort_condition(self):
        self.delete_result()
        sort_condition = self.sort_condition_var.get()
        self._prev_sort_condition = sort_condition
        if sort_condition == 2:
            self._apply_ranking_order()
            self.display_result_1()
            self.display_result_2()
            self.display_image()
            return

        new_result_list = list(
            zip(
                self.pokemon_list,
                self.result_1_list,
                self.result_2_list,
                self.result_1_counts,
                self.result_2_counts,
                strict=False,
            )
        )

        name_order_dict = {name: index for index, name in enumerate(self.kp_list)}
        sort_line = self.sort_line_var.get()
        if sort_condition == 0:
            new_result_list.sort(
                key=lambda x: (x[1], x[2], name_order_dict.get(x[0], 0)),
                reverse=bool(sort_line),
            )
        elif sort_condition == 1:
            new_result_list.sort(
                key=lambda x: (x[2], x[1], name_order_dict.get(x[0], 0)),
                reverse=bool(sort_line),
            )

        self.pokemon_list = [item[0] for item in new_result_list]
        self.result_1_list = [item[1] for item in new_result_list]
        self.result_2_list = [item[2] for item in new_result_list]
        self.result_1_counts = [item[3] for item in new_result_list]
        self.result_2_counts = [item[4] for item in new_result_list]

        self.display_result_1()
        self.display_result_2()
        self.display_image()

    def _apply_ranking_order(self):
        from database.pokemon import DB_pokemon

        limit = self.ranking_count_var.get()
        ranked = sorted(self._ranking_index.items(), key=lambda x: x[1])[:limit]
        base_pokemon_list = [self._from_ranking_key(k) for k, _ in ranked]
        merge_mega = self.merge_mega_var.get()
        if merge_mega:
            pokemon_list = base_pokemon_list
            query_groups: list = [
                DB_battle._expand_mega_forms(p) for p in pokemon_list
            ]
        else:
            pokemon_list = []
            for p in base_pokemon_list:
                pokemon_list.append(p)
                parts = p.split("-")
                if len(parts) >= 2:
                    try:
                        no = int(parts[0])
                        for f in DB_pokemon.get_mega_forms_by_no(no):
                            pokemon_list.append(f"{no}-{f}")
                    except ValueError:
                        pass
                if len(pokemon_list) >= limit:
                    break
            pokemon_list = pokemon_list[:limit]
            query_groups = pokemon_list
        _regend = (
            self.regends_dict[self.regend_num.get()]
            if self.regend_num.get() != "0"
            else "0"
        )
        title = self.title_var.get()
        if title == "選出と勝率":
            c1 = DB_battle.get_oppo_chosen_counts(
                query_groups, self.from_date, self.to_date, self.rule.get(),
                self.party_num, self.party_subnum, _regend,
            )
            c2 = DB_battle.get_oppo_chosen_and_win_counts(
                query_groups, self.from_date, self.to_date, self.rule.get(),
                self.party_num, self.party_subnum, _regend,
            )
        elif title == "初手と勝率":
            c1 = DB_battle.get_oppo_first_chosen_counts(
                query_groups, self.from_date, self.to_date, self.rule.get(),
                self.party_num, self.party_subnum, _regend,
            )
            c2 = DB_battle.get_oppo_first_chosen_and_win_counts(
                query_groups, self.from_date, self.to_date, self.rule.get(),
                self.party_num, self.party_subnum, _regend,
            )
        else:
            kp_result = DB_battle.calc_kp(
                self.from_date, self.to_date, self.rule.get(),
                self.party_num, self.party_subnum, _regend,
            )
            kp_map: dict[str, int] = {}
            for pid, kp in kp_result:
                key = DB_battle._normalize_mega_form(pid) if merge_mega else pid
                kp_map[key] = kp_map.get(key, 0) + kp
            kp_list = [kp_map.get(p, 0) for p in pokemon_list]
            c1 = [(kp, self.record_count[0]) for kp in kp_list]
            c2 = DB_battle.get_win_counts(
                query_groups, self.from_date, self.to_date, self.rule.get(),
                self.party_num, self.party_subnum, _regend,
            )
        self.pokemon_list = pokemon_list
        self.kp_list = list(pokemon_list)
        self.result_1_counts = c1
        self.result_2_counts = c2
        if title == "ＫＰと勝率":
            self.result_1_list = [n for n, _ in c1]
        else:
            self.result_1_list = [n / d if d else 0 for n, d in c1]
        self.result_2_list = [n / d if d else 0 for n, d in c2]

    def apply_mode(self):
        _regend = self.regends_dict[self.regend_num.get()] if self.regend_num.get() != "0" else "0"
        title = self.title_var.get()
        if title == "ＫＰと勝率":
            _kp_result = DB_battle.calc_kp(
                self.from_date, self.to_date, self.rule.get(),
                self.party_num, self.party_subnum, _regend,
            )
            if self.merge_mega_var.get():
                _kp_result = self._merge_kp_results(_kp_result)
            else:
                self._mega_groups = {}
            self.pokemon_list = [item[0] for item in _kp_result]
            self.result_1_list = [item[1] for item in _kp_result]
            self.kp_list = list(self.pokemon_list)
            self.result_1_counts = [
                (kp, self.record_count[0]) for kp in self.result_1_list
            ]
            win_counts = DB_battle.get_win_counts(
                self._get_query_groups(),
                self.from_date, self.to_date, self.rule.get(),
                self.party_num, self.party_subnum, _regend,
            )
            self.result_2_counts = win_counts
            self.result_2_list = [n / d if d else 0 for n, d in win_counts]
        elif title == "選出と勝率":
            _qgroups = self._get_query_groups()
            c1 = DB_battle.get_oppo_chosen_counts(
                _qgroups, self.from_date, self.to_date, self.rule.get(),
                self.party_num, self.party_subnum, _regend,
            )
            c2 = DB_battle.get_oppo_chosen_and_win_counts(
                _qgroups, self.from_date, self.to_date, self.rule.get(),
                self.party_num, self.party_subnum, _regend,
            )
            self.result_1_counts = c1
            self.result_2_counts = c2
            self.result_1_list = [n / d if d else 0 for n, d in c1]
            self.result_2_list = [n / d if d else 0 for n, d in c2]
        elif title == "初手と勝率":
            _qgroups = self._get_query_groups()
            c1 = DB_battle.get_oppo_first_chosen_counts(
                _qgroups, self.from_date, self.to_date, self.rule.get(),
                self.party_num, self.party_subnum, _regend,
            )
            c2 = DB_battle.get_oppo_first_chosen_and_win_counts(
                _qgroups, self.from_date, self.to_date, self.rule.get(),
                self.party_num, self.party_subnum, _regend,
            )
            self.result_1_counts = c1
            self.result_2_counts = c2
            self.result_1_list = [n / d if d else 0 for n, d in c1]
            self.result_2_list = [n / d if d else 0 for n, d in c2]
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
        self.delete_result()

    def delete_result(self):
        for kp_label in self.result_1_label_list:
            kp_label.destroy()
        self.result_1_label_list = []
        for win_rate_label in self.result_2_label_list:
            win_rate_label.destroy()
        self.result_2_label_list = []
        for canvas in self.canvas_list:
            canvas.destroy()
        self.canvas_list = []
        self.kp_img_list = []

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
