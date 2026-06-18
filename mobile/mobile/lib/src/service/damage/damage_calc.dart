/// ポケモンのダメージ計算エンジン（旧 `pokedata/calc.py` の忠実移植）。
///
/// 計算は純粋関数として実装され、入力に対し決定論的に 16 通りの乱数ダメージを返す。
/// DB へは依存せず、与えられた解決済み状態（[CombatantState] / [MoveState] /
/// [FieldState]）のみで計算する。
///
/// 数値の丸めは [rounding.dart] のヘルパで Python の `Decimal.quantize` と一致させている。
library;

import 'models.dart';
import 'move_tables.dart';
import 'poke_types.dart';
import 'rounding.dart';

class DamageCalc {
  const DamageCalc._();

  // ===== タイプ相性（pokemon.py get_type_effective の移植）=====

  /// 防御側 [defender] が技 [move] を受けたときの相性倍率。
  static double getTypeEffective(
    CombatantState defender,
    MoveState move,
    String attackerAbility,
    PokeType attackerTera,
    PokeType defenderTera,
  ) {
    List<PokeType> types;
    if (defender.battleType != null) {
      types = defender.battleType!;
    } else if (defenderTera != PokeType.none && defenderTera != PokeType.stellar) {
      types = <PokeType>[defenderTera];
    } else {
      types = defender.types;
    }

    // フライングプレス: かくとう × ひこう の複合相性。
    if (move.name == 'フライングプレス') {
      double fighting = 1.0;
      for (final t in types) {
        if ((attackerAbility == 'しんがん' || attackerAbility == 'きもったま') &&
            t == PokeType.ghost) {
          // ゴーストには等倍（無効化を貫通）。
        } else {
          fighting *= singleTypeEffective(PokeType.fighting, t);
        }
      }
      double flying = 1.0;
      for (final t in types) {
        flying *= singleTypeEffective(PokeType.flying, t);
      }
      return fighting * flying;
    }

    double value = 1.0;
    for (final t in types) {
      if (move.name == 'フリーズドライ' && t == PokeType.water) {
        value *= 2.0;
      } else if (move.name == 'サウザンアロー' && t == PokeType.ground) {
        value *= 2.0;
      } else if ((attackerAbility == 'しんがん' || attackerAbility == 'きもったま') &&
          (move.type == PokeType.normal || move.type == PokeType.fighting) &&
          t == PokeType.ghost) {
        value *= 1.0;
      } else if (defender.smackdown &&
          move.type == PokeType.ground &&
          t == PokeType.flying &&
          singleTypeEffective(move.type, t) == 0) {
        value *= 1.0;
      } else {
        value *= singleTypeEffective(move.type, t);
      }
    }

    if (move.name == 'テラバースト' &&
        defenderTera == PokeType.stellar &&
        defenderTera != PokeType.none) {
      value = 2.0;
    }
    if (move.name == 'テラクラスター' &&
        attackerTera != PokeType.none &&
        defenderTera != PokeType.none) {
      value = 2.0;
    }
    return value;
  }

  // ===== ランク補正済み実数値（pokemon.py get_ranked_stats の移植）=====

  static int rankedStat(CombatantState p, StatKey key) {
    final int stat = p.stats[key.index];
    final int rank = p.boosts[key.index];
    if (rank > 0) {
      return (stat * (2 + rank)) ~/ 2;
    } else if (rank < 0) {
      return (stat * 2) ~/ (2 - rank);
    }
    return stat;
  }

  static int rankedA(CombatantState p) => rankedStat(p, StatKey.a);
  static int rankedB(CombatantState p) => rankedStat(p, StatKey.b);
  static int rankedC(CombatantState p) => rankedStat(p, StatKey.c);
  static int rankedS(CombatantState p) => rankedStat(p, StatKey.s);

  static bool _hasType(CombatantState p, PokeType t) {
    if (p.tera != PokeType.none) return t == p.tera;
    if (p.battleType != null) return p.battleType!.contains(t);
    return p.types.contains(t);
  }

  // ===== トップレベル API =====

  /// 単一の技について 16 通りのダメージ・最小/最大・割合を返す。
  ///
  /// spec の `calculateDamage(attacker, defender, move, field)` に対応。
  static DamageResult calculateDamage(
    AttackerState attacker,
    DefenderState defender,
    MoveState move,
    FieldState field,
  ) {
    // get_all_damages 相当の前処理（トレース特性・技の解決）。
    _applyTrace(attacker, defender);
    _resolveMove(attacker, move);

    // シェルアームズ: 物理/特殊の高い方を採用。
    if (move.name == 'シェルアームズ') {
      move.category = MoveCategory.physical;
      final phys = _calcCore(attacker, defender, move, field);
      move.category = MoveCategory.special;
      final spec = _calcCore(attacker, defender, move, field);
      final useSpec =
          (spec.damages.isNotEmpty ? spec.maxDamage : 0) >
              (phys.damages.isNotEmpty ? phys.maxDamage : 0);
      move.category = useSpec ? MoveCategory.special : MoveCategory.physical;
      return useSpec ? spec : phys;
    }
    return _calcCore(attacker, defender, move, field);
  }

  /// トレース特性の適用（get_all_damages 99-104 行）。
  static void _applyTrace(AttackerState attacker, DefenderState defender) {
    if (attacker.ability == 'トレース' &&
        !unTraceAbilities.contains(defender.ability)) {
      attacker.ability = defender.ability;
    }
    if (defender.ability == 'トレース' &&
        !unTraceAbilities.contains(attacker.ability)) {
      defender.ability = attacker.ability;
    }
  }

