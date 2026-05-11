from __future__ import annotations

import sys
import tkinter
import webbrowser
from tkinter import E, N, S, W, ttk
from typing import TYPE_CHECKING

from component.parts import const, images
from component.parts.button import MyButton, TypeIconButton
from component.parts.combobox import MyCombobox, WazaNameCombobox
from component.parts.const import ITEM_COMBOBOX_VALUES, WALL_COMBOBOX_VALUES
from component.parts.dialog import PokemonMemoLabelDialog
from component.parts.label import MyLabel

_IS_MAC = sys.platform == "darwin"
_SCALE_X = 1.0
_SCALE_Y = 0.92 if _IS_MAC else 1.0


def _sx(v: int) -> int:
    return int(v * _SCALE_X)


def _sy(v: int) -> int:
    return int(v * _SCALE_Y)


from pokedata.calc import DamageCalcResult
from pokedata.const import ABILITY_VALUES, Ailments, Types, Walls
from pokedata.exception import changeble_form_in_battle
from pokedata.nature import get_seikaku_from_arrows
from pokedata.pokemon import Pokemon
from pokedata.stats import Stats, StatsKey
from pokedata.waza import WazaBase
from recog.recog import get_recog_value

if TYPE_CHECKING:
    from component.stage import Stage


# パーティ表示フレーム
class PartyFrame(ttk.LabelFrame):
    def __init__(self, master, player: int, **kwargs):
        super().__init__(master, **kwargs)
        self._player: int = player
        self._stage: Stage | None = None
        self._button_list: list[MyButton] = []
        self.pokemon_list: list[Pokemon] = [Pokemon()] * 6

        # ポケモン表示ボタン
        for i in range(6):
            btn = MyButton(
                self,
                size=(30, 30),
                padding=0,
                command=lambda idx=i: self.on_push_pokemon_button(idx),
            )
            btn.grid(column=i, row=0, sticky=W)
            self._button_list.append(btn)

        # 編集ボタン
        edit_btn = MyButton(
            master=self,
            image=images.get_menu_icon("edit"),
            padding=0,
            command=lambda: self.on_push_edit_button(),
        )
        edit_btn.grid(column=6, row=0, sticky=E)

        # パーティ読み込みボタン
        if player == 0:
            load_btn = MyButton(
                master=self,
                image=images.get_menu_icon("load"),
                padding=0,
                command=lambda: self.on_push_load_button(),
            )
            load_btn.grid(column=7, row=0, sticky=E)
        # パーティクリアボタン
        elif player == 1:
            load_btn = MyButton(
                master=self,
                image=images.get_menu_icon("trush"),
                padding=0,
                command=lambda: self.on_push_clear_button(),
            )
            load_btn.grid(column=7, row=0, sticky=E)

    def set_stage(self, stage: Stage):
        self._stage = stage

    def set_party(self, party: list[Pokemon]):
        for i, pokemon in enumerate(party):
            if pokemon.is_empty is False:
                self._button_list[i].set_pokemon_icon(pokemon.pid, size=(30, 30))
                self.pokemon_list[i] = pokemon
            else:
                self._button_list[i].set_image(images.get_blank_image(size=(30, 30)))
                self.pokemon_list[i] = Pokemon()

    def set_party_from_capture(self, party: list[Pokemon]):
        self._stage.load_party(1, party)
        self.set_party(party)

    def on_push_pokemon_button(self, index: int):
        self._stage.set_active_pokemon_from_index(player=self._player, index=index)
        self._stage.set_info(self._player)

    def on_push_edit_button(self):
        try:
            self._stage.edit_party(self._player)
        except Exception:
            import traceback
            from tkinter import messagebox
            messagebox.showerror("エラー", f"パーティ編集画面を開けませんでした:\n{traceback.format_exc()}")

    def on_push_load_button(self):
        self._stage.load_party(self._player)

    def on_push_clear_button(self):
        self._stage.clear_party(self._player)

    def set_first_chosen_to_active(self):
        index = self._stage.search_first_chosen()
        if index != -1:
            self.on_push_pokemon_button(index)


