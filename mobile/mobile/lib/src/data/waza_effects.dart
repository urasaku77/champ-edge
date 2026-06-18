import '../service/damage_engine.dart';

/// 技の効果メタデータ（旧 champ-edge `pokedata/waza.py` を移植）。
///
/// 技効果ボタンで操作する。種別:
/// - multiHit/addPower/powerHosei : 威力・回数（値リストを循環）
/// - selfRank/opponentRank : ランク変化（自分/相手の boosts に1回分の段階差分を適用、トグル）
/// - typeChange : タイプ変更（みずびたし=相手をみず／もえつきる・でんこうそうげき=自分のタイプ除去、トグル）
enum WazaEffectKind {
  none,
  multiHit,
  addPower,
  powerHosei,
  selfRank,
  opponentRank,
  typeChange,
  // other_effect 系
  copyBoosts, // じこあんじ：相手のランクを自分へコピー
  swapAbility, // スキルスワップ：特性入替
  swapField, // コートチェンジ：壁・定数等を攻守入替
  moveTypeChange, // オーラぐるま：技タイプをあくへ
}

class WazaEffect {
  const WazaEffect(
    this.kind, {
    this.values = const [],
    this.defaultValue = 0,
    this.rankDelta = const [],
    this.changeType = PokeType.none,
    this.removeType = false,
    this.targetOpponent = false,
  });
  final WazaEffectKind kind;

  /// 威力・回数系の選択値。
  final List<num> values;
  final num defaultValue;

  /// ランク系：[H,A,B,C,D,S] の段階差分。
  final List<int> rankDelta;

  /// タイプ変更系：変更後タイプ（removeType=false のとき）／除去対象タイプ（removeType=true）。
  final PokeType changeType;
  final bool removeType;

  /// 対象が相手側か（みずびたし／相手ランク変化）。
  final bool targetOpponent;

  static const none = WazaEffect(WazaEffectKind.none);

  bool get isToggle =>
      kind == WazaEffectKind.selfRank ||
      kind == WazaEffectKind.opponentRank ||
      kind == WazaEffectKind.typeChange ||
      kind == WazaEffectKind.copyBoosts ||
      kind == WazaEffectKind.swapAbility ||
      kind == WazaEffectKind.swapField ||
      kind == WazaEffectKind.moveTypeChange;

  /// 現在値の次の値（威力・回数は循環、トグルは 0↔1）。
  num next(num current) {
    if (isToggle) return current == 0 ? 1 : 0;
    if (values.isEmpty) return current;
    final i = values.indexOf(current);
    return values[(i + 1) % values.length];
  }
}

/// ランク指定文字列（"AS+1" / "ACS+2 BD-1" 等）→ [H,A,B,C,D,S] 段階差分。
List<int> parseRankSpec(String spec) {
  final d = List<int>.filled(6, 0);
  const idx = {'A': 1, 'B': 2, 'C': 3, 'D': 4, 'S': 5};
  for (final group in spec.split(' ')) {
    final m = RegExp(r'^([ABCDS]+)([+-]\d+)$').firstMatch(group.trim());
    if (m == null) continue;
    final n = int.parse(m.group(2)!);
    for (final ch in m.group(1)!.split('')) {
      d[idx[ch]!] = n;
    }
  }
  return d;
}

/// 「A|B|C」形式のキーを個別の技名へ展開した参照表。
final Map<String, WazaEffect> _table = _build();