  /// 技のタイプ・分類・急所の解決（get_all_damages 124-177 行）。
  static void _resolveMove(AttackerState attacker, MoveState waza) {
    // 常に急所の技
    if (waza.name == 'トリックフラワー' ||
        waza.name == 'あんこくきょうだ' ||
        waza.name == 'すいりゅうれんだ') {
      waza.critical = true;
    }
    // テラバースト
    if (waza.name == 'テラバースト' && attacker.tera != PokeType.none) {
      waza.category = rankedA(attacker) >= rankedC(attacker)
          ? MoveCategory.physical
          : MoveCategory.special;
      waza.type = attacker.tera;
    }
    // テラクラスター
    if (waza.name == 'テラクラスター' && attacker.tera != PokeType.none) {
      waza.category = rankedA(attacker) >= rankedC(attacker)
          ? MoveCategory.physical
          : MoveCategory.special;
      waza.type = PokeType.stellar;
    }
    // ツタこんぼう（オーガポンのフォーム）
    if (waza.name == 'ツタこんぼう') {
      if (attacker.name == 'オーガポン(水)') {
        waza.type = PokeType.water;
      } else if (attacker.name == 'オーガポン(炎)') {
        waza.type = PokeType.fire;
      } else if (attacker.name == 'オーガポン(岩)') {
        waza.type = PokeType.rock;
      }
    }
    // うるおいボイス + 音技 → みず
    if (attacker.ability == 'うるおいボイス' && soundMoves.contains(waza.name)) {
      waza.type = PokeType.water;
    }
    // めざめるダンス → 自分のタイプ1
    if (waza.name == 'めざめるダンス') {
      waza.type = attacker.type1;
    }
    // レイジングブル（ケンタロスのフォーム）
    if (waza.name == 'レイジングブル') {
      if (attacker.name == 'ケンタロス(パルデア単)') {
        waza.type = PokeType.fighting;
      } else if (attacker.name == 'ケンタロス(パルデア炎)') {
        waza.type = PokeType.fire;
      } else if (attacker.name == 'ケンタロス(パルデア水)') {
        waza.type = PokeType.water;
      }
    }
    // さばきのつぶて / テクノバスター / マルチアタック → 自分のタイプ1
    if (waza.name == 'さばきのつぶて' ||
        waza.name == 'テクノバスター' ||
        waza.name == 'マルチアタック') {
      waza.type = attacker.type1;
    }
    // オーラぐるま（はらぺこスイッチ・はらぺこもよう）→ あく
    if (waza.name == 'オーラぐるま' &&
        attacker.ability == 'はらぺこスイッチ' &&
        attacker.abilityValue == 'はらぺこもよう') {
      waza.type = PokeType.dark;
    }
  }

  /// 多段ヒット込みの実ダメージ計算（旧 __get_damage 相当）。
  static DamageResult _calcCore(
    AttackerState attacker,
    DefenderState defender,
    MoveState move,
    FieldState field,
  ) {
    if (move.category == MoveCategory.status) {
      return DamageResult(
        damages: const <int>[],
        minDamage: 0,
        maxDamage: 0,
        percentage: 0,
        type: move.type,
      );
    }

    final int hits = move.multiHit > 0 ? move.multiHit : 1;
    List<int> total = List<int>.filled(16, 0);
    for (int h = 0; h < hits; h++) {
      final int wazaPower =
          _wazaPower(attacker, defender, move, field);
      if (wazaPower == -1) {
        return DamageResult(
          damages: const <int>[],
          minDamage: 0,
          maxDamage: 0,
          percentage: 0,
          type: move.type,
        );
      }
      final int attackPower = _attackPower(attacker, defender, move, field);
      final int defencePower = _defencePower(attacker, defender, move, field);
      final int damageHosei = _damageHosei(attacker, defender, move, field);
      final List<int> damages = _fixDamages(
        attacker,
        defender,
        move,
        wazaPower,
        attackPower,
        defencePower,
        damageHosei,
        field,
      );
      for (int i = 0; i < 16; i++) {
        total[i] += damages[i];
      }
    }

    final int constant = (defender.hp * defender.constantDamage).floor();
    final int minD = total.first + constant;
    final int maxD = total.last + constant;
    final double per = _round1(maxD / defender.hp * 100);
    return DamageResult(
      damages: total,
      minDamage: minD,
      maxDamage: maxD,
      percentage: per,
      type: move.type,
    );
  }

  static double _round1(double v) => (v * 10).round() / 10;

  // ===== 技威力（__get_waza_power の移植）=====

