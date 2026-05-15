from __future__ import annotations

import sys
import tkinter
import webbrowser
from fractions import Fraction
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
        self.pokemon_list: list[Pokemon] = [Pokemon() for _ in range(6)]

        # ポケモン表示ボタン
        for i in range(6):
            btn = MyButton(
                self,
                size=(30, 30),
                padding=0,
                command=lambda idx=i: self.on_push_pokemon_button(idx),
            )
            btn.bind("<Button-3>", lambda e, idx=i: self._on_right_click_pokemon(e, idx))
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

    def _on_right_click_pokemon(self, event, index: int):
        pokemon = self.pokemon_list[index]
        if pokemon.is_empty:
            return
        menu = tkinter.Menu(self, tearoff=0)
        menu.add_command(
            label="ポケ徹で開く",
            command=lambda: webbrowser.open(
                "https://yakkun.com/sv/zukan/?national_no=" + str(pokemon.no)
            ),
        )
        menu.add_command(
            label="バトルDBで開く",
            command=lambda: self._open_battle_db(pokemon),
        )
        menu.tk_popup(event.x_root, event.y_root)

    def _open_battle_db(self, pokemon: Pokemon):
        try:
            with open("stats/season.txt", encoding="utf-8") as f:
                season = f.read().strip()
        except FileNotFoundError:
            season = "1"
        pid = str(pokemon.no).zfill(4) + "-" + str(pokemon.form).zfill(2)
        webbrowser.open(
            f"https://champs.pokedb.tokyo/pokemon/show/{pid}?season={season}&rule=0"
        )

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
        for i, pokemon in enumerate(party):
            if pokemon.is_empty:
                self._button_list[i].set_image(images.get_unrecognized_image(size=(30, 30)))

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
        self.pokemon_list: list[Pokemon] = [Pokemon() for _ in range(sensyutu_num)]
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

        self._seikaku_button = MyButton(
            left_frame,
            text="まじめ",
            command=self.on_push_seikaku_button,
            padding=0,
        )
        self._seikaku_button.grid(column=0, row=1, sticky=W + E)

        self._form_button_state = tkinter.BooleanVar()
        self._form_button_state.set(False)
        _form_kwargs = {"width": 5} if const.IS_MAC else {}
        self._form_button = MyButton(
            left_frame,
            text="フォーム",
            padding=0,
            state=tkinter.DISABLED,
            command=self.change_form,
            **_form_kwargs,
        )
        self._form_button.grid(column=0, row=2)

        self.burned = tkinter.BooleanVar()
        self.burned_check = tkinter.Checkbutton(
            left_frame, text="やけど", variable=self.burned, command=self.change_burned
        )
        self.burned_check.grid(column=0, row=3)

        self._status_frame = StatusFrame(self, player, text="ステータス")
        self._status_frame.grid(
            column=1, row=0, columnspan=5, sticky=S + N + W + E, padx=3
        )

        # 上段: 持ち物・特性2つ・壁（ラベルなし）
        self._item_combobox = MyCombobox(self, values=ITEM_COMBOBOX_VALUES, width=14)
        self._item_combobox.set("もちものなし")
        self._item_combobox.bind("<<ComboboxSelected>>", self.on_select_item)
        self._item_combobox.bind("<Return>", self.on_select_item)
        self._item_combobox.bind("<Button-3>", self._on_right_click_item)
        self._item_combobox.grid(column=1, row=2, sticky=W, padx=(3, 0), pady=3)

        _ability_frame = ttk.Frame(self)
        self._ability_combobox = MyCombobox(_ability_frame, width=14)
        self._ability_combobox.set("とくせい")
        self._ability_combobox.bind("<<ComboboxSelected>>", self.on_select_ability)
        self._ability_combobox.bind("<Button-3>", self._on_right_click_ability)
        self._ability_combobox.pack(side="left")

        self._ability_value_combobox = MyCombobox(_ability_frame, width=4, state="disable")
        self._ability_value_combobox.bind(
            "<<ComboboxSelected>>", self.on_select_ability_value
        )
        self._ability_value_combobox.pack(side="left", fill="x", expand=True)
        _ability_frame.grid(column=2, row=2, columnspan=2, sticky=W + E, pady=3)

        self._wall_combobox = MyCombobox(self, width=12, values=WALL_COMBOBOX_VALUES)
        self._wall_combobox.set(WALL_COMBOBOX_VALUES[0])
        self._wall_combobox.bind("<<ComboboxSelected>>", self.on_select_wall)
        self._wall_combobox.grid(column=4, row=2, sticky=W, pady=3)

        # 下段: 定数ダメージ加算パネル
        self._const_dmg_frac: Fraction = Fraction(0)

        _const_row = ttk.Frame(self)
        _const_row.grid(column=1, row=3, columnspan=5, sticky=W + E, padx=3, pady=(0, 3))

        self._const_dmg_btn = tkinter.Button(
            _const_row, text="定数ダメージなし", width=const.char_width(default=12, mac=10),
            anchor="w", relief=tkinter.FLAT, command=self._on_clear_const_dmg,
        )
        self._const_dmg_btn.pack(side="left")
        self._const_dmg_btn.bind("<Button-3>", lambda _: self._on_show_const_list())

        # ボタンは右詰め（急所が一番右）
        self.critical = tkinter.BooleanVar()
        self.critical_check = tkinter.Checkbutton(
            _const_row, text="急所", variable=self.critical, command=self.change_critical
        )
        self.critical_check.pack(side="right", padx=(1, 1))
        for _lbl, _frac in reversed([("1/16", Fraction(1, 16)), ("1/10", Fraction(1, 10)),
                                      ("1/8",  Fraction(1, 8)),  ("1/6",  Fraction(1, 6)),
                                      ("1/4",  Fraction(1, 4)),  ("1/2",  Fraction(1, 2))]):
            tkinter.Button(_const_row, text=_lbl,
                           command=lambda f=_frac: self._on_add_const_dmg(f)
                           ).pack(side="right", padx=1)
        tkinter.Button(_const_row, text="ステロ",
                       command=self._on_add_sr).pack(side="right", padx=(0, 1))

        self.charging = tkinter.BooleanVar()
        self.charging_check = tkinter.Checkbutton(
            left_frame, text="じゅうでん", variable=self.charging, command=self.change_charging
        )
        self.charging_check.grid(column=0, row=4)

        self.smackdown = tkinter.BooleanVar()
        self.smackdown_check = tkinter.Checkbutton(
            left_frame, text="うちおとす", variable=self.smackdown, command=self.change_smackdown
        )
        self.smackdown_check.grid(column=0, row=5)

        self.all_check_reset()

    def set_pokemon(self, poke: Pokemon):
        if not self._pokemon.no == poke.no:
            self.all_check_reset()
        self._pokemon_icon.set_pokemon_icon(pid=poke.pid, size=(60, 60))
        self._status_frame.update_pokemon(poke)
        self._seikaku_button["text"] = poke.seikaku
        self._item_combobox.set("もちものなし" if poke.item == "なし" else poke.item)
        self._ability_combobox["values"] = poke.abilities
        self._ability_combobox.set(poke.ability if poke.ability else "とくせい")
        self.set_ability_values(poke.ability)
        self._ability_value_combobox.set(poke.ability_value)
        self._wall_combobox.set("壁なし" if poke.wall == Walls.なし else poke.wall.name)

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

    def change_smackdown(self):
        self._stage.set_value_to_active_pokemon(
            player=self._player, smackdown=self.smackdown.get()
        )

    def on_push_seikaku_button(self):
        x = self._seikaku_button.winfo_rootx()
        y = self._seikaku_button.winfo_rooty() + self._seikaku_button.winfo_height()
        SeikakuPopup(self, self._on_seikaku_selected).open((x, y))

    def _on_seikaku_selected(self, seikaku: str):
        self._seikaku_button["text"] = seikaku
        self._stage.set_value_to_active_pokemon(player=self._player, seikaku=seikaku)

    def on_select_item(self, *_args):
        selected = self._item_combobox.get()
        item = "なし" if selected == "もちものなし" else selected
        self._stage.set_value_to_active_pokemon(player=self._player, item=item)

    def on_select_ability(self, *_args):
        ability = self._ability_combobox.get()
        self._stage.set_value_to_active_pokemon(player=self._player, ability=ability)
        self.set_ability_values(ability)

    def on_select_ability_value(self, *_args):
        self._stage.set_value_to_active_pokemon(
            player=self._player, ability_value=self._ability_value_combobox.get()
        )

    def on_select_wall(self, *_args):
        selected = self._wall_combobox.get()
        name = "なし" if selected == "壁なし" else selected
        for wall in Walls:
            if wall.name == name:
                self._stage.set_value_to_active_pokemon(player=self._player, wall=wall)

    def on_push_pokemon_button(self):
        self._stage.set_chosen(self._player)

    def _refresh_const_display(self):
        if self._const_dmg_frac != 0:
            f = self._const_dmg_frac
            self._const_dmg_btn.config(text=f"{f.numerator}/{f.denominator}")
        else:
            self._const_dmg_btn.config(text="定数ダメージなし")

    def _on_add_const_dmg(self, frac: Fraction):
        if self._pokemon.is_empty:
            return
        self._const_dmg_frac += frac
        self._refresh_const_display()
        self._stage.set_value_to_active_pokemon(
            player=self._player,
            constant_damage=float(self._const_dmg_frac),
        )

    def _on_add_sr(self):
        if self._pokemon.is_empty:
            return
        sr_frac = Fraction(self._pokemon.get_stealth_rock_damage()).limit_denominator(32)
        self._const_dmg_frac += sr_frac
        self._refresh_const_display()
        self._stage.set_value_to_active_pokemon(
            player=self._player,
            constant_damage=float(self._const_dmg_frac),
        )

    def _on_clear_const_dmg(self):
        if self._pokemon.is_empty:
            return
        self._const_dmg_frac = Fraction(0)
        self._refresh_const_display()
        self._stage.set_value_to_active_pokemon(
            player=self._player,
            constant_damage=0.0,
        )

    def _on_show_const_list(self):
        win = tkinter.Toplevel(self)
        win.title("定数ダメージ一覧")
        win.resizable(False, False)
        content = (
            "■ 状態異常\n"
            "─────────────────────────────────────────────\n"
            "やけど                        1/16\n"
            "どく                          1/8\n"
            "もうどく                      n/16（最大15/16）\n"
            "\n"
            "■ 天気\n"
            "─────────────────────────────────────────────\n"
            "すなあらし                    1/16\n"
            "\n"
            "■ 場の状態（登場時）\n"
            "─────────────────────────────────────────────\n"
            "ステルスロック（等倍）         1/8\n"
            "ステルスロック（2倍弱点）      1/4\n"
            "ステルスロック（4倍弱点）      1/2\n"
            "ステルスロック（0.5倍耐性）    1/16\n"
            "ステルスロック（0.25倍耐性）   1/32\n"
            "まきびし 1回                  1/8\n"
            "まきびし 2回                  1/6\n"
            "まきびし 3回                  1/4\n"
            "ひのうみ                      1/8（ほのお無効）\n"
            "\n"
            "■ 特性\n"
            "─────────────────────────────────────────────\n"
            "さめはだ / てつのとげ          1/8（直接攻撃した相手）\n"
            "サンパワー / かんそうはだ      1/8（晴れ時毎ターン）\n"
            "ナイトメア                    1/8\n"
            "ばけのかわ                    1/8\n"
            "ゆうばく                      1/4（ひんし時、しめりけ無効）\n"
            "\n"
            "■ 状態変化\n"
            "─────────────────────────────────────────────\n"
            "バインド・まとわりつく等       1/8\n"
            "やどりぎのタネ                1/8（くさ無効）\n"
            "しおづけ                      1/16（みず・はがね 1/8）\n"
            "ふんじん                      1/4\n"
            "あくむ                        1/4\n"
            "\n"
            "■ 持ち物\n"
            "─────────────────────────────────────────────\n"
            "いのちのたま                  1/10\n"
            "くろいヘドロ（非どくタイプ）   1/8\n"
            "くっつきバリ                  1/8\n"
            "ゴツゴツメット                1/6\n"
            "ジャポのみ                    1/8\n"
            "レンブのみ                    1/8\n"
            "\n"
            "■ 技\n"
            "─────────────────────────────────────────────\n"
            "いかりのまえば / しぜんのいかり  相手HP×1/2\n"
            "はらだいこ                    自分HP×1/2\n"
            "とびげり / とびひざげり        自分HP×1/2（失敗時）\n"
            "かかとおとし / サンダーダイブ   自分HP×1/2（失敗時）\n"
            "ビックリヘッド / てっていこうせん 相手HP×1/2（切上）\n"
            "クロロブラスト                相手HP×1/2（切上）\n"
            "みがわり                      自分HP×1/4\n"
            "わるあがき                    自分HP×1/4（四捨五入）\n"
            "うのミサイル                  相手HP×1/4（最大3発）\n"
            "ニードルガード                直接攻撃した相手HP×1/8\n"
            "はじけるほのお                相手HP×1/16（毎ターン）\n"
            "\n"
            "■ ダイマックス技\n"
            "─────────────────────────────────────────────\n"
            "キョダイコウジン               はがね相性×1/8\n"
            "キョダイゴクエン              1/6（ほのお無効）\n"
            "キョダイフンセキ              1/6（いわ無効）\n"
            "キョダイベンタツ              1/6（くさ無効）\n"
            "キョダイホウゲキ              1/6（みず無効）\n"
        )
        frame = ttk.Frame(win)
        frame.pack(fill="both", expand=True, padx=8, pady=8)
        sb = ttk.Scrollbar(frame, orient="vertical")
        text_widget = tkinter.Text(
            frame, width=50, height=36,
            font=(const.FONT_FAMILY, 10),
            state="normal", wrap="none",
            yscrollcommand=sb.set,
        )
        sb.config(command=text_widget.yview)
        sb.pack(side="right", fill="y")
        text_widget.insert("1.0", content)
        text_widget.config(state="disabled")
        text_widget.pack(side="left", fill="both", expand=True)

    def change_form(self):
        self._pokemon.form_change()
        self._pokemon_icon.set_pokemon_icon(pid=self._pokemon.pid, size=(60, 60))
        self._ability_combobox["values"] = self._pokemon.abilities
        self._ability_combobox.set(self._pokemon.ability)
        self.set_ability_values(self._pokemon.ability)
        self._status_frame.update_pokemon(self._pokemon, False)
        self._stage.set_info(self._player)
        self._stage._app._waza_damage_frames[self._player].set_waza_info(self._pokemon.waza_list)
        self._stage.calc_damage()

    def _on_right_click_item(self, _event=None):
        name = self._item_combobox.get()
        if not name or name in ("なし", "もちものなし"):
            return
        from database.pokemon import DB_pokemon
        effect = DB_pokemon.get_item_effect(name)
        self._show_effect_popup("持ち物詳細", name, effect)

    def _on_right_click_ability(self, _event=None):
        name = self._ability_combobox.get()
        if not name:
            return
        from database.pokemon import DB_pokemon
        effect = DB_pokemon.get_ability_effect(name)
        self._show_effect_popup("特性詳細", name, effect)

    def _show_effect_popup(self, title: str, name: str, effect: str):
        import math
        popup = tkinter.Toplevel(self)
        popup.title(title)
        width = 350
        text = effect if effect else "効果情報なし"
        height = 80 + math.ceil(len(text) * 7.5 / (width - 40)) * 20
        popup.geometry(f"{width}x{max(120, height)}")
        tkinter.Label(
            popup, text=name, font=("Arial", 14, "bold"), anchor="center"
        ).pack(side="top", pady=10)
        tkinter.Label(
            popup, text=text, anchor="w", justify="left", wraplength=width - 40
        ).pack(fill="x", padx=10, pady=4)

    def all_check_reset(self):
        self.critical.set(False)
        self.burned.set(False)
        self.charging.set(False)
        self.smackdown.set(False)
        self._const_dmg_frac = Fraction(0)
        self._refresh_const_display()


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
        self._current_results: list = [None] * num

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
            dmgframe.set_right_click_callback(lambda e: self._open_multi_waza_window(e))
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
        self._current_results = list(lst)
        for i in range(len(self._dmgframe_list)):
            result = lst[i]
            self._dmgframe_list[i].set_calc_result(result)

    def _open_multi_waza_window(self, event=None):
        items = []
        for i, cbx in enumerate(self._cbx_list):
            name = cbx.get().strip()
            if name:
                result = self._current_results[i] if i < len(self._current_results) else None
                items.append((name, result))
        if not items:
            return
        win = MultiWazaDamageWindow(self, items)
        if event is not None:
            win.geometry(f"+{event.x_root}+{event.y_root}")


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
            ko = result.ko_text
            self.dmg2_label["text"] = result.damage_per_text + (f"  {ko}" if ko else "")
            self.hpbar.set_damage(
                mindmg=result.min_damage_per, maxdmg=result.max_damage_per
            )
        else:
            self.dmg1_label["text"] = ""
            self.dmg2_label["text"] = ""
            self.hpbar.clear()

    def set_right_click_callback(self, callback):
        def _bind(widget):
            widget.bind("<Button-3>", callback)
            for child in widget.winfo_children():
                _bind(child)
        _bind(self)


