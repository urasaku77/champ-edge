# パーティ管理とボックス（個別ポケモン保管庫）

## Why

旧 champ-edge の PartyEditor（`party/csv/{番号}-{連番}_{タイトル}.csv` ＋ パーティメモ）に相当する
保存パーティの管理がモバイル未実装だった。ドロワーの「パーティ編集」「ボックス編集」を実体化する。
ユーザー確定：保存単位は 番号/連番/タイトル＋パーティメモ＋**ポケモン個別メモ**、ボックスは
**個別ポケモンの保管庫**、6体は **D&D 並べ替え**。

## What Changes

- 新 capability **party-management** を追加（原典 PartyEditor の「作る→使う」を踏襲）：
  - **パーティ編集**：作った構築の一覧（既定＝登録日降順・番号順に並び替え可）→ 選択して詳細編集
    （番号/連番/タイトル/パーティメモ・6体の D&D 並べ替え）→ ポケモンを選んで個別フル編集
    （種族は Top と同じ検索窓・性格/持ち物/特性/努力値/技4/個別メモ）→「使用」で自分パーティ（Top）へ反映。
    新規作成あり。「現在の Top パーティを保存」方式は採らない。
  - **ボックス画面**：個別ポケモンを技・努力値まで編集（パーティの個体と同等）。履歴と同じ縦スクロール一覧。
    「配置」で自分パーティの空き枠（無ければ選択枠）へ入れる。
- `BattlePokemon` に `memo` フィールドを追加（JSON 永続化）。
- `PartyStore` を拡張：保存パーティ（番号/連番/タイトル/メモ＋6体）とボックス（個別ポケモン）の CRUD。

## Impact

- New spec: party-management
- Affected code: model/battle_pokemon.dart（memo）, data/party_store.dart（SavedParty・savePartyEntry・
  listSavedParties・deletePartyEntry・listBox・saveBoxPokemon・deleteBoxPokemon）,
  screens/party_manager_screen.dart（新規）, screens/box_screen.dart（新規）, screens/home_screen.dart（導線・呼出反映）。
- 旧形式 `{title, pokemons}` の保存ファイルも読み込み互換。