  static int _wazaPower(
    AttackerState attacker,
    DefenderState defender,
    MoveState waza,
    FieldState field,
  ) {
    final Map<String, int> hosei = {};
    final Weather weather = field.weather;
    final Field fld = field.field;
    int power;

    // region 技の初期威力
    switch (waza.name) {
      case 'ジャイロボール':
        power =
            ((25 * rankedS(defender)) ~/ rankedS(attacker) + 1).clamp(0, 150);
        break;
      case 'エレキボール':
        final int rate = (25 * rankedS(attacker)) ~/ rankedS(defender);
        if (rate < 1) {
          power = 40;
        } else if (rate < 2) {
          power = 60;
        } else if (rate < 3) {
          power = 80;
        } else if (rate < 4) {
          power = 120;
        } else {
          power = 150;
        }
        break;
      case 'ヒートスタンプ':
      case 'ヘビーボンバー':
        power = 40;
        for (int ratio = 5; ratio >= 2; ratio--) {
          if (attacker.weight >= (defender.weight * ratio).toInt()) {
            power = ratio * 20 + 20;
            break;
          }
        }
        break;
      case 'けたぐり':
      case 'くさむすび':
        power = 120;
        for (final v in damagesAtWeight) {
          if (defender.weight < v[0]) {
            power = v[1];
            break;
          }
        }
        break;
      case 'アシストパワー':
      case 'つけあがる':
        power = 20 + _sumPlusBoosts(attacker) * 20;
        break;
      case 'ウェザーボール':
        power = 50;
        if (weather == Weather.sunny) {
          waza.type = PokeType.fire;
          power = 100;
        } else if (weather == Weather.rainy) {
          waza.type = PokeType.water;
          power = 100;
        } else if (weather == Weather.snow) {
          waza.type = PokeType.ice;
          power = 100;
        } else if (weather == Weather.sandstorm) {
          waza.type = PokeType.rock;
          power = 100;
        }
        break;
      case 'だいちのはどう':
        power = 50;
        if (!attacker.types.contains(PokeType.flying) &&
            attacker.ability != 'ふゆう' &&
            fld != Field.none) {
          if (fld == Field.grassy) {
            waza.type = PokeType.grass;
            power = 100;
          } else if (fld == Field.misty) {
            waza.type = PokeType.fairy;
            power = 100;
          } else if (fld == Field.electric) {
            waza.type = PokeType.electric;
            power = 100;
          } else if (fld == Field.psychic) {
            waza.type = PokeType.psychic;
            power = 100;
          }
        }
        break;
      case 'サイコブレイド':
        power = fld == Field.electric ? 120 : 80;
        break;
      case 'テラバースト':
        power = attacker.tera == PokeType.stellar ? 100 : 80;
        break;
      default:
        if (waza.addPower > -1) {
          power = (waza.power * waza.addPower).toInt();
        } else {
          power = waza.power;
        }
    }
    // endregion

    // region 攻撃側の特性補正
    if (defender.ability != 'かがくへんかガス') {
      final String key = '攻撃特性:${attacker.ability}';
      switch (attacker.ability) {
        case 'エレキスキン':
        case 'スカイスキン':
        case 'フェアリースキン':
        case 'フリーズスキン':
        case 'ドラゴンスキン':
          if (waza.type == PokeType.normal) {
            waza.type = skinAbilities[attacker.ability]!;
            hosei[key] = 4915;
          }
          break;
        case 'ノーマルスキン':
          if (waza.type != PokeType.normal) {
            waza.type = PokeType.normal;
            hosei[key] = 4915;
          }
          break;
        case 'てつのこぶし':
          if (punchMoves.contains(waza.name)) hosei[key] = 4915;
          break;
        case 'すてみ':
          if (recoilMoves.contains(waza.name)) hosei[key] = 4915;
          break;
        case 'ちからずく':
          if (waza.hasEffect) hosei[key] = 5325;
          break;
        case 'すなのちから':
          if ((waza.type == PokeType.ground ||
                  waza.type == PokeType.rock ||
                  waza.type == PokeType.steel) &&
              weather == Weather.sandstorm) {
            hosei[key] = 5325;
          }
          break;
        case 'アナライズ':
          if (attacker.abilityEnable) hosei[key] = 5325;
          break;
        case 'かたいツメ':
          if (waza.isTouch) hosei[key] = 5325;
          break;
        case 'パンクロック':
          if (soundMoves.contains(waza.name)) hosei[key] = 4915;
          break;
        case 'フェアリーオーラ':
          if (waza.type == PokeType.fairy) {
            hosei[key] = defender.ability == 'オーラブレイク' ? 3072 : 5448;
          }
          break;
        case 'ダークオーラ':
          if (waza.type == PokeType.dark) {
            hosei[key] = defender.ability == 'オーラブレイク' ? 3072 : 5448;
          }
          break;
        case 'きれあじ':
          if (slashMoves.contains(waza.name)) hosei[key] = 6144;
          break;
        case 'テクニシャン':
          if (waza.power <= 60) hosei[key] = 6144;
          break;
        case 'ねつぼうそう':
          if (waza.category == MoveCategory.special && attacker.abilityEnable) {
            hosei[key] = 6144;
          }
          break;
        case 'どくぼうそう':
          if (waza.category == MoveCategory.physical && attacker.abilityEnable) {
            hosei[key] = 6144;
          }
          break;
        case 'がんじょうあご':
          if (fangMoves.contains(waza.name)) hosei[key] = 6144;
          break;
        case 'メガランチャー':
          if (blastMoves.contains(waza.name)) hosei[key] = 6144;
          break;
        case 'はがねのせいしん':
          if (waza.type == PokeType.steel) hosei[key] = 6144;
          break;
        case 'そうだいしょう':
          if (attacker.abilityValue.isNotEmpty) {
            hosei[key] = soudaisyouValues[attacker.abilityValue]!;
          }
          break;
        case 'とうそうしん':
          if (attacker.abilityValue.isNotEmpty) {
            hosei[key] = tousoushinValues[attacker.abilityValue]!;
          }
          break;
      }
    }
    // endregion

    // region 防御側の特性補正
    if (_defenderAbilityActive(attacker, waza)) {
      final String key = '防御特性:${defender.ability}';
      switch (defender.ability) {
        case 'たいねつ':
          if (waza.type == PokeType.fire) hosei[key] = 2048;
          break;
        case 'かんそうはだ':
          if (waza.type == PokeType.fire) hosei[key] = 5120;
          break;
      }
    }
    // endregion

    // region オーラ特性（防御側がオーラを持つ場合）
    if ((defender.ability == 'フェアリーオーラ' || defender.ability == 'ダークオーラ') &&
        attacker.ability != defender.ability) {
      final String key = '防御特性:${defender.ability}';
      final PokeType auraType =
          defender.ability == 'フェアリーオーラ' ? PokeType.fairy : PokeType.dark;
      if (waza.type == auraType) {
        hosei[key] = attacker.ability == 'オーラブレイク' ? 3072 : 5448;
      }
    }
    // endregion

    // region 攻撃側の持ち物補正
    {
      final String key = '持ち物:${attacker.item}';
      switch (attacker.item) {
        case 'ちからのハチマキ':
          if (waza.category == MoveCategory.physical) hosei[key] = 4505;
          break;
        case 'ものしりメガネ':
          if (waza.category == MoveCategory.special) hosei[key] = 4505;
          break;
        case 'パンチグローブ':
          if (punchMoves.contains(waza.name)) hosei[key] = 4506;
          break;
        case 'こんごうだま':
          if (attacker.name == 'ディアルガ' &&
              (waza.type == PokeType.steel || waza.type == PokeType.dragon)) {
            hosei[key] = 4915;
          }
          break;
        case 'しらたま':
          if (attacker.name == 'パルキア' &&
              (waza.type == PokeType.water || waza.type == PokeType.dragon)) {
            hosei[key] = 4915;
          }
          break;
        case 'はっきんだま':
          if (attacker.name == 'ギラティナ(オリジン)' &&
              (waza.type == PokeType.ghost || waza.type == PokeType.dragon)) {
            hosei[key] = 4915;
          }
          break;
        case 'こころのしずく':
          if ((attacker.name == 'ラティアス' || attacker.name == 'ラティオス') &&
              (waza.type == PokeType.psychic || waza.type == PokeType.dragon)) {
            hosei[key] = 4915;
          }
          break;
        case 'ノーマルジュエル':
          if (waza.type == PokeType.normal) hosei[key] = 5325;
          break;
        case 'いどのめん':
          if (attacker.name == 'オーガポン(水)') hosei[key] = 4915;
          break;
        case 'かまどのめん':
          if (attacker.name == 'オーガポン(炎)') hosei[key] = 4915;
          break;
        case 'いしずえのめん':
          if (attacker.name == 'オーガポン(岩)') hosei[key] = 4915;
          break;
      }
      final PokeType? buffType = typeBuffItems[attacker.item];
      if (typeBuffItems.containsKey(attacker.item) ||
          attacker.item == 'タイプ強化アイテム') {
        if ((buffType != null && buffType == waza.type) ||
            attacker.item == 'タイプ強化アイテム') {
          hosei[attacker.item] = 4915;
        }
      }
    }
    // endregion

    // region 技による補正
    {
      final String key = '技:${waza.name}';
      switch (waza.name) {
        case 'ソーラービーム':
        case 'ソーラーブレード':
          if (weather == Weather.rainy ||
              weather == Weather.sandstorm ||
              weather == Weather.snow) {
            hosei[key] = 2048;
          }
          break;
        case 'アクセルブレイク':
        case 'イナズマドライブ':
          if (getTypeEffective(defender, waza, attacker.ability, attacker.tera,
                  defender.tera) ==
              2.0) {
            hosei[key] = 5461;
          }
          break;
        case 'ワイドフォース':
          if (fld == Field.psychic && !attacker.isFlying) hosei[key] = 6144;
          break;
        case 'ライジングボルト':
          if (fld == Field.electric && !defender.isFlying) hosei[key] = 8192;
          break;
        default:
          if (attacker.charging && waza.type == PokeType.electric) {
            hosei[key] = 8192;
          }
          if (waza.powerHosei == 2.0) {
            hosei[key] = 8192;
          } else if (waza.powerHosei == 1.5) {
            hosei[key] = 6144;
          }
      }
    }
    // endregion

    // region フィールド補正
    {
      final String key = 'フィールド:${fld.name}';
      switch (fld) {
        case Field.electric:
          if (waza.type == PokeType.electric && !attacker.isFlying) {
            hosei[key] = 5325;
          }
          break;
        case Field.psychic:
          if (waza.type == PokeType.psychic && !attacker.isFlying) {
            hosei[key] = 5325;
          }
          break;
        case Field.grassy:
          if (waza.type == PokeType.grass && !attacker.isFlying) {
            hosei[key] = 5325;
          }
          if ((waza.name == 'じしん' ||
                  waza.name == 'じならし' ||
                  waza.name == 'マグニチュード') &&
              !defender.isFlying) {
            hosei[key] = 2048;
          }
          break;
        case Field.misty:
          if (waza.type == PokeType.dragon && !defender.isFlying) {
            hosei[key] = 2048;
          }
          break;
        case Field.none:
          break;
      }
    }
    // endregion

    // region ダブル用補正
    if (field.doubleParams != null &&
        (field.doubleParams!['is_tedasuke'] ?? false)) {
      hosei['ダブル用: てだすけ'] = 6144;
    }
    // endregion

    final int hoseiTotal = combineHosei(hosei.values);
    int finalPower = roundHalfDown(power, hoseiTotal, 4096);

    // 一致テラスで威力 60 以下なら 60 に底上げ。
    if (waza.type == attacker.tera &&
        finalPower < 60 &&
        !waza.priority &&
        waza.multiHit == -1) {
      finalPower = 60;
    }

    return finalPower > 0 ? finalPower : 1;
  }

