import 'dart:convert';
import 'dart:io';

import 'package:champ_edge_mobile/src/service/damage_engine.dart';
import 'package:flutter_test/flutter_test.dart';

/// JSON の攻守状態を [CombatantState] のフィールド群へ変換するヘルパ。
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
  final List<dynamic> cases =
      jsonDecode(file.readAsStringSync()) as List<dynamic>;

  group('Python calc.py との一致テスト (${cases.length} 件)', () {
    for (var i = 0; i < cases.length; i++) {
      final c = cases[i] as Map<String, dynamic>;
      final move = c['move'] as Map<String, dynamic>;
      test('case #$i: ${c['attacker']['name']} の ${move['name']} → '
          '${c['defender']['name']}', () {
        final result = DamageCalc.calculateDamage(
          _attacker(c['attacker'] as Map<String, dynamic>),
          _defender(c['defender'] as Map<String, dynamic>),
          _move(move),
          _field(c['field'] as Map<String, dynamic>),
        );
        final expected = c['expected'] as Map<String, dynamic>;
        final expectedDamages = (expected['damages'] as List).cast<int>();

        expect(result.damages, expectedDamages,
            reason: '16 通りの乱数ダメージが一致すること');
        expect(result.minDamage, expected['min'] as int);
        expect(result.maxDamage, expected['max'] as int);
        expect(result.percentage,
            closeTo((expected['percentage'] as num).toDouble(), 0.05),
            reason: '対 HP 割合が一致すること');
      });
    }
  });

  group('エンジン基本仕様', () {
    test('getTypeEffectiveness: 複合タイプの倍率', () {
      // でんき → みず(2.0) × ひこう(2.0) = 4.0
      expect(
        DamageCalc.getTypeEffectiveness(
            PokeType.electric, [PokeType.water, PokeType.flying]),
        4.0,
      );
      // でんき → じめん は無効 (0.0)
      expect(
        DamageCalc.getTypeEffectiveness(PokeType.electric, [PokeType.ground]),
        0.0,
      );
    });

    test('calculateStats: ガブリアス A 振り(0-32換算32, ようき) の実数値', () {
      // 種族値 [108,130,95,80,85,102]
      final stats = DamageCalc.calculateStats(
        baseStats: const [108, 130, 95, 80, 85, 102],
        iv: const [31, 31, 31, 31, 31, 31],
        ev: const [0, 32, 0, 0, 0, 32],
        level: 50,
        nature: 'ようき',
      );
      // HP=183, S(ようき↑)=169, A=182 などが目安（旧実装と一致）
      expect(stats[StatKey.h.index], 183);
      expect(stats[StatKey.a.index], 182);
      expect(stats[StatKey.s.index], 169);
    });

    test('変化技はダメージ 0', () {
      final r = DamageCalc.calculateDamage(
        AttackerState(stats: const [200, 200, 100, 100, 100, 100], type1: PokeType.normal),
        DefenderState(stats: const [200, 100, 100, 100, 100, 100], type1: PokeType.normal),
        MoveState(
            name: 'つるぎのまい',
            type: PokeType.normal,
            category: MoveCategory.status,
            power: 0),
        const FieldState(),
      );
      expect(r.isDamage, isFalse);
      expect(r.damages, isEmpty);
    });
  });

  group('性能要件', () {
    test('1 回の calculateDamage は 100ms 未満', () {
      final a = AttackerState(
          name: 'ガブリアス',
          stats: const [183, 182, 115, 100, 105, 169],
          type1: PokeType.ground,
          type2: PokeType.dragon);
      final d = DefenderState(
          name: 'カビゴン',
          stats: const [294, 159, 96, 137, 116, 53],
          type1: PokeType.normal);
      final m = MoveState(
          name: 'じしん',
          type: PokeType.ground,
          category: MoveCategory.physical,
          power: 100);
      final sw = Stopwatch()..start();
      DamageCalc.calculateDamage(a, d, m, const FieldState());
      sw.stop();
      expect(sw.elapsedMilliseconds, lessThan(100));
    });

    test('1000 回連続実行の平均が 100ms 未満（ベンチ）', () {
      final a = AttackerState(
          name: 'ガブリアス',
          stats: const [183, 182, 115, 100, 105, 169],
          type1: PokeType.ground,
          type2: PokeType.dragon);
      final d = DefenderState(
          name: 'カビゴン',
          stats: const [294, 159, 96, 137, 116, 53],
          type1: PokeType.normal);
      final sw = Stopwatch()..start();
      const iterations = 1000;
      for (var i = 0; i < iterations; i++) {
        // 毎回 move を作り直す（type 書き換えの副作用を避ける）
        final m = MoveState(
            name: 'じしん',
            type: PokeType.ground,
            category: MoveCategory.physical,
            power: 100);
        DamageCalc.calculateDamage(a, d, m, const FieldState());
      }
      sw.stop();
      final avgMs = sw.elapsedMicroseconds / iterations / 1000.0;
      // ignore: avoid_print
      print('平均実行時間: ${avgMs.toStringAsFixed(4)} ms/calc '
          '($iterations回 計 ${sw.elapsedMilliseconds}ms)');
      expect(avgMs, lessThan(100));
    });
  });
}
