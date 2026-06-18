import 'package:flutter/material.dart';

import '../model/battle_pokemon.dart';

/// 素早さ上昇/下降性格（旧 champ-edge SpeedComparing.set_pokemon と同一）。
const Set<String> _speedUpNatures = {'おくびょう', 'せっかち', 'やんちゃ', 'ようき'};
const Set<String> _speedDownNatures = {'ゆうかん', 'のんき', 'れいせい', 'なまいき'};

/// 素早さ実数値の計算（旧 champ-edge SpeedComparing.calc_speed と同一式）。
/// `floor((種族値×2+31+努力値×2)×50/100)+5` に各倍率とランク倍率を乗じて切り捨て。
int calcSpeedValue({
  required int base,
  required int ev,
  required double nature,
  required double ability,
  required double item,
  required bool tailwind,
  required bool paralysis,
  required int rank,
}) {
  final rankMult = rank >= 0 ? (rank + 2) / 2 : 2 / (rank.abs() + 2);
  final stat = ((base * 2 + 31 + ev * 2) * 50 ~/ 100) + 5;
  return (stat *
          nature *
          ability *
          item *
          (tailwind ? 2.0 : 1.0) *
          (paralysis ? 0.5 : 1.0) *
          rankMult)
      .toInt();
}

/// 片側の入力状態。
class _SideState {
  _SideState(BattlePokemon p)
      : name = p.name,
        pid = p.pid,
        base = p.baseStats[5],
        ev = p.ev[5],
        rank = p.boosts[5],
        nature = _speedUpNatures.contains(p.nature)
            ? 1.1
            : _speedDownNatures.contains(p.nature)
                ? 0.9
                : 1.0,
        item = p.item == 'こだわりスカーフ' ? 1.5 : 1.0;

  final String name;
  final String pid;
  final int base;
  int ev;
  int rank;
  double nature;
  double ability = 1.0;
  double item;
  bool tailwind = false;
  bool paralysis = false;

  int get speed => calcSpeedValue(
      base: base,
      ev: ev,
      nature: nature,
      ability: ability,
      item: item,
      tailwind: tailwind,
      paralysis: paralysis,
      rank: rank);
}

/// 素早さ比較ポップアップ（旧 champ-edge SpeedComparing 踏襲）。
/// 閉じると入力内容は破棄され、ポケモン本体には反映しない。
Future<void> showSpeedCompareDialog(
    BuildContext context, BattlePokemon mine, BattlePokemon opp) {
  final sides = [_SideState(mine), _SideState(opp)];
  return showDialog<void>(
    context: context,
    builder: (ctx) => Dialog(
      insetPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
      child: StatefulBuilder(
        builder: (ctx, setLocal) => _SpeedCompareBody(
            sides: sides, onChanged: () => setLocal(() {})),
      ),
    ),
  );
}

class _SpeedCompareBody extends StatelessWidget {
  const _SpeedCompareBody({required this.sides, required this.onChanged});

  final List<_SideState> sides;
  final VoidCallback onChanged;

