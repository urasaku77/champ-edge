import 'package:flutter/material.dart';

import '../data/party_store.dart';
import '../data/poke_db.dart';
import '../model/battle_pokemon.dart';
import 'party_manager_screen.dart';
import 'pokemon_picker.dart';

/// ボックス編集画面（個別ポケモンの保管庫）。各個体を技・努力値まで編集でき、
/// 履歴と同じ縦スクロールの一覧で表示する。長押しで複数選択して一括削除できる。
class BoxScreen extends StatefulWidget {
  const BoxScreen({super.key});

  @override
  State<BoxScreen> createState() => _BoxScreenState();
}

class _BoxScreenState extends State<BoxScreen> {
  List<({String id, BattlePokemon pokemon})> _box = const [];
  final Set<String> _selected = {}; // 選択中の id（複数選択モード）
  bool _loading = true;

  bool get _selectionMode => _selected.isNotEmpty;

  @override
  void initState() {
    super.initState();
    _reload();
  }

  Future<void> _reload() async {
    final list = await PartyStore.instance.listBox();
    if (!mounted) return;
    setState(() {
      _box = list;
      _selected.removeWhere((id) => !list.any((e) => e.id == id));
      _loading = false;
    });
  }

  /// 追加：「パーティから選択（複数）」か「一から作成」を選ぶ。
  Future<void> _add() async {
    final choice = await showDialog<String>(
      context: context,
      builder: (ctx) => SimpleDialog(
        title: const Text('ポケモンを追加'),
        children: [
          SimpleDialogOption(
            onPressed: () => Navigator.pop(ctx, 'party'),
            child: const ListTile(
                leading: Icon(Icons.groups),
                title: Text('パーティから選択'),
                subtitle: Text('保存パーティから複数選んで追加')),
          ),
          SimpleDialogOption(
            onPressed: () => Navigator.pop(ctx, 'new'),
            child: const ListTile(
                leading: Icon(Icons.add),
                title: Text('一から作成'),
                subtitle: Text('種族を検索して個別に作成')),
          ),
        ],
      ),
    );
    if (choice == 'new') {
      await _addNew();
    } else if (choice == 'party') {
      await _addFromParty();
    }
  }

  /// 一から作成：種族を検索窓で選び、そのまま個別編集（技・努力値まで）して保存。
  Future<void> _addNew() async {
    final pid = await pickPokemon(context);
    if (pid == null) return;
    final p = await PokeDb.instance.buildPokemon(pid);
    if (p == null || !mounted) return;
    final edited = await Navigator.of(context).push<BattlePokemon>(
      MaterialPageRoute(builder: (_) => PokemonEditScreen(pokemon: p)),
    );
    if (edited == null) return;
    await PartyStore.instance.saveBoxPokemon(edited);
    _reload();
  }

  /// 保存パーティから複数選択してボックスへ追加。
  Future<void> _addFromParty() async {
    final picked = await Navigator.of(context).push<List<BattlePokemon>>(
      MaterialPageRoute(builder: (_) => const _PartyPokemonMultiPicker()),
    );
    if (picked == null || picked.isEmpty) return;
    for (final p in picked) {
      await PartyStore.instance
          .saveBoxPokemon(BattlePokemon.fromJson(p.toJson()));
    }
    _reload();
  }

  /// 既存ボックス個体の編集（技・努力値・メモ含む）。
  Future<void> _edit(String id, BattlePokemon p) async {
    final edited = await Navigator.of(context).push<BattlePokemon>(
      MaterialPageRoute(builder: (_) => PokemonEditScreen(pokemon: p)),
    );
    if (edited == null) return;
    await PartyStore.instance.saveBoxPokemon(edited, id: id);
    _reload();
  }

  void _toggleSelect(String id) {
    setState(() {
      if (!_selected.add(id)) _selected.remove(id);
    });
  }