# 選出表示フレーム
class ChosenFrame(ttk.LabelFrame):
    def __init__(self, master, player: int, **kwargs):
        super().__init__(master, **kwargs)
        sensyutu_num = 3 if get_recog_value("rule") == 1 else 4
        self._player: int = player
        self._stage: Stage | None = None
        self._button_list: list[MyButton] = []
        self.pokemon_list: list[Pokemon] = [Pokemon()] * sensyutu_num
        # ポケモン表示ボタン

        for i in range(sensyutu_num):
            btn = MyButton(
                self,
                size=(30, 30),
                padding=0,
                command=lambda idx=i: self.on_push_pokemon_button(idx),
            )
            btn.grid(column=i, row=0, sticky=W)
            self._button_list.append(btn)

        # 選出クリアボタン
        load_btn = MyButton(
            master=self,
            image=images.get_menu_icon("trush"),
            padding=0,
            command=lambda: self.on_push_clear_button(),
        )
        load_btn.grid(column=7, row=0, sticky=E)

    def set_stage(self, stage: Stage):
        self._stage = stage

    def set_chosen(self, pokemon: Pokemon, index: int):
        if pokemon.is_empty is False:
            self._button_list[index].set_pokemon_icon(pokemon.pid, size=(30, 30))
            self.pokemon_list[index] = pokemon
        else:
            self._button_list[index].set_image(images.get_blank_image(size=(30, 30)))
            self.pokemon_list[index] = Pokemon()

    def set_chosen_from_capture(self, index: list[int]):
        self._stage.set_chosen(0, index)

    def on_push_pokemon_button(self, index: int):
        self._stage.delete_chosen(self._player, index)

    def on_push_clear_button(self):
        self._stage.clear_chosen(self._player)


class SeikakuPopup(tkinter.Toplevel):
    _STAT_KEYS = [StatsKey.A, StatsKey.B, StatsKey.C, StatsKey.D, StatsKey.S]
    _STAT_LABELS = ["こうげき", "ぼうぎょ", "とくこう", "とくぼう", "すばやさ"]
    _CENTER = 2  # C×C のみ「まじめ」を表示

    def __init__(self, master, callback):
        super().__init__(master)
        self.title("性格選択")
        self._callback = callback
        self.resizable(False, False)
        self.grab_set()
        self.focus_set()

        ttk.Label(self, text="").grid(row=0, column=0)
        for col, label in enumerate(self._STAT_LABELS):
            ttk.Label(self, text=f"↓{label}", anchor="center").grid(
                row=0, column=col + 1, padx=4, pady=4
            )

        for row, (up_key, up_label) in enumerate(
            zip(self._STAT_KEYS, self._STAT_LABELS, strict=True)
        ):
            ttk.Label(self, text=f"↑{up_label}", anchor="e").grid(
                row=row + 1, column=0, padx=4, pady=2
            )
            for col, down_key in enumerate(self._STAT_KEYS):
                if row == col:
                    if row == self._CENTER:
                        MyButton(
                            self,
                            text="まじめ",
                            command=lambda: self._select("まじめ"),
                        ).grid(row=row + 1, column=col + 1, padx=2, pady=2)
                    else:
                        ttk.Label(self, text="").grid(
                            row=row + 1, column=col + 1
                        )
                else:
                    nature = get_seikaku_from_arrows(up_key, down_key)
                    MyButton(
                        self,
                        text=nature,
                        command=lambda n=nature: self._select(n),
                    ).grid(row=row + 1, column=col + 1, padx=2, pady=2)

    def _select(self, nature: str):
        self._callback(nature)
        self.destroy()

    def open(self, location: tuple[int, int]):
        self.geometry(f"+{location[0]}+{location[1]}")