  @override
  Widget build(BuildContext context) {
    final s0 = sides[0].speed;
    final s1 = sides[1].speed;
    final mark = s0 > s1 ? '>' : (s0 < s1 ? '<' : '=');
    Color color(int me, int other) => me > other
        ? Colors.red
        : (me < other ? Colors.blue : Colors.black87);

    return Padding(
      padding: const EdgeInsets.all(10),
      child: SingleChildScrollView(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Text('素早さ比較',
                style: TextStyle(fontSize: 13, fontWeight: FontWeight.bold)),
            const SizedBox(height: 4),
            // アイコン・名前・実数値・比較記号
            Row(
              children: [
                Expanded(child: _header(sides[0], color(s0, s1))),
                SizedBox(
                  width: 36,
                  child: Center(
                    child: Text(mark,
                        style: const TextStyle(
                            fontSize: 22, fontWeight: FontWeight.bold)),
                  ),
                ),
                Expanded(child: _header(sides[1], color(s1, s0))),
              ],
            ),
            const Divider(height: 12),
            _row('種族値', (i) => Text('${sides[i].base}')),
            _row('努力値', (i) => _evEditor(sides[i])),
            _row('性格', (i) => _multChips(sides[i], const [0.9, 1.0, 1.1],
                (s) => s.nature, (s, v) => s.nature = v)),
            _row('ランク', (i) => _rankEditor(sides[i])),
            _row('特性', (i) => _multChips(sides[i], const [0.5, 1.0, 1.5, 2.0],
                (s) => s.ability, (s, v) => s.ability = v)),
            _row('道具', (i) => _multChips(sides[i], const [0.5, 1.0, 1.5, 2.0],
                (s) => s.item, (s, v) => s.item = v)),
            _row(
                'おいかぜ',
                (i) => _check(sides[i].tailwind,
                    (v) => _set(() => sides[i].tailwind = v))),
            _row(
                'まひ',
                (i) => _check(sides[i].paralysis,
                    (v) => _set(() => sides[i].paralysis = v))),
          ],
        ),
      ),
    );
  }

  void _set(VoidCallback fn) {
    fn();
    onChanged();
  }

  Widget _header(_SideState s, Color color) {
    return Column(
      children: [
        Row(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Image.asset('assets/pokemon/${s.pid}.png',
                width: 30,
                height: 30,
                fit: BoxFit.contain,
                errorBuilder: (_, __, ___) => const SizedBox(width: 30)),
            const SizedBox(width: 4),
            Flexible(
              child: Text(s.name,
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: const TextStyle(
                      fontSize: 12, fontWeight: FontWeight.bold)),
            ),
          ],
        ),
        Text('${s.speed}',
            style: TextStyle(
                fontSize: 26, fontWeight: FontWeight.bold, color: color)),
      ],
    );
  }

  /// 中央ラベル＋左右ウィジェットの1行。
  Widget _row(String label, Widget Function(int side) builder) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 2),
      child: Row(
        children: [
          Expanded(child: Center(child: builder(0))),
          SizedBox(
            width: 52,
            child: Center(
              child: Text(label,
                  style: const TextStyle(fontSize: 10, color: Colors.black54)),
            ),
          ),
          Expanded(child: Center(child: builder(1))),
        ],
      ),
    );
  }

  Widget _miniBtn(String text, VoidCallback onTap) {
    return InkWell(
      onTap: () => _set(onTap),
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 3),
        decoration: BoxDecoration(
          color: Colors.blueGrey.withValues(alpha: 0.10),
          borderRadius: BorderRadius.circular(4),
        ),
        child: Text(text, style: const TextStyle(fontSize: 11)),
      ),
    );
  }

  Widget _evEditor(_SideState s) {
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        _miniBtn('0', () => s.ev = 0),
        const SizedBox(width: 4),
        _miniBtn('−', () => s.ev = (s.ev - 1).clamp(0, 32)),
        SizedBox(
            width: 26,
            child: Center(
                child: Text('${s.ev}',
                    style: const TextStyle(
                        fontSize: 12, fontWeight: FontWeight.bold)))),
        _miniBtn('＋', () => s.ev = (s.ev + 1).clamp(0, 32)),
        const SizedBox(width: 4),
        _miniBtn('32', () => s.ev = 32),
      ],
    );
  }

  Widget _rankEditor(_SideState s) {
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        _miniBtn('−1', () => s.rank = (s.rank - 1).clamp(-6, 6)),
        SizedBox(
            width: 30,
            child: Center(
                child: Text('${s.rank >= 0 ? '+' : ''}${s.rank}',
                    style: const TextStyle(
                        fontSize: 12, fontWeight: FontWeight.bold)))),
        _miniBtn('+1', () => s.rank = (s.rank + 1).clamp(-6, 6)),
      ],
    );
  }

  /// 倍率選択チップ（性格/特性/道具）。
  Widget _multChips(_SideState s, List<double> values,
      double Function(_SideState) get, void Function(_SideState, double) set) {
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        for (final v in values)
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 1.5),
            child: InkWell(
              onTap: () => _set(() => set(s, v)),
              child: Container(
                padding:
                    const EdgeInsets.symmetric(horizontal: 5, vertical: 3),
                decoration: BoxDecoration(
                  color: get(s) == v
                      ? Colors.orange.withValues(alpha: 0.25)
                      : Colors.blueGrey.withValues(alpha: 0.08),
                  borderRadius: BorderRadius.circular(4),
                  border: Border.all(
                      color: get(s) == v ? Colors.orange : Colors.black12),
                ),
                child: Text('$v', style: const TextStyle(fontSize: 10)),
              ),
            ),
          ),
      ],
    );
  }

  Widget _check(bool value, ValueChanged<bool> onChangedValue) {
    return SizedBox(
      height: 26,
      child: Checkbox(
        value: value,
        visualDensity: VisualDensity.compact,
        materialTapTargetSize: MaterialTapTargetSize.shrinkWrap,
        onChanged: (v) => onChangedValue(v ?? false),
      ),
    );
  }
}
