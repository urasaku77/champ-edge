import copy
import dataclasses
import os
import sys
import threading
import tkinter
from tkinter import E, N, S, W, messagebox, ttk

from ttkthemes.themed_tk import ThemedTk

from component.frames.common import (
    ActivePokemonFrame,
    ChosenFrame,
    InfoFrame,
    PartyFrame,
    WazaDamageListFrame,
)
from component.frames.whole import (
    CompareButton,
    CountersFrame,
    DoubleFrame,
    FieldFrame,
    HomeFrame,
    RecordFrame,
    TimerFrame,
    WeatherFrame,
)
from component.parts.button import MyButton
from component.parts.dialog import (
    BoxDialog,
    FormSelect,
    PartyInputDialog,
    SimilarParty,
    SpeedComparing,
    TypeSelectDialog,
    WeightComparing,
)
from database.battle import Battle, DB_battle
from mypgl import analytics, record
from party.party import PartyEditor
from pokedata.const import Types
from pokedata.pokemon import Pokemon
from pokedata.stats import StatsKey
from recog.capture import Capture
from recog.recog import CaptureSetting, ModeSetting, get_recog_value
from stats.search import get_similar_party

_IS_MAC = sys.platform == "darwin"
# Mac の ttk ウィジェットは Windows より幅広に描画されるため
# 横方向だけスケールし、縦方向は Mac 画面の高さに収まるよう微圧縮
_SCALE_X = 1.0
_SCALE_Y = 0.92 if _IS_MAC else 1.0


def _sx(v: int) -> int:
    return int(v * _SCALE_X)


def _sy(v: int) -> int:
    return int(v * _SCALE_Y)