_HEAL_ITEMS = [
    ("オボンのみ", Fraction(1, 4)),
    ("たべのこし", Fraction(1, 16)),
    ("混乱実", Fraction(1, 3)),
    ("やどりぎのタネ", Fraction(1, 8)),
]


# 複数技ダメージ確認ウィンドウ
class MultiWazaDamageWindow(tkinter.Toplevel):
    def __init__(self, master, items: list[tuple[str, "DamageCalcResult | None"]]):
        super().__init__(master)
        self.title("加算ツール")
        self.resizable(False, False)

        self._items = items
        # ("move", item_idx) or ("heal", name, Fraction)
        self._pressed: list[tuple] = []

        # 初期化時に守備側HPを取得しておく（回復量計算用）
        self._defender_hp: int | None = None
        for _, result in items:
            if result is not None and result.is_damage:
                self._defender_hp = result.defender[StatsKey.H]
                break

        # 技選択ボタン (5列グリッド) + クリアボタン
        btn_frame = ttk.Frame(self, padding=(8, 8, 8, 4))
        btn_frame.pack(fill="x")
        _cols = 5
        _btn_w = const.char_width(default=12, mac=9)
        for i, (name, _) in enumerate(items):
            tkinter.Button(
                btn_frame, text=name, width=_btn_w, anchor="w",
                command=lambda idx=i: self._press_move(idx),
            ).grid(row=i // _cols, column=i % _cols, padx=2, pady=2, sticky=W + E)
        _last_btn_row = (len(items) - 1) // _cols if items else 0
        tkinter.Button(
            btn_frame, text="クリア", command=self._clear,
        ).grid(row=_last_btn_row + 1, column=0, columnspan=_cols, padx=2, pady=(6, 2), sticky=W + E)

        # 回復ボタン
        heal_frame = ttk.LabelFrame(self, text="回復", padding=(8, 4))
        heal_frame.pack(fill="x", padx=4, pady=(0, 4))
        for i, (h_name, h_frac) in enumerate(_HEAL_ITEMS):
            heal_frame.columnconfigure(i, weight=1)
            tkinter.Button(
                heal_frame, text=h_name, anchor="w",
                command=lambda n=h_name, f=h_frac: self._press_heal(n, f),
            ).grid(row=0, column=i, padx=2, pady=2, sticky=W + E)

        ttk.Separator(self, orient="horizontal").pack(fill="x", padx=4, pady=4)

        # ダメージ結果テーブル
        self._result_frame = ttk.Frame(self, padding=(8, 0, 8, 4))
        self._result_frame.pack(fill="x")
        self._result_frame.columnconfigure(0, minsize=const.char_width(default=110, mac=85))
        self._result_frame.columnconfigure(1, minsize=80)
        self._result_frame.columnconfigure(2, minsize=180)
        ttk.Label(self._result_frame, text="技名").grid(row=0, column=0, sticky=W, padx=2)
        ttk.Label(self._result_frame, text="ダメージ").grid(row=0, column=1, sticky=W, padx=4)
        ttk.Label(self._result_frame, text="割合 / 確定").grid(row=0, column=2, sticky=W, padx=4)
        self._row_widgets: list[tuple] = []

        ttk.Separator(self, orient="horizontal").pack(fill="x", padx=4, pady=4)

        # 合計行
        total_frame = ttk.Frame(self, padding=(8, 0, 8, 8))
        total_frame.pack(fill="x")
        ttk.Label(total_frame, text="合計:").grid(row=0, column=0, sticky=W)
        self._total_label = MyLabel(total_frame, text="")
        self._total_label.grid(row=0, column=1, sticky=W, padx=8)

    def _press_move(self, index: int):
        self._pressed.append(("move", index))
        self._update_display()

    def _press_heal(self, name: str, frac: "Fraction"):
        self._pressed.append(("heal", name, frac))
        self._update_display()

    def _remove(self, index: int):
        del self._pressed[index]
        self._update_display()

    def _clear(self):
        self._pressed.clear()
        self._update_display()

    def _update_display(self):
        for widgets in self._row_widgets:
            for w in widgets:
                w.destroy()
        self._row_widgets.clear()

        total_min = 0
        total_max = 0
        total_heal = 0
        first_result = None

        for seq_i, action in enumerate(self._pressed):
            r = seq_i + 1
            name_lbl = MyLabel(self._result_frame, text="", cursor="hand2")
            name_lbl.grid(row=r, column=0, sticky=W, padx=2, pady=1)
            dmg_lbl = MyLabel(self._result_frame, text="", cursor="hand2")
            dmg_lbl.grid(row=r, column=1, sticky=W, padx=4)
            pct_lbl = MyLabel(self._result_frame, text="", font=(const.FONT_FAMILY, 8), cursor="hand2")
            pct_lbl.grid(row=r, column=2, sticky=W, padx=4)
            for lbl in (name_lbl, dmg_lbl, pct_lbl):
                lbl.bind("<Button-1>", lambda e, idx=seq_i: self._remove(idx))
            self._row_widgets.append((name_lbl, dmg_lbl, pct_lbl))

            if action[0] == "move":
                _, item_idx = action
                name, result = self._items[item_idx]
                name_lbl["text"] = name
                if result is not None and result.is_damage:
                    c = int(result.defender[StatsKey.H] * result.defender.constant_damage)
                    dmg_lbl["text"] = result.damage_text
                    ko = result.ko_text
                    pct_lbl["text"] = result.damage_per_text + (f"  {ko}" if ko else "")
                    total_min += result.min_damage + c
                    total_max += result.max_damage + c
                    if first_result is None:
                        first_result = result
                else:
                    dmg_lbl["text"] = "-"
            elif action[0] == "heal":
                _, heal_name, heal_frac = action
                name_lbl["text"] = heal_name
                hp = self._defender_hp
                if hp is not None:
                    heal_hp = hp * heal_frac.numerator // heal_frac.denominator
                    heal_pct = round(heal_hp / hp * 100, 1)
                    dmg_lbl["text"] = f"-{heal_hp}"
                    pct_lbl["text"] = f"-{heal_pct}%"
                    total_heal += heal_hp
                else:
                    dmg_lbl["text"] = "-"

        if first_result is not None:
            hp = first_result.defender[StatsKey.H]
            entry = (int(hp * first_result.defender.get_stealth_rock_damage())
                     if first_result.defender.has_stealth_rock else 0)
            effective_hp = max(1, hp - entry)
            net_min = total_min - total_heal
            net_max = total_max - total_heal
            min_pct = round(net_min / hp * 100, 1)
            max_pct = round(net_max / hp * 100, 1)
            ko = self._calc_ko_text(effective_hp, total_heal)
            total_text = f"{net_min}-{net_max}  {min_pct}%-{max_pct}%"
            if ko:
                total_text += f"  {ko}"
            self._total_label["text"] = total_text
        else:
            self._total_label["text"] = ""

    def _calc_ko_text(self, effective_hp: int, total_heal: int) -> str:
        damage_lists = []
        for action in self._pressed:
            if action[0] != "move":
                continue
            _, item_idx = action
            _, result = self._items[item_idx]
            if result is not None and result.is_damage:
                c = int(result.defender[StatsKey.H] * result.defender.constant_damage)
                damage_lists.append([d + c for d in result.damages])
        if not damage_lists:
            return ""
        threshold = effective_hp + total_heal
        dp: dict[int, int] = {0: 1}
        total_combos = 1
        for damages in damage_lists:
            new_dp: dict[int, int] = {}
            for dmg, count in dp.items():
                for d in damages:
                    key = dmg + d
                    new_dp[key] = new_dp.get(key, 0) + count
            dp = new_dp
            total_combos *= 16
        ko_count = sum(count for dmg, count in dp.items() if dmg >= threshold)
        if ko_count == 0:
            return ""
        if ko_count == total_combos:
            return "確定KO"
        pct = round(ko_count / total_combos * 100, 1)
        return f"乱数KO ({pct}%)"


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
        self._stage: Stage | None = None
        self._pokemon: Pokemon = Pokemon()
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
        self.type1_icon.bind("<Button-1>", lambda _e: self._on_click_type())

        self.type2_img = img[self._player][1]
        self.type2_icon = ttk.Label(basic_info_flame, image=self.type2_img)
        self.type2_icon.grid(column=2, row=0, sticky="w")
        self.type2_icon.bind("<Button-1>", lambda _e: self._on_click_type())

        self._teras_button = TypeIconButton(
            basic_info_flame,
            types=Types.なし,
            padding=0,
            command=self.on_push_terasbutton
            if get_recog_value("terastal_enabled")
            else None,
            state=tkinter.NORMAL
            if get_recog_value("terastal_enabled")
            else tkinter.DISABLED,
        )
        self._teras_button.grid(column=3, row=0, sticky=W + E)
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

    def set_stage(self, stage: Stage):
        self._stage = stage

    def _on_click_type(self):
        if self._stage is None or self._pokemon.is_empty:
            return
        if self._pokemon.ability not in ("へんげんじざい", "リベロ"):
            return
        self._stage.select_battle_type(self._player)

    def set_info(self, pokemon: Pokemon):
        self._pokemon = pokemon
        if pokemon.is_empty is False:
            self._no = pokemon.no
            self._form = pokemon.form
            self.name.set(pokemon.name)
            is_protean = pokemon.ability in ("へんげんじざい", "リベロ")
            cursor = "hand2" if is_protean else ""
            self.type1_icon.configure(cursor=cursor)
            self.type2_icon.configure(cursor=cursor)
            if pokemon.battle_type is not None:
                display_type1 = pokemon.battle_type[0]
                display_type2 = None
            else:
                display_types = pokemon.type
                display_type1 = display_types[0]
                display_type2 = display_types[1] if len(display_types) > 1 else None
            img[self._player][0] = tkinter.PhotoImage(
                file=display_type1.icon
            ).subsample(3, 3)
            self.type1_icon.configure(
                image=img[self._player][0], text=display_type1.name, compound="left"
            )
            img[self._player][1] = tkinter.PhotoImage(
                file=display_type2.icon if display_type2 else Types.なし.icon
            ).subsample(3, 3)
            self.type2_icon.configure(
                image=img[self._player][1],
                text=display_type2.name if display_type2 else "",
                compound="left",
            )
            for _i, statskey in enumerate([x for x in StatsKey]):
                self.syuzoku[statskey].set(pokemon.syuzoku[statskey])
            self._teras_button.set_type(pokemon.battle_terastype)
            self._update_teras_state(pokemon.ability)

    def _update_teras_state(self, ability: str):
        enabled = get_recog_value("terastal_enabled")
        self._teras_button.config(
            state=tkinter.NORMAL if enabled else tkinter.DISABLED,
            command=self.on_push_terasbutton if enabled else (lambda: None),
        )

    def on_push_terasbutton(self, *_args):
        self._stage.select_terastype(self._player)

    def open_poketetsu(self):
        if self._no != 0:
            url = "https://yakkun.com/sv/zukan/?national_no=" + str(self._no)
            webbrowser.open(url)

    def open_db(self):
        if self._no != 0:
            season = 1
            pid = str(self._no).zfill(4) + "-" + str(self._form).zfill(2)
            with open("stats/season.txt", encoding="utf-8") as ranking_txt:
                season = ranking_txt.read()

            url = (
                f"https://champs.pokedb.tokyo/pokemon/show/{pid}?season={season}&rule=0"
            )
            webbrowser.open(url)
