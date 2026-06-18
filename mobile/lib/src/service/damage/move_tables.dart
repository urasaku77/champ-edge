/// 旧 `calc.py` の `# region 特定の技や特性などの定義` をそのまま移植した定数群。
/// 値・順序は Python 版と一致させている。
library;

import 'poke_types.dart';

/// スキン系特性 → 変換先タイプ。
const Map<String, PokeType> skinAbilities = {
  'エレキスキン': PokeType.electric,
  'スカイスキン': PokeType.flying,
  'フェアリースキン': PokeType.fairy,
  'フリーズスキン': PokeType.ice,
  'ドラゴンスキン': PokeType.dragon,
};

/// タイプ強化系の特性 → 対象タイプ。
const Map<String, PokeType> typeBuffAbilities = {
  'しんりょく': PokeType.grass,
  'もうか': PokeType.fire,
  'もらいび': PokeType.fire,
  'げきりゅう': PokeType.water,
  'むしのしらせ': PokeType.bug,
  'いわはこび': PokeType.rock,
  'はがねつかい': PokeType.steel,
  'トランジスタ': PokeType.electric,
  'りゅうのあぎと': PokeType.dragon,
};

/// パンチ技（てつのこぶし等）。
const Set<String> punchMoves = {
  'アイスハンマー', 'アームハンマー', 'かみなりパンチ', 'きあいパンチ', 'グロウパンチ',
  'コメットパンチ', 'シャドーパンチ', 'スカイアッパー', 'ドレインパンチ', 'ばくれつパンチ',
  'バレットパンチ', 'ピヨピヨパンチ', 'プラズマフィスト', 'ほのおのパンチ', 'マッハパンチ',
  'メガトンパンチ', 'れいとうパンチ', 'れんぞくパンチ', 'ダブルパンツァー', 'あんこくきょうだ',
  'すいりゅうれんだ', 'ぶちかまし', 'ジェットパンチ', 'ふんどのこぶし',
};

/// 反動技（すてみ）。
const Set<String> recoilMoves = {
  'アフロブレイク', 'ウッドハンマー', 'じごくぐるま', 'すてみタックル', 'とっしん',
  'とびげり', 'とびひざげり', 'もろはのずつき', 'フレアドライブ', 'ブレイブバード',
  'ボルテッカー', 'ワイルドボルト', 'ウェーブタックル',
};

/// 音技（パンクロック等）。
const Set<String> soundMoves = {
  'いにしえのうた', 'いびき', 'うたかたのアリア', 'エコーボイス', 'さわぐ',
  'スケイルノイズ', 'チャームボイス', 'バークアウト', 'ハイパーボイス', 'ばくおんぱ',
  'むしのさざめき', 'りんしょう', 'オーバードライブ', 'ぶきみなじゅもん', 'フレアソング',
  'サイコノイズ', 'みわくのボイス',
};

/// キバ技（がんじょうあご）。
const Set<String> fangMoves = {
  'かみつく', 'かみくだく', 'ひっさつまえば', 'ほのおのキバ', 'かみなりのキバ',
  'こおりのキバ', 'どくどくのキバ', 'サイコファング', 'エラがみ', 'くらいつく',
};

/// 波動技（メガランチャー）。
const Set<String> blastMoves = {
  'あくのはどう', 'はどうだん', 'みずのはどう', 'りゅうのはどう', 'だいちのはどう',
  'こんげんのはどう',
};

/// 切る技（きれあじ）。
const Set<String> slashMoves = {
  'アクアカッター', 'いあいぎり', 'エアカッター', 'エアスラッシュ', 'がんせきアックス',
  'きょじゅうざん', 'きりさく', 'クロスポイズン', 'サイコカッター', 'サイコブレイド',
  'シェルブレード', 'シザークロス', 'しんぴのつるぎ', 'せいなるつるぎ', 'ソーラーブレード',
  'つじぎり', 'つばめがえし', 'ドゲザン', 'ネズミざん', 'はっぱカッター',
  'ひけん・ちえなみ', 'むねんのつるぎ', 'リーフブレード',
};