  static int _sumPlusBoosts(CombatantState p) {
    int sum = 0;
    for (final key in [StatKey.a, StatKey.b, StatKey.c, StatKey.d, StatKey.s]) {
      final v = p.boosts[key.index];
      if (v > 0) sum += v;
    }
    return sum;
  }

  /// 防御側特性が有効か（かたやぶり系/特定技で無視されない）。
  static bool _defenderAbilityActive(AttackerState attacker, MoveState waza) {
    final bool moldBreaker =
        moldBreakerAbilities.contains(attacker.ability) && attacker.abilityEnable;
    final bool ignoreMove =
        waza.name == 'メテオドライブ' || waza.name == 'シャドーレイ';
    return !moldBreaker && !ignoreMove;
  }

  // ===== 攻撃力（__get_attack_power の移植）=====

  static int _attackPower(
    AttackerState attacker,
    DefenderState defender,
    MoveState waza,
    FieldState field,
  ) {
    final Map<String, int> hosei = {};
    int basePower;

    switch (waza.name) {
      case 'イカサマ':
        if (waza.critical && defender.boosts[StatKey.a.index] < 0) {
          basePower = defender[StatKey.a];
        } else {
          basePower = rankedA(defender);
        }
        break;
      case 'ボディプレス':
        if (waza.critical && attacker.boosts[StatKey.b.index] < 0) {
          basePower = attacker[StatKey.b];
        } else {
          basePower = rankedB(attacker);
        }
        break;
      case 'フォトンゲイザー':
        basePower = rankedA(attacker) > rankedC(attacker)
            ? rankedA(attacker)
            : rankedC(attacker);
        waza.category = rankedA(attacker) > rankedC(attacker)
            ? MoveCategory.physical
            : MoveCategory.special;
        break;
      default:
        final StatKey statKey =
            waza.category == MoveCategory.physical ? StatKey.a : StatKey.c;
        if (waza.critical && attacker.boosts[statKey.index] < 0) {
          basePower = attacker[statKey];
        } else if (defender.ability == 'てんねん' &&
            _defenderAbilityActive(attacker, waza)) {
          basePower = attacker[statKey];
        } else {
          basePower = rankedStat(attacker, statKey);
        }
    }

    int power = basePower;

    // わざわい（攻撃力 25% 減）
    if ((waza.category == MoveCategory.physical &&
            attacker.ability != 'わざわいのおふだ' &&
            attacker.ability != 'かがくへんかガス' &&
            (defender.ability == 'わざわいのおふだ' ||
                (field.doubleParams?['is_wazawai_a'] ?? false))) ||
        (waza.category == MoveCategory.special &&
            attacker.ability != 'わざわいのうつわ' &&
            attacker.ability != 'かがくへんかガス' &&
            (defender.ability == 'わざわいのうつわ' ||
                (field.doubleParams?['is_wazawai_c'] ?? false)))) {
      hosei['わざわい:${defender.ability}'] = 3072;
    }

    // 攻撃側の特性補正
    if (defender.ability != 'かがくへんかガス') {
      final String key = '攻撃特性:${attacker.ability}';
      switch (attacker.ability) {
        case 'はりきり':
          if (waza.category == MoveCategory.physical) {
            power = floorMul(power, 6144, 4096); // 補正ではなく攻撃力に直接
          }
          break;
        case 'スロースタート':
        case 'よわき':
          if (attacker.abilityEnable) hosei[key] = 2048;
          break;
        case 'こだいかっせい':
        case 'クォークチャージ':
          if (attacker.abilityValue == 'A' &&
              waza.category == MoveCategory.physical) {
            hosei[key] = 5325;
          } else if (attacker.abilityValue == 'C' &&
              waza.category == MoveCategory.special) {
            hosei[key] = 5325;
          }
          break;
        case 'トランジスタ':
          if (waza.type == typeBuffAbilities[attacker.ability]) {
            hosei[key] = 5325;
          }
          break;
        case 'ハドロンエンジン':
          if (waza.category == MoveCategory.special &&
              field.field == Field.electric) {
            hosei[key] = 5461;
          }
          break;
        case 'ひひいろのこどう':
          if (waza.category == MoveCategory.physical &&
              field.weather == Weather.sunny) {
            hosei[key] = 5461;
          }
          break;
        case 'フラワーギフト':
          if (field.weather == Weather.sunny &&
              waza.category == MoveCategory.physical) {
            hosei[key] = 6144;
          }
          break;
        case 'こんじょう':
          if (attacker.status != Ailment.none &&
              waza.category == MoveCategory.physical) {
            hosei[key] = 6144;
          }
          break;
        case 'しんりょく':
        case 'もうか':
        case 'もらいび':
        case 'げきりゅう':
        case 'むしのしらせ':
          if (attacker.abilityEnable &&
              waza.type == typeBuffAbilities[attacker.ability]) {
            hosei[key] = 6144;
          }
          break;
        case 'サンパワー':
          if (field.weather == Weather.sunny &&
              waza.category == MoveCategory.special) {
            hosei[key] = 6144;
          }
          break;
        case 'プラス':
        case 'マイナス':
          if (attacker.abilityEnable && waza.category == MoveCategory.special) {
            hosei[key] = 6144;
          }
          break;
        case 'いわはこび':
        case 'はがねつかい':
        case 'りゅうのあぎと':
        case 'ほのおのたてがみ':
          if (waza.type == typeBuffAbilities[attacker.ability]) {
            hosei[key] = 6144;
          }
          break;
        case 'ごりむちゅう':
          if (waza.category == MoveCategory.physical) hosei[key] = 6144;
          break;
        case 'ちからもち':
        case 'ヨガパワー':
          if (waza.category == MoveCategory.physical) hosei[key] = 8192;
          break;
        case 'すいほう':
          if (waza.type == PokeType.water) hosei[key] = 8192;
          break;
      }
    }

    // 防御側の特性補正
    if (_defenderAbilityActive(attacker, waza)) {
      final String key = '防御特性:${defender.ability}';
      switch (defender.ability) {
        case 'あついしぼう':
          if (waza.type == PokeType.fire || waza.type == PokeType.ice) {
            hosei[key] = 2048;
          }
          break;
        case 'きよめのしお':
          if (waza.type == PokeType.ghost) hosei[key] = 2048;
          break;
        case 'すいほう':
          if (waza.type == PokeType.fire) hosei[key] = 2048;
          break;
      }
    }

    // 攻撃側の持ち物補正
    {
      final String key = '持ち物:${attacker.item}';
      switch (attacker.item) {
        case 'こだわりハチマキ':
          if (waza.category == MoveCategory.physical) hosei[key] = 6144;
          break;
        case 'こだわりメガネ':
          if (waza.category == MoveCategory.special) hosei[key] = 6144;
          break;
        case 'ふといホネ':
          if ((attacker.name == 'カラカラ' ||
                  attacker.name == 'ガラガラ' ||
                  attacker.name == 'アローラガラガラ') &&
              waza.category == MoveCategory.physical) {
            hosei[key] = 8192;
          }
          break;
        case 'しんかいのキバ':
          if (attacker.name == 'パールル' &&
              waza.category == MoveCategory.special) {
            hosei[key] = 8192;
          }
          break;
        case 'でんきだま':
          if (attacker.name == 'ピカチュウ') hosei[key] = 8192;
          break;
      }
    }

    final int hoseiTotal = combineHosei(hosei.values);
    final int finalPower = roundHalfDown(power, hoseiTotal, 4096);
    return finalPower > 1 ? finalPower : 1;
  }

