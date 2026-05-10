from component.app import MainApp
from pokedata.calc import DamageCalc
from pokedata.const import Ailments, Fields, Types, Walls, Weathers
from pokedata.loader import get_top_home_doryoku
from pokedata.pokemon import Pokemon
from pokedata.stats import Stats, StatsKey
from pokedata.waza import WazaBase
from recog.recog import get_recog_value


class Stage:
    def __init__(self, app: MainApp):
        self._app = app
        self._weather: Weathers = Weathers.なし
        self._field: Fields = Fields.なし
        self._app.set_stage(self)
        self.double_params: dict[str, bool] = {
            "is_wazawai_a": False,
            "is_wazawai_b": False,
            "is_wazawai_c": False,
            "is_wazawai_d": False,
            "is_overall": True,
            "is_tedasuke": False,
            "is_friend_guard": True,
        }

    def get_party(self, index: int) -> list[Pokemon]:
        return self._app.party_frames[index].pokemon_list

    def set_party(self, index: int, party: list[Pokemon]):
        self._app.party_frames[index].set_party(party)

    def get_active_pokemons(self):
        return [
            self._app.active_poke_frames[0]._pokemon,
            self._app.active_poke_frames[1]._pokemon,
        ]

    def set_active_pokemon_from_index(self, player: int, index: int):
        if not self._app.party_frames[player].pokemon_list[index].form_selected:
            form = self._app.form_select(
                self._app.party_frames[player].pokemon_list[index].no
            )
            if form != -1:
                self._app.party_frames[player].pokemon_list[index] = Pokemon.by_pid(
                    str(self._app.party_frames[player].pokemon_list[index].no)
                    + "-"
                    + str(form),
                    True,
                )

        if self._app.party_frames[player].pokemon_list[index].form_selected:
            self.pokemon = self._app.party_frames[player].pokemon_list[index]
            self.pokemon.on_stage()
            if self.pokemon.is_empty is False:
                self.set_active_pokemon(player, self.pokemon)
                self.calc_damage()

    def set_active_pokemon(self, player: int, pokemon: Pokemon):
        self._app.set_active_pokemon(player=player, pokemon=pokemon)

        if get_recog_value("active_chosen_auto") and player == 1:
            self.set_chosen(1)

        self._app.after_appear(pokemon, player)

    def on_activepokemon_statechanged(self):
        pass

    # 表示ポケモンへの各種値セット
    def set_value_to_active_pokemon(
        self,
        player: int,
        seikaku: str = None,
        doryoku_text: str = None,
        doryoku_number: Stats = None,
        kotai: Stats = None,
        rank: Stats = None,
        item: str = None,
        ability: str = None,
        ability_value: str = None,
        wall: Walls = None,
        terastype: Types = None,
        waza: tuple[int, str] = None,
        waza_effect: int = None,
        critical: bool = None,
        ailment: Ailments = None,
        charging: bool = None,
        is_same: bool = False,
    ):
        pokemon = self._app.active_poke_frames[player]._pokemon
        if seikaku is not None:
            if is_same and pokemon.seikaku == seikaku:
                pokemon.seikaku = "まじめ"
            else:
                pokemon.seikaku = seikaku
            if player == 1 and get_recog_value("doryoku_reset_auto"):
                doryoku_text_from_home = get_top_home_doryoku(pokemon.name)
                pokemon.doryoku.init_values(0)
                if doryoku_text_from_home is not None:
                    pokemon.doryoku.set_values_from_string(doryoku_text_from_home)
            self._app.set_active_pokemon(player, pokemon)
        if doryoku_text is not None:
            new_doryoku = Stats()
            new_doryoku.set_values_from_string(doryoku_text)
            if is_same and all(
                pokemon.doryoku[k] == new_doryoku[k] for k in StatsKey
            ):
                pokemon.doryoku.init_values(0)
            else:
                pokemon.doryoku.init_values(0)
                pokemon.doryoku.set_values_from_string(doryoku_text)
            self._app.set_active_pokemon(player, pokemon)
        if doryoku_number is not None:
            pokemon.doryoku.init_values(0)
            pokemon.doryoku.set_values_from_stats(doryoku_number)
            self._app.set_active_pokemon(player, pokemon)
        if kotai is not None:
            pokemon.kotai.set_values_from_stats(kotai)
            self._app.set_active_pokemon(player, pokemon)
        if rank is not None:
            pokemon.rank.set_values_from_stats(rank)
            self._app.set_active_pokemon(player, pokemon)
        if item is not None:
            if is_same and pokemon.item == item:
                pokemon.item = ""
            else:
                pokemon.item = item
            self._app.set_active_pokemon(player, pokemon)
        if ability is not None:
            if is_same and pokemon.ability == ability:
                pokemon.ability = ""
            else:
                pokemon.ability = ability
            self._app.set_active_pokemon(player, pokemon)
        if ability_value is not None:
            pokemon.ability_value = ability_value
        if wall is not None:
            pokemon.wall = wall
        if terastype is not None:
            if is_same and pokemon.battle_terastype == terastype:
                pokemon.battle_terastype = Types.なし
            else:
                pokemon.battle_terastype = terastype
            self._app.set_active_pokemon(player, pokemon)
        if waza is not None:
            pokemon.set_waza(waza_name=waza[1], index=waza[0])
            self._app.set_active_pokemon(player, pokemon)
        if waza_effect is not None:
            wazabase = pokemon.waza_list[waza_effect]
            self.set_waza_effect(player, wazabase)
        if ailment is not None:
            pokemon.ailment = ailment
        if critical is not None:
            for w in pokemon.waza_list:
                if w is not None:
                    w.critical = critical
        if charging is not None:
            pokemon.charging = charging

        self.calc_damage()

    # 天気の変更
    def change_weather(self, weather: str):
        for w in Weathers:
            if w.name == weather:
                self._weather = w
        self.calc_damage()

    # フィールドの変更
    def change_field(self, field: str):
        for f in Fields:
            if f.name == field:
                self._field = f
        self.calc_damage()

    # ダブルバトルのパラメータ変更
    def change_double_params(
        self,
        is_wazawai_a: bool = None,
        is_wazawai_b: bool = None,
        is_wazawai_c: bool = None,
        is_wazawai_d: bool = None,
        is_overall: bool = None,
        is_tedasuke: bool = None,
        is_friend_guard: bool = None,
    ):
        if is_wazawai_a is not None:
            self.double_params["is_wazawai_a"] = is_wazawai_a
        if is_wazawai_b is not None:
            self.double_params["is_wazawai_b"] = is_wazawai_b
        if is_wazawai_c is not None:
            self.double_params["is_wazawai_c"] = is_wazawai_c
        if is_wazawai_d is not None:
            self.double_params["is_wazawai_d"] = is_wazawai_d
        if is_overall is not None:
            self.double_params["is_overall"] = is_overall
        if is_tedasuke is not None:
            self.double_params["is_tedasuke"] = is_tedasuke
        if is_friend_guard is not None:
            self.double_params["is_friend_guard"] = is_friend_guard
        self.calc_damage()

    # 戦闘時テラスタイプ変更
    def select_terastype(self, player: int):
        pokemon = self._app.active_poke_frames[player]._pokemon
        if pokemon.is_empty:
            return
        # 自分かつテラスタイプの設定がある場合
        if player == 0 and pokemon.terastype != Types.なし:
            if pokemon.battle_terastype == Types.なし:
                pokemon.battle_terastype = pokemon.terastype
            else:
                pokemon.battle_terastype = Types.なし
        # それ以外の場合、ダイアログ表示で選択する
        else:
            types: Types = self._app.select_type(player=player)
            if types is None:
                return
            pokemon.battle_terastype = types
        # 表示の更新、ダメージ計算の再実行
        self._app.set_active_pokemon(player, pokemon)
        self.calc_damage()

    # 技追加効果の分岐処理
    def set_waza_effect(self, player: int, wazabase: WazaBase):
        non_player = 0 if player == 1 else 1
        if wazabase is not None:
            if wazabase.has_value_list:
                wazabase.set_next_value()
            if wazabase.is_self_buff or wazabase.is_self_debuff:
                if wazabase.name == "はらだいこ":
                    self._app.active_poke_frames[
                        player
                    ]._pokemon.rank.set_values_from_string(wazabase.value)
                else:
                    self._app.active_poke_frames[
                        player
                    ]._pokemon.rank.add_ranks_from_string(
                        wazabase.value,
                        self._app.active_poke_frames[player]._pokemon.ability
                        == "あまのじゃく",
                    )
            elif wazabase.is_opponent_buff or wazabase.is_opponent_debuff:
                self._app.active_poke_frames[
                    non_player
                ]._pokemon.rank.add_ranks_from_string(
                    wazabase.value,
                    self._app.active_poke_frames[player]._pokemon.ability
                    == "あまのじゃく",
                )
            elif wazabase.name == "じこあんじ":
                self._app.active_poke_frames[
                    0
                ]._pokemon.rank = self._app.active_poke_frames[1]._pokemon.rank
            elif wazabase.name == "スキルスワップ":
                (
                    self._app.active_poke_frames[0]._pokemon.ability,
                    self._app.active_poke_frames[1]._pokemon.ability,
                ) = (
                    self._app.active_poke_frames[1]._pokemon.ability,
                    self._app.active_poke_frames[0]._pokemon.ability,
                )
            elif wazabase.name == "コートチェンジ":
                (
                    self._app.active_poke_frames[0]._pokemon.wall,
                    self._app.active_poke_frames[1]._pokemon.wall,
                ) = (
                    self._app.active_poke_frames[1]._pokemon.wall,
                    self._app.active_poke_frames[0]._pokemon.wall,
                )
            for i in range(2):
                self._app.set_active_pokemon(
                    i, self._app.active_poke_frames[i]._pokemon
                )

    def _reset_trace(self, pokemon1: Pokemon, pokemon2: Pokemon):
        if pokemon1.base_ability == "トレース":
            pokemon1.apply_trace("トレース")
        if pokemon2.base_ability == "トレース":
            pokemon2.apply_trace("トレース")

    def _update_trace_display(self, pokemon1: Pokemon, pokemon2: Pokemon):
        for i, poke in enumerate([pokemon1, pokemon2]):
            if poke.base_ability == "トレース":
                self._app.active_poke_frames[i].update_ability_display()

    # ダメージ計算
    def calc_damage(self):
        pokemon1 = self._app.active_poke_frames[0]._pokemon
        pokemon2 = self._app.active_poke_frames[1]._pokemon
        if pokemon1.is_empty or pokemon2.is_empty:
            return
        if get_recog_value("rule") == 2:
            self._reset_trace(pokemon1, pokemon2)
            calc_result = DamageCalc.get_all_damages(
                pokemon1, pokemon2, self._weather, self._field, self.double_params
            )
            self._app.set_calc_results(0, calc_result)

            self._reset_trace(pokemon1, pokemon2)
            calc_result = DamageCalc.get_all_damages(
                pokemon2, pokemon1, self._weather, self._field, self.double_params
            )
            self._app.set_calc_results(1, calc_result)
        else:
            self._reset_trace(pokemon1, pokemon2)
            calc_result = DamageCalc.get_all_damages(
                pokemon1, pokemon2, self._weather, self._field
            )
            self._app.set_calc_results(0, calc_result)

            self._reset_trace(pokemon1, pokemon2)
            calc_result = DamageCalc.get_all_damages(
                pokemon2, pokemon1, self._weather, self._field
            )
            self._app.set_calc_results(1, calc_result)

        self._update_trace_display(pokemon1, pokemon2)

    # パーティ編集
    def edit_party(self, player: int):
        party = self._app.edit_party(party=self._app.party_frames[player].pokemon_list)
        self._app.set_party(player=player, party=party)

    # パーティの読み込み
    def load_party(self, player: int, party: list[Pokemon] = None):
        from pokedata.loader import get_party_data

        if party is None:
            party = []
        if len(party) == 0:
            for _i, data in enumerate(get_party_data()):
                pokemon: Pokemon = Pokemon.by_name(data[0])
                pokemon.set_load_data(data, True)
                party.append(pokemon)
        self._app.set_party(player=player, party=party)

    # パーティのクリア
    def clear_party(self, player: int):
        party = [Pokemon()] * 6
        self._app.set_party(player=player, party=party)

    # 選出の登録
    def set_chosen(self, player: int, index: list[int] = None):
        if index is None:
            index = []
        if len(index) == 0:
            index_list = [
                i
                for i, p in enumerate(self._app.chosen_frames[player].pokemon_list)
                if p.is_empty
            ]
            if (
                len(index_list) != 0
                and len(
                    list(
                        filter(
                            lambda p: p.name
                            == self._app.active_poke_frames[player]._pokemon.name,
                            self._app.chosen_frames[player].pokemon_list,
                        )
                    )
                )
                == 0
            ):
                self._app.set_chosen(
                    player, self._app.active_poke_frames[player]._pokemon, index_list[0]
                )
                self._app.chosen_frames[player].pokemon_list[
                    index_list[0]
                ] = self._app.active_poke_frames[player]._pokemon
        else:
            for i in range(len(index)):
                pokemon = (
                    self._app.party_frames[player].pokemon_list[index[i]]
                    if index[i] != -1
                    else Pokemon()
                )
                self._app.set_chosen(player, pokemon, i)
                self._app.chosen_frames[player].pokemon_list[i] = pokemon

    # 選出の削除
    def delete_chosen(self, player: int, index: int):
        self._app.chosen_frames[player].pokemon_list[index] = Pokemon()
        self._app.set_chosen(player, Pokemon, index)

    # 選出のクリア
    def clear_chosen(self, player: int):
        for i in range(len(self._app.chosen_frames[player].pokemon_list)):
            self.delete_chosen(player, i)

    # 自分一番手のポケモンを探す
    def search_first_chosen(self):
        if self._app.chosen_frames[0].pokemon_list[0].no != -1:
            for i, pokemon in enumerate(self._app.party_frames[0].pokemon_list):
                if self._app.chosen_frames[0].pokemon_list[0].no == pokemon.no:
                    return i
        return -1

    # バトルの記録
    def record_battle(self):
        self._app.record_battle()

    # バトルのクリア
    def clear_battle(self):
        self._app.clear_battle()

    # 画像認識ループ制御
    def loop_image_recognize(self):
        self._app.image_recognize()

    # 選出の基本情報表示
    def set_info(self, player: int):
        if self._app.active_poke_frames[player]._pokemon.form != -1:
            self._app.set_info(player, self._app.active_poke_frames[player]._pokemon)

    @property
    def weather(self) -> Weathers:
        return self._weather

    @weather.setter
    def weather(self, value):
        self._weather = value

    @property
    def field(self) -> Fields:
        return self._field

    @field.setter
    def field(self, value):
        self._field = value
