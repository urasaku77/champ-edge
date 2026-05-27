import dataclasses
import datetime
import json
import math
import tkinter
from tkinter import messagebox

from PIL import Image, ImageTk

from component.parts.combobox import AutoCompleteCombobox
from database.battle import Battle, DB_battle
from database.pokemon import DB_pokemon
from mypgl.const import Const
from recog.recog import get_recog_value


class EditBattleDialog(tkinter.Toplevel):
    def __init__(
        self,
        master,
        battle_data=None,
        default_rule: int = 1,
        default_party_num: str = "",
        default_party_subnum: str = "",
    ):
        super().__init__(master)
        self.is_new = battle_data is None
        self.title("対戦記録の新規追加" if self.is_new else "対戦記録の編集")
        self.saved = False
        self.deleted = False
        self.battle_id = None if self.is_new else battle_data[0]

        row = 0

        if self.is_new:
            init_date_str = datetime.datetime.now().strftime("%Y/%m/%d")
            init_time_str = datetime.datetime.now().strftime("%H:%M")
            init_rule = default_rule if default_rule in (1, 2) else 1
            init_party_num = str(default_party_num or "")
            init_party_subnum = str(default_party_subnum or "")
        else:
            dt = datetime.datetime.fromtimestamp(battle_data[1])
            init_date_str = dt.strftime("%Y/%m/%d")
            init_time_str = dt.strftime("%H:%M")
            init_rule = battle_data[2] if battle_data[2] in (1, 2) else 1
            init_party_num = str(battle_data[8] or "")
            init_party_subnum = str(battle_data[9] or "")

        tkinter.Label(self, text="日時:").grid(row=row, column=0, sticky="e", padx=5, pady=5)
        dt_frame = tkinter.Frame(self)
        dt_frame.grid(row=row, column=1, columnspan=3, sticky="w", padx=5)
        self.date_var = tkinter.StringVar(value=init_date_str)
        tkinter.Entry(dt_frame, textvariable=self.date_var, width=12).pack(side=tkinter.LEFT)
        self.time_var = tkinter.StringVar(value=init_time_str)
        tkinter.Entry(dt_frame, textvariable=self.time_var, width=8).pack(side=tkinter.LEFT, padx=(4, 0))
        row += 1

        tkinter.Label(self, text="ルール:").grid(row=row, column=0, sticky="e", padx=5, pady=5)
        rule_frame = tkinter.Frame(self)
        rule_frame.grid(row=row, column=1, columnspan=3, sticky="w", padx=5)
        self.rule_var = tkinter.IntVar(value=init_rule)
        tkinter.Radiobutton(rule_frame, text="シングル", variable=self.rule_var, value=1).pack(side=tkinter.LEFT)
        tkinter.Radiobutton(rule_frame, text="ダブル", variable=self.rule_var, value=2).pack(side=tkinter.LEFT)
        row += 1

        tkinter.Label(self, text="P番号:").grid(row=row, column=0, sticky="e", padx=5, pady=5)
        pn_frame = tkinter.Frame(self)
        pn_frame.grid(row=row, column=1, columnspan=3, sticky="w", padx=5)
        self.party_num_var = tkinter.StringVar(value=init_party_num)
        tkinter.Entry(pn_frame, textvariable=self.party_num_var, width=6).pack(side=tkinter.LEFT)
        tkinter.Label(pn_frame, text="連番:").pack(side=tkinter.LEFT, padx=(10, 2))
        self.party_subnum_var = tkinter.StringVar(value=init_party_subnum)
        tkinter.Entry(pn_frame, textvariable=self.party_subnum_var, width=6).pack(side=tkinter.LEFT)
        row += 1

        tkinter.Label(self, text="TN:").grid(row=row, column=0, sticky="e", padx=5, pady=5)
        self.tn_var = tkinter.StringVar(value="" if self.is_new else (battle_data[5] or ""))
        tkinter.Entry(self, textvariable=self.tn_var, width=20).grid(row=row, column=1, columnspan=3, sticky="w", padx=5)
        row += 1

        tkinter.Label(self, text="レート:").grid(row=row, column=0, sticky="e", padx=5, pady=5)
        self.rate_var = tkinter.StringVar(value="" if self.is_new else (battle_data[6] or ""))
        tkinter.Entry(self, textvariable=self.rate_var, width=20).grid(row=row, column=1, columnspan=3, sticky="w", padx=5)
        row += 1

        tkinter.Label(self, text="メモ:").grid(row=row, column=0, sticky="ne", padx=5, pady=5)
        self.memo_text = tkinter.Text(self, width=30, height=4)
        self.memo_text.insert("1.0", "" if self.is_new else (battle_data[7] or ""))
        self.memo_text.grid(row=row, column=1, columnspan=3, sticky="w", padx=5)
        row += 1

        tkinter.Label(self, text="勝敗:").grid(row=row, column=0, sticky="e", padx=5, pady=5)
        self.result_var = tkinter.IntVar(value=1 if self.is_new else battle_data[3])
        tkinter.Radiobutton(self, text="勝ち", variable=self.result_var, value=1).grid(row=row, column=1)
        tkinter.Radiobutton(self, text="負け", variable=self.result_var, value=0).grid(row=row, column=2)
        tkinter.Radiobutton(self, text="引き分け", variable=self.result_var, value=-1).grid(row=row, column=3)
        row += 1

        tkinter.Label(self, text="自分P:").grid(row=row, column=0, sticky="e", padx=5, pady=3)
        p_frame = tkinter.Frame(self)
        p_frame.grid(row=row, column=1, columnspan=3, sticky="w", padx=5)
        self.player_pokemon_vars = []
        for col in range(10, 16):
            initial = "" if self.is_new else self._pid_to_name(battle_data[col])
            var = tkinter.StringVar(value=initial)
            cb = AutoCompleteCombobox.pokemons(p_frame, textvariable=var, width=10)
            cb.pack(side=tkinter.LEFT, padx=2)
            cb.bind("<<ComboboxSelected>>", self._refresh_player_choices, add="+")
            cb.bind("<FocusOut>", self._refresh_player_choices, add="+")
            self.player_pokemon_vars.append(var)
        row += 1

        tkinter.Label(self, text="相手P:").grid(row=row, column=0, sticky="e", padx=5, pady=3)
        o_frame = tkinter.Frame(self)
        o_frame.grid(row=row, column=1, columnspan=3, sticky="w", padx=5)
        self.opponent_pokemon_vars = []
        for col in range(16, 22):
            initial = "" if self.is_new else self._pid_to_name(battle_data[col])
            var = tkinter.StringVar(value=initial)
            cb = AutoCompleteCombobox.pokemons(o_frame, textvariable=var, width=10)
            cb.pack(side=tkinter.LEFT, padx=2)
            cb.bind("<<ComboboxSelected>>", self._refresh_opponent_choices, add="+")
            cb.bind("<FocusOut>", self._refresh_opponent_choices, add="+")
            self.opponent_pokemon_vars.append(var)
        row += 1

        tkinter.Label(self, text="自分選:").grid(row=row, column=0, sticky="e", padx=5, pady=3)
        pc_frame = tkinter.Frame(self)
        pc_frame.grid(row=row, column=1, columnspan=3, sticky="w", padx=5)
        self.player_choice_vars = []
        self.player_choice_cbs = []
        self.player_choice_mega_vars = []
        self.player_choice_mega_cbs = []
        for slot, col in enumerate(range(22, 26)):
            if self.is_new:
                name, mega_label = "", ""
            else:
                name, mega_label = self._pid_to_choice_pair(battle_data[col])
            var = tkinter.StringVar(value=name)
            cb = tkinter.ttk.Combobox(pc_frame, textvariable=var, values=[""], width=10, state="readonly")
            cb.pack(side=tkinter.LEFT, padx=(2, 0))
            self.player_choice_vars.append(var)
            self.player_choice_cbs.append(cb)
            mega_var = tkinter.StringVar(value=mega_label)
            mega_cb = tkinter.ttk.Combobox(pc_frame, textvariable=mega_var, values=[""], width=4, state="readonly")
            mega_cb.pack(side=tkinter.LEFT, padx=(0, 4))
            self.player_choice_mega_vars.append(mega_var)
            self.player_choice_mega_cbs.append(mega_cb)
            cb.bind(
                "<<ComboboxSelected>>",
                lambda e, i=slot: self._refresh_player_mega(i),
                add="+",
            )
        row += 1

        tkinter.Label(self, text="相手選:").grid(row=row, column=0, sticky="e", padx=5, pady=3)
        oc_frame = tkinter.Frame(self)
        oc_frame.grid(row=row, column=1, columnspan=3, sticky="w", padx=5)
        self.opponent_choice_vars = []
        self.opponent_choice_cbs = []
        self.opponent_choice_mega_vars = []
        self.opponent_choice_mega_cbs = []
        for slot, col in enumerate(range(26, 30)):
            if self.is_new:
                name, mega_label = "", ""
            else:
                name, mega_label = self._pid_to_choice_pair(battle_data[col])
            var = tkinter.StringVar(value=name)
            cb = tkinter.ttk.Combobox(oc_frame, textvariable=var, values=[""], width=10, state="readonly")
            cb.pack(side=tkinter.LEFT, padx=(2, 0))
            self.opponent_choice_vars.append(var)
            self.opponent_choice_cbs.append(cb)
            mega_var = tkinter.StringVar(value=mega_label)
            mega_cb = tkinter.ttk.Combobox(oc_frame, textvariable=mega_var, values=[""], width=4, state="readonly")
            mega_cb.pack(side=tkinter.LEFT, padx=(0, 4))
            self.opponent_choice_mega_vars.append(mega_var)
            self.opponent_choice_mega_cbs.append(mega_cb)
            cb.bind(
                "<<ComboboxSelected>>",
                lambda e, i=slot: self._refresh_opponent_mega(i),
                add="+",
            )
        row += 1

        self._refresh_player_choices()
        self._refresh_opponent_choices()
        for i in range(len(self.player_choice_cbs)):
            self._refresh_player_mega(i)
        for i in range(len(self.opponent_choice_cbs)):
            self._refresh_opponent_mega(i)

        tkinter.Button(self, text="保存", command=self._save).grid(row=row, column=1, pady=10)
        tkinter.Button(self, text="キャンセル", command=self.destroy).grid(row=row, column=2, pady=10)
        if not self.is_new:
            tkinter.Button(self, text="削除", fg="red", command=self._delete).grid(row=row, column=3, pady=10)

        self.grab_set()
        self.focus_set()

    def _refresh_player_choices(self, *args):
        names = [""] + [v.get() for v in self.player_pokemon_vars if v.get().strip()]
        for cb in self.player_choice_cbs:
            cb["values"] = names

    def _refresh_opponent_choices(self, *args):
        names = [""] + [v.get() for v in self.opponent_pokemon_vars if v.get().strip()]
        for cb in self.opponent_choice_cbs:
            cb["values"] = names

    def _refresh_player_mega(self, slot: int):
        name = self.player_choice_vars[slot].get()
        options = self._get_mega_options_for_name(name)
        self.player_choice_mega_cbs[slot]["values"] = options
        if self.player_choice_mega_vars[slot].get() not in options:
            self.player_choice_mega_vars[slot].set("")

    def _refresh_opponent_mega(self, slot: int):
        name = self.opponent_choice_vars[slot].get()
        options = self._get_mega_options_for_name(name)
        self.opponent_choice_mega_cbs[slot]["values"] = options
        if self.opponent_choice_mega_vars[slot].get() not in options:
            self.opponent_choice_mega_vars[slot].set("")

    @staticmethod
    def _pid_to_name(pid: str) -> str:
        if not pid or pid == "-1":
            return ""
        try:
            return DB_pokemon.get_pokemon_name_by_pid(pid) or ""
        except Exception:
            return ""

    @staticmethod
    def _name_to_pid(name: str) -> str:
        name = (name or "").strip()
        if not name:
            return "-1"
        try:
            return DB_pokemon.get_pokemon_pid_by_name(name) or "-1"
        except Exception:
            return "-1"

    @staticmethod
    def _pid_to_choice_pair(pid: str) -> tuple[str, str]:
        """選出枠の保存pidを (表示名, メガラベル) に分解する。"""
        if not pid or pid == "-1":
            return ("", "")
        try:
            no_str, form_str = pid.split("-")
            form_int = int(form_str)
        except Exception:
            return (EditBattleDialog._pid_to_name(pid), "")
        if 10 <= form_int <= 19:
            try:
                base_name = DB_pokemon.get_pokemon_name_by_pid(f"{no_str}-0") or ""
            except Exception:
                base_name = ""
            try:
                mega_forms = DB_pokemon.get_mega_forms_by_no(int(no_str))
            except Exception:
                mega_forms = []
            if len(mega_forms) >= 2:
                label = "Y" if form_int == 12 else "X"
            else:
                label = "メガ"
            return (base_name, label)
        return (EditBattleDialog._pid_to_name(pid), "")

    @staticmethod
    def _get_mega_options_for_name(name: str) -> list[str]:
        """選択中ポケモン名に応じたメガ選択肢を返す。"""
        if not name or not name.strip():
            return [""]
        try:
            pid = DB_pokemon.get_pokemon_pid_by_name(name)
        except Exception:
            return [""]
        if not pid:
            return [""]
        try:
            no = int(pid.split("-")[0])
            mega_forms = DB_pokemon.get_mega_forms_by_no(no)
        except Exception:
            return [""]
        if not mega_forms:
            return [""]
        if len(mega_forms) >= 2:
            options = [""]
            if any(f != 12 for f in mega_forms):
                options.append("X")
            if 12 in mega_forms:
                options.append("Y")
            return options
        return ["", "メガ"]

    @staticmethod
    def _choice_to_pid(name: str, mega_label: str) -> str:
        """選出枠の (表示名, メガラベル) から保存pidを組み立てる。"""
        name = (name or "").strip()
        if not name:
            return "-1"
        try:
            pid = DB_pokemon.get_pokemon_pid_by_name(name) or "-1"
        except Exception:
            return "-1"
        if not mega_label or pid == "-1":
            return pid
        no_str = pid.split("-")[0]
        try:
            mega_forms = DB_pokemon.get_mega_forms_by_no(int(no_str))
        except Exception:
            mega_forms = []
        if not mega_forms:
            return pid
        if mega_label == "Y":
            target = 12 if 12 in mega_forms else mega_forms[0]
        elif mega_label == "X":
            non_y = [f for f in mega_forms if f != 12]
            target = non_y[0] if non_y else mega_forms[0]
        else:
            target = mega_forms[0]
        return f"{no_str}-{target}"

    def _save(self):
        player_pokemons = [self._name_to_pid(v.get()) for v in self.player_pokemon_vars]
        opponent_pokemons = [self._name_to_pid(v.get()) for v in self.opponent_pokemon_vars]
        player_choices = [
            self._choice_to_pid(
                self.player_choice_vars[i].get(),
                self.player_choice_mega_vars[i].get(),
            )
            for i in range(len(self.player_choice_vars))
        ]
        opponent_choices = [
            self._choice_to_pid(
                self.opponent_choice_vars[i].get(),
                self.opponent_choice_mega_vars[i].get(),
            )
            for i in range(len(self.opponent_choice_vars))
        ]

        try:
            dt = datetime.datetime.strptime(
                f"{self.date_var.get().strip()} {self.time_var.get().strip()}",
                "%Y/%m/%d %H:%M",
            )
        except ValueError:
            messagebox.showerror(
                "入力エラー",
                "日時は YYYY/MM/DD HH:MM 形式で入力してください。",
                parent=self,
            )
            return

        if self.is_new:
            battle = Battle(
                None,
                int(dt.timestamp()),
                self.rule_var.get(),
                self.result_var.get(),
                0,
                self.tn_var.get(),
                self.rate_var.get(),
                self.memo_text.get("1.0", "end-1c"),
                self.party_num_var.get().strip(),
                self.party_subnum_var.get().strip(),
                *player_pokemons,
                *opponent_pokemons,
                *player_choices,
                *opponent_choices,
            )
            DB_battle.register_battle(dataclasses.astuple(battle))
        else:
            DB_battle.update_battle_full(
                self.battle_id,
                int(dt.timestamp()),
                self.rule_var.get(),
                self.result_var.get(),
                self.tn_var.get(),
                self.rate_var.get(),
                self.memo_text.get("1.0", "end-1c"),
                self.party_num_var.get().strip(),
                self.party_subnum_var.get().strip(),
                player_pokemons,
                opponent_pokemons,
                player_choices,
                opponent_choices,
            )
        self.saved = True
        self.destroy()

    def _delete(self):
        if not messagebox.askyesno("削除確認", "このレコードを削除しますか？\nこの操作は元に戻せません。", parent=self):
            return
        DB_battle.delete_by_id(self.battle_id)
        self.deleted = True
        self.destroy()


