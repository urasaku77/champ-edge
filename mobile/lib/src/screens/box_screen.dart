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

  /// 追加：種族を検索窓で選び、そのまま個別編集（技・努力値まで）して保存。
  Future<void> _add() async {
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
