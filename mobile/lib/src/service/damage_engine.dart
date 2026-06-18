/// ダメージエンジンの公開エントリポイント。
///
/// 実体は [damage/] 配下に分割実装している（旧 `pokedata/calc.py` の忠実移植）。
/// このファイルは UI 層からの利用を簡潔にするためのファサード兼再エクスポート。
library;

export 'damage/damage_calc.dart';
export 'damage/models.dart';
export 'damage/move_tables.dart';
export 'damage/poke_types.dart';

import 'damage/damage_calc.dart';
import 'damage/models.dart';

/// 後方互換のための薄いラッパ。
///
/// 詳細なダメージ計算は [DamageCalc.calculateDamage] を直接利用する。
class DamageEngine {
  const DamageEngine();

  /// 攻撃側・防御側・技・場を指定して 16 通りのダメージ結果を返す。
  DamageResult calculate(
    AttackerState attacker,
    DefenderState defender,
    MoveState move, {
    FieldState field = const FieldState(),
  }) {
    return DamageCalc.calculateDamage(attacker, defender, move, field);
  }

  /// 種族値等から実数値を算出する（[DamageCalc.calculateStats] の委譲）。
  List<int> calculateStats({
    required List<int> baseStats,
    required List<int> iv,
    required List<int> ev,
    required int level,
    required String nature,
  }) =>
      DamageCalc.calculateStats(
        baseStats: baseStats,
        iv: iv,
        ev: ev,
        level: level,
        nature: nature,
      );
}