/// トレースできない特性。
const Set<String> unTraceAbilities = {
  'フラワーベール', 'イリュージョン', 'かわりもの', 'ぜったいねむり', 'ばけのかわ',
  'レシーバー', 'アイスフェイス',
};

/// タイプ強化アイテム → 対象タイプ。
const Map<String, PokeType> typeBuffItems = {
  'シルクのスカーフ': PokeType.normal, 'もくたん': PokeType.fire, 'しんぴのしずく': PokeType.water,
  'じしゃく': PokeType.electric, 'きせきのタネ': PokeType.grass, 'とけないこおり': PokeType.ice,
  'くろおび': PokeType.fighting, 'どくバリ': PokeType.poison, 'やわからいすな': PokeType.ground,
  'するどいくちばし': PokeType.flying, 'まがったスプーン': PokeType.psychic, 'ぎんのこな': PokeType.bug,
  'かたいいし': PokeType.rock, 'のろいのおふだ': PokeType.ghost, 'りゅうのキバ': PokeType.dragon,
  'くろいメガネ': PokeType.dark, 'メタルコード': PokeType.steel, 'せいれいプレート': PokeType.fairy,
  'うしおのおこう': PokeType.water, 'さざなみのおこう': PokeType.water, 'おはなのおこう': PokeType.grass,
  'がんせきおこう': PokeType.rock, 'あやしいおこう': PokeType.psychic, 'ようせいのハネ': PokeType.fairy,
  'ひのたまプレート': PokeType.fire, 'しずくプレート': PokeType.water, 'いかずちプレート': PokeType.electric,
  'みどりのプレート': PokeType.grass, 'つららのプレート': PokeType.ice, 'こぶしのプレート': PokeType.fighting,
  'もうどくプレート': PokeType.poison, 'だいちのプレート': PokeType.ground, 'あおぞらプレート': PokeType.flying,
  'ふしぎのプレート': PokeType.psychic, 'たまむしプレート': PokeType.bug, 'がんせきプレート': PokeType.rock,
  'もののけプレート': PokeType.ghost, 'りゅうのプレート': PokeType.dragon, 'こわもてプレート': PokeType.dark,
  'こうてつプレート': PokeType.steel,
};

/// 半減きのみ → 対象タイプ。
const Map<String, PokeType> typeDebuffItems = {
  'ホズのみ': PokeType.normal, 'オッカのみ': PokeType.fire, 'イトケのみ': PokeType.water,
  'ソクノのみ': PokeType.electric, 'リンドのみ': PokeType.grass, 'ヤチェのみ': PokeType.ice,
  'ヨプのみ': PokeType.fighting, 'ビアーのみ': PokeType.poison, 'シュカのみ': PokeType.ground,
  'バコウのみ': PokeType.flying, 'ウタンのみ': PokeType.psychic, 'タンガのみ': PokeType.bug,
  'ヨロギのみ': PokeType.rock, 'カシブのみ': PokeType.ghost, 'ハバンのみ': PokeType.dragon,
  'ナモのみ': PokeType.dark, 'リリバのみ': PokeType.steel, 'ロゼルのみ': PokeType.fairy,
};

/// そうだいしょう倍率（×4096 表現）。
const Map<String, int> soudaisyouValues = {
  '1.0': 4096, '1.1': 4506, '1.2': 4915, '1.3': 5325, '1.4': 5734, '1.5': 6144,
};

/// とうそうしん倍率（×4096 表現）。
const Map<String, int> tousoushinValues = {
  '1.0': 4096, '1.25': 5120, '0.75': 3072,
};

/// けたぐり・くさむすび用 (重さ閾値, 威力)。
const List<List<int>> damagesAtWeight = [
  [10, 20], [25, 40], [50, 60], [100, 80], [200, 100],
];

/// かたやぶり系（防御特性を無視する特性）。
const Set<String> moldBreakerAbilities = {
  'かたやぶり', 'テラボルテージ', 'ターボブレイズ', 'かがくへんかガス',
};