  Future<void> _deleteSelected() async {
    final n = _selected.length;
    final ok = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('一括削除'),
        content: Text('選択した $n 件をボックスから削除します。'),
        actions: [
          TextButton(
              onPressed: () => Navigator.pop(ctx, false),
              child: const Text('キャンセル')),
          FilledButton(
              style: FilledButton.styleFrom(backgroundColor: Colors.red),
              onPressed: () => Navigator.pop(ctx, true),
              child: const Text('削除')),
        ],
      ),
    );
    if (ok != true) return;
    for (final id in _selected) {
      await PartyStore.instance.deleteBoxPokemon(id);
    }
    _selected.clear();
    _reload();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: _selectionMode
          ? AppBar(
              leading: IconButton(
                  icon: const Icon(Icons.close),
                  tooltip: '選択解除',
                  onPressed: () => setState(_selected.clear)),
              title: Text('${_selected.length} 件選択'),
              actions: [
                IconButton(
                    icon: const Icon(Icons.delete),
                    tooltip: '選択を削除',
                    onPressed: _deleteSelected),
              ],
            )
          : AppBar(
              title: const Text('ボックス編集'),
              actions: [
                IconButton(
                    tooltip: 'ポケモンを追加',
                    icon: const Icon(Icons.add),
                    onPressed: _add),
              ],
            ),
      body: SafeArea(
        child: _loading
            ? const Center(child: CircularProgressIndicator())
            : _box.isEmpty
                ? const Center(
                    child: Text('ボックスは空です。\n右上の＋でポケモンを追加できます。',
                        textAlign: TextAlign.center,
                        style: TextStyle(color: Colors.black54)))
                : ListView.separated(
                    padding: const EdgeInsets.symmetric(vertical: 4),
                    itemCount: _box.length,
                    separatorBuilder: (_, __) => const Divider(height: 1),
                    itemBuilder: (_, i) => _row(_box[i].id, _box[i].pokemon),
                  ),
      ),
    );
  }

  Widget _row(String id, BattlePokemon p) {
    const labels = ['H', 'A', 'B', 'C', 'D', 'S'];
    final ev = [
      for (var i = 0; i < 6; i++)
        if (p.ev[i] > 0) '${labels[i]}${p.ev[i]}'
    ].join(' ');
    final selected = _selected.contains(id);
    return InkWell(
      // 通常タップ＝編集／選択モード中はタップで選択トグル。長押しで選択モードへ。
      onTap: () => _selectionMode ? _toggleSelect(id) : _edit(id, p),
      onLongPress: () => _toggleSelect(id),
      child: Container(
        color: selected ? Colors.indigo.withValues(alpha: 0.10) : null,
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
        child: Row(
          children: [
            if (_selectionMode)
              Padding(
                padding: const EdgeInsets.only(right: 6),
                child: Icon(
                    selected
                        ? Icons.check_circle
                        : Icons.radio_button_unchecked,
                    size: 20,
                    color: selected ? Colors.indigo : Colors.black38),
              ),
            Image.asset(p.imageAsset,
                width: 40,
                height: 40,
                errorBuilder: (_, __, ___) => const SizedBox(width: 40)),
            const SizedBox(width: 8),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      Text(p.name,
                          style: const TextStyle(
                              fontSize: 14, fontWeight: FontWeight.bold)),
                      const SizedBox(width: 8),
                      Flexible(
                        child: Text('${p.nature} / ${p.item}',
                            maxLines: 1,
                            overflow: TextOverflow.ellipsis,
                            style: const TextStyle(
                                fontSize: 11, color: Colors.black54)),
                      ),
                    ],
                  ),
                  Text(
                      [
                        if (ev.isNotEmpty) '努力値 $ev',
                        ...[
                          for (final m in p.moves)
                            if (!m.isEmpty) m.name
                        ],
                      ].join(' ・ '),
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style:
                          const TextStyle(fontSize: 10, color: Colors.black45)),
                  if (p.memo.isNotEmpty)
                    Text(p.memo,
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                        style: const TextStyle(
                            fontSize: 10, color: Colors.indigo)),
                ],
              ),
            ),
            if (!_selectionMode)
              IconButton(
                  icon: const Icon(Icons.delete_outline, size: 18),
                  visualDensity: VisualDensity.compact,
                  onPressed: () => _deleteOne(id, p)),
          ],
        ),
      ),
    );
  }

  Future<void> _deleteOne(String id, BattlePokemon p) async {
    final ok = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('削除'),
        content: Text('「${p.name}」をボックスから削除します。'),
        actions: [
          TextButton(
              onPressed: () => Navigator.pop(ctx, false),
              child: const Text('キャンセル')),
          FilledButton(
              style: FilledButton.styleFrom(backgroundColor: Colors.red),
              onPressed: () => Navigator.pop(ctx, true),
              child: const Text('削除')),
        ],
      ),
    );
    if (ok != true) return;
    await PartyStore.instance.deleteBoxPokemon(id);
    _reload();
  }
}

