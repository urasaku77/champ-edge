// ignore_for_file: avoid_print
/// `flutter test` がプラグインのネイティブアセットビルド（要 Xcode ライセンス）で
/// 止まる環境向けの、純粋 Dart 検証ランナー。
///
/// 実行: `dart run test/verify_damage.dart`
/// ダメージエンジンは純粋 Dart のため Flutter/ネイティブ依存なしで検証できる。
import 'dart:convert';
import 'dart:io';

import 'package:champ_edge_mobile/src/service/damage_engine.dart';

AttackerState _attacker(Map<String, dynamic> m) => AttackerState(
      name: m['name'] as String,
      level: m['level'] as int,
      stats: (m['stats'] as List).cast<int>(),
      boosts: (m['boosts'] as List).cast<int>(),
      type1: PokeType.fromJp(m['type1'] as String),
      type2: PokeType.fromJp(m['type2'] as String),
      tera: PokeType.fromJp(m['tera'] as String),
      ability: m['ability'] as String,
      abilityValue: m['abilityValue'] as String,
      item: m['item'] as String,
      status: Ailment.fromJp(m['status'] as String),
      weight: (m['weight'] as num).toDouble(),
      wall: Wall.fromJp(m['wall'] as String),
    );

DefenderState _defender(Map<String, dynamic> m) => DefenderState(
      name: m['name'] as String,
      level: m['level'] as int,
      stats: (m['stats'] as List).cast<int>(),
      boosts: (m['boosts'] as List).cast<int>(),
      type1: PokeType.fromJp(m['type1'] as String),
      type2: PokeType.fromJp(m['type2'] as String),
      tera: PokeType.fromJp(m['tera'] as String),
      ability: m['ability'] as String,
      abilityValue: m['abilityValue'] as String,
      item: m['item'] as String,
      status: Ailment.fromJp(m['status'] as String),
      weight: (m['weight'] as num).toDouble(),
      wall: Wall.fromJp(m['wall'] as String),
    );

MoveState _move(Map<String, dynamic> m) => MoveState(
      name: m['name'] as String,
      type: PokeType.fromJp(m['type'] as String),
      category: MoveCategory.fromJp(m['category'] as String),
      power: m['power'] as int,
      isTouch: m['isTouch'] == true || m['isTouch'] == 1,
      target: m['target'] as String,
      priority: m['priority'] as bool,
      hasEffect: m['hasEffect'] as bool,
      addPower: (m['addPower'] as num).toDouble(),
      powerHosei: (m['powerHosei'] as num).toDouble(),
      multiHit: m['multiHit'] as int,
      critical: m['critical'] as bool,
    );

FieldState _field(Map<String, dynamic> m) => FieldState(
      weather: Weather.fromJp(m['weather'] as String),
      field: Field.fromJp(m['field'] as String),
    );

void main() {
  final file = File('test/fixtures/damage_cases.json');
  final cases = (jsonDecode(file.readAsStringSync()) as List).cast<Map<String, dynamic>>();

  int pass = 0;
  final List<String> failures = [];
  for (var i = 0; i < cases.length; i++) {
    final c = cases[i];
    final result = DamageCalc.calculateDamage(
      _attacker(c['attacker'] as Map<String, dynamic>),
      _defender(c['defender'] as Map<String, dynamic>),
      _move(c['move'] as Map<String, dynamic>),
      _field(c['field'] as Map<String, dynamic>),
    );
    final expected = c['expected'] as Map<String, dynamic>;
    final expDamages = (expected['damages'] as List).cast<int>();
    final okDamages = _listEq(result.damages, expDamages);
    final okMin = result.minDamage == expected['min'] as int;
    final okMax = result.maxDamage == expected['max'] as int;
    final okPer =
        (result.percentage - (expected['percentage'] as num).toDouble()).abs() <
            0.05;
    if (okDamages && okMin && okMax && okPer) {
      pass++;
    } else {
      final move = c['move'] as Map<String, dynamic>;
      failures.add('#$i ${c['attacker']['name']} ${move['name']} → '
          '${c['defender']['name']}\n'
          '   exp=$expDamages min=${expected['min']} max=${expected['max']} per=${expected['percentage']}\n'
          '   got=${result.damages} min=${result.minDamage} max=${result.maxDamage} per=${result.percentage}');
    }
  }

  print('=== calc.py 一致検証 ===');
  print('合格: $pass / ${cases.length}');
  if (failures.isNotEmpty) {
    print('--- 不一致 (${failures.length} 件, 先頭 15 件) ---');
    for (final f in failures.take(15)) {
      print(f);
    }
  }

  // 性能ベンチ
  final a = AttackerState(
      name: 'ガブリアス',
      stats: const [183, 182, 115, 100, 105, 169],
      type1: PokeType.ground,
      type2: PokeType.dragon);
  final d = DefenderState(
      name: 'カビゴン',
      stats: const [294, 159, 96, 137, 116, 53],
      type1: PokeType.normal);
  const iters = 10000;
  final sw = Stopwatch()..start();
  for (var i = 0; i < iters; i++) {
    final m = MoveState(
        name: 'じしん',
        type: PokeType.ground,
        category: MoveCategory.physical,
        power: 100);
    DamageCalc.calculateDamage(a, d, m, const FieldState());
  }
  sw.stop();
  final avgUs = sw.elapsedMicroseconds / iters;
  print('=== 性能 ===');
  print('平均 ${avgUs.toStringAsFixed(2)} µs/calc '
      '(${(avgUs / 1000).toStringAsFixed(4)} ms, $iters 回)');

  if (pass != cases.length) {
    exitCode = 1;
  }
}

bool _listEq(List<int> a, List<int> b) {
  if (a.length != b.length) return false;
  for (var i = 0; i < a.length; i++) {
    if (a[i] != b[i]) return false;
  }
  return true;
}