  // ===== 防御力（__get_defence_power の移植）=====

  static int _defencePower(
    AttackerState attacker,
    DefenderState defender,
    MoveState waza,
    FieldState field,
  ) {
    final Map<String, int> hosei = {};
    final StatKey dfKey = (waza.category == MoveCategory.physical ||
            waza.name == 'サイコショック' ||
            waza.name == 'サイコブレイク')
        ? StatKey.b
        : StatKey.d;

    int power;
    if (waza.critical && defender.boosts[dfKey.index] > 0) {
      power = defender[dfKey];
    } else if ((waza.name == 'せいなるつるぎ' || waza.name == 'DDラリアット') &&
        defender.boosts[dfKey.index] > 0) {
      power = defender[dfKey];
    } else {
      power = rankedStat(defender, dfKey);
    }

    // 岩タイプは砂嵐で特防 1.5 倍
    if (field.weather == Weather.sandstorm &&
        _hasType(defender, PokeType.rock) &&
        dfKey == StatKey.d) {
      power = floorMul(power, 6144, 4096);
    }
    // 氷タイプは雪で防御 1.5 倍
    if (field.weather == Weather.snow &&
        _hasType(defender, PokeType.ice) &&
        dfKey == StatKey.b) {
      power = floorMul(power, 6144, 4096);
    }

    // わざわい（防御力 25% 減）
    if ((dfKey == StatKey.b &&
            defender.ability != 'わざわいのつるぎ' &&
            defender.ability != 'かがくへんかガス' &&
            (attacker.ability == 'わざわいのつるぎ' ||
                (field.doubleParams?['is_wazawai_b'] ?? false))) ||
        (dfKey == StatKey.d &&
            defender.ability != 'わざわいのたま' &&
            defender.ability != 'かがくへんかガス' &&
            (attacker.ability == 'わざわいのたま' ||
                (field.doubleParams?['is_wazawai_d'] ?? false)))) {
      hosei['わざわい:${attacker.ability}'] = 3072;
    }

    // 防御側の特性補正
    final String key = '防御特性:${defender.ability}';
    switch (defender.ability) {
      case 'こだいかっせい':
      case 'クォークチャージ':
        if (defender.abilityValue == 'B' && dfKey == StatKey.b) {
          hosei[key] = 5325;
        } else if (defender.abilityValue == 'D' && dfKey == StatKey.d) {
          hosei[key] = 5325;
        }
        break;
    }
    if (_defenderAbilityActive(attacker, waza)) {
      switch (defender.ability) {
        case 'フラワーギフト':
          if (field.weather == Weather.sunny && dfKey == StatKey.d) {
            hosei[key] = 6144;
          }
          break;
        case 'ふしぎなうろこ':
          if (defender.abilityEnable && dfKey == StatKey.b) hosei[key] = 6144;
          break;
        case 'くさのけがわ':
          if (field.field == Field.grassy && dfKey == StatKey.b) {
            hosei[key] = 6144;
          }
          break;
        case 'ファーコート':
          if (waza.category == MoveCategory.physical) hosei[key] = 8192;
          break;
      }
    }

    // 防御側の持ち物補正
    {
      final String itemKey = '持ち物:${defender.item}';
      switch (defender.item) {
        case 'しんかのきせき':
          hosei[itemKey] = 6144;
          break;
        case 'とつげきチョッキ':
          if (dfKey == StatKey.d) hosei[itemKey] = 6144;
          break;
      }
    }

    final int hoseiTotal = combineHosei(hosei.values);
    final int finalPower = roundHalfDown(power, hoseiTotal, 4096);
    return finalPower > 1 ? finalPower : 1;
  }

