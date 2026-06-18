// ignore_for_file: avoid_print
/// ダメージエンジンの動作デモ（人が目視確認するための簡易ランナー）。
/// 実行: `dart run test/demo_damage.dart`
import 'package:champ_edge_mobile/src/service/damage_engine.dart';

void _show(String title, AttackerState a, DefenderState d, MoveState m,
    [FieldState f = const FieldState()]) {
  final r = DamageCalc.calculateDamage(a, d, m, f);
  final hp = d.hp;
  print('■ $title');
  print('  ${a.name} の ${m.name}（威力${m.power}/${m.type.jp}） → ${d.name}(HP$hp)');
  print('  ダメージ: ${r.minDamage}〜${r.maxDamage}  '
      '(${(r.minDamage / hp * 100).toStringAsFixed(1)}%〜${r.percentage}%)');
  print('  乱数16: ${r.damages}');
  print('');
}

void main() {
  // ガブリアス(A特化) の じしん → カビゴン
  _show(
    '一致技 + 等倍',
    AttackerState(
        name: 'ガブリアス',
        stats: const [183, 200, 115, 100, 105, 169],
        type1: PokeType.dragon,
        type2: PokeType.ground),
    DefenderState(
        name: 'カビゴン',
        stats: const [227, 159, 116, 117, 156, 50],
        type1: PokeType.normal),
    MoveState(
        name: 'じしん',
        type: PokeType.ground,
        category: MoveCategory.physical,
        power: 100),
  );

  // れいとうビーム → ガブリアス（4倍 効果ばつぐん）
  _show(
    '4倍（こおり→ドラゴン/じめん）',
    AttackerState(
        name: 'ハバタクカミ',
        stats: const [155, 70, 91, 200, 156, 197],
        type1: PokeType.ghost,
        type2: PokeType.fairy),
    DefenderState(
        name: 'ガブリアス',
        stats: const [183, 200, 115, 100, 105, 169],
        type1: PokeType.dragon,
        type2: PokeType.ground),
    MoveState(
        name: 'れいとうビーム',
        type: PokeType.ice,
        category: MoveCategory.special,
        power: 90),
  );

  // テラスタル一致（テラスでんき）でんき技 + こだわりメガネ + エレキフィールド
  _show(
    'テラス一致 + メガネ + エレキF',
    AttackerState(
        name: 'サーフゴー',
        stats: const [175, 90, 105, 197, 120, 144],
        type1: PokeType.steel,
        type2: PokeType.ghost,
        tera: PokeType.electric,
        item: 'こだわりメガネ'),
    DefenderState(
        name: 'カイリュー',
        stats: const [197, 154, 115, 110, 120, 100],
        type1: PokeType.dragon,
        type2: PokeType.flying),
    MoveState(
        name: '10まんボルト',
        type: PokeType.electric,
        category: MoveCategory.special,
        power: 90),
    const FieldState(field: Field.electric),
  );
}
