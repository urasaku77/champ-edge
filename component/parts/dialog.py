import csv
import math
import tkinter
import webbrowser
from tkinter import E, N, S, W, messagebox, ttk


def _open_url(url: str):
    try:
        webbrowser.open(url)
    except Exception as e:
        messagebox.showerror("エラー", f"ブラウザを開けませんでした\n{e}")
from tkinter.font import Font

from component.parts import images
from component.parts.button import MyButton, TypeButton
from component.parts.combobox import AutoCompleteCombobox, ModifiedEntry
from component.parts.label import MyLabel
from database.pokemon import DB_pokemon
from pokedata.const import Types
from pokedata.pokemon import Pokemon
from recog.recog import get_recog_value


# パーティ入力ダイアログ
class PartyInputDialog(tkinter.Toplevel):
    def __init__(self, master=None, title: str = "", width: int = 400, height: int = 300):
        super().__init__(master)
        if master is not None:
            self.transient(master)
        self.title("パーティ入力")

        self._selected = tkinter.IntVar()
        self._radio_buttons = []
        self._labels = []
        _blank = Pokemon()
        self._party: list[Pokemon] = [_blank, _blank, _blank, _blank, _blank, _blank]

        # ウィジェットの配置
        main_frame = ttk.Frame(self, padding=10)
        main_frame.grid(row=0, column=0, sticky=N + E + W + S)
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        self._labelframe = ttk.LabelFrame(main_frame, text="ポケモン名を入力")
        self._labelframe.grid(row=0, column=0, columnspan=6)

        self._name_input: AutoCompleteCombobox = AutoCompleteCombobox.pokemons(
            self._labelframe
        )
        self._name_input.bind("<<submit>>", self.on_input_name)
        self._name_input.grid(row=0, column=0)

        for i in range(6):
            radio = ttk.Radiobutton(
                main_frame,
                value=i,
                variable=self._selected,
                command=self.on_push_radiobutton,
            )
            radio.grid(row=1, column=i)
            self._radio_buttons.append(radio)

            label = MyLabel(main_frame, size=(40, 40), relief=tkinter.RAISED, padding=0)
            label.grid(row=2, column=i)
            self._labels.append(label)

        self._close_button = ttk.Button(
            main_frame, text="決定", command=lambda: self.destroy()
        )
        self._close_button.bind("<Return>", lambda _: self.destroy())
        self._close_button.grid(row=3, column=0, columnspan=6)

    @property
    def party(self) -> list[Pokemon]:
        return self._party

    @party.setter
    def party(self, value: list[Pokemon]):
        self._party = value
        for i in range(6):
            if value[i].is_empty is False:
                self.set_pokemon_icon(pid=value[i].pid, index=i)

    @property
    def selected_index(self) -> int:
        return self._selected.get()

    def open(self, location=tuple[int, int]):
        self.grab_set()
        self.select(0)
        self._name_input.focus_set()
        self.geometry("+{0}+{1}".format(location[0], location[1]))

    def select(self, index: int):
        pokemon = self._party[index]
        if pokemon.is_empty:
            self._name_input.set("")
        else:
            self._name_input.set(pokemon.name)

    def set_pokemon_icon(self, pid: str, index: int):
        self._labels[index].set_image(images.get_pokemon_icon(pid=pid, size=(40, 40)))

    def on_input_name(self, *args):
        pokemon_name = self._name_input.get()
        pokemon: Pokemon = Pokemon.by_name(pokemon_name, default=True)
        index: int = self.selected_index

        self._party[index] = pokemon
        self.set_pokemon_icon(pid=pokemon.pid, index=index)

        if index < 5:
            self._selected.set(index + 1)
            self.select(index + 1)
        else:
            self._close_button.focus_set()

    def on_push_radiobutton(self, *args):
        self.select(self.selected_index)