Map<String, WazaEffect> _build() {
  final m = <String, WazaEffect>{};
  void add(WazaEffectKind kind, String keys, List<num> values, num def) {
    for (final name in keys.split('|')) {
      m[name] = WazaEffect(kind, values: values, defaultValue: def);
    }
  }

  // ランク変化技（self/opponent）。spec は "AS+1" 等。
  void addRank(WazaEffectKind kind, String keys, String spec,
      {bool opponent = false}) {
    final delta = parseRankSpec(spec);
    for (final name in keys.split('|')) {
      m[name] = WazaEffect(kind, rankDelta: delta, targetOpponent: opponent);
    }
  }

  // --- 連続技（回数）---
  add(WazaEffectKind.multiHit,
      'タネマシンガン|ロックブラスト|つららばり|スケイルショット|ミサイルばり',
      const [2, 3, 4, 5], 3);
  add(WazaEffectKind.multiHit, 'ネズミざん',
      const [10, 9, 8, 7, 6, 5, 4, 3, 2, 1], 10);
  add(WazaEffectKind.multiHit, 'ドラゴンアロー|ダブルウイング|タキオンカッター',
      const [1, 2], 2);
  add(WazaEffectKind.multiHit, 'すいりゅうれんだ', const [1, 2, 3], 3);
  add(WazaEffectKind.multiHit, 'トリプルアクセル', const [1, 3, 6], 6);

  // --- 威力増加（倍率）---
  add(WazaEffectKind.addPower, 'ふんどのこぶし',
      const [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0], 1.0);
  add(WazaEffectKind.addPower, 'アクロバット|しっぺがえし', const [1.0, 2.0], 2.0);
  add(WazaEffectKind.addPower, 'おはかまいり', const [1.0, 2.0, 3.0], 3.0);
  add(WazaEffectKind.addPower, 'プレゼント', const [1.0, 2.0, 3.0], 3.0);
  add(WazaEffectKind.addPower, 'はきだす', const [0.0, 1.0, 2.0, 3.0], 3.0);
  add(WazaEffectKind.addPower, 'なげつける',
      const [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0, 13.0], 1.0);
  add(WazaEffectKind.addPower, 'きしかいせい|じたばた',
      const [1.0, 2.0, 4.0, 5.0, 7.5, 10.0], 10.0);
  add(WazaEffectKind.addPower, 'ミストバースト', const [1.0, 1.5], 1.0);
  add(WazaEffectKind.addPower, 'ゆきなだれ', const [1.0, 2.0], 2.0);
  add(WazaEffectKind.addPower, 'ころがる', const [1.0, 2.0, 4.0, 8.0, 16.0], 1.0);
  add(WazaEffectKind.addPower, 'ダメおし', const [1.0, 2.0], 2.0);
  add(WazaEffectKind.addPower,
      'のしかかり|ふみつけ|ヒートスタンプ|ドラゴンダイブ|かぜおこし|なみのり|じしん|たつまき|フライングプレス',
      const [1.0, 2.0], 1.0);

  // --- 威力補正 ---
  add(WazaEffectKind.powerHosei, 'はたきおとす', const [1.0, 1.5], 1.5);
  add(WazaEffectKind.powerHosei, 'たたりめ|からげんき|しおみず|ベノムショック',
      const [1.0, 2.0], 2.0);
  add(WazaEffectKind.powerHosei, 'Gのちから', const [1.0, 1.5], 1.0);
  add(WazaEffectKind.powerHosei, 'かたきうち|はりこみ', const [1.0, 2.0], 1.0);
  add(WazaEffectKind.powerHosei, 'きまぐレーザー|じだんだ|やけっぱち',
      const [1.0, 2.0], 2.0);

  // きょけんとつげき「受×2」は addPower ×1/×2 のトグルで近似（既存機構を流用）。
  add(WazaEffectKind.addPower, 'きょけんとつげき', const [1.0, 2.0], 1.0);

  // --- 自分のランク上昇技 ---
  addRank(WazaEffectKind.selfRank, 'りゅうのまい', 'AS+1');
  addRank(WazaEffectKind.selfRank, 'つるぎのまい', 'A+2');
  addRank(WazaEffectKind.selfRank, 'ビルドアップ|とぐろをまく', 'AB+1');
  addRank(WazaEffectKind.selfRank, 'のろい', 'AB+1 S-1');
  addRank(WazaEffectKind.selfRank, 'からをやぶる', 'ACS+2 BD-1');
  addRank(WazaEffectKind.selfRank, 'めいそう', 'CD+1');
  addRank(WazaEffectKind.selfRank, 'ちょうのまい', 'CDS+1');
  addRank(WazaEffectKind.selfRank, 'わるだくみ', 'C+2');
  addRank(WazaEffectKind.selfRank, 'てっぺき|たてこもる|とける|ダイヤストーム', 'B+2');
  addRank(WazaEffectKind.selfRank, 'ドわすれ', 'D+2');
  addRank(
      WazaEffectKind.selfRank,
      'くさわけ|ニトロチャージ|こうそくスピン|アクアステップ',
      'S+1');
  addRank(WazaEffectKind.selfRank, 'メテオビーム|コメットパンチ|フレアソング', 'C+1');
  addRank(WazaEffectKind.selfRank, 'こうそくいどう', 'S+2');
  addRank(WazaEffectKind.selfRank, 'コットンガード', 'B+3');
  addRank(WazaEffectKind.selfRank, 'はらだいこ', 'A+6');
  addRank(WazaEffectKind.selfRank, 'せいちょう', 'AC+1');
  addRank(WazaEffectKind.selfRank, 'ソウルビート', 'ABCDS+1');
  addRank(WazaEffectKind.selfRank, 'コスモパワー', 'BD+1');

  // --- 自分のランク下降技 ---
  addRank(WazaEffectKind.selfRank, 'インファイト|ぶちかまし|アーマーキャノン', 'BD-1');
  addRank(WazaEffectKind.selfRank, 'ばかぢから', 'AB-1');
  addRank(WazaEffectKind.selfRank, 'アームハンマー', 'S-1');
  addRank(WazaEffectKind.selfRank, 'スケイルノイズ|いじげんラッシュ', 'B-1');
  addRank(
      WazaEffectKind.selfRank,
      'リーフストーム|オーバーヒート|りゅうせいぐん|サイコブースト',
      'C-2');
  addRank(WazaEffectKind.selfRank, 'テラバースト', 'AC-1');

  // --- 相手のランク上昇/下降技 ---
  addRank(WazaEffectKind.opponentRank, 'いばる', 'A+2', opponent: true);
  addRank(WazaEffectKind.opponentRank, 'あまえる', 'A-2', opponent: true);
  // キングシールド：接触技を受けると相手の『こうげき』を1段階下げる（第8世代以降）。
  addRank(WazaEffectKind.opponentRank, 'キングシールド', 'A-1', opponent: true);
  addRank(WazaEffectKind.opponentRank,
      'マジカルフレイム|ムーンフォース|ミストボール|バークアウト|ソウルクラッシュ', 'C-1',
      opponent: true);
  addRank(
      WazaEffectKind.opponentRank,
      'シャドーボール|ラスターパージ|じならし|エナジーボール|ラスターカノン|だいちのちから|サイコキネシス',
      'D-1',
      opponent: true);
  addRank(WazaEffectKind.opponentRank,
      'がんせきふうじ|こごえるかぜ|マッドショット|ドラムアタック|エレキネット', 'S-1',
      opponent: true);
  addRank(WazaEffectKind.opponentRank,
      'ひやみず|ワイドブレイカー|じゃれつく|うらみつらみ', 'A-1',
      opponent: true);
  addRank(WazaEffectKind.opponentRank, 'すてゼリフ', 'AC-1', opponent: true);
  addRank(WazaEffectKind.opponentRank, 'おきみやげ', 'AC-2', opponent: true);
  addRank(WazaEffectKind.opponentRank, 'アクアブレイク|かみくだく|らいめいげり', 'B-1',
      opponent: true);
  addRank(WazaEffectKind.opponentRank, 'かいでんぱ', 'C-2', opponent: true);
  addRank(WazaEffectKind.opponentRank, 'アシッドボム|ルミナコリジョン|シードフレア', 'D-2',
      opponent: true);
  addRank(WazaEffectKind.opponentRank, 'きあいだま', 'D-1', opponent: true);

  // --- タイプ変更技 ---
  // みずびたし：相手をみずタイプに。もえつきる/でんこうそうげき：自分のほのお/でんきを失う。
  m['みずびたし'] = const WazaEffect(WazaEffectKind.typeChange,
      changeType: PokeType.water, targetOpponent: true);
  m['もえつきる'] = const WazaEffect(WazaEffectKind.typeChange,
      changeType: PokeType.fire, removeType: true);
  m['でんこうそうげき'] = const WazaEffect(WazaEffectKind.typeChange,
      changeType: PokeType.electric, removeType: true);

  // --- other_effect 系トグル ---
  m['じこあんじ'] = const WazaEffect(WazaEffectKind.copyBoosts);
  m['スキルスワップ'] = const WazaEffect(WazaEffectKind.swapAbility);
  m['コートチェンジ'] = const WazaEffect(WazaEffectKind.swapField);
  m['オーラぐるま'] =
      const WazaEffect(WazaEffectKind.moveTypeChange, changeType: PokeType.dark);

  return m;
}

/// 技名から効果メタデータを返す（無ければ none）。
WazaEffect wazaEffectOf(String name) => _table[name] ?? WazaEffect.none;