  // ===== ダメージ補正（__get_damage_hosei の移植）=====

  static int _damageHosei(
    AttackerState attacker,
    DefenderState defender,
    MoveState waza,
    FieldState field,
  ) {
    final Map<String, int> hosei = {};
    final double typeEffective = getTypeEffective(
        defender, waza, attacker.ability, attacker.tera, defender.tera);

    // 壁の補正（原典の waza not in [..] は常に真のため省略）
    final bool wallPhysical = (defender.wall == Wall.reflect ||
            defender.wall == Wall.auroraVeil) &&
        waza.category == MoveCategory.physical;
    final bool wallSpecial = (defender.wall == Wall.lightScreen ||
            defender.wall == Wall.auroraVeil) &&
        waza.category == MoveCategory.special;
    if ((wallPhysical || wallSpecial) &&
        !waza.critical &&
        attacker.ability != 'すりぬけ') {
      hosei['壁:${defender.wall.name}'] = field.doubleParams == null ? 2048 : 3072;
    }

    // 攻撃側の特性補正
    if (defender.ability != 'かがくへんかガス') {
      final String key = '攻撃特性:${attacker.ability}';
      switch (attacker.ability) {
        case 'スナイパー':
          if (waza.critical && attacker.abilityEnable) hosei[key] = 6144;
          break;
        case 'いろめがね':
          if (typeEffective < 1.0) hosei[key] = 8192;
          break;
        case 'ふかしのこぶし':
        case 'かんつうドリル':
          if (attacker.abilityEnable) hosei[key] = 1024;
          break;
      }
    }

    // 防御側の特性補正（かがくへんかガス無効化なし側）
    if (defender.ability != 'かがくへんかガス') {
      final String key = '防御特性:${defender.ability}';
      switch (defender.ability) {
        case 'ファントムガード':
          if (defender.abilityEnable) hosei[key] = 2048;
          break;
        case 'プリズムアーマー':
          if (typeEffective > 1.0) hosei[key] = 3072;
          break;
      }
    }
    if (_defenderAbilityActive(attacker, waza)) {
      final String key = '防御特性:${defender.ability}';
      switch (defender.ability) {
        case 'もふもふ':
          if (waza.type == PokeType.fire) hosei['もふもふ(ほのお)'] = 6144;
          if (waza.isTouch) hosei['もふもふ(接触)'] = 2048;
          break;
        case 'マルチスケイル':
          if (defender.abilityEnable) hosei[key] = 2048;
          break;
        case 'パンクロック':
          if (soundMoves.contains(waza.name)) hosei[key] = 2048;
          break;
        case 'こおりのりんぷん':
          if (waza.category == MoveCategory.special) hosei[key] = 2048;
          break;
        case 'ハードロック':
        case 'フィルター':
          if (typeEffective > 1.0) hosei[key] = 3072;
          break;
      }
    }

    // 攻撃側の持ち物補正
    {
      final String key = '攻撃持ち物:${attacker.item}';
      switch (attacker.item) {
        case 'たつじんのおび':
          if (typeEffective > 1.0) hosei[key] = 4915;
          break;
        case 'いのちのたま':
          hosei[key] = 5324;
          break;
      }
    }

    // 防御側の持ち物補正（半減きのみ）
    if (typeDebuffItems.containsKey(defender.item) ||
        defender.item == '半減きのみ') {
      final PokeType? t = typeDebuffItems[defender.item];
      if ((t != null && t == waza.type) || defender.item == '半減きのみ') {
        hosei[attacker.item] = 2048;
      }
    }

    // ダブル用補正
    if (field.doubleParams != null &&
        (field.doubleParams!['is_friend_guard'] ?? false)) {
      hosei['ダブル用: フレンドガード'] = 3072;
    }

    // きょけんとつげき（受けダメージ 2 倍）
    if (defender.kyokenCharge) hosei['きょけんとつげき'] = 8192;

    return combineHosei(hosei.values);
  }