# 選択状態ポケモン表示フレーム
class ActivePokemonFrame(ttk.LabelFrame):
    def __init__(self, master, player: int, **kwargs):
        super().__init__(master, **kwargs)
        self._player: int = player
        self._pokemon: Pokemon = Pokemon()
        self._stage: Stage | None = None
        self.columnconfigure(2, weight=1)

        # ウィジェットの配置
        left_frame = ttk.Frame(self)
        left_frame.grid(column=0, row=0, rowspan=4, padx=3)

        self._pokemon_icon = MyButton(
            left_frame, size=(60, 60), padding=0, command=self.on_push_pokemon_button
        )
        self._pokemon_icon.grid(column=0, row=0)

        teras_frame = ttk.LabelFrame(left_frame, text="テラス", labelanchor="n")
        teras_frame.grid(column=0, row=1, sticky=W + E)
        teras_frame.columnconfigure(0, weight=1)

        self._teras_button = TypeIconButton(
            teras_frame,
            types=Types.なし,
            command=self.on_push_terasbutton
            if get_recog_value("terastal_enabled")
            else None,
            state=tkinter.NORMAL
            if get_recog_value("terastal_enabled")
            else tkinter.DISABLED,
        )
        self._teras_button.grid(column=0, row=0, sticky=W + E)

        self._form_button_state = tkinter.BooleanVar()
        self._form_button_state.set(False)
        _form_kwargs = {"width": 5} if const.IS_MAC else {}
        self._form_button = MyButton(
            left_frame,
            text="フォーム",
            state=tkinter.DISABLED,
            command=self.change_form,
            **_form_kwargs,
        )
        self._form_button.grid(column=0, row=2, pady=5)

        self._seikaku_button = MyButton(
            left_frame,
            text="まじめ",
            command=self.on_push_seikaku_button,
            width=const.char_width(default=8, mac=6),
        )
        self._seikaku_button.grid(column=0, row=3, sticky=W + E)

        self._status_frame = StatusFrame(self, player, text="ステータス")
        # self._status_combobox.bind("<<ComboboxSelected>>", self.on_select_doryoku)
        self._status_frame.grid(
            column=1, row=0, columnspan=4, sticky=S + N + W + E, padx=3
        )

        self._item_label = MyLabel(self, text="持ち物")
        self._item_label.grid(column=1, row=2, padx=5, pady=5)
        self._item_combobox = MyCombobox(self, values=ITEM_COMBOBOX_VALUES)
        self._item_combobox.set(ITEM_COMBOBOX_VALUES[0])
        self._item_combobox.bind("<<ComboboxSelected>>", self.on_select_item)
        self._item_combobox.bind("<Return>", self.on_select_item)
        self._item_combobox.grid(column=2, row=2, sticky=W + E)

        self._ability_label = MyLabel(self, text="特性")
        self._ability_label.grid(column=1, row=3, padx=5, pady=5)
        self._ability_combobox = MyCombobox(self)
        self._ability_combobox.bind("<<ComboboxSelected>>", self.on_select_ability)
        self._ability_combobox.grid(column=2, row=3, sticky=W + E)

        self._ability_value_combobox = MyCombobox(self, width=4, state="disable")
        self._ability_value_combobox.bind(
            "<<ComboboxSelected>>", self.on_select_ability_value
        )
        self._ability_value_combobox.grid(column=3, row=3)

        wall_frame = ttk.Frame(self)

        self._wall_combobox = MyCombobox(
            wall_frame, width=12, values=WALL_COMBOBOX_VALUES
        )
        self._wall_combobox.set(WALL_COMBOBOX_VALUES[0])
        self._wall_combobox.bind("<<ComboboxSelected>>", self.on_select_wall)
        self._wall_combobox.grid(column=1, row=0, sticky=W)

        wall_frame.grid(column=4, row=3, sticky=W)
        wall_label = MyLabel(wall_frame, text="壁")
        wall_label.grid(column=0, row=0, padx=5, pady=5)

        checkbox_frame = ttk.Frame(self)

        self.critical = tkinter.BooleanVar()
        self.critical_check = tkinter.Checkbutton(
            checkbox_frame,
            text="急所",
            variable=self.critical,
            command=self.change_critical,
        )
        self.critical_check.grid(column=0, row=0, sticky=W + E)

        self.burned = tkinter.BooleanVar()
        self.burned_check = tkinter.Checkbutton(
            checkbox_frame,
            text="やけど",
            variable=self.burned,
            command=self.change_burned,
        )
        self.burned_check.grid(column=1, row=0, sticky=W)

        self.charging = tkinter.BooleanVar()
        self.charging_check = tkinter.Checkbutton(
            checkbox_frame,
            text="じゅうでん",
            variable=self.charging,
            command=self.change_charging,
        )
        self.charging_check.grid(column=2, row=0, sticky=W)

        self.all_check_reset()

        checkbox_frame.grid(column=3, row=2, columnspan=2)

    def set_pokemon(self, poke: Pokemon):
        if not self._pokemon.no == poke.no:
            self.all_check_reset()
        self._pokemon_icon.set_pokemon_icon(pid=poke.pid, size=(60, 60))
        self._status_frame.update_pokemon(poke)
        self._seikaku_button["text"] = poke.seikaku
        self._item_combobox.set(poke.item)
        self._ability_combobox["values"] = poke.abilities
        self._ability_combobox.set(poke.ability)
        self.set_ability_values(poke.ability)
        self._ability_value_combobox.set(poke.ability_value)
        self._teras_button.set_type(poke.battle_terastype)
        self._update_teras_state(poke.ability)
        self._wall_combobox.set(poke.wall.name)
        if poke.no in changeble_form_in_battle:
            self._form_button["state"] = tkinter.NORMAL
        else:
            self._form_button["state"] = tkinter.DISABLED
        self._pokemon = poke

    def set_stage(self, stage: Stage):
        self._stage = stage

    def set_ability_values(self, ability: str):
        if len(ability) > 0:
            for k, v in ABILITY_VALUES.items():
                if ability in k:
                    self._ability_value_combobox["values"] = v
                    self._ability_value_combobox["state"] = "normal"
                    self._ability_value_combobox.set(v[0])
                    return
        self._ability_value_combobox["state"] = "disable"
        self._ability_value_combobox.set("")

    def update_ability_display(self):
        ability = self._pokemon.ability
        self._ability_combobox.set(ability)
        self.set_ability_values(ability)

    def change_burned(self):
        self._stage.set_value_to_active_pokemon(
            player=self._player,
            ailment=Ailments.やけど if self.burned.get() else Ailments.なし,
        )

    def change_critical(self):
        self._stage.set_value_to_active_pokemon(
            player=self._player, critical=self.critical.get()
        )

    def change_charging(self):
        self._stage.set_value_to_active_pokemon(
            player=self._player, charging=self.charging.get()
        )

    def on_push_seikaku_button(self):
        x = self._seikaku_button.winfo_rootx()
        y = self._seikaku_button.winfo_rooty() + self._seikaku_button.winfo_height()
        SeikakuPopup(self, self._on_seikaku_selected).open((x, y))

    def _on_seikaku_selected(self, seikaku: str):
        self._seikaku_button["text"] = seikaku
        self._stage.set_value_to_active_pokemon(player=self._player, seikaku=seikaku)

    def on_select_item(self, *_args):
        self._stage.set_value_to_active_pokemon(
            player=self._player, item=self._item_combobox.get()
        )

    def _update_teras_state(self, ability: str):
        if ability in ("へんげんじざい", "リベロ"):
            self._teras_button.config(
                state=tkinter.NORMAL, command=self.on_push_terasbutton
            )
        else:
            enabled = get_recog_value("terastal_enabled")
            self._teras_button.config(
                state=tkinter.NORMAL if enabled else tkinter.DISABLED,
                command=self.on_push_terasbutton if enabled else (lambda: None),
            )

    def on_select_ability(self, *_args):
        ability = self._ability_combobox.get()
        self._stage.set_value_to_active_pokemon(player=self._player, ability=ability)
        self.set_ability_values(ability)
        self._update_teras_state(ability)

    def on_select_ability_value(self, *_args):
        self._stage.set_value_to_active_pokemon(
            player=self._player, ability_value=self._ability_value_combobox.get()
        )

    def on_select_wall(self, *_args):
        for wall in Walls:
            if wall.name == self._wall_combobox.get():
                self._stage.set_value_to_active_pokemon(player=self._player, wall=wall)

    def on_push_pokemon_button(self):
        self._stage.set_chosen(self._player)

    def on_push_terasbutton(self, *_args):
        self._stage.select_terastype(self._player)

    def change_form(self):
        self._pokemon.form_change()
        self._pokemon_icon.set_pokemon_icon(pid=self._pokemon.pid, size=(60, 60))
        self._ability_combobox["values"] = self._pokemon.abilities
        self._ability_combobox.set(self._pokemon.ability)
        self.set_ability_values(self._pokemon.ability)
        self._status_frame.update_pokemon(self._pokemon, False)
        self._stage.set_info(self._player)
        self._stage.calc_damage()

    def all_check_reset(self):
        self.critical.set(False)
        self.burned.set(False)
        self.charging.set(False)


