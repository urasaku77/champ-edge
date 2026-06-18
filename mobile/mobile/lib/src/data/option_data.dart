import '../model/battle_pokemon.dart';
import '../service/damage_engine.dart';

/// 実行時に使う持ち物候補。DB 接続後に `item_data` 全件で差し替えられる。
/// 未接続時はフォールバックの [itemOptions] を使う。
List<String> loadedItemOptions = List.of(itemOptions);

/// 持ち物候補（フォールバック用）。DB 接続時は item_data 全件に差し替わる。
const List<String> itemOptions = [
  'なし',
  'いのちのたま',
  'こだわりハチマキ',
  'こだわりメガネ',
  'こだわりスカーフ',
  'とつげきチョッキ',
  'たべのこし',
  'たつじんのおび',
  'オボンのみ',
  'しんかのきせき',
  'ちからのハチマキ',
  'ものしりメガネ',
  'もくたん',
  'しんぴのしずく',
  'とけないこおり',
  'くろおび',
  'シルクのスカーフ',
  'ブーストエナジー',
  'きあいのタスキ',
  'ゴツゴツメット',
];

const _m = BattleMove.new;

/// 技候補プール（差し替え用）。本来は `waza_data` テーブルから引く。
final List<BattleMove> moveDex = [
  // ノーマル
  _m(name: 'しんそく', type: PokeType.normal, category: MoveCategory.physical, power: 80),
  _m(name: 'のしかかり', type: PokeType.normal, category: MoveCategory.physical, power: 85),
  _m(name: 'からげんき', type: PokeType.normal, category: MoveCategory.physical, power: 70),
  _m(name: 'ハイパーボイス', type: PokeType.normal, category: MoveCategory.special, power: 90),
  // ほのお
  _m(name: 'だいもんじ', type: PokeType.fire, category: MoveCategory.special, power: 110),
  _m(name: 'かえんほうしゃ', type: PokeType.fire, category: MoveCategory.special, power: 90),
  _m(name: 'フレアドライブ', type: PokeType.fire, category: MoveCategory.physical, power: 120),
  // みず
  _m(name: 'なみのり', type: PokeType.water, category: MoveCategory.special, power: 90),
  _m(name: 'ハイドロポンプ', type: PokeType.water, category: MoveCategory.special, power: 110),
  _m(name: 'たきのぼり', type: PokeType.water, category: MoveCategory.physical, power: 80),
  // でんき
  _m(name: '10まんボルト', type: PokeType.electric, category: MoveCategory.special, power: 90),
  _m(name: 'かみなり', type: PokeType.electric, category: MoveCategory.special, power: 110),
  // くさ
  _m(name: 'エナジーボール', type: PokeType.grass, category: MoveCategory.special, power: 90),
  _m(name: 'ギガドレイン', type: PokeType.grass, category: MoveCategory.special, power: 75),
  _m(name: 'ソーラービーム', type: PokeType.grass, category: MoveCategory.special, power: 120),
  // こおり
  _m(name: 'れいとうビーム', type: PokeType.ice, category: MoveCategory.special, power: 90),
  _m(name: 'つららおとし', type: PokeType.ice, category: MoveCategory.physical, power: 85),
  _m(name: 'こおりのキバ', type: PokeType.ice, category: MoveCategory.physical, power: 65),
  // かくとう
  _m(name: 'インファイト', type: PokeType.fighting, category: MoveCategory.physical, power: 120),
  _m(name: 'ボディプレス', type: PokeType.fighting, category: MoveCategory.physical, power: 80),
  _m(name: 'きあいだま', type: PokeType.fighting, category: MoveCategory.special, power: 120),
  // どく
  _m(name: 'ヘドロばくだん', type: PokeType.poison, category: MoveCategory.special, power: 90),
  _m(name: 'どくづき', type: PokeType.poison, category: MoveCategory.physical, power: 80),
  // じめん
  _m(name: 'じしん', type: PokeType.ground, category: MoveCategory.physical, power: 100),
  _m(name: 'だいちのちから', type: PokeType.ground, category: MoveCategory.special, power: 90),
  // ひこう
  _m(name: 'ブレイブバード', type: PokeType.flying, category: MoveCategory.physical, power: 120),
  _m(name: 'エアスラッシュ', type: PokeType.flying, category: MoveCategory.special, power: 75),
  // エスパー
  _m(name: 'サイコキネシス', type: PokeType.psychic, category: MoveCategory.special, power: 90),
  _m(name: 'サイコショック', type: PokeType.psychic, category: MoveCategory.special, power: 80),
  // むし
  _m(name: 'とんぼがえり', type: PokeType.bug, category: MoveCategory.physical, power: 70),
  _m(name: 'むしのさざめき', type: PokeType.bug, category: MoveCategory.special, power: 90),
  // いわ
  _m(name: 'ストーンエッジ', type: PokeType.rock, category: MoveCategory.physical, power: 100),
  _m(name: 'いわなだれ', type: PokeType.rock, category: MoveCategory.physical, power: 75),
  // ゴースト
  _m(name: 'シャドーボール', type: PokeType.ghost, category: MoveCategory.special, power: 80),
  _m(name: 'シャドークロー', type: PokeType.ghost, category: MoveCategory.physical, power: 70),
  // ドラゴン
  _m(name: 'げきりん', type: PokeType.dragon, category: MoveCategory.physical, power: 120),
  _m(name: 'りゅうのはどう', type: PokeType.dragon, category: MoveCategory.special, power: 85),
  // あく
  _m(name: 'かみくだく', type: PokeType.dark, category: MoveCategory.physical, power: 80),
  _m(name: 'はたきおとす', type: PokeType.dark, category: MoveCategory.physical, power: 65),
  // はがね
  _m(name: 'アイアンヘッド', type: PokeType.steel, category: MoveCategory.physical, power: 80),
  _m(name: 'ラスターカノン', type: PokeType.steel, category: MoveCategory.special, power: 80),
  // フェアリー
  _m(name: 'ムーンフォース', type: PokeType.fairy, category: MoveCategory.special, power: 95),
  _m(name: 'じゃれつく', type: PokeType.fairy, category: MoveCategory.physical, power: 90),
];