  // ===== 最終ダメージ（__get_fix_damages の移植）=====

  static List<int> _fixDamages(
    AttackerState attacker,
    DefenderState defender,
    MoveState waza,
    int wazaPower,
    int attackPower,
    int defencePower,
    int damageHosei,
    FieldState field,
  ) {
    // レベル補正
    int damage = (2 * attacker.level) ~/ 5 + 2;
    // × 威力 × 攻撃 ÷ 防御
    damage = (damage * wazaPower * attackPower) ~/ defencePower;
    // ÷ 50 + 2
    damage = damage ~/ 50 + 2;

    // 天候補正
    if (attacker.item != 'ばんのうがさ' && defender.item != 'ばんのうがさ') {
      switch (field.weather) {
        case Weather.sunny:
          if (waza.type == PokeType.fire || waza.name == 'ハイドロスチーム') {
            damage = roundHalfDown(damage, 6144, 4096);
          } else if (waza.type == PokeType.water) {
            damage = roundHalfDown(damage, 2048, 4096);
          }
          break;
        case Weather.rainy:
          if (waza.type == PokeType.water) {
            damage = roundHalfDown(damage, 6144, 4096);
          } else if (waza.type == PokeType.fire) {
            damage = roundHalfDown(damage, 2048, 4096);
          }
          break;
        default:
          break;
      }
    }

    // 全体攻撃（ダブル用）
    if (field.doubleParams != null &&
        (field.doubleParams!['is_overall'] ?? false) &&
        waza.target == '相手全体') {
      damage = roundHalfUp(damage, 3072, 4096);
    }

    // 急所
    if (waza.critical) {
      damage = roundHalfDown(damage, 6144, 4096);
    }

    final double typeEffective = getTypeEffective(
        defender, waza, attacker.ability, attacker.tera, defender.tera);
    final int teQuarters = (typeEffective * 4).round();

    final List<PokeType> attackerTypes =
        attacker.battleType ?? attacker.types;
    final bool typeEqual = (waza.name == 'テラクラスター' &&
            attacker.tera == PokeType.stellar)
        ? false
        : attackerTypes.contains(waza.type);
    final bool terasEqual = waza.type == attacker.tera;

    final List<int> damages = [];
    for (int i = 0; i < 16; i++) {
      // 乱数 0.85 〜 1.00
      int rnd = (damage * (85 + i)) ~/ 100;

      // タイプ一致補正
      int value = 4096;
      if (attacker.ability != 'かがくへんかガス') {
        switch (attacker.ability) {
          case 'へんげんじざい':
          case 'リベロ':
            if (attacker.abilityValue == '有効') {
              value = (terasEqual || attacker.tera == PokeType.stellar)
                  ? 8192
                  : 6144;
            } else if (attacker.abilityValue == '無効' &&
                (terasEqual || attacker.tera == PokeType.stellar)) {
              value = 6144;
            }
            break;
          case 'てきおうりょく':
            if (terasEqual || attacker.tera == PokeType.stellar) {
              value = typeEqual ? 9216 : 8192;
            } else if (attacker.tera == PokeType.none && typeEqual) {
              value = 8192;
            }
            break;
          default:
            if (typeEqual && (terasEqual || attacker.tera == PokeType.stellar)) {
              value = 8192;
            } else if (attacker.tera == PokeType.stellar) {
              value = 4915;
            } else if (typeEqual || terasEqual) {
              value = 6144;
            }
        }
      }
      if (value != 4096) {
        rnd = roundHalfDown(rnd, value, 4096);
      }

      // タイプ相性
      rnd = (rnd * teQuarters) ~/ 4;

      // やけど
      if (attacker.status == Ailment.burn &&
          waza.category == MoveCategory.physical &&
          waza.name != 'からげんき') {
        rnd = roundHalfDown(rnd, 2048, 4096);
      }

      // ダメージ補正値
      rnd = roundHalfDown(rnd, damageHosei, 4096);

      damages.add(rnd);
    }
    return damages;
  }