# ステータスフレーム
class StatusFrame(ttk.LabelFrame):
    def on_validate_2(self, P):
        if P == "":
            return True
        if P.isdigit():
            return int(P) <= 32
        return False

    def __init__(self, master, player: int, **kwargs):
        super().__init__(master, **kwargs)
        self._pokemon = Pokemon()
        self._doryoku: Stats = Stats(0)
        self._rank: Stats = Stats(0)
        self._stats_value_list: list[tkinter.IntVar] = []
        self._doryoku_spinbox_dict = {}
        self._rank_spinbox_dict = {}
        self._player = player
        self._stage: Stage | None = None

        self.doryoku_validate = self.register(self.on_validate_2)

        self.is_rank = tkinter.BooleanVar()
        self.is_rank__check = tkinter.Checkbutton(
            self,
            text="反映",
            variable=self.is_rank,
            command=self.set_stats,
        )
        self.is_rank.set(True)
        self.is_rank__check.grid(column=1, row=3, sticky=W + E)

        memo_btn = MyButton(
            master=self,
            image=images.get_menu_icon("load"),
            padding=0,
            command=self.show_pokemon_memo if player == 0 else self.show_party_memo,
        )
        memo_btn.grid(column=0, row=0)

        jissu_label = MyLabel(self, text="実数値")
        jissu_label.grid(column=0, row=1, padx=2)

        doryoku_label = tkinter.Button(
            self, text="努力値", command=lambda: self.on_push_doryoku_clear_button()
        )
        doryoku_label.grid(column=0, row=2, padx=2)

        rank_label = tkinter.Button(
            self, text="ランク", command=self.on_push_rank_clear_button
        )
        rank_label.grid(column=0, row=3, padx=2)

        for i, statskey in enumerate([x for x in StatsKey]):
            label = tkinter.Label(
                self,
                text=statskey.name,
                anchor=tkinter.CENTER,
            )
            label.grid(column=i + 1, row=0, padx=2)

            stats_value = tkinter.IntVar()
            stats_value.set(0)
            stats_label = MyLabel(self, textvariable=stats_value, anchor=tkinter.CENTER)
            stats_label.grid(column=i + 1, row=1, padx=2, sticky=W + E)
            self._stats_value_list.append(stats_value)

            doryoku_spin = ttk.Spinbox(
                self,
                from_=0,
                to=32,
                increment=1,
                width=const.char_width(default=4, mac=3),
                validate="key",
                validatecommand=(self.doryoku_validate, "%P"),
                command=lambda key=statskey: self.on_push_doryoku_spin(key),
            )
            doryoku_spin.bind("<Return>", self.on_change_doryoku_spin)
            doryoku_spin.bind(
                "<Button-3>",
                lambda e, key=statskey: self.on_right_click_doryoku_spin(key),
            )
            doryoku_spin.grid(column=i + 1, row=2, padx=2, pady=3)
            self._doryoku_spinbox_dict[statskey] = doryoku_spin

            if statskey != StatsKey.H:
                rank_spin = ttk.Spinbox(
                    self,
                    from_=-6,
                    to=6,
                    increment=1,
                    width=const.char_width(default=3, mac=2),
                    command=lambda key=statskey: self.on_push_rank_spin(
                        key, int(self._rank_spinbox_dict[key].get())
                    ),
                )
                rank_spin.grid(column=i + 1, row=3, padx=2, pady=3)
                self._rank_spinbox_dict[statskey] = rank_spin

    def set_stage(self, stage: Stage):
        self._stage = stage

    @property
    def doryoku(self) -> Stats:
        return self._doryoku

    @property
    def rank(self) -> Stats:
        return self._rank

    def update_pokemon(self, poke: Pokemon, all=True):
        self._pokemon = poke
        self.set_stats()
        if all:
            self.change_all_doryoku_box(poke.doryoku)
            self.change_all_rank_box(poke.rank)

    # ポケモン登録時に実数値を表示する
    def set_stats(self):
        self.stats: list[int] = []
        if self.is_rank.get():
            self.stats = self._pokemon.get_all_ranked_stats()
        else:
            self.stats = self._pokemon.get_all_stats()
        for i in range(len(self.stats)):
            self._stats_value_list[i].set(self.stats[i])

    # 個体値のチェックボックス更新時処理
    def on_kotai_value_change(self, key: StatsKey):
        if self._pokemon.kotai.__getitem__(key) != 0:
            self._pokemon.kotai.__setitem__(key, 0)
        else:
            self._pokemon.kotai.__setitem__(key, 31)
        self._stage.set_value_to_active_pokemon(self._player, kotai=self._pokemon.kotai)

    # 努力値Spinbox直接入力時処理（Enter押下後起動）
    def on_change_doryoku_spin(self, *args):
        for _i, key in enumerate([x for x in StatsKey]):
            self._doryoku[key] = int(self._doryoku_spinbox_dict[key].get())
        if self._stage is not None:
            self._stage.set_value_to_active_pokemon(
                self._player,
                doryoku_number=self._doryoku,
            )

    # 努力値Spinboxの上下ボタン押下時処理
    def on_push_doryoku_spin(self, key: StatsKey):
        self._doryoku[key] = int(self._doryoku_spinbox_dict[key].get())
        if self._stage is not None:
            self._stage.set_value_to_active_pokemon(
                self._player,
                doryoku_number=self._doryoku,
            )

    # 努力値Spinboxの右クリック時処理（32と0をトグル）
    def on_right_click_doryoku_spin(self, key: StatsKey):
        self._doryoku[key] = 32 if self._doryoku[key] != 32 else 0
        if self._stage is not None:
            self._stage.set_value_to_active_pokemon(
                self._player,
                doryoku_number=self._doryoku,
            )

    # Spinbox外から全努力値の値を変更
    def change_all_doryoku_box(self, doryoku: Stats):
        for key in [x for x in StatsKey]:
            self._doryoku[key] = doryoku[key]
            self._doryoku_spinbox_dict[key].select_clear()
            self._doryoku_spinbox_dict[key].set(doryoku[key])

    # 努力値Spinbox全クリア処理
    def on_push_doryoku_clear_button(self):
        self.change_all_doryoku_box(Stats(0))
        if self._stage is not None:
            self._stage.set_value_to_active_pokemon(
                self._player, doryoku_number=self._doryoku
            )

    # ランクSpinboxの上下ボタン押下時処理
    def on_push_rank_spin(self, key: StatsKey, value: int):
        self.change_rank_box(key, value)
        if self._stage is not None:
            self._stage.set_value_to_active_pokemon(self._player, rank=self._rank)

    # Spinbox外から全ランクの値を変更
    def change_all_rank_box(self, rank: Stats):
        for key in [x for x in StatsKey if x != StatsKey.H]:
            self.change_rank_box(key, rank[key])

    # ランクSpinbox全クリア処理
    def on_push_rank_clear_button(self):
        self.change_all_rank_box(Stats(0))
        if self._stage is not None:
            self._stage.set_value_to_active_pokemon(self._player, rank=self._rank)

    # ランクSpinboxの表示変更（色など）
    def change_rank_box(self, key: StatsKey, value: int):
        self._rank[key] = value
        self._rank_spinbox_dict[key].select_clear()
        if value > 0:
            self._rank_spinbox_dict[key].set("+" + str(value))
            self._rank_spinbox_dict[key]["foreground"] = "coral"
        else:
            self._rank_spinbox_dict[key].set(value)
            self._rank_spinbox_dict[key]["foreground"] = (
                "steel blue" if value < 0 else ""
            )

    def show_pokemon_memo(self):
        dialog = PokemonMemoLabelDialog()
        dialog.open(self._pokemon.memo, location=(self.winfo_x(), self.winfo_y()))
        self.wait_window(dialog)

    def show_party_memo(self):
        from pokedata.loader import get_party_csv

        party_file = get_party_csv().replace("csv", "txt")
        memo = ""
        try:
            with open(party_file, "r") as txt:
                memo = txt.read()
        except FileNotFoundError:
            pass

        dialog = PokemonMemoLabelDialog()
        dialog.open(memo, location=(self.winfo_x(), self.winfo_y()))
        self.wait_window(dialog)