# タイプ指定ダイアログ
class TypeSelectDialog(tkinter.Toplevel):
    def __init__(self, master=None, title: str = "タイプ選択", width: int = 400, height: int = 300):
        super().__init__(master)
        if master is not None:
            self.transient(master)
        self.title(title)
        self._selected_type = None

        for idx, t in enumerate(Types):
            button = TypeButton(
                self, type_=t, command=lambda x=t: self.on_push_button(x)
            )
            button.grid(column=(idx % 4), row=(idx // 4), sticky=E + W)

    @property
    def selected_type(self):
        return self._selected_type

    def open(self, location=tuple[int, int]):
        self.grab_set()
        self.focus_set()
        self.geometry("+{0}+{1}".format(location[0], location[1]))

    def on_push_button(self, t: Types):
        self._selected_type = t
        self.destroy()


# ポケモンメモ表示ダイアログ
class PokemonMemoLabelDialog(tkinter.Toplevel):
    def __init__(self, master=None, title: str = "", width: int = 400, height: int = 300):
        super().__init__(master)
        if master is not None:
            self.transient(master)
        self.title("ポケモンメモ")

        # ウィジェットの配置
        main_frame = ttk.Frame(self, padding=10)
        main_frame.pack()
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        self.memo_var = tkinter.StringVar()
        self.memo_var.set("")
        self.memo_label = ttk.Label(main_frame, textvariable=self.memo_var)
        self.memo_label.pack()

    def open(self, memo: str, location=tuple[int, int]):
        self.grab_set()
        self.memo_var.set(memo)
        self.geometry("+{0}+{1}".format(location[0], location[1]))

    def close(self, *args):
        self.destroy()


# 素早さ比較画面
class SpeedComparing(tkinter.Toplevel):
    def on_validate_2(self, P, V):
        if P.isdigit() or P == "":
            return len(P) <= 2
        else:
            return False

    def on_validate_3(self, P, V):
        if P.isdigit() or P == "":
            return len(P) <= 3
        else:
            return False

    def __init__(self, master=None, title: str = "素早さ比較", width: int = 600, height: int = 500):
        super().__init__(master)
        if master is not None:
            self.transient(master)
        self.title(title)
        self.pokemons: list[Pokemon] = [Pokemon(), Pokemon()]
        self.tailwind = [1.0, 1.0]
        self.paralysis = [1.0, 1.0]

        self.name_var: list[tkinter.StringVar] = [
            tkinter.StringVar(),
            tkinter.StringVar(),
        ]
        self.compare_mark: tkinter.StringVar = tkinter.StringVar()
        self.speed_var: list[tkinter.StringVar] = [
            tkinter.StringVar(),
            tkinter.StringVar(),
        ]
        self.base_stat_var: list[tkinter.IntVar] = [tkinter.IntVar(), tkinter.IntVar()]
        self.nature_var: list[tkinter.StringVar] = [
            tkinter.StringVar(value="1.0"),
            tkinter.StringVar(value="1.0"),
        ]
        self.rank_var: list[tkinter.IntVar] = [
            tkinter.IntVar(value=0),
            tkinter.IntVar(value=0),
        ]
        self.ability_var: list[tkinter.StringVar] = [
            tkinter.StringVar(value="1.0"),
            tkinter.StringVar(value="1.0"),
        ]
        self.item_var: list[tkinter.StringVar] = [
            tkinter.StringVar(value="1.0"),
            tkinter.StringVar(value="1.0"),
        ]
        self.tailwind_var: list[tkinter.BooleanVar] = [
            tkinter.BooleanVar(value=False),
            tkinter.BooleanVar(value=False),
        ]
        self.paralysis_var: list[tkinter.BooleanVar] = [
            tkinter.BooleanVar(value=False),
            tkinter.BooleanVar(value=False),
        ]

        base_stat_label = tkinter.Label(self, text="種族値")
        base_stat_label.grid(row=3, column=1)
        iv_label = tkinter.Label(self, text="個体値")
        iv_label.grid(row=4, column=1)
        ev_label = tkinter.Label(self, text="努力値")
        ev_label.grid(row=5, column=1)
        nature_label = tkinter.Label(self, text="性格")
        nature_label.grid(row=6, column=1)
        rank_label = tkinter.Label(self, text="ランク")
        rank_label.grid(row=7, column=1)
        ability_label = tkinter.Label(self, text="特性")
        ability_label.grid(row=8, column=1)
        item_label = tkinter.Label(self, text="道具")
        item_label.grid(row=9, column=1)
        tailwind_label = tkinter.Label(self, text="おいかぜ")
        tailwind_label.grid(row=10, column=1)
        paralysis_label = tkinter.Label(self, text="まひ")
        paralysis_label.grid(row=11, column=1)

        self.validate_cmd_2 = self.register(self.on_validate_2)
        self.validate_cmd_3 = self.register(self.on_validate_3)

        self.pokemon_icon: list[MyLabel] = [MyLabel(self), MyLabel(self)]
        self.name_label = [
            tkinter.Label(self, textvariable=self.name_var[i]) for i in range(2)
        ]

        self.compare = tkinter.Label(
            self, textvariable=self.compare_mark, font=Font(weight="bold", size=16)
        )
        self.compare.grid(row=2, column=1, pady=5)
        self.speed_label = [
            tkinter.Label(
                self, textvariable=self.speed_var[i], font=Font(weight="bold", size=32)
            )
            for i in range(2)
        ]

        # 種族値
        self.base_stat = [
            tkinter.Label(self, textvariable=self.base_stat_var[i]) for i in range(2)
        ]

        # 個体値（31固定）
        self.iv_box = [ttk.Frame(self, padding=10), ttk.Frame(self, padding=10)]
        self.iv_label = [
            tkinter.Label(self.iv_box[i], text="31")
            for i in range(2)
        ]

        # 努力値
        self.ev_box = [ttk.Frame(self, padding=10), ttk.Frame(self, padding=10)]
        self.ev_entry = [
            ModifiedEntry(
                self.ev_box[i],
                validate="key",
                width=4,
                validatecommand=(self.validate_cmd_2, "%P", "%V"),
            )
            for i in range(2)
        ]
        self.ev_max = [
            MyButton(
                self.ev_box[i],
                text="32",
                command=lambda index=i: self.change_ev(True, index),
            )
            for i in range(2)
        ]
        self.ev_min = [
            MyButton(
                self.ev_box[i],
                text="0",
                command=lambda index=i: self.change_ev(False, index),
            )
            for i in range(2)
        ]
        self.ev_entry[0].bind("<<TextModified>>", self.calc_speed)
        self.ev_entry[1].bind("<<TextModified>>", self.calc_speed)

        # 性格
        self.nature_box = [ttk.Frame(self), ttk.Frame(self)]
        self.nature_radio1 = [
            tkinter.Radiobutton(
                self.nature_box[i],
                text="0.9",
                variable=self.nature_var[i],
                value="0.9",
                command=self.calc_speed,
            )
            for i in range(2)
        ]
        self.nature_radio2 = [
            tkinter.Radiobutton(
                self.nature_box[i],
                text="1.0",
                variable=self.nature_var[i],
                value="1.0",
                command=self.calc_speed,
            )
            for i in range(2)
        ]
        self.nature_radio3 = [
            tkinter.Radiobutton(
                self.nature_box[i],
                text="1.1",
                variable=self.nature_var[i],
                value="1.1",
                command=self.calc_speed,
            )
            for i in range(2)
        ]

        # ランク
        self.rank_box = [ttk.Frame(self, padding=10), ttk.Frame(self, padding=10)]
        self.rank_minus = [
            MyButton(
                self.rank_box[i],
                text="-1",
                command=lambda index=i: self.change_rank(False, index),
            )
            for i in range(2)
        ]
        self.rank = [
            tkinter.Label(self.rank_box[i], textvariable=self.rank_var[i])
            for i in range(2)
        ]
        self.rank_plus = [
            MyButton(
                self.rank_box[i],
                text="+1",
                command=lambda index=i: self.change_rank(True, index),
            )
            for i in range(2)
        ]

        # 特性
        self.ability_box = [ttk.Frame(self), ttk.Frame(self)]
        self.ability_radio1 = [
            tkinter.Radiobutton(
                self.ability_box[i],
                text="0.5",
                variable=self.ability_var[i],
                value="0.5",
                command=self.calc_speed,
            )
            for i in range(2)
        ]
        self.ability_radio2 = [
            tkinter.Radiobutton(
                self.ability_box[i],
                text="1.0",
                variable=self.ability_var[i],
                value="1.0",
                command=self.calc_speed,
            )
            for i in range(2)
        ]
        self.ability_radio3 = [
            tkinter.Radiobutton(
                self.ability_box[i],
                text="1.5",
                variable=self.ability_var[i],
                value="1.5",
                command=self.calc_speed,
            )
            for i in range(2)
        ]
        self.ability_radio4 = [
            tkinter.Radiobutton(
                self.ability_box[i],
                text="2.0",
                variable=self.ability_var[i],
                value="2.0",
                command=self.calc_speed,
            )
            for i in range(2)
        ]

        # 道具
        self.item_box = [ttk.Frame(self), ttk.Frame(self)]
        self.item_radio1 = [
            tkinter.Radiobutton(
                self.item_box[i],
                text="0.5",
                variable=self.item_var[i],
                value="0.5",
                command=self.calc_speed,
            )
            for i in range(2)
        ]
        self.item_radio2 = [
            tkinter.Radiobutton(
                self.item_box[i],
                text="1.0",
                variable=self.item_var[i],
                value="1.0",
                command=self.calc_speed,
            )
            for i in range(2)
        ]
        self.item_radio3 = [
            tkinter.Radiobutton(
                self.item_box[i],
                text="1.5",
                variable=self.item_var[i],
                value="1.5",
                command=self.calc_speed,
            )
            for i in range(2)
        ]
        self.item_radio4 = [
            tkinter.Radiobutton(
                self.item_box[i],
                text="2.0",
                variable=self.item_var[i],
                value="2.0",
                command=self.calc_speed,
            )
            for i in range(2)
        ]

        # おいかぜ
        self.tailwind_checkbox = [
            tkinter.Checkbutton(
                self, variable=self.tailwind_var[i], command=self.change_tailwind
            )
            for i in range(2)
        ]

        # まひ
        self.paralysis_checkbox = [
            tkinter.Checkbutton(
                self, variable=self.paralysis_var[i], command=self.change_paralysis
            )
            for i in range(2)
        ]

        self.all_components: list[list] = [
            self.pokemon_icon,
            self.name_label,
            self.speed_label,
            self.base_stat,
            self.iv_box,
            self.ev_box,
            self.nature_box,
            self.rank_box,
            self.ability_box,
            self.item_box,
            self.tailwind_checkbox,
            self.paralysis_checkbox,
        ]

        self.all_sub_components: list[list] = [
            self.iv_label,
            self.ev_entry,
            self.ev_min,
            self.ev_max,
            self.nature_radio1,
            self.nature_radio2,
            self.nature_radio3,
            self.rank_minus,
            self.rank,
            self.rank_plus,
            self.ability_radio1,
            self.ability_radio2,
            self.ability_radio3,
            self.ability_radio4,
            self.item_radio1,
            self.item_radio2,
            self.item_radio3,
            self.item_radio4,
        ]

        for i in range(2):
            for j in range(len(self.all_sub_components)):
                self.all_sub_components[j][i].pack(side="left")

        for i in range(2):
            for j in range(len(self.all_components)):
                self.all_components[j][i].grid(row=j, column=i * 2, pady=5)

    def set_pokemon(self, pokemons: list[Pokemon]):
        self.pokemons = pokemons
        for i in range(2):
            self.pokemon_icon[i].set_pokemon_icon(pokemons[i].pid, [60, 60])
            self.name_var[i].set(pokemons[i].name)
            self.base_stat_var[i].set(pokemons[i].syuzoku.S)
            self.ev_entry[i].delete(0, tkinter.END)
            self.ev_entry[i].insert(0, pokemons[i].doryoku.S)
            self.rank_var[i].set(pokemons[i].rank.S)
            if pokemons[i].seikaku in ["おくびょう", "せっかち", "やんちゃ", "ようき"]:
                self.nature_var[i].set("1.1")
            elif pokemons[i].seikaku in ["ゆうかん", "のんき", "れいせい", "なまいき"]:
                self.nature_var[i].set("0.9")
            if pokemons[i].item == "こだわりスカーフ":
                self.item_var[i].set("1.5")
        self.calc_speed()

    def change_rank(self, up: bool, player: int):
        rank = self.rank_var[player].get()
        if up and rank < 6:
            rank += 1
        elif not up and rank > -6:
            rank -= 1
        self.rank_var[player].set(rank)
        self.calc_speed()

    def change_ev(self, up: bool, player: int):
        self.ev_entry[player].delete(0, tkinter.END)
        if up:
            self.ev_entry[player].insert(0, "32")
        else:
            self.ev_entry[player].insert(0, "0")
        self.calc_speed()

    def change_tailwind(self):
        for i in range(2):
            if self.tailwind_var[i].get():
                self.tailwind[i] = 2.0
            else:
                self.tailwind[i] = 1.0
        self.calc_speed(self)

    def change_paralysis(self):
        for i in range(2):
            if self.paralysis_var[i].get():
                self.paralysis[i] = 0.5
            else:
                self.paralysis[i] = 1.0
        self.calc_speed(self)

    def calc_speed(self, *args):
        rank = [
            (
                (self.rank_var[i].get() + 2) / 2
                if self.rank_var[i].get() >= 0
                else 2 / (abs(self.rank_var[i].get()) + 2)
            )
            for i in range(2)
        ]
        base = [
            (
                math.floor(
                    (
                        self.base_stat_var[i].get() * 2
                        + 31
                        + int(self.ev_entry[i].get()) * 2
                    )
                    * 50
                    / 100
                )
                + 5
            )
            * float(self.nature_var[i].get())
            * float(self.ability_var[i].get())
            * float(self.item_var[i].get())
            * self.tailwind[i]
            * self.paralysis[i]
            * rank[i]
            for i in range(2)
        ]

        if int(base[0]) < int(base[1]):
            self.compare_mark.set("<")
            self.speed_label[0]["fg"] = "blue"
            self.speed_label[1]["fg"] = "red"
        elif int(base[0]) > int(base[1]):
            self.compare_mark.set(">")
            self.speed_label[0]["fg"] = "red"
            self.speed_label[1]["fg"] = "blue"
        else:
            self.compare_mark.set("=")
            self.speed_label[0]["fg"] = "black"
            self.speed_label[1]["fg"] = "black"

        for i in range(2):
            self.speed_var[i].set(int(base[i]))

    def open(self, location=tuple[int, int]):
        self.grab_set()
        self.focus_set()
        self.geometry("+{0}+{1}".format(location[0], location[1]))


# フォーム選択画面
class FormSelect(tkinter.Toplevel):
    def __init__(
        self, master=None, title: str = "フォーム選択", width: int = 400, height: int = 300
    ):
        super().__init__(master)
        if master is not None:
            self.transient(master)
        self.title(title)
        self.form_num = -1

    def set_pokemon(self, num: int):
        self.no = str(num)
        self.pokemon_names = DB_pokemon.get_pokemons_name_by_no(self.no)

        for i in range(len(self.pokemon_names)):
            self.form_button = MyButton(
                self,
                text=self.pokemon_names[i],
                command=lambda index=i: self.on_push_button(index),
            )
            self.form_button.grid(row=1, column=i, pady=10)

    def open(self, location=tuple[int, int]):
        self.grab_set()
        self.focus_set()
        self.geometry("+{0}+{1}".format(location[0], location[1]))

    def on_push_button(self, index):
        self.form_num = index
        self.destroy()


# 類似パーティ検索結果画面
class SimilarParty(tkinter.Toplevel):
    def __init__(
        self,
        master=None,
        title: str = "類似パーティ検索結果",
        width: int = 400,
        height: int = 300,
        current_party: list[str] = None,
        party_list: list[dict] = None,
    ):
        if current_party is None:
            current_party = []
        if party_list is None:
            party_list = []
        super().__init__(master)
        if master is not None:
            self.transient(master)
        self.title(title)

        if len(party_list) != 0:
            result_label = ttk.Label(
                self, text=f"一致したパーティ：{len(party_list)}件", padding=10
            )
            result_label.pack(side="top")
            for i in range(len(party_list)):
                icons_frame = ttk.Frame(self, padding=10)
                for j in range(6):
                    icon = MyLabel(
                        icons_frame,
                    )
                    icon.set_pokemon_icon(
                        party_list[i]["icons"][j], size=(30, 30)
                    )
                    icon.pack(side="left", padx=20, pady=10)
                link_button = MyButton(
                    icons_frame,
                    text="構築記事",
                    command=lambda url=party_list[i]["url"]: _open_url(url),
                )
                link_button.pack(side="left", padx=50)
                icons_frame.pack(side="top")

    def open(self, location=tuple[int, int]):
        self.grab_set()
        self.focus_set()
        self.geometry("+{0}+{1}".format(location[0], location[1]))


# 重さ比較画面
class WeightComparing(tkinter.Toplevel):
    def __init__(self, master=None, title: str = "重さ比較", width: int = 600, height: int = 500):
        super().__init__(master)
        if master is not None:
            self.transient(master)
        self.title(title)
        self.pokemons: list[Pokemon] = [Pokemon(), Pokemon()]

        self.name_var: list[tkinter.StringVar] = [
            tkinter.StringVar(),
            tkinter.StringVar(),
        ]
        self.compare_mark: tkinter.StringVar = tkinter.StringVar()
        self.weight_var: list[tkinter.DoubleVar] = [
            tkinter.DoubleVar(),
            tkinter.DoubleVar(),
        ]
        self.power_var: list[tkinter.IntVar] = [
            tkinter.IntVar(),
            tkinter.IntVar(),
        ]

        self.pokemon_icon: list[MyLabel] = [MyLabel(self), MyLabel(self)]
        self.name_label = [
            tkinter.Label(self, textvariable=self.name_var[i]) for i in range(2)
        ]
        self.weight_label = [
            tkinter.Label(
                self, textvariable=self.weight_var[i], font=Font(weight="bold", size=32)
            )
            for i in range(2)
        ]

        self.power_label = [
            tkinter.Label(
                self, textvariable=self.power_var[i], font=Font(weight="bold", size=32)
            )
            for i in range(2)
        ]

        self.compare = tkinter.Label(
            self, textvariable=self.compare_mark, font=Font(weight="bold", size=16)
        )
        self.compare.grid(row=2, column=1, pady=5)

        self.power_name_label = tkinter.Label(
            self, text="威力", font=Font(weight="bold", size=16)
        )
        self.power_name_label.grid(row=3, column=1, pady=5)

        self.all_components: list[list] = [
            self.pokemon_icon,
            self.name_label,
        ]

        for i in range(2):
            for j in range(len(self.all_components)):
                self.all_components[j][i].grid(row=j, column=i * 2, pady=5)

        for i in range(2):
            self.weight_label[i].grid(row=2, column=i * 2, pady=5)
            self.power_label[i].grid(row=3, column=i * 2, pady=5)

    def set_pokemon(self, pokemons: list[Pokemon]):
        self.pokemons = pokemons
        for i in range(2):
            self.pokemon_icon[i].set_pokemon_icon(pokemons[i].pid, [60, 60])
            self.name_var[i].set(pokemons[i].name)
            self.weight_var[i].set(pokemons[i].weight)
        self.calc_weight()
        self.calc_power()

    def calc_weight(self, *args):
        if self.weight_var[0].get() < self.weight_var[1].get():
            self.compare_mark.set("<")
            self.weight_label[0]["fg"] = "blue"
            self.weight_label[1]["fg"] = "red"
        elif self.weight_var[0].get() > self.weight_var[1].get():
            self.compare_mark.set(">")
            self.weight_label[0]["fg"] = "red"
            self.weight_label[1]["fg"] = "blue"
        else:
            self.compare_mark.set("=")
            self.weight_label[0]["fg"] = "black"
            self.weight_label[1]["fg"] = "black"

    def calc_power(self, *args):
        power: list[float] = [
            self.weight_var[1].get() / self.weight_var[0].get(),
            self.weight_var[0].get() / self.weight_var[1].get(),
        ]

        for i in range(2):
            if power[i] < 0.2:
                self.power_var[i].set(120)
            elif power[i] < 0.25:
                self.power_var[i].set(100)
            elif power[i] < 0.3:
                self.power_var[i].set(80)
            elif power[i] < 0.5:
                self.power_var[i].set(60)
            else:
                self.power_var[i].set(40)

    def open(self, location=tuple[int, int]):
        self.grab_set()
        self.focus_set()
        self.geometry("+{0}+{1}".format(location[0], location[1]))


class BoxDialog(tkinter.Toplevel):
    def __init__(self, master=None):
        super().__init__(master)
        if master is not None:
            self.transient(master)
        self.title("ボックス管理")
        tera_enabled = get_recog_value("terastal_enabled")
        self.geometry(f"{'1400' if tera_enabled else '1250'}x900")

        self.pokemon = Pokemon()
        self.file_path = "party\\csv\\box.csv"
        self.all_box_data = self.read_csv(self.file_path)

        self.current_page_num = tkinter.IntVar()
        self.all_page_num = tkinter.IntVar()

        self.pokes_frame = ttk.Frame(self, padding=10)
        self.top_frame = ttk.Frame(self, padding=10)
        self.top_frame.pack(side="top", padx=20, fill="x")
        self.top_left_frame = ttk.Frame(self.top_frame)
        self.top_left_frame.pack(side="left", padx=20, fill="x", expand=True)
        self.top_right_frame = ttk.Frame(self.top_frame)
        self.top_right_frame.pack(side="right", padx=20, fill="x", expand=True)

        self._labelframe = ttk.LabelFrame(self.top_left_frame, text="ポケモン名を入力")
        self._labelframe.pack(side="left", padx=20, expand=True)
        self._name_input: AutoCompleteCombobox = AutoCompleteCombobox.pokemons(
            self._labelframe
        )
        if self.pokemon.no != -1:
            self._name_input.set(self.pokemon.name)
        self._name_input.bind("<<submit>>", self.on_input_name)
        self._name_input.pack(side="left")

        proceed_button = MyButton(
            self.top_right_frame,
            text="次へ",
            command=self.click_paging_right,
        )
        proceed_button.pack(side="right", padx=20)
        all_page_num = MyLabel(
            self.top_right_frame,
            textvariable=self.all_page_num,
        )
        all_page_num.pack(side="right", padx=20)
        slash_label = MyLabel(
            self.top_right_frame,
            text=" / ",
        )
        slash_label.pack(side="right", padx=20)
        current_page_num = MyLabel(
            self.top_right_frame,
            textvariable=self.current_page_num,
        )
        current_page_num.pack(side="right", padx=20)
        back_button = MyButton(
            self.top_right_frame,
            text="前へ",
            command=self.click_paging_left,
        )
        back_button.pack(side="right", padx=20)
        clear_button = MyButton(
            self.top_right_frame,
            text="リセット",
            command=self.reset,
        )
        clear_button.pack(side="right", padx=20)

        self.update_box_list()
        self.set_pokemon_list()

    def update_box_list(self):
        self.box_data = self.read_csv(self.file_path)
        self.box_data.reverse()
        if self.pokemon.no != -1:
            box = [
                pokemon for pokemon in self.box_data if pokemon[0] == self.pokemon.name
            ]
            if len(box) > 0:
                self.box_data = box
        self.current_page_num.set(1)
        self.all_page_num.set((len(self.box_data) // 15) + 1)

    def set_pokemon_list(self):
        self.pokes_frame.destroy()
        self.pokes_frame = ttk.Frame(self, padding=10)
        tera_enabled = get_recog_value("terastal_enabled")

        # CSV index 1 (個体値) は常に非表示、index 6 (テラス) はテラスタル無効時に非表示
        skip_indices = {1} if tera_enabled else {1, 6}

        column_title = ["名前", "努力値", "性格", "持ち物", "特性"]
        if tera_enabled:
            column_title.append("テラス")

        for i, value in enumerate(column_title):
            label = MyLabel(self.pokes_frame, text=value)
            label.grid(row=0, column=i + 1, padx=15, pady=10)

        waza_col = len(column_title) + 1
        memo_col = waza_col + 4

        label = MyLabel(self.pokes_frame, text="技")
        label.grid(row=0, column=waza_col, columnspan=4)

        for i, row in enumerate(
            self.box_data[
                (self.current_page_num.get() - 1) * 15 : (
                    (self.current_page_num.get() - 1) * 15
                )
                + 15
            ],
            start=(self.current_page_num.get() - 1) * 15,
        ):
            choose_button = MyButton(
                master=self.pokes_frame,
                image=images.get_menu_icon("trush"),
                command=lambda idx=i: self.on_delete_pokemon(idx),
            )
            choose_button.grid(row=i + 1, column=0, padx=15, pady=10)
            display_col = 1
            for j, value in enumerate(row):
                if j in skip_indices:
                    continue
                elif j == 7:
                    memo_button = MyButton(
                        master=self.pokes_frame,
                        image=images.get_menu_icon("load"),
                        command=lambda memo=value: self.show_pokemon_memo(memo),
                    )
                    memo_button.grid(row=i + 1, column=memo_col, padx=15, pady=10)
                elif j >= 8:
                    label = MyLabel(self.pokes_frame, text=value)
                    label.grid(row=i + 1, column=waza_col + (j - 8), padx=15, pady=10)
                else:
                    label = MyLabel(self.pokes_frame, text=value)
                    label.grid(row=i + 1, column=display_col, padx=15, pady=10)
                    display_col += 1

        self.pokes_frame.pack(fill="both", expand=True, side="top")

    def open(self, location=tuple[int, int]):
        self.grab_set()
        self.focus_set()
        self.geometry("+{0}+{1}".format(location[0], location[1]))

    def read_csv(self, file_path):
        rows = []
        with open(file_path, mode="r", newline="") as file:
            reader = csv.reader(file)
            next(reader)
            for row in reader:
                rows.append(row)
        return rows

    def on_input_name(self, *args):
        pokemon_name = self._name_input.get()
        self.pokemon = Pokemon.by_name(pokemon_name, default=True)
        self.update_box_list()
        self.set_pokemon_list()

    def show_pokemon_memo(self, memo: str):
        dialog = PokemonMemoLabelDialog(self)
        dialog.open(memo, location=(self.winfo_x(), self.winfo_y()))
        self.wait_window(dialog)

    def on_delete_pokemon(self, index: int):
        ret = messagebox.askyesno(
            "確認",
            "選択したポケモンを削除しますか？(この操作は元に戻せません)",
            parent=self,
        )
        if ret is True:
            with open(self.file_path, "w") as box_csv:
                writer = csv.writer(box_csv, lineterminator="\n")
                writer.writerow(
                    [
                        "名前",
                        "個体値",
                        "努力値",
                        "性格",
                        "持ち物",
                        "特性",
                        "テラス",
                        "メモ",
                        "技",
                        "技",
                        "技",
                        "技",
                    ]
                )
                rows = [row for row in self.all_box_data if row != self.box_data[index]]
                for row in rows:
                    writer.writerow(row)

            self.update_box_list()
            self.set_pokemon_list()

    def reset(self):
        self.pokemon = Pokemon()
        self._name_input.set("")
        self.update_box_list()
        self.set_pokemon_list()

    def click_paging_left(self):
        if self.current_page_num.get() > 1:
            self.current_page_num.set(self.current_page_num.get() - 1)
            self.set_pokemon_list()

    def click_paging_right(self):
        if self.current_page_num.get() < self.all_page_num.get():
            self.current_page_num.set(self.current_page_num.get() + 1)
            self.set_pokemon_list()