  // ===== ステータス実数値計算（pokemon.py __get_stats の移植）=====

  /// 種族値・個体値・努力値（0-32 換算）・レベル・性格から実数値を算出する。
  ///
  /// spec の `calculateStats(baseStats, iv, ev, level, nature)` に対応。
  /// 努力値スケールは旧実装に合わせ 0-32（1 = 実値 +2 寄与）とする。
  static List<int> calculateStats({
    required List<int> baseStats,
    required List<int> iv,
    required List<int> ev,
    required int level,
    required String nature,
  }) {
    assert(baseStats.length == 6 && iv.length == 6 && ev.length == 6);
    final List<int> result = List<int>.filled(6, 0);
    for (final key in StatKey.values) {
      final int i = key.index;
      final int common = (2 * baseStats[i] + iv[i] + 2 * ev[i]);
      if (key == StatKey.h) {
        result[i] = (common * level) ~/ 100 + 10 + level;
      } else {
        int v = (common * level) ~/ 100 + 5;
        final double natureHosei = _natureHosei(nature, key);
        if (natureHosei == 1.1) {
          v = (v * 11) ~/ 10;
        } else if (natureHosei == 0.9) {
          v = (v * 9) ~/ 10;
        }
        result[i] = v;
      }
    }
    return result;
  }

  /// 性格補正（nature.py get_seikaku_hosei の移植）。
  static double _natureHosei(String nature, StatKey key) {
    final entry = _natures[nature];
    if (entry == null) return 1.0;
    if (entry.up == key) return 1.1;
    if (entry.down == key) return 0.9;
    return 1.0;
  }

  static const Map<String, ({StatKey up, StatKey down})> _natures = {
    'さみしがり': (up: StatKey.a, down: StatKey.b),
    'いじっぱり': (up: StatKey.a, down: StatKey.c),
    'やんちゃ': (up: StatKey.a, down: StatKey.d),
    'ゆうかん': (up: StatKey.a, down: StatKey.s),
    'ずぶとい': (up: StatKey.b, down: StatKey.a),
    'わんぱく': (up: StatKey.b, down: StatKey.c),
    'のうてんき': (up: StatKey.b, down: StatKey.d),
    'のんき': (up: StatKey.b, down: StatKey.s),
    'ひかえめ': (up: StatKey.c, down: StatKey.a),
    'おっとり': (up: StatKey.c, down: StatKey.b),
    'うっかりや': (up: StatKey.c, down: StatKey.d),
    'れいせい': (up: StatKey.c, down: StatKey.s),
    'おだやか': (up: StatKey.d, down: StatKey.a),
    'おとなしい': (up: StatKey.d, down: StatKey.b),
    'しんちょう': (up: StatKey.d, down: StatKey.c),
    'なまいき': (up: StatKey.d, down: StatKey.s),
    'おくびょう': (up: StatKey.s, down: StatKey.a),
    'せっかち': (up: StatKey.s, down: StatKey.b),
    'ようき': (up: StatKey.s, down: StatKey.c),
    'むじゃき': (up: StatKey.s, down: StatKey.d),
  };

  /// 攻撃タイプと防御タイプ群から相性倍率を返す（spec の getTypeEffectiveness）。
  static double getTypeEffectiveness(
    PokeType offenseType,
    List<PokeType> defenseTypes,
  ) {
    double v = 1.0;
    for (final d in defenseTypes) {
      v *= singleTypeEffective(offenseType, d);
    }
    return v;
  }
}