/// 保存パーティのポケモンを複数選択してボックスへ追加するピッカー。
class _PartyPokemonMultiPicker extends StatefulWidget {
  const _PartyPokemonMultiPicker();

  @override
  State<_PartyPokemonMultiPicker> createState() =>
      _PartyPokemonMultiPickerState();
}

class _PartyPokemonMultiPickerState extends State<_PartyPokemonMultiPicker> {
  List<SavedParty> _parties = const [];
  final Set<String> _sel = {}; // key: "partyIndex:slotIndex"
  bool _loading = true;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    final list = await PartyStore.instance.listSavedParties();
    if (!mounted) return;
    setState(() {
      _parties = list;
      _loading = false;
    });
  }

  List<BattlePokemon> _selectedPokemon() {
    final out = <BattlePokemon>[];
    for (var pi = 0; pi < _parties.length; pi++) {
      final party = _parties[pi].party;
      for (var si = 0; si < party.length; si++) {
        if (_sel.contains('$pi:$si')) out.add(party[si]);
      }
    }
    return out;
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('パーティから選択', style: TextStyle(fontSize: 16)),
        actions: [
          TextButton(
            onPressed: _sel.isEmpty
                ? null
                : () => Navigator.pop(context, _selectedPokemon()),
            child: Text('追加 (${_sel.length})',
                style: TextStyle(
                    color: _sel.isEmpty ? Colors.white38 : Colors.white)),
          ),
        ],
      ),
      body: _loading
          ? const Center(child: CircularProgressIndicator())
          : _parties.isEmpty
              ? const Center(child: Text('保存パーティがありません'))
              : ListView.builder(
                  itemCount: _parties.length,
                  itemBuilder: (_, pi) {
                    final sp = _parties[pi];
                    final mons = [
                      for (var si = 0; si < sp.party.length; si++)
                        if (sp.party[si].name.isNotEmpty) (si, sp.party[si])
                    ];
                    if (mons.isEmpty) return const SizedBox.shrink();
                    return Card(
                      margin:
                          const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Padding(
                            padding: const EdgeInsets.fromLTRB(12, 8, 12, 0),
                            child: Text(sp.label.isEmpty ? '(無題)' : sp.label,
                                style:
                                    const TextStyle(fontWeight: FontWeight.bold)),
                          ),
                          for (final (si, mon) in mons)
                            CheckboxListTile(
                              dense: true,
                              value: _sel.contains('$pi:$si'),
                              onChanged: (v) => setState(() {
                                final k = '$pi:$si';
                                if (v == true) {
                                  _sel.add(k);
                                } else {
                                  _sel.remove(k);
                                }
                              }),
                              secondary: Image.asset(mon.imageAsset,
                                  width: 32,
                                  height: 32,
                                  errorBuilder: (_, __, ___) =>
                                      const SizedBox(width: 32)),
                              title: Text(mon.name),
                            ),
                        ],
                      ),
                    );
                  },
                ),
    );
  }
}