# 技・ダメージ表示リストフレーム
class WazaDamageListFrame(ttk.LabelFrame):
    def __init__(self, master, index: int, **kwargs):
        super().__init__(master, **kwargs, padding=5)
        self._index = index
        self._stage: Stage | None = None
        self.columnconfigure(3, weight=1)

        self._cbx_list: list[WazaNameCombobox] = []
        self._reg_btn_list: list[MyButton] = []
        self._lbl_list: list[MyLabel] = []
        self._btn_list: list[MyButton] = []
        self._dmgframe_list = []

        num = 5 if self._index == 0 else 10
        for i in range(num):
            if self._index == 1:
                lbl = MyLabel(self, text="", width=4)
                lbl.grid(column=0, row=i)
                self._lbl_list.append(lbl)

            cbx = WazaNameCombobox(self, width=16)
            cbx.grid(column=1, row=i)
            cbx.bind("<<submit>>", lambda _, idx=i: self.on_submit_waza(idx))
            self._cbx_list.append(cbx)

            btn = MyButton(
                self, width=4, command=lambda idx=i: self.on_push_waza_button(idx)
            )
            btn.grid(column=2, row=i, sticky=W)
            self._btn_list.append(btn)

            dmgframe = DamageDispFrame(self)
            dmgframe.grid(column=3, row=i, sticky=W + E)
            self._dmgframe_list.append(dmgframe)

    def set_stage(self, stage: Stage):
        self._stage = stage

    def on_submit_waza(self, index: int):
        waza = self._cbx_list[index].get()
        self._stage.set_value_to_active_pokemon(self._index, waza=(index, waza))

    def on_push_waza_button(self, index: int):
        self._stage.set_value_to_active_pokemon(self._index, waza_effect=index)

    def set_waza_info(self, lst: list[WazaBase]):
        for i in range(len(self._cbx_list)):
            wazabase = lst[i]
            if wazabase is not None:
                self._cbx_list[i].set(wazabase.name)
                match wazabase.type:
                    case (
                        wazabase.TYPE_ADD_POWER
                        | wazabase.TYPE_MULTI_HIT
                        | wazabase.TYPE_POWER_HOSEI
                    ):
                        self._btn_list[i].text = "x" + str(wazabase.value)
                    case wazabase.TYPE_SELF_BUFF | wazabase.TYPE_OPPONENT_BUFF:
                        self._btn_list[i].text = "+"
                    case wazabase.TYPE_SELF_DEBUFF | wazabase.TYPE_OPPONENT_DEBUFF:
                        self._btn_list[i].text = "-"
                    case wazabase.TYPE_OTHER_EFFECT:
                        self._btn_list[i].text = str(wazabase.value)
                    case _:
                        self._btn_list[i].text = ""
            else:
                self._cbx_list[i].set("")
                self._btn_list[i].text = ""

    def set_waza_rate(self, lst: list[float]):
        for i in range(len(self._lbl_list)):
            rate = lst[i]
            if rate is not None:
                self._lbl_list[i]["text"] = str(rate)
            else:
                self._lbl_list[i]["text"] = ""

    def set_damages(self, lst: list[DamageCalcResult]):
        for i in range(len(self._dmgframe_list)):
            result = lst[i]
            self._dmgframe_list[i].set_calc_result(result)