class MainApp(ThemedTk):
    def __init__(self, **kwargs):
        super().__init__(theme="arc", **kwargs)
        self.title("ChampEdge")
        if sys.platform == "win32":
            self.iconbitmap(default="image/favicon.ico")
        if _IS_MAC:
            # Mac の named font (TkDefaultFont 等) は 13pt と大きく、
            # ttk widget の高さ・幅・パディングがこれに比例して大きくなる。
            # Windows 同等 (10pt 前後) に縮めて全体を圧縮する。
            import tkinter.font as _tkfont

            for _name in (
                "TkDefaultFont",
                "TkTextFont",
                "TkMenuFont",
                "TkHeadingFont",
                "TkCaptionFont",
                "TkIconFont",
                "TkTooltipFont",
                "TkSmallCaptionFont",
            ):
                try:
                    _f = _tkfont.nametofont(_name)
                    _f.configure(size=10)
                except Exception:
                    pass
        # Mac の dark mode 対策:
        # arc テーマは TLabel/TButton 等の background は明るく設定するが
        # TCombobox/TSpinbox/TEntry の fieldbackground は OS デフォルト
        # にフォールバックするため、dark mode で黒く表示されてしまう。
        # ここで全 ttk 入力系の field 系色と、tkinter (非 ttk) 系の
        # デフォルト色を明示的に上書きする。
        if _IS_MAC:
            _bg = "#f5f6f7"
            _field = "white"
            _fg = "black"
            style = ttk.Style(self)
            for widget in (
                "TEntry",
                "TCombobox",
                "TSpinbox",
            ):
                style.configure(
                    widget,
                    fieldbackground=_field,
                    foreground=_fg,
                    background=_bg,
                    selectbackground="#c0d8f0",
                    selectforeground=_fg,
                    insertcolor=_fg,
                    arrowcolor=_fg,
                    bordercolor="#cccccc",
                )
                style.map(
                    widget,
                    fieldbackground=[("readonly", _field), ("disabled", "#e8e8e8")],
                    foreground=[("disabled", "#888888")],
                )
            # ttk.Treeview の dark mode 対策
            style.configure(
                "Treeview",
                background=_field,
                fieldbackground=_field,
                foreground=_fg,
            )
            style.configure(
                "Treeview.Heading",
                background=_bg,
                foreground=_fg,
            )
            # tkinter (非 ttk) widget 用デフォルト
            # highlightThickness=0 で focus 用の黒い枠線を消す
            # （これが「黒線」の主因）
            self.option_add("*highlightThickness", 0)
            self.option_add("*highlightBackground", _bg)
            self.option_add("*highlightColor", _bg)
            self.option_add("*Background", _bg)
            self.option_add("*Foreground", _fg)
            self.option_add("*Canvas.Background", _bg)
            self.option_add("*Canvas.borderWidth", 0)
            self.option_add("*Canvas.highlightThickness", 0)
            self.option_add("*Frame.Background", _bg)
            self.option_add("*Label.Background", _bg)
            self.option_add("*Label.Foreground", _fg)
            self.option_add("*Button.Background", _bg)
            self.option_add("*Button.Foreground", _fg)
            self.option_add("*Button.activeBackground", "#e0e0e0")
            self.option_add("*Button.activeForeground", _fg)
            self.option_add("*Button.highlightBackground", _bg)
            self.option_add("*Button.highlightThickness", 0)
            self.option_add("*Button.relief", "raised")
            self.option_add("*Button.borderWidth", 1)
            self.option_add("*Entry.Background", _field)
            self.option_add("*Entry.Foreground", _fg)
            self.option_add("*Entry.insertBackground", _fg)
            self.option_add("*Entry.highlightBackground", _bg)
            self.option_add("*Entry.highlightThickness", 0)
            self.option_add("*Entry.borderWidth", 1)
            self.option_add("*Entry.relief", "solid")
            self.option_add("*Text.Background", _field)
            self.option_add("*Text.Foreground", _fg)
            self.option_add("*Text.insertBackground", _fg)
            self.option_add("*Text.highlightBackground", _bg)
            self.option_add("*Text.highlightThickness", 0)
            self.option_add("*Checkbutton.Background", _bg)
            self.option_add("*Checkbutton.Foreground", _fg)
            self.option_add("*Checkbutton.activeBackground", "#e0e0e0")
            self.option_add("*Checkbutton.activeForeground", _fg)
            self.option_add("*Checkbutton.selectColor", _field)
            self.option_add("*Checkbutton.highlightBackground", _bg)
            self.option_add("*Checkbutton.highlightThickness", 0)
            self.option_add("*Menu.Background", _bg)
            self.option_add("*Menu.Foreground", _fg)
            self.option_add("*Menu.activeBackground", "#e0e0e0")
            self.option_add("*Menu.activeForeground", _fg)
            self.option_add("*Spinbox.Background", _field)
            self.option_add("*Spinbox.Foreground", _fg)
            self.option_add("*Listbox.Background", _field)
            self.option_add("*Listbox.Foreground", _fg)
            self.option_add("*Scrollbar.Background", _bg)
            self.option_add("*Scrollbar.troughColor", _bg)
            # ttk LabelFrame の border を薄いグレーに
            style.configure(
                "TLabelframe",
                bordercolor="#cccccc",
                lightcolor="#cccccc",
                darkcolor="#cccccc",
            )
            # カウンタの -/0/+ ボタン用 compact style (padding 詰めて狭い Canvas に収める)
            style.configure("Counter.TButton", padding=(0, 0))
        if _IS_MAC:
            # Mac はメニューバー直下に配置することで縦方向の使える高さを最大化
            self.geometry(f"{_sx(950)}x{_sy(915)}+0+25")
        else:
            self.geometry(f"{_sx(950)}x{_sy(915)}")

        self.capture = Capture()
        self.websocket = False
        self.monitor = False

        self.party_frames: list[PartyFrame] = []
        self.chosen_frames: list[ChosenFrame] = []
        self._info_frames: list[InfoFrame] = []
        self.active_poke_frames: list[ActivePokemonFrame] = []
        self._waza_damage_frames: list[WazaDamageListFrame] = []

        # メインフレーム
        main_frame = tkinter.Frame(self, bg="gray97")
        self.bind("<Configure>", self.on_change_transport)
        main_frame.grid(row=0, column=0, sticky=N + E + W + S)

        menu = tkinter.Menu(self)
        self.config(menu=menu)
        battle_menu = tkinter.Menu(menu, tearoff=0)
        battle_menu.add_command(label="HOME情報取得", command=self.update_home_data)
        battle_menu.add_command(
            label="HOME情報最終更新日", command=self.show_last_update_date
        )
        battle_menu.add_separator()
        battle_menu.add_command(label="構築記事取得", command=self.update_battle_data)
        battle_menu.add_command(
            label="構築記事最終更新日", command=self.show_last_battle_update_date
        )
        menu.add_cascade(label="バトルデータ", menu=battle_menu)
        menu.add_cascade(label="キャプチャ設定", command=self.capture_setting)
        menu.add_cascade(label="モード切替", command=self.mode_setting)
        menu.add_cascade(label="パーティ編集", command=self.edit_party_csv)
        menu.add_cascade(label="ボックス編集", command=self.open_box)
        menu.add_cascade(label="対戦履歴", command=self.open_records)
        menu.add_cascade(label="対戦分析", command=self.open_analytics)
        menu.add_command(label="アップデート確認", command=self.check_update)

        for i, side in enumerate(["自分側", "相手側"]):
            sticky = N + W + S if side == "自分側" else N + E + S
            # パーティ＆選出フレーム
            top_frame = ttk.Frame(
                master=main_frame, width=_sx(500), height=_sy(60), padding=5
            )
            top_frame.grid(row=0, column=i * 3, rowspan=2, columnspan=3, sticky=sticky)
            top_frame.grid_propagate(False)
            # パーティ表示フレーム
            party_frame = PartyFrame(
                master=top_frame,
                player=i,
                width=_sx(350),
                height=_sy(60),
                text=side + "パーティ",
            )
            party_frame.pack(fill="both", expand=0, side="left")
            self.party_frames.append(party_frame)

            # 選出表示フレーム
            chosen_frame = ChosenFrame(
                master=top_frame,
                player=i,
                width=_sx(180),
                height=_sy(60),
                text=side + "選出",
            )
            chosen_frame.pack(fill="both", expand=0, side="left")
            self.chosen_frames.append(chosen_frame)

            # 選択ポケモン基本情報表示フレーム
            # Mac は status row (H A B C D S 値) が 14px に潰される問題があるので明示的に高めに
            _info_h = 75 if _IS_MAC else _sy(80)
            info_frame = InfoFrame(
                master=main_frame,
                player=i,
                width=_sx(475),
                height=_info_h,
                text=side + "基本情報",
            )
            info_frame.grid(row=2, column=i * 3, columnspan=3, sticky=sticky)
            info_frame.grid_propagate(False)
            self._info_frames.append(info_frame)

            # 選択ポケモン表示フレーム
            _poke_h = 190 if _IS_MAC else _sy(213)
            poke_frame = ActivePokemonFrame(
                master=main_frame,
                player=i,
                width=_sx(475),
                height=_poke_h,
                text=side + "ポケモン",
            )
            poke_frame.grid(row=3, column=i * 3, columnspan=3, sticky=sticky)
            poke_frame.grid_propagate(False)
            self.active_poke_frames.append(poke_frame)

        # 技・ダメージ表示フレーム(自分)
        # Mac で 4 行分の表示が押し潰されないよう明示的に高さ指定
        _waza_my_h = 145 if _IS_MAC else _sy(60)
        waza_frame_my = WazaDamageListFrame(
            master=main_frame,
            index=0,
            width=_sx(475),
            height=_waza_my_h,
            text="自分わざ情報",
        )
        waza_frame_my.grid(row=4, column=0, columnspan=3, sticky=N + W + S)
        waza_frame_my.grid_propagate(False)
        self._waza_damage_frames.append(waza_frame_my)

        # 技・ダメージ表示フレーム(相手)
        # Mac 画面が低いため、相手わざ情報の rowspan 高さを抑えて
        # 左カラムの行高さを圧迫しないようにする
        _waza_your_h = 200 if _IS_MAC else _sy(313)
        waza_frame_your = WazaDamageListFrame(
            master=main_frame,
            index=1,
            width=_sx(475),
            height=_waza_your_h,
            text="相手わざ情報",
        )
        waza_frame_your.grid(row=4, column=3, rowspan=2, columnspan=3, sticky=N + E + S)
        waza_frame_your.grid_propagate(False)
        self._waza_damage_frames.append(waza_frame_your)

        # HOME情報フレーム
        self.home_frame = HomeFrame(
            master=main_frame, width=_sx(475), height=_sy(258), text="HOME情報"
        )
        self.home_frame.grid(row=6, column=3, rowspan=4, columnspan=3, sticky=N + E + S)
        self.home_frame.grid_propagate(False)

        # ツールフレーム（タイマー・カウンター・ダブル・共通）
        if _IS_MAC:
            tool_frame = ttk.Frame(main_frame, padding=4, width=_sx(475), height=105)
            tool_frame.grid(row=5, column=0, rowspan=3, columnspan=3, sticky=N + W + S)
            tool_frame.pack_propagate(False)
        else:
            tool_frame = ttk.Frame(main_frame, padding=4)
            tool_frame.grid(row=5, column=0, rowspan=3, sticky=N + W + S)
            tool_frame.grid_propagate(False)

        # タイマーフレーム
        self.timer_frame = TimerFrame(master=tool_frame, text="タイマー")
        self.timer_frame.pack(fill="both", expand=0, side="left")

        # カウンターフレーム
        self.counter_frame = CountersFrame(
            master=tool_frame,
            num=2 if get_recog_value("rule") == 1 else 1,
            text="カウンター",
        )
        self.counter_frame.pack(fill="both", expand=0, side="left")

        if get_recog_value("rule") == 2:
            # ダブルフレーム
            self.double_frame = DoubleFrame(tool_frame)
            self.double_frame.pack(fill="both", expand=0, side="left")

        # 共通フレーム（天気・フィールド）
        common_frame = ttk.Frame(tool_frame)
        common_frame.pack(fill="both", expand=0, side="left")

        # 天候フレーム
        self.weather_frame = WeatherFrame(
            master=common_frame,
            text="天候",
            padding=1 if _IS_MAC else 6,
        )
        self.weather_frame.pack(fill="x", expand=0)

        # フィールドフレーム
        self.field_frame = FieldFrame(
            master=common_frame,
            text="フィールド",
            padding=1 if _IS_MAC else 6,
        )
        self.field_frame.pack(fill="x", expand=0)

        # 比較ボタンフレーム（素早さ・重さ）
        _cmp_pad = 1 if _IS_MAC else 5
        if _IS_MAC:
            compare_frame = ttk.Frame(tool_frame)
            compare_frame.pack(fill="both", expand=0, side="left")
        else:
            compare_frame = ttk.Frame(common_frame)
            compare_frame.pack(fill="both", expand=0)

        # 素早さ比較ボタン
        self.speed_button = CompareButton(
            master=compare_frame,
            text="S比較",
            width=6 if not _IS_MAC else 5,
            padding=_cmp_pad,
            command=self.speed_comparing,
        )
        if _IS_MAC:
            self.speed_button.pack(fill="x", expand=0)
        else:
            self.speed_button.pack(fill="both", expand=0, side="left")

        # 重さ比較ボタン
        self.weight_button = CompareButton(
            master=compare_frame,
            text="重さ比較",
            width=8 if not _IS_MAC else 6,
            padding=_cmp_pad,
            command=self.weight_comparing,
        )
        if _IS_MAC:
            self.weight_button.pack(fill="x", expand=0)
        else:
            self.weight_button.pack(fill="both", expand=0, side="left")

        # 対戦記録フレーム
        _record_h = 135 if _IS_MAC else _sy(157)
        self.record_frame = RecordFrame(
            master=main_frame, width=_sx(474), height=_record_h, text="対戦記録"
        )
        self.record_frame.grid(row=8, column=0, columnspan=3, sticky=N + W + S)
        self.record_frame.grid_propagate(False)

        # 最終メニューフレーム
        if _IS_MAC:
            last_menu_frame = ttk.Frame(
                master=main_frame, padding=2, width=_sx(475), height=50
            )
            last_menu_frame.grid(row=9, column=0, columnspan=3, sticky=N + W)
            last_menu_frame.pack_propagate(False)
        else:
            last_menu_frame = ttk.Frame(master=main_frame, padding=4)
            last_menu_frame.grid(row=9, column=0, columnspan=3, sticky=N + W)

        # 制御フレーム
        control_frame = ttk.LabelFrame(master=last_menu_frame, text="制御", padding=5)
        control_frame.pack(fill="both", expand=0, side="left")

        from component.parts import const as _parts_const

        # フォント縮小済みなので、ボタン幅も小さめに
        _ctrl_btn_w = _parts_const.char_width(default=0, mac=6)
        _ws_btn_w = _parts_const.char_width(default=0, mac=11)
        _btn_kwargs_ctrl = {"width": _ctrl_btn_w} if _ctrl_btn_w else {}
        _btn_kwargs_ws = {"width": _ws_btn_w} if _ws_btn_w else {}

        # Websocket接続ボタン
        self.websocket_var = tkinter.StringVar()
        self.websocket_var.set("Websocket接続")

        self.websocket_button = MyButton(
            control_frame,
            textvariable=self.websocket_var,
            command=self.connect_websocket,
            **_btn_kwargs_ws,
        )
        self.websocket_button.pack(fill="both", expand=0, side="left")

        # キャプチャ監視ボタン
        self.monitor_var = tkinter.StringVar()
        self.monitor_var.set("監視開始")
        self.monitor_button = MyButton(
            control_frame,
            textvariable=self.monitor_var,
            command=self.image_recognize,
            state=tkinter.DISABLED,
            **_btn_kwargs_ctrl,
        )
        self.monitor_button.pack(fill="both", expand=0, side="left")

        # 手動キャプチャボタン
        self.shot_button = MyButton(
            control_frame,
            text="選出取得",
            command=self.manual_capture,
            state=tkinter.DISABLED,
            **_btn_kwargs_ctrl,
        )
        self.shot_button.pack(fill="both", expand=0, side="left")

        # 検索フレーム
        search_frame = ttk.LabelFrame(
            master=last_menu_frame, text="類似パーティ", padding=5
        )
        search_frame.pack(fill="both", expand=0, side="left")

        # 類似パーティ検索ボタン
        self.search_button = MyButton(
            search_frame,
            text="構築記事",
            command=self.search_similar_party,
            **_btn_kwargs_ctrl,
        )
        self.search_button.pack(fill="both", expand=0, side="left")

        # 対戦履歴から検索ボタン
        self.search_button = MyButton(
            search_frame,
            text="対戦履歴",
            command=self.search_record,
            **_btn_kwargs_ctrl,
        )
        self.search_button.pack(fill="both", expand=0, side="left")

        # グリッド間ウェイト
        main_frame.columnconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        main_frame.columnconfigure(2, weight=1)
        main_frame.columnconfigure(3, weight=1)
        main_frame.columnconfigure(4, weight=1)
        main_frame.columnconfigure(5, weight=1)

        self.columnconfigure(0, weight=True)
        self.rowconfigure(0, weight=True)

        self._stage = None
        self._after_id: int | None = None
        self._party_progress_win: tkinter.Toplevel | None = None

        self.after(1000, self._auto_check_update)

    def _auto_check_update(self):
        threading.Thread(target=self._auto_check_update_worker, daemon=True).start()

    def _auto_check_update_worker(self):
        import json as _json
        import urllib.request

        current = self._get_current_version()
        api_url = f"https://api.github.com/repos/{self._RELEASES_REPO}/releases/latest"
        _headers = {
            "User-Agent": "champedge-updater/1.0",
            "Authorization": f"token {self._RELEASE_TOKEN}",
        }

        try:
            req = urllib.request.Request(api_url, headers=_headers)
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = _json.loads(resp.read().decode("utf-8"))
        except Exception:
            return

        latest = data.get("tag_name", "").lstrip("v")
        if not latest or self._parse_version(latest) <= self._parse_version(current):
            return

        assets = [
            a
            for a in data.get("assets", [])
            if a["name"] == "champedge_forwin_update.zip"
        ]
        if not assets:
            return

        asset_id = assets[0]["id"]
        self.after(
            0,
            lambda: self._prompt_auto_update(current, latest, asset_id),
        )

    def _prompt_auto_update(self, current: str, latest: str, asset_id: int):
        if not messagebox.askyesno(
            "アップデート確認",
            f"新しいバージョンがあります\n\n現在: v{current}  →  最新: v{latest}\n\n"
            "アップデートしますか？\n（パーティやDBのデータは保持されます）",
        ):
            return
        self._apply_update(asset_id)

    # 各フレームにStageクラスを配置
    def set_stage(self, stage):
        self._stage = stage
        self.home_frame.set_stage(stage)
        for i in range(2):
            self.party_frames[i].set_stage(stage)
            self.chosen_frames[i].set_stage(stage)
            self._info_frames[i].set_stage(stage)
            self.active_poke_frames[i].set_stage(stage)
            self.active_poke_frames[i]._status_frame.set_stage(stage)
            self._waza_damage_frames[i].set_stage(stage)
            self.weather_frame.set_stage(stage)
            self.field_frame.set_stage(stage)
            self.speed_button.set_stage(stage)
            self.weight_button.set_stage(stage)
            self.record_frame.set_stage(stage)
        if get_recog_value("rule") == 2:
            self.double_frame.set_stage(stage)

    # パーティCSV編集
    def edit_party_csv(self):
        dialog = PartyEditor()
        dialog.open(location=(self.winfo_x(), self.winfo_y()))
        self.withdraw()
        self.wait_window(dialog)
        return self.deiconify()

    # パーティセット
    def set_party(self, player: int, party: list[Pokemon]):
        self.party_frames[player].set_party(party)

    # 選出登録
    def set_chosen(self, player: int, pokemon: Pokemon, index: int):
        self.chosen_frames[player].set_chosen(pokemon, index)

    # 選出基本情報表示
    def set_info(self, player: int, pokemon: Pokemon):
        self._info_frames[player].set_info(pokemon)

    # ポケモン選択
    def set_active_pokemon(self, player: int, pokemon: Pokemon):
        change_flag = self.active_poke_frames[player]._pokemon.no == pokemon.no
        self.active_poke_frames[player].set_pokemon(pokemon)
        self._waza_damage_frames[player].set_waza_info(pokemon.waza_list)
        if player == 1:
            self._waza_damage_frames[player].set_waza_rate(pokemon.waza_rate_list)
            if not change_flag:
                self.home_frame.set_home_data(pokemon.name)

    def after_appear(self, pokemon: Pokemon, player: int):
        match pokemon.ability:
            case "すなおこし":
                self.weather_frame.change_weather_from_ability("砂嵐")
            case "ひでり" | "ひひいろのこどう" | "メガソーラー":
                self.weather_frame.change_weather_from_ability("晴れ")
            case "あめふらし":
                self.weather_frame.change_weather_from_ability("雨")
            case "ゆきふらし":
                self.weather_frame.change_weather_from_ability("雪")
            case "エレキメイカー" | "ハドロンエンジン":
                self.field_frame.change_field_from_ability("エレキ")
            case "グラスメイカー":
                self.field_frame.change_field_from_ability("グラス")
            case "ミストメイカー":
                self.field_frame.change_field_from_ability("ミスト")
            case "サイコメイカー":
                self.field_frame.change_field_from_ability("サイコ")
            case _ if pokemon.name == "メタモン":
                after_ditto = (
                    copy.deepcopy(self.active_poke_frames[1]._pokemon)
                    if player == 0
                    else copy.deepcopy(self.active_poke_frames[0]._pokemon)
                )
                after_ditto.syuzoku.__setitem__(StatsKey.H, 48)
                after_ditto.doryoku.__setitem__(StatsKey.H, 32)
                self.active_poke_frames[player].set_pokemon(after_ditto)
                if player == 1:
                    self._waza_damage_frames[player].set_waza_info(
                        self.active_poke_frames[0]._pokemon.waza_list
                    )

    # ダメージ計算
    def set_calc_results(self, player: int, results):
        self._waza_damage_frames[player].set_damages(results)

    # タイプ選択
    def select_type(self, player: int) -> Types:
        dialog = TypeSelectDialog()
        dialog.open(location=(self.winfo_x(), self.winfo_y()))
        self.wait_window(dialog)
        return dialog.selected_type

    # パーティ編集
    def edit_party(self, party) -> list[Pokemon]:
        dialog = PartyInputDialog()
        dialog.party = party
        dialog.open(location=(self.winfo_x(), self.winfo_y()))
        self.wait_window(dialog)
        return dialog.party

    # 素早さ比較
    def speed_comparing(self):
        pokemons = self.speed_button.get_active_pokemons()
        if pokemons[0].no != -1 and pokemons[1].no != -1:
            dialog = SpeedComparing()
            dialog.set_pokemon(pokemons)
            dialog.open(location=(self.winfo_x(), self.winfo_y()))
            self.wait_window(dialog)

    # 重さ比較
    def weight_comparing(self):
        pokemons = self.weight_button.get_active_pokemons()
        if pokemons[0].no != -1 and pokemons[1].no != -1:
            dialog = WeightComparing()
            dialog.set_pokemon(pokemons)
            dialog.open(location=(self.winfo_x(), self.winfo_y()))
            self.wait_window(dialog)

    # 対戦登録
    def record_battle(self):
        battle = Battle.set_battle(
            self.record_frame, self.party_frames, self.chosen_frames
        )
        battle_data = dataclasses.astuple(battle)
        DB_battle.register_battle(battle_data)
        self.record_frame.clear()
        ret = messagebox.askyesno(
            "確認",
            "データを登録しました\n次の対戦へ移りますか？）",
        )
        if ret is False:
            return
        self.image_recognize()

    # 対戦記録情報クリア
    def clear_battle(self):
        self.party_frames[1].on_push_clear_button()
        self.chosen_frames[0].on_push_clear_button()
        self.chosen_frames[1].on_push_clear_button()
        self.timer_frame.reset_button_clicked()
        self.counter_frame.clear_all_counters()
        self.weather_frame.reset_weather()
        self.field_frame.reset_field()

    # キャプチャ設定画面
    def capture_setting(self):
        dialog = CaptureSetting()
        dialog.open(location=(self.winfo_x(), self.winfo_y()))
        self.wait_window(dialog)

    # モード切替画面
    def mode_setting(self):
        dialog = ModeSetting()
        dialog.open(location=(self.winfo_x(), self.winfo_y()))
        self.wait_window(dialog)

    # Websocket処理
    def connect_websocket(self):
        if not self.websocket:
            value = self.capture.connect_websocket()
            if value:
                self.websocket_var.set("Websocket切断")
                self.monitor_button["state"] = tkinter.NORMAL
                self.shot_button["state"] = tkinter.NORMAL
                self.websocket = True

                if get_recog_value("capture_monitor_auto"):
                    self.image_recognize()

        else:
            value = self.capture.disconnect_websocket()
            if value:
                self.websocket_var.set("Websocket接続")
                self.monitor_button["state"] = tkinter.DISABLED
                self.shot_button["state"] = tkinter.DISABLED
                self.websocket = False

    # 画像認識処理
    def image_recognize(self):
        if self.monitor:
            self.stop_image_recognize()
        else:
            self.capture.phase = "sensyutu"
            self.capture.party_recognized = False
            self.party_frames[0].on_push_load_button()
            self.after(2000, self.loop_image_recognize)

    # 画像認識ループ開始
    def loop_image_recognize(self):
        self.monitor = True
        self.monitor_var.set("監視停止")
        self.websocket_button["state"] = tkinter.DISABLED
        self.shot_button["state"] = tkinter.DISABLED
        threading.Thread(target=self._loop_recognize_worker, daemon=True).start()

    def _loop_recognize_worker(self):
        def _on_start(total: int):
            self.after(0, lambda t=total: self._show_party_progress(t))

        def _on_progress(current: int, total: int):
            self.after(0, lambda c=current, t=total: self._update_party_progress(c, t))

        self.capture.on_party_start_progress = _on_start
        self.capture.on_party_progress = _on_progress
        result = self.capture.image_recognize()
        self.after(0, self._close_party_progress)
        self.after(0, lambda r=result: self._handle_loop_result(r))

    def _handle_loop_result(self, result):
        if not self.monitor:
            return
        match result:
            case tuple():
                self.party_frames[1].set_party_from_capture(result[0])
                self.record_frame.tn.insert(0, result[1])
                if get_recog_value("similar_party_auto"):
                    self.search_similar_party(isOpen=False)
                if get_recog_value("search_record_auto"):
                    self.search_record(isOpen=False)
            case list():
                if not all(x == -1 for x in result):
                    self.chosen_frames[0].set_chosen_from_capture(result)
            case bool():
                if result:
                    self.timer_frame.reset_button_clicked()
                    self.timer_frame.start_button_clicked()
                    self.party_frames[0].set_first_chosen_to_active()
                    self.stop_image_recognize()
                    return
            case int():
                if result != -1:
                    self.record_frame.rank.insert(0, result)
            case _:
                pass
        self._after_id = self.after(1000, self.loop_image_recognize)

    def _show_party_progress(self, total: int):
        if self._party_progress_win is not None:
            return
        self._party_progress_win = tkinter.Toplevel(self)
        self._party_progress_win.title("パーティ認識中...")
        self._party_progress_win.resizable(False, False)
        self._party_progress_win.grab_set()
        self._party_progress_label = tkinter.Label(
            self._party_progress_win,
            text=f"ポケモン認識中... 0 / {total}",
            padx=30, pady=10, width=28, justify="center",
        )
        self._party_progress_label.pack()
        self._party_progress_bar = ttk.Progressbar(
            self._party_progress_win, length=280, mode="determinate", maximum=total,
        )
        self._party_progress_bar.pack(padx=30, pady=(0, 20))

    def _update_party_progress(self, current: int, total: int):
        if self._party_progress_win is None:
            return
        try:
            self._party_progress_label.config(text=f"ポケモン認識中... {current} / {total}")
            self._party_progress_bar["value"] = current
        except Exception:
            pass

    def _close_party_progress(self):
        if self._party_progress_win is not None:
            try:
                self._party_progress_win.destroy()
            except Exception:
                pass
            self._party_progress_win = None

    # 画像認識ループ停止
    def stop_image_recognize(self):
        if self.monitor:
            self.after_cancel(self._after_id)
            self.monitor = False
            self.monitor_var.set("監視開始")
            self.websocket_button["state"] = tkinter.NORMAL
            self.shot_button["state"] = tkinter.NORMAL

    # 手動キャプチャ
    def manual_capture(self):
        threading.Thread(target=self._manual_capture_worker, daemon=True).start()

    def _manual_capture_worker(self):
        def _on_start(total: int):
            self.after(0, lambda t=total: self._show_party_progress(t))

        def _on_progress(current: int, total: int):
            self.after(0, lambda c=current, t=total: self._update_party_progress(c, t))

        self.capture.on_party_start_progress = _on_start
        self.capture.on_party_progress = _on_progress
        result = self.capture.recognize_chosen_capture()
        self.after(0, self._close_party_progress)
        if result is not None:
            self.after(0, lambda r=result: self._on_manual_capture_result(r))

    def _on_manual_capture_result(self, result):
        self.party_frames[1].set_party_from_capture(result[0])
        self.record_frame.tn.insert(0, result[1])

    # 類似パーティ検索
    def search_similar_party(self, isOpen: bool = True):
        current_party = [pokemon.pid for pokemon in self.party_frames[1].pokemon_list]
        party_list = get_similar_party(self.party_frames[1].pokemon_list)
        if isOpen or party_list:
            dialog = SimilarParty(current_party=current_party, party_list=party_list)
            dialog.open(location=(self.winfo_x(), self.winfo_y()))

    # 対戦履歴から検索
    def search_record(self, isOpen: bool = True):
        current_party = [pokemon.pid for pokemon in self.party_frames[1].pokemon_list]
        dialog = record.ListRecord()
        if (
            isOpen
            or len(dialog.full_frame.get_battle_data(current_party)) > 0
            or len(dialog.part_frame.get_battle_data(current_party)) > 0
        ):
            dialog.full_frame.get_battle_data(current_party)
            dialog.part_frame.get_battle_data(current_party)
            dialog.open()

    # HOME情報更新
    _LAST_UPDATE_FILE = "stats/last_update.txt"
    _LAST_BATTLE_UPDATE_FILE = "stats/last_update_battle.txt"
    _STATS_BASE_URL = "https://raw.githubusercontent.com/urasaku77/champ-edge/main/stats"
    _HOME_FILES = [
        "home_waza.csv", "home_tokusei.csv", "home_motimono.csv",
        "home_seikaku.csv", "home_doryoku.csv",
    ]
    _BATTLE_FILES = ["ranking.json", "ranking.txt", "season.txt"]

    # アップデート
    _RELEASES_REPO = "urasaku77/champ-edge"
    _RELEASE_TOKEN = "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"
    _VERSION_FILE = "version.txt"

    def _fetch_text(self, url: str) -> str:
        import ssl
        import urllib.request
        ctx = ssl._create_unverified_context()
        headers = {
            "User-Agent": "champedge/1.0",
            "Authorization": f"token {self._RELEASE_TOKEN}",
        }
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, context=ctx) as r:
            return r.read().decode("utf-8")

    def _download_stats_files(self, filenames: list[str], update_cb):
        """GitHubからstatsファイルをダウンロードしてローカルに保存する"""
        for i, name in enumerate(filenames, 1):
            update_cb(f"{i} / {len(filenames)}  {name}")
            content = self._fetch_text(f"{self._STATS_BASE_URL}/{name}")
            with open(f"stats/{name}", "w", encoding="utf-8", newline="") as f:
                f.write(content)

    def update_home_data(self):
        try:
            local_date = open(self._LAST_UPDATE_FILE, encoding="utf-8").read().strip()
        except FileNotFoundError:
            local_date = ""

        progress_win = tkinter.Toplevel(self)
        progress_win.title("HOME情報取得中...")
        progress_win.resizable(False, False)
        progress_win.grab_set()
        progress_label = tkinter.Label(
            progress_win, text="準備中...", padx=30, pady=10, width=36, justify="center",
        )
        progress_label.pack()
        bar = ttk.Progressbar(progress_win, length=300, mode="indeterminate")
        bar.pack(padx=30, pady=(0, 20))
        bar.start(15)

        def _update(text: str):
            self.after(0, lambda t=text: progress_label.config(text=t))

        def _run():
            err_msg = None
            remote_date = None
            try:
                remote_date = self._fetch_text(f"{self._STATS_BASE_URL}/last_update.txt").strip()
                if remote_date == local_date:
                    self.after(0, progress_win.destroy)
                    self.after(0, lambda: messagebox.showinfo("HOME情報更新", "最新データです"))
                    return
                self._download_stats_files(self._HOME_FILES, _update)
            except Exception as e:
                err_msg = str(e)
            finally:
                self.after(0, progress_win.destroy)
            if err_msg is None:
                self.after(0, lambda d=remote_date: self._on_home_update_done(True, None, d))
            else:
                self.after(0, lambda e=err_msg: self._on_home_update_done(False, e, None))

        threading.Thread(target=_run, daemon=True).start()

    def _on_home_update_done(self, success: bool, error: str | None, remote_date: str | None):
        if success:
            with open(self._LAST_UPDATE_FILE, "w", encoding="utf-8") as f:
                f.write(remote_date)
            messagebox.showinfo("HOME情報更新", "更新が完了しました")
        else:
            messagebox.showerror(
                "HOME情報更新", f"更新中にエラーが発生しました\n{(error or '')[:300]}"
            )

    def show_last_update_date(self):
        try:
            with open(self._LAST_UPDATE_FILE, encoding="utf-8") as f:
                date = f.read().strip()
            messagebox.showinfo("HOME情報更新日", f"最終更新日: {date}")
        except FileNotFoundError:
            messagebox.showinfo("HOME情報更新日", "まだ更新されていません")

    def update_battle_data(self):
        try:
            local_date = open(self._LAST_BATTLE_UPDATE_FILE, encoding="utf-8").read().strip()
        except FileNotFoundError:
            local_date = ""

        progress_win = tkinter.Toplevel(self)
        progress_win.title("構築記事取得中...")
        progress_win.resizable(False, False)
        progress_win.grab_set()
        progress_label = tkinter.Label(
            progress_win, text="準備中...", padx=30, pady=10, width=36, justify="center",
        )
        progress_label.pack()
        bar = ttk.Progressbar(progress_win, length=300, mode="indeterminate")
        bar.pack(padx=30, pady=(0, 20))
        bar.start(15)

        def _update(text: str):
            self.after(0, lambda t=text: progress_label.config(text=t))

        def _run():
            err_msg = None
            remote_date = None
            try:
                remote_date = self._fetch_text(f"{self._STATS_BASE_URL}/last_update_battle.txt").strip()
                if remote_date == local_date:
                    self.after(0, progress_win.destroy)
                    self.after(0, lambda: messagebox.showinfo("構築記事取得", "最新データです"))
                    return
                self._download_stats_files(self._BATTLE_FILES, _update)
            except Exception as e:
                err_msg = str(e)
            finally:
                self.after(0, progress_win.destroy)
            if err_msg is None:
                self.after(0, lambda d=remote_date: self._on_battle_update_done(True, None, d))
            else:
                self.after(0, lambda e=err_msg: self._on_battle_update_done(False, e, None))

        threading.Thread(target=_run, daemon=True).start()

    def _on_battle_update_done(self, success: bool, error: str | None, remote_date: str | None):
        if success:
            with open(self._LAST_BATTLE_UPDATE_FILE, "w", encoding="utf-8") as f:
                f.write(remote_date)
            messagebox.showinfo("構築記事取得", "更新が完了しました")
        else:
            messagebox.showerror(
                "構築記事取得", f"更新中にエラーが発生しました\n{(error or '')[:300]}"
            )

    def show_last_battle_update_date(self):
        try:
            with open(self._LAST_BATTLE_UPDATE_FILE, encoding="utf-8") as f:
                date = f.read().strip()
            messagebox.showinfo("構築記事取得日", f"最終更新日: {date}")
        except FileNotFoundError:
            messagebox.showinfo("構築記事取得日", "まだ更新されていません")

    # アップデート確認
    def _get_current_version(self) -> str:
        try:
            with open(self._VERSION_FILE, encoding="utf-8") as f:
                return f.read().strip()
        except FileNotFoundError:
            return "0.0.0"

    @staticmethod
    def _parse_version(v: str) -> tuple:
        try:
            return tuple(int(x) for x in v.lstrip("v").split("."))
        except ValueError:
            return (0, 0, 0)

    def check_update(self):
        import json as _json
        import urllib.request

        current = self._get_current_version()
        api_url = f"https://api.github.com/repos/{self._RELEASES_REPO}/releases/latest"
        _headers = {
            "User-Agent": "champedge-updater/1.0",
            "Authorization": f"token {self._RELEASE_TOKEN}",
        }

        try:
            req = urllib.request.Request(api_url, headers=_headers)
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = _json.loads(resp.read().decode("utf-8"))
        except Exception as e:
            messagebox.showerror(
                "アップデート確認", f"確認中にエラーが発生しました\n{e}"
            )
            return

        latest = data["tag_name"].lstrip("v")

        if self._parse_version(latest) <= self._parse_version(current):
            messagebox.showinfo("アップデート確認", f"最新バージョンです（v{current}）")
            return

        assets = [
            a
            for a in data.get("assets", [])
            if a["name"] == "champedge_forwin_update.zip"
        ]
        if not assets:
            messagebox.showerror(
                "アップデート確認", "ダウンロードファイルが見つかりませんでした"
            )
            return

        if not messagebox.askyesno(
            "アップデート確認",
            f"新しいバージョンがあります\n\n現在: v{current}  →  最新: v{latest}\n\n"
            "アップデートしますか？\n（パーティやDBのデータは保持されます）",
        ):
            return

        self._apply_update(assets[0]["id"])

    def _apply_update(self, asset_id: int):
        import urllib.request

        if not getattr(sys, "frozen", False):
            messagebox.showinfo("アップデート", "開発環境ではアップデートできません")
            return

        app_dir = os.path.dirname(sys.executable)
        zip_path = os.path.join(app_dir, "_champedge_update.zip")
        bat_path = os.path.join(app_dir, "_update.bat")

        progress_win = tkinter.Toplevel(self)
        progress_win.title("アップデート")
        progress_win.resizable(False, False)
        progress_win.grab_set()
        progress_label = tkinter.Label(
            progress_win,
            text="ダウンロード中... 0.0 MB",
            padx=30,
            pady=20,
            wraplength=320,
            justify="center",
        )
        progress_label.pack()

        def _update_label(text: str):
            progress_label.config(text=text)

        def _run():
            try:
                asset_url = f"https://api.github.com/repos/{self._RELEASES_REPO}/releases/assets/{asset_id}"
                req = urllib.request.Request(
                    asset_url,
                    headers={
                        "User-Agent": "champedge-updater/1.0",
                        "Authorization": f"token {self._RELEASE_TOKEN}",
                        "Accept": "application/octet-stream",
                    },
                )
                downloaded = 0
                with urllib.request.urlopen(req) as resp:
                    total = int(resp.headers.get("Content-Length", 0))
                    with open(zip_path, "wb") as f:
                        while chunk := resp.read(65536):
                            f.write(chunk)
                            downloaded += len(chunk)
                            mb = downloaded / 1024 / 1024
                            if total:
                                total_mb = total / 1024 / 1024
                                self.after(
                                    0,
                                    lambda m=mb, t=total_mb: _update_label(
                                        f"ダウンロード中... {m:.1f} / {t:.1f} MB"
                                    ),
                                )
                            else:
                                self.after(
                                    0,
                                    lambda m=mb: _update_label(
                                        f"ダウンロード中... {m:.1f} MB"
                                    ),
                                )

                bat = (
                    "@echo off\n"
                    'cd /d "%~dp0"\n'
                    ":wait_loop\n"
                    'tasklist /FI "IMAGENAME eq champedge.exe" 2>NUL | find /I "champedge.exe" >NUL\n'
                    "if not errorlevel 1 (\n"
                    "    timeout /t 1 /nobreak > nul\n"
                    "    goto wait_loop\n"
                    ")\n"
                    "timeout /t 1 /nobreak > nul\n"
                    "powershell -Command "
                    "\"Expand-Archive -LiteralPath '_champedge_update.zip' "
                    "-DestinationPath '.' -Force\"\n"
                    "del _champedge_update.zip\n"
                    'start "" "%~dp0champedge.exe"\n'
                    'del "%~f0"\n'
                )
                with open(bat_path, "w", encoding="ascii") as f:
                    f.write(bat)

                self.after(
                    0,
                    lambda: _update_label(
                        "ダウンロード完了！\n\n"
                        "インストール中です...\n"
                        "完了後、自動でアプリが起動します。"
                    ),
                )
                self.after(4000, lambda: self._launch_updater(bat_path))
            except Exception as e:
                err = str(e)
                self.after(
                    0,
                    lambda: (
                        progress_win.destroy(),
                        messagebox.showerror(
                            "アップデート", f"ダウンロードエラー\n{err}"
                        ),
                    ),
                )

        threading.Thread(target=_run, daemon=True).start()

    def _launch_updater(self, bat_path: str):
        import subprocess

        subprocess.Popen(
            ["cmd.exe", "/c", bat_path],
            creationflags=subprocess.CREATE_NEW_CONSOLE,
            close_fds=True,
        )
        os._exit(0)

    # フォーム選択画面
    def form_select(self, no: int):
        dialog = FormSelect()
        dialog.set_pokemon(no)
        dialog.open(location=(self.winfo_x(), self.winfo_y()))
        self.wait_window(dialog)
        return dialog.form_num

    # 個体管理画面
    def open_box(self):
        dialog = BoxDialog()
        dialog.open(location=(self.winfo_x(), self.winfo_y()))

    # 対戦履歴画面
    def open_records(self):
        dialog = record.Record()
        dialog.open()

    # 対戦分析画面
    def open_analytics(self):
        dialog = analytics.Analytics()
        dialog.open()

    def on_change_transport(self, event):
        # -transparentcolor は Windows 専用の Tk 属性
        if sys.platform != "win32":
            return
        # ウィンドウが最大化されたかどうかをチェック
        if self.winfo_width() >= 1200:
            self.attributes("-transparentcolor", "gray97")
        else:
            self.attributes("-transparentcolor", "")