class Record(tkinter.Toplevel):
    def __init__(self, master=None):
        super().__init__(master)
        self.title("対戦履歴")

        self.page_num_var = tkinter.IntVar(value=1)
        self.page_num_label = None
        self.page_position_label = None

        self.party_num = 0
        self.party_subnum = 0

        self.battle_time_label_list = []
        self.sensyutu_img_list = []
        self.rank_label_list = []
        self.win_lose_label_list = []
        self.canvas_list = []
        self.battle_data_list = []

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

        self.display_gui()

    def open(self):
        self.focus_set()
        self.geometry("1800x950")

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

    def display_gui(self):
        # 上部メニューの左端を「対戦時間」列の左端 (summaryX + 60 = 70) に合わせる
        search_x = Const.summaryX + 60
        search_y = Const.searchY
        search_dy = Const.searchDY

        self._seasons = self._load_seasons()
        season_names = ["カスタム"] + [s["name"] for s in self._seasons]
        season_label = tkinter.Label(self, text="シーズン")
        season_label.place(x=search_x, y=search_y - search_dy)
        self.season_var = tkinter.StringVar(self, value="カスタム")
        season_menu = tkinter.OptionMenu(
            self, self.season_var, *season_names, command=self._on_season_select
        )
        season_menu.place(x=search_x, y=search_y)

        self.time9_bln = tkinter.BooleanVar()
        self.time9_bln.set(True)
        time9_check = tkinter.Checkbutton(
            self, variable=self.time9_bln, text="開始日を11時以降にする"
        )
        time9_check.place(x=search_x + 120, y=search_y - search_dy)

        self.time23_bln = tkinter.BooleanVar()
        self.time23_bln.set(True)
        time23_check = tkinter.Checkbutton(
            self, variable=self.time23_bln, text="終了日を11時までにする"
        )
        time23_check.place(x=search_x + 320, y=search_y - search_dy)

        rank_label = tkinter.Label(self, text="パーティ絞り込み")
        rank_label.place(x=search_x, y=search_y + search_dy * 2)

        self.from_year_var = tkinter.IntVar(self)
        self.from_year_var.set(int(self.recent_date.year))
        self.from_year_menu = tkinter.OptionMenu(self, self.from_year_var, *Const.yearList)
        self.from_year_menu.place(x=search_x + 120, y=search_y)
        self.from_month_var = tkinter.IntVar(self)
        self.from_month_var.set(int(self.recent_date.month))
        self.from_date_var = tkinter.IntVar(self)
        self.from_date_var.set(13 if self.recent_date.day > 13 else 1)
        self.from_month_menu = tkinter.OptionMenu(
            self, self.from_month_var, *Const.monthList
        )
        self.from_month_menu.place(x=search_x + 190, y=search_y)
        self.from_date_menu = tkinter.OptionMenu(self, self.from_date_var, *Const.dateList)
        self.from_date_menu.place(x=search_x + 240, y=search_y)

        mack_label = tkinter.Label(self, text=" ~ ", font=Const.titleFont)
        mack_label.place(x=search_x + 290, y=search_y)

        self.to_year_var = tkinter.IntVar(self)
        self.to_year_var.set(int(self.recent_date.year))
        self.to_year_menu = tkinter.OptionMenu(self, self.to_year_var, *Const.yearList)
        self.to_year_menu.place(x=search_x + 320, y=search_y)
        self.to_month_var = tkinter.IntVar(self)
        self.to_month_var.set(int(self.recent_date.month))
        self.to_date_var = tkinter.IntVar(self)
        self.to_date_var.set(int(self.recent_date.day))
        self.to_month_menu = tkinter.OptionMenu(self, self.to_month_var, *Const.monthList)
        self.to_month_menu.place(x=search_x + 390, y=search_y)
        self.to_date_menu = tkinter.OptionMenu(self, self.to_date_var, *Const.dateList)
        self.to_date_menu.place(x=search_x + 450, y=search_y)

        sort_field_label = tkinter.Label(self, text="並び替え")
        sort_field_label.place(x=search_x + 550, y=search_y)
        self.sort_field_var = tkinter.StringVar(self, value="対戦時間")
        sort_field_menu = tkinter.OptionMenu(
            self, self.sort_field_var, "対戦時間", "登録順"
        )
        sort_field_menu.place(x=search_x + 610, y=search_y)

        self.sort_asc_var = tkinter.BooleanVar(value=True)

        def _toggle_sort_order():
            self.sort_asc_var.set(not self.sort_asc_var.get())
            self.sort_order_btn.config(text="昇順" if self.sort_asc_var.get() else "降順")

        self.sort_order_btn = tkinter.Button(
            self, text="昇順", width=4, command=_toggle_sort_order
        )
        self.sort_order_btn.place(x=search_x + 710, y=search_y)

        self.rule = tkinter.IntVar()
        self.rule.set(get_recog_value("rule"))
        rb_single = tkinter.Radiobutton(
            self, text="シングル", variable=self.rule, value=1
        )
        rb_single.place(x=search_x + 200, y=search_y + search_dy * 2.7)
        rb_double = tkinter.Radiobutton(
            self, text="ダブル", variable=self.rule, value=2
        )
        rb_double.place(x=search_x + 270, y=search_y + search_dy * 2.7)

        num_label = tkinter.Label(self, text="番号")
        num_label.place(x=search_x, y=search_y + search_dy * 3)
        self.num_txt = tkinter.Entry(self, width=Const.txtboxWidth)
        self.num_txt.place(x=search_x + 40, y=search_y + search_dy * 3)
        sub_num_label = tkinter.Label(self, text="連番")
        sub_num_label.place(x=search_x + 90, y=search_y + search_dy * 3)
        self.sub_num_txt = tkinter.Entry(self, width=Const.txtboxWidth)
        self.sub_num_txt.place(
            x=search_x + 130, y=search_y + search_dy * 3
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

        keyword_label = tkinter.Label(self, text="キーワード")
        keyword_label.place(x=search_x + 850, y=search_y - search_dy)
        _KW_PH = "相手TN・バトルメモで絞り込み"
        self.keyword_txt = tkinter.Text(self, width=24, height=2, fg="gray")
        self.keyword_txt.insert("1.0", _KW_PH)
        self.keyword_txt.place(x=search_x + 850, y=search_y)

        def _kw_focus_in(e):
            if self.keyword_txt.get("1.0", "end-1c") == _KW_PH:
                self.keyword_txt.delete("1.0", "end")
                self.keyword_txt.config(fg="black")

        def _kw_focus_out(e):
            if not self.keyword_txt.get("1.0", "end-1c").strip():
                self.keyword_txt.insert("1.0", _KW_PH)
                self.keyword_txt.config(fg="gray")

        self.keyword_txt.bind("<FocusIn>", _kw_focus_in)
        self.keyword_txt.bind("<FocusOut>", _kw_focus_out)
        self._keyword_ph = _KW_PH

        search_button = tkinter.Button(
            self,
            text="検索",
            command=self.get_battle_data,
        )
        search_button.place(
            x=search_x + 550, y=search_y + search_dy * 2.7
        )
        delete_range_button = tkinter.Button(
            self,
            text="この範囲を全削除",
            command=self.delete_range_data,
            fg="red",
        )
        delete_range_button.place(
            x=search_x + 620, y=search_y + search_dy * 2.7
        )
        export_button = tkinter.Button(
            self,
            text="CSVエクスポート",
            command=self.export_csv,
        )
        export_button.place(
            x=search_x + 760, y=search_y + search_dy * 2.7
        )
        self.favorite_var = tkinter.BooleanVar()
        self.favorite_var.set(False)
        favorite_check = tkinter.Checkbutton(
            self,
            variable=self.favorite_var,
            text="お気に入り",
            command=self.filter_favorites,
        )
        favorite_check.place(
            x=search_x + 450, y=search_y + search_dy * 2.7
        )
        add_button = tkinter.Button(
            self,
            text="新規追加",
            command=self._open_add_dialog,
        )
        add_button.place(
            x=search_x + 340, y=search_y + search_dy * 2.7
        )

        koumoku_label0 = tkinter.Label(
            self,
            text="対戦時間",
        )
        koumoku_label0.place(x=Const.summaryX + 30, y=Const.koumokuY)
        koumoku_label1 = tkinter.Label(
            self,
            text="自分のパーティ",
        )
        koumoku_label1.place(x=Const.myPokemonX + 50, y=Const.koumokuY)
        koumoku_label2 = tkinter.Label(self, text="選出")
        koumoku_label2.place(x=Const.mysensyutuX, y=Const.koumokuY)
        koumoku_label3 = tkinter.Label(self, text="勝敗")
        koumoku_label3.place(x=Const.winLoseX - 20, y=Const.koumokuY)
        koumoku_label4 = tkinter.Label(self, text="相手のパーティ")
        koumoku_label4.place(x=Const.opoPokemonX + 50, y=Const.koumokuY)
        koumoku_label4 = tkinter.Label(self, text="選出")
        koumoku_label4.place(x=Const.opposensyutuX + 50, y=Const.koumokuY)
        koumoku_label5 = tkinter.Label(self, text="TN")
        koumoku_label5.place(x=Const.tnX, y=Const.koumokuY)
        koumoku_label6 = tkinter.Label(self, text="相手のレート")
        koumoku_label6.place(x=Const.rankX, y=Const.koumokuY)

        paging_left_button = tkinter.Button(
            self, text="◀", command=self.click_paging_left
        )
        paging_left_button.place(x=1500, y=Const.koumokuY)
        paging_right_button = tkinter.Button(
            self, text="▶", command=self.click_paging_right
        )
        paging_right_button.place(x=1600, y=Const.koumokuY)

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

    def get_battle_data(self):
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
        kw_raw = self.keyword_txt.get("1.0", "end-1c").strip()
        keyword = "" if kw_raw == self._keyword_ph else kw_raw
        sort_field = "date" if self.sort_field_var.get() == "対戦時間" else "id"
        sort_asc = self.sort_asc_var.get()
        self.battle_data_list = DB_battle.get_battle_data_by_date(
            self.from_date,
            self.to_date,
            self.rule.get(),
            self.party_num,
            self.party_subnum,
            self.regends_dict[self.regend_num.get()]
            if self.regend_num.get() != "0"
            else "0",
            keyword,
            sort_field,
            sort_asc,
        )

        self.page_num_var.set(1)
        self.update_result()

    def update_result(self):
        self.sensyutu_img_list = []

        self.trash_photo = ImageTk.PhotoImage(Image.open("image/menu/trush.png"))

        self.canvas = tkinter.Canvas(self, width=1800, height=720)
        self.canvas.place(x=0, y=Const.pokemonImageY + 5)
        self.canvas.bind("<Button-3>", self._on_canvas_right_click)
        self.canvas.create_line(
            Const.outlineX,
            Const.outlineY,
            Const.outlineEndX,
            Const.outlineEndY,
            width=2.0,
            tag="line",
        )
        self.canvas.create_line(
            Const.outline2X,
            Const.outlineY,
            Const.outline2X,
            Const.outlineEndY,
            width=2.0,
            tag="line",
        )
        i = (self.page_num_var.get() - 1) * 15

        if self.page_position_label is not None:
            self.page_position_label.destroy()
        if self.page_num_label is not None:
            self.page_num_label.destroy()
        self.page_num_label = tkinter.Label(
            self,
            textvariable=self.page_num_var,
        )
        self.page_num_label.place(x=1540, y=Const.koumokuY)
        self.page_position_label = tkinter.Label(
            self,
            text=f"/ {math.ceil(len(self.battle_data_list) / 15)}",
        )
        self.page_position_label.place(x=1560, y=Const.koumokuY)
        for battle_data in self.battle_data_list[
            (self.page_num_var.get()) * 15 - 15 : (self.page_num_var.get()) * 15
        ]:
            battle_time = datetime.datetime.fromtimestamp(battle_data[1])
            row_y = Const.textStartY + Const.imageStartY + Const.battleDataDY * int(i % 15)
            self.canvas.create_text(
                Const.summaryX + 60,
                row_y - 8,
                text=battle_time.strftime("%Y/%m/%d"),
            )
            self.canvas.create_text(
                Const.summaryX + 60,
                row_y + 8,
                text=battle_time.strftime("%H:%M"),
            )
            trash_tag = f"trash_{i % 15}"
            self.canvas.create_image(
                Const.summaryX + 10,
                row_y,
                image=self.trash_photo,
                tags=(trash_tag,),
                anchor=tkinter.CENTER,
            )
            battle_id = battle_data[0]
            self.canvas.tag_bind(
                trash_tag, "<Button-1>",
                lambda e, bid=battle_id: self._delete_single(bid),
            )
            self.display_my_pokemon(battle_data, int(i % 15))
            self.display_my_sensyutu(battle_data, int(i % 15))
            self.display_opo_pokemon(battle_data, int(i % 15))
            self.display_oppo_sensyutu(battle_data, int(i % 15))
            self.canvas.create_text(
                Const.winLoseX,
                Const.textStartY + Const.imageStartY + Const.battleDataDY * int(i % 15),
                text="win" if battle_data[3] == 1 else ("draw" if battle_data[3] == -1 else "lose"),
                font=Const.titleFont,
            )
            self.canvas.create_text(
                Const.tnX + Const.tnDX,
                Const.textStartY + Const.imageStartY + Const.battleDataDY * int(i % 15),
                text=battle_data[5],
                font=Const.titleFont,
            )
            if battle_data[6] is not None and battle_data[6] != "":
                rankTxt = str(battle_data[6])
            else:
                rankTxt = "-"
            self.canvas.create_text(
                Const.rankX + Const.rankDX,
                Const.textStartY + Const.imageStartY + Const.battleDataDY * int(i % 15),
                text=rankTxt,
                font=Const.titleFont,
            )
            self.canvas.create_text(
                Const.memoX,
                Const.textStartY + Const.imageStartY + Const.battleDataDY * int(i % 15),
                text=battle_data[7],
                font=Const.smallFont,
            )

            i = i + 1
            if i > (self.page_num_var.get()) * 15 - 1:
                break

    def display_my_sensyutu(self, battle_data, i):
        for index, value in enumerate(range(22, 26)):
            if not (battle_data[value] is None or battle_data[value] == "-1"):
                img = Image.open(Const.createPass(battle_data[value]))
                img = img.resize((40, 40))
                img = ImageTk.PhotoImage(img)
                self.canvas.create_image(
                    Const.mysensyutuX + Const.myPartyDX * index,
                    Const.imageStartY + Const.battleDataDY * i,
                    image=img,
                    anchor=tkinter.NW,
                )
                self.sensyutu_img_list.append(img)

    def display_oppo_sensyutu(self, battle_data, i):
        for index, value in enumerate(range(26, 30)):
            if not (battle_data[value] is None or battle_data[value] == "-1"):
                img = Image.open(Const.createPass(battle_data[value]))
                img = img.resize((40, 40))
                img = ImageTk.PhotoImage(img)
                self.canvas.create_image(
                    Const.opposensyutuX + Const.myPartyDX * index,
                    Const.imageStartY + Const.battleDataDY * i,
                    image=img,
                    anchor=tkinter.NW,
                )
                self.sensyutu_img_list.append(img)

    def display_opo_pokemon(self, battle_data, i):
        for index, value in enumerate(range(16, 22)):
            if not battle_data[value] == "-1":
                img = Image.open(Const.createPass(battle_data[value]))
                img = img.resize((40, 40))
                img = ImageTk.PhotoImage(img)
                self.canvas.create_image(
                    Const.opoPokemonX + Const.myPartyDX * index,
                    Const.imageStartY + Const.battleDataDY * i,
                    image=img,
                    anchor=tkinter.NW,
                )
                self.sensyutu_img_list.append(img)

    def display_my_pokemon(self, battle_data, i):
        for index, value in enumerate(range(10, 16)):
            if not battle_data[value] == "-1":
                img = Image.open(Const.createPass(battle_data[value]))
                img = img.resize((40, 40))
                img = ImageTk.PhotoImage(img)
                self.canvas.create_image(
                    Const.myPokemonX + Const.myPartyDX * index,
                    Const.imageStartY + Const.battleDataDY * i,
                    image=img,
                    anchor=tkinter.NW,
                )
                self.sensyutu_img_list.append(img)

    def export_csv(self):
        import csv
        from tkinter import filedialog
        if not hasattr(self, "battle_data_list") or len(self.battle_data_list) == 0:
            messagebox.showinfo("情報", "エクスポートするデータがありません。先に検索してください。", parent=self)
            return
        path = filedialog.asksaveasfilename(
            title="エクスポート先を選択",
            defaultextension=".csv",
            filetypes=[("CSV", "*.csv"), ("すべてのファイル", "*.*")],
            initialfile="battle_export.csv",
        )
        if not path:
            return
        headers = [
            "id", "日時", "ルール", "勝敗", "お気に入り",
            "相手TN", "相手レート", "メモ", "パーティ番号", "パーティ連番",
            "自分P1", "自分P2", "自分P3", "自分P4", "自分P5", "自分P6",
            "相手P1", "相手P2", "相手P3", "相手P4", "相手P5", "相手P6",
            "自分選出1", "自分選出2", "自分選出3", "自分選出4",
            "相手選出1", "相手選出2", "相手選出3", "相手選出4",
        ]
        try:
            with open(path, "w", newline="", encoding="utf-8-sig") as f:
                writer = csv.writer(f)
                writer.writerow(headers)
                for row in self.battle_data_list:
                    dt = datetime.datetime.fromtimestamp(row[1]).strftime("%Y/%m/%d %H:%M")
                    result_str = "勝ち" if row[3] == 1 else ("引き分け" if row[3] == -1 else "負け")
                    writer.writerow([row[0], dt, row[2], result_str] + list(row[4:]))
            messagebox.showinfo("完了", f"{len(self.battle_data_list)}件をエクスポートしました。\n{path}", parent=self)
        except Exception as e:
            messagebox.showerror("エラー", f"エクスポートに失敗しました。\n{e}", parent=self)

    def _on_canvas_right_click(self, event):
        row_index = (event.y - Const.imageStartY) // Const.battleDataDY
        data_index = (self.page_num_var.get() - 1) * 15 + row_index
        if 0 <= data_index < len(self.battle_data_list):
            battle_data = self.battle_data_list[data_index]
            dialog = EditBattleDialog(self, battle_data)
            self.wait_window(dialog)
            if dialog.saved or dialog.deleted:
                self.get_battle_data()

    def _open_add_dialog(self):
        dialog = EditBattleDialog(
            self,
            battle_data=None,
            default_rule=self.rule.get(),
            default_party_num=self.num_txt.get(),
            default_party_subnum=self.sub_num_txt.get(),
        )
        self.wait_window(dialog)
        if dialog.saved and hasattr(self, "from_date"):
            self.get_battle_data()

    def _delete_single(self, battle_id: int):
        if not messagebox.askyesno("削除確認", "この対戦記録を削除しますか？\nこの操作は元に戻せません。", parent=self):
            return
        DB_battle.delete_by_id(battle_id)
        self.battle_data_list = [d for d in self.battle_data_list if d[0] != battle_id]
        self.update_result()

    def delete_range_data(self):
        if not hasattr(self, "from_date") or not hasattr(self, "to_date"):
            messagebox.showwarning("警告", "先に検索ボタンで絞り込んでください。", parent=self)
            return
        count = len(self.battle_data_list)
        if count == 0:
            messagebox.showinfo("情報", "削除対象のデータがありません。", parent=self)
            return
        if not messagebox.askokcancel(
            "削除確認",
            f"この操作は元に戻せません。\n現在の絞り込み範囲（{count}件）のデータを全て削除しますか？",
            parent=self,
        ):
            return
        DB_battle.delete_by_date_range(
            self.from_date, self.to_date, self.rule.get(), self.party_num, self.party_subnum
        )
        self.battle_data_list = []
        self.page_num_var.set(1)
        self.update_result()
        messagebox.showinfo("完了", f"{count}件のデータを削除しました。", parent=self)

    def filter_favorites(self):
        if self.favorite_var.get():
            self.battle_data_list = [x for x in self.battle_data_list if x[4] in (1, "1")]
            self.page_num_var.set(1)
            self.update_result()
        else:
            self.get_battle_data()

    def click_paging_left(self):
        if self.page_num_var.get() > 1:
            self.sensyutu_img_list = []
            self.page_num_var.set(self.page_num_var.get() - 1)
            self.update_result()

    def click_paging_right(self):
        if self.page_num_var.get() < len(self.battle_data_list) / 15:
            self.canvas.destroy()
            self.sensyutu_img_list = []
            self.page_num_var.set(self.page_num_var.get() + 1)
            self.update_result()


# 類似パーティ検索結果画面
class ListRecord(tkinter.Toplevel):
    def __init__(self, master=None):
        super().__init__(master)
        self.title("対戦履歴検索")
        self.full_frame = SearchRecord(
            master=self, source="full", height=290, width=1780
        )
        self.full_frame.grid(row=0, column=0)
        self.part_frame = SearchRecord(
            master=self, source="part", height=290, width=1780
        )
        self.part_frame.grid(row=1, column=0)

    def open(self):
        self.focus_set()
        self.geometry("1800x600")


# 履歴検索結果フレーム
class SearchRecord(tkinter.Frame):
    def __init__(self, master, source, **kwargs):
        super().__init__(master, **kwargs)

        self.source = source

        self.page_num_var = tkinter.IntVar(value=0)
        self.page_num_label = None
        self.page_position_label = None

        self.battle_time_label_list = []
        self.sensyutu_img_list = []
        self.rank_label_list = []
        self.win_lose_label_list = []
        self.canvas_list = []
        self.battle_data_list = []

        self.display_gui()

    def display_gui(self):
        koumoku_label0 = tkinter.Label(
            self,
            text="対戦時間",
        )
        koumoku_label0.place(x=Const.summaryX + 20, y=Const.searchY)
        koumoku_label1 = tkinter.Label(
            self,
            text="自分のパーティ",
        )
        koumoku_label1.place(x=Const.myPokemonX, y=Const.searchY)
        koumoku_label2 = tkinter.Label(self, text="選出")
        koumoku_label2.place(x=Const.mysensyutuX, y=Const.searchY)
        koumoku_label3 = tkinter.Label(self, text="勝敗")
        koumoku_label3.place(x=Const.winLoseX - 20, y=Const.searchY)
        koumoku_label4 = tkinter.Label(self, text="相手のパーティ")
        koumoku_label4.place(x=Const.opoPokemonX + 50, y=Const.searchY)
        koumoku_label4 = tkinter.Label(self, text="選出")
        koumoku_label4.place(x=Const.opposensyutuX + 50, y=Const.searchY)
        koumoku_label5 = tkinter.Label(self, text="TN")
        koumoku_label5.place(x=Const.tnX, y=Const.searchY)
        koumoku_label6 = tkinter.Label(self, text="相手のレート")
        koumoku_label6.place(x=Const.rankX, y=Const.searchY)

        paging_left_button = tkinter.Button(
            self, text="◀", command=self.click_paging_left
        )
        paging_left_button.place(x=1500, y=Const.searchY)
        paging_right_button = tkinter.Button(
            self, text="▶", command=self.click_paging_right
        )
        paging_right_button.place(x=1600, y=Const.searchY)

    def get_battle_data(self, poke_list: list[str]):
        self.battle_data_list = (
            DB_battle.record_search_full(poke_list)
            if self.source == "full"
            else DB_battle.record_search(poke_list)
        )
        if len(self.battle_data_list) > 0:
            self.page_num_var.set(1)
        self.update_result()
        return self.battle_data_list

    def update_result(self):
        self.sensyutu_img_list = []

        result_label = (
            "完全一致の検索結果" if self.source == "full" else "6匹同じポケモン"
        )
        result_num_label = tkinter.Label(
            self,
            text=f"{result_label}：{len(self.battle_data_list)}件",
            font=Const.titleFont,
        )
        result_num_label.place(x=Const.summaryX + 20, y=Const.searchDY)

        self.canvas = tkinter.Canvas(self, width=1800, height=270)
        self.canvas.place(x=0, y=Const.pokemonImageY - Const.titleLabelY)
        self.canvas.create_line(
            Const.outlineX,
            Const.outlineY,
            Const.outlineEndX,
            Const.outlineY + 250,
            width=2.0,
            tag="line",
        )
        self.canvas.create_line(
            Const.outline2X,
            Const.outlineY,
            Const.outline2X,
            Const.outlineY + 250,
            width=2.0,
            tag="line",
        )
        i = (self.page_num_var.get() - 1) * 5

        if self.page_position_label is not None:
            self.page_position_label.destroy()
        if self.page_num_label is not None:
            self.page_num_label.destroy()
        self.page_num_label = tkinter.Label(
            self,
            textvariable=self.page_num_var,
        )
        self.page_num_label.place(x=1540, y=Const.searchY)
        self.page_position_label = tkinter.Label(
            self,
            text=f"/ {math.ceil(len(self.battle_data_list) / 5)}",
        )
        self.page_position_label.place(x=1560, y=Const.searchY)
        for battle_data in self.battle_data_list[
            (self.page_num_var.get()) * 5 - 5 : (self.page_num_var.get()) * 5
        ]:
            battle_time = datetime.datetime.fromtimestamp(battle_data[1])
            self.canvas.create_text(
                Const.summaryX + 50,
                Const.textStartY + Const.imageStartY + Const.battleDataDY * int(i % 5),
                text=battle_time.strftime("%Y/%m/%d %H:%M"),
            )
            self.display_my_pokemon(battle_data, int(i % 5))
            self.display_my_sensyutu(battle_data, int(i % 5))
            self.display_opo_pokemon(battle_data, int(i % 5))
            self.display_oppo_sensyutu(battle_data, int(i % 5))
            self.canvas.create_text(
                Const.winLoseX,
                Const.textStartY + Const.imageStartY + Const.battleDataDY * int(i % 5),
                text="win" if battle_data[3] == 1 else ("draw" if battle_data[3] == -1 else "lose"),
                font=Const.titleFont,
            )
            self.canvas.create_text(
                Const.tnX + Const.tnDX,
                Const.textStartY + Const.imageStartY + Const.battleDataDY * int(i % 5),
                text=battle_data[5],
                font=Const.titleFont,
            )
            if battle_data[6] is not None and battle_data[6] != "":
                rankTxt = str(battle_data[6])
            else:
                rankTxt = "-"
            self.canvas.create_text(
                Const.rankX + Const.rankDX,
                Const.textStartY + Const.imageStartY + Const.battleDataDY * int(i % 5),
                text=rankTxt,
                font=Const.titleFont,
            )
            self.canvas.create_text(
                Const.memoX,
                Const.textStartY + Const.imageStartY + Const.battleDataDY * int(i % 5),
                text=battle_data[7],
                font=Const.smallFont,
            )

            i = i + 1
            if i > (self.page_num_var.get()) * 5 - 1:
                break

    def display_my_sensyutu(self, battle_data, i):
        for index, value in enumerate(range(22, 26)):
            if not (battle_data[value] is None or battle_data[value] == "-1"):
                img = Image.open(Const.createPass(battle_data[value]))
                img = img.resize((40, 40))
                img = ImageTk.PhotoImage(img)
                self.canvas.create_image(
                    Const.mysensyutuX + Const.myPartyDX * index,
                    Const.imageStartY + Const.battleDataDY * i,
                    image=img,
                    anchor=tkinter.NW,
                )
                self.sensyutu_img_list.append(img)

    def display_oppo_sensyutu(self, battle_data, i):
        for index, value in enumerate(range(26, 30)):
            if not (battle_data[value] is None or battle_data[value] == "-1"):
                img = Image.open(Const.createPass(battle_data[value]))
                img = img.resize((40, 40))
                img = ImageTk.PhotoImage(img)
                self.canvas.create_image(
                    Const.opposensyutuX + Const.myPartyDX * index,
                    Const.imageStartY + Const.battleDataDY * i,
                    image=img,
                    anchor=tkinter.NW,
                )
                self.sensyutu_img_list.append(img)

    def display_opo_pokemon(self, battle_data, i):
        for index, value in enumerate(range(16, 22)):
            if not battle_data[value] == "-1":
                img = Image.open(Const.createPass(battle_data[value]))
                img = img.resize((40, 40))
                img = ImageTk.PhotoImage(img)
                self.canvas.create_image(
                    Const.opoPokemonX + Const.myPartyDX * index,
                    Const.imageStartY + Const.battleDataDY * i,
                    image=img,
                    anchor=tkinter.NW,
                )
                self.sensyutu_img_list.append(img)

    def display_my_pokemon(self, battle_data, i):
        for index, value in enumerate(range(10, 16)):
            if not battle_data[value] == "-1":
                img = Image.open(Const.createPass(battle_data[value]))
                img = img.resize((40, 40))
                img = ImageTk.PhotoImage(img)
                self.canvas.create_image(
                    Const.myPokemonX + Const.myPartyDX * index,
                    Const.imageStartY + Const.battleDataDY * i,
                    image=img,
                    anchor=tkinter.NW,
                )
                self.sensyutu_img_list.append(img)

    def click_paging_left(self):
        if self.page_num_var.get() > 1:
            self.sensyutu_img_list = []
            self.page_num_var.set(self.page_num_var.get() - 1)
            self.update_result()

    def click_paging_right(self):
        if self.page_num_var.get() < len(self.battle_data_list) / 5:
            self.canvas.destroy()
            self.sensyutu_img_list = []
            self.page_num_var.set(self.page_num_var.get() + 1)
            self.update_result()