# ダメージ表示
class DamageDispFrame(ttk.Frame):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self.columnconfigure(0, weight=1)
        self.columnconfigure(1, weight=1)
        self.rowconfigure(0, weight=1)

        self.dmg1_label = MyLabel(self)
        self.dmg1_label.grid(column=0, row=0, sticky=W + E)

        self.dmg2_label = MyLabel(self, font=(const.FONT_FAMILY, 8))
        self.dmg2_label.grid(column=1, row=0, sticky=W + E)

        self.hpbar = HpBarFrame(self)
        self.hpbar.grid(column=0, row=1, columnspan=2, sticky=W + E)

    def set_calc_result(self, result: DamageCalcResult):
        if result is not None and result.is_damage:
            self.dmg1_label["text"] = result.damage_text
            self.dmg2_label["text"] = result.damage_per_text
            self.hpbar.set_damage(
                mindmg=result.min_damage_per, maxdmg=result.max_damage_per
            )
        else:
            self.dmg1_label["text"] = ""
            self.dmg2_label["text"] = ""
            self.hpbar.clear()


# HPバー表示フレーム
class HpBarFrame(tkinter.Frame):
    def __init__(self, master, **kwargs):
        super().__init__(master, height=5, background="#c8c8c8", **kwargs)
        self.propagate(False)

        self.bar_1 = tkinter.Frame(self, width=0, height=5, background="#323232")
        self.bar_1.propagate(False)
        self.bar_1.grid(column=0, row=0, sticky=N + S)

        self.bar_2 = tkinter.Frame(self, width=0, height=5, background="#323232")
        self.bar_2.propagate(False)
        self.bar_2.grid(column=1, row=0, sticky=N + S)

    def set_damage(self, mindmg: float, maxdmg: float):
        if maxdmg >= 80:
            colors = ("#ff3232", "#a43e3e")
        elif maxdmg >= 50:
            colors = ("#fbc02d", "#907329")
        else:
            colors = ("#0eda0e", "#25a425")

        bar_width = self.winfo_width()
        if maxdmg >= 100:
            width_1 = 0
            if mindmg >= 100:
                width_2 = 0
            else:
                width_2 = int(bar_width * (100 - mindmg) / 100)
        else:
            width_1 = int(bar_width * (100 - maxdmg) / 100)
            width_2 = int(bar_width * (maxdmg - mindmg) / 100)

        self.bar_1["width"] = width_1
        self.bar_1["background"] = colors[0]
        self.bar_2["width"] = width_2
        self.bar_2["background"] = colors[1]

    def clear(self):
        self.bar_1["width"] = 0
        self.bar_2["width"] = 0


# 基本情報フレーム
class InfoFrame(ttk.LabelFrame):
    def __init__(self, master, player: int, **kwargs):
        super().__init__(master, **kwargs)
        self._player: int = player
        self._no: int = 0
        self._form: int = -1
        self.syuzoku = {}
        global img
        img = [
            [tkinter.PhotoImage(file=Types.なし.icon).subsample(3, 3)] * 2,
            [tkinter.PhotoImage(file=Types.なし.icon).subsample(3, 3)] * 2,
        ]
        self.size = (_sx(457), _sy(77))
        self.pack_propagate(False)
        basic_info_flame = ttk.Frame(self, width=_sx(457), height=_sy(37))
        basic_info_flame.pack_propagate(False)
        basic_info_flame.columnconfigure(0, minsize=_sx(210))
        basic_info_flame.columnconfigure(1, minsize=_sx(70))
        basic_info_flame.columnconfigure(2, minsize=_sx(100))
        basic_info_flame.columnconfigure(3, minsize=_sx(50))
        self.name = tkinter.StringVar()
        self.name.set("")
        self.name_text = ttk.Label(
            basic_info_flame,
            textvariable=self.name,
            font=(const.FONT_FAMILY, 12, "italic"),
            padding=5,
        )
        self.name_text.grid(column=0, row=0)

        self.type1_img = img[self._player][0]
        self.type1_icon = ttk.Label(basic_info_flame, image=self.type1_img)
        self.type1_icon.grid(column=1, row=0, sticky="w")

        self.type2_img = img[self._player][1]
        self.type2_icon = ttk.Label(basic_info_flame, image=self.type2_img)
        self.type2_icon.grid(column=2, row=0, sticky="w")

        buttons = ttk.Frame(basic_info_flame)
        self.poketetsu_button = MyButton(
            buttons,
            image=images.get_menu_icon("poketetsu"),
            command=self.open_poketetsu,
        )
        self.poketetsu_button.pack(fill="both", expand=0, side="left")

        self.db_button = MyButton(
            buttons, image=images.get_menu_icon("battle_db"), command=self.open_db
        )
        self.db_button.pack(fill="both", expand=0, side="left")

        buttons.grid(column=3, row=0)
        basic_info_flame.pack(side="top", anchor="w")

        status_flame = ttk.Frame(
            self,
            width=_sx(457),
            height=_sy(35),
        )
        status_flame.pack_propagate(False)
        for i, statskey in enumerate([x for x in StatsKey]):
            label = ttk.Label(
                status_flame, text=f" {statskey.name} ", font=(const.FONT_FAMILY, 15)
            )
            label.grid(column=i * 2, row=1)
            value = tkinter.StringVar()
            value.set("")
            text = ttk.Label(
                status_flame, textvariable=value, font=(const.FONT_FAMILY, 15, "bold")
            )
            status_flame.columnconfigure(i * 2 + 1, minsize=_sx(45))
            text.grid(column=i * 2 + 1, row=1)
            self.syuzoku[statskey] = value
        status_flame.pack(side="top", anchor="w")

    def set_info(self, pokemon: Pokemon):
        if pokemon.is_empty is False:
            self._no = pokemon.no
            self._form = pokemon.form
            self.name.set(pokemon.name)
            img[self._player][0] = tkinter.PhotoImage(
                file=pokemon.type[0].icon
            ).subsample(3, 3)
            self.type1_icon.configure(
                image=img[self._player][0], text=pokemon.type[0].name, compound="left"
            )
            img[self._player][1] = tkinter.PhotoImage(
                file=pokemon.type[1].icon if len(pokemon.type) > 1 else Types.なし.icon
            ).subsample(3, 3)
            self.type2_icon.configure(
                image=img[self._player][1],
                text=pokemon.type[1].name if len(pokemon.type) > 1 else "",
                compound="left",
            )
            for _i, statskey in enumerate([x for x in StatsKey]):
                self.syuzoku[statskey].set(pokemon.syuzoku[statskey])

    def open_poketetsu(self):
        if self._no != 0:
            url = "https://yakkun.com/sv/zukan/?national_no=" + str(self._no)
            webbrowser.open(url)

    def open_db(self):
        if self._no != 0:
            season = 1
            pid = str(self._no).zfill(4) + "-0" + str(self._form)
            with open("stats/season.txt", encoding="utf-8") as ranking_txt:
                season = ranking_txt.read()

            url = (
                f"https://champs.pokedb.tokyo/pokemon/show/{pid}?season={season}&rule=0"
            )
            webbrowser.open(url)
