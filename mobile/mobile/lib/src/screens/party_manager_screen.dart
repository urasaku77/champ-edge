import 'package:flutter/material.dart';

import '../data/home_stats.dart';
import '../data/my_party_ocr.dart';
import '../data/party_store.dart';
import '../data/poke_db.dart';
import '../model/battle_pokemon.dart';
import '../service/damage/poke_types.dart';
import '../widgets/nature_picker.dart';
import 'my_party_import_screen.dart';
import 'pokemon_picker.dart';

/// 一覧の並び替え基準（登録日／番号）。
enum _PartySort { date, number }

/// パーティ編集（旧 champ-edge PartyEditor 相当）。
/// 「これまで作った構築の一覧（既定：登録日降順・並び替え可）→ 選択して6体を編集
/// → ポケモンを選んで個別編集（種族は検索窓で選択）」。「使用」でそのパーティを
/// 自分パーティへ反映する（呼び出し側＝ホームが受け取る）。
class PartyManagerScreen extends StatefulWidget {
  const PartyManagerScreen({super.key});

  @override
  State<PartyManagerScreen> createState() => _PartyManagerScreenState();
}

class _PartyManagerScreenState extends State<PartyManagerScreen> {
  List<SavedParty> _saved = const [];
  String? _usingId; // 使用中パーティ（1つだけ）。Top に反映されているもの。
  final Set<String> _selected = {}; // 複数選択（長押し→一括削除）
  _PartySort _sort = _PartySort.date;
  bool _loading = true;

  bool get _selectionMode => _selected.isNotEmpty;

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
        content: Text('選択した $n 件の構築を削除します。'),
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
      await PartyStore.instance.deletePartyEntry(id);
    }
    _selected.clear();
    _reload();
  }

  @override
  void initState() {
    super.initState();
    _reload();
  }

  Future<void> _reload() async {
    final list = await PartyStore.instance.listSavedParties();
    final using = await PartyStore.instance.loadUsingPartyId();
    if (!mounted) return;
    setState(() {
      _saved = _applySort(list);
      _usingId = using;
      _loading = false;
    });
  }

  /// このパーティを使用中にして Top へ反映（呼び出し側＝ホームが SavedParty を受け取る）。
  Future<void> _use(SavedParty s) async {
    await PartyStore.instance.saveUsingPartyId(s.id);
    if (mounted) Navigator.of(context).pop(s);
  }

  List<SavedParty> _applySort(List<SavedParty> list) {
    final l = [...list];
    int byNum(String s) => int.tryParse(s) ?? 1 << 30;
    switch (_sort) {
      case _PartySort.date:
        l.sort((a, b) => b.modified.compareTo(a.modified));
      case _PartySort.number:
        l.sort((a, b) {
          final n = byNum(a.num).compareTo(byNum(b.num));
          if (n != 0) return n;
          final s = byNum(a.subnum).compareTo(byNum(b.subnum));
          return s != 0 ? s : a.title.compareTo(b.title);
        });
    }
    return l;
  }

  BattlePokemon _emptyPoke() => BattlePokemon(
        name: '',
        pid: '0000-0',
        baseStats: const [0, 0, 0, 0, 0, 0],
        type1: PokeType.none,
        abilityOptions: const ['—'],
        moves: List.generate(4, (_) => emptyMove()),
      );

  /// 新規作成：まだ保存しない（メモリ上の空パーティを作って詳細を開く）。
  /// 何も入力せず戻った場合は保存されない（詳細の「保存」で初めて書き込む）。
  Future<void> _createNew() async {
    final created = SavedParty(
      id: 'p${DateTime.now().millisecondsSinceEpoch}',
      num: '',
      subnum: '',
      title: '',
      memo: '',
      party: List.generate(6, (_) => _emptyPoke()),
      modified: DateTime.now(),
    );
    await _openDetail(created);
  }

  Future<void> _openDetail(SavedParty s) async {
    final result = await Navigator.of(context).push<Object>(
      MaterialPageRoute(builder: (_) => _PartyDetailEditor(saved: s)),
    );
    // 詳細で「使用中」にして保存したら SavedParty が返るので、そのまま Top へ転送する。
    if (result is SavedParty) {
      if (mounted) Navigator.of(context).pop(result);
      return;
    }
    _reload();
  }

  Future<void> _delete(SavedParty s) async {
    final ok = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('削除'),
        content: Text('「${s.label.isEmpty ? '無題' : s.label}」を削除します。'),
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
    await PartyStore.instance.deletePartyEntry(s.id);
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
              title: const Text('パーティ編集'),
              actions: [
                PopupMenuButton<_PartySort>(
                  tooltip: '並び替え',
                  icon: const Icon(Icons.sort),
                  initialValue: _sort,
                  onSelected: (v) => setState(() {
                    _sort = v;
                    _saved = _applySort(_saved);
                  }),
                  itemBuilder: (_) => const [
                    PopupMenuItem(
                        value: _PartySort.date, child: Text('登録日（新しい順）')),
                    PopupMenuItem(value: _PartySort.number, child: Text('番号順')),
                  ],
                ),
                IconButton(
                    tooltip: '新規作成',
                    icon: const Icon(Icons.add),
                    onPressed: _createNew),
              ],
            ),
      body: SafeArea(
        child: _loading
            ? const Center(child: CircularProgressIndicator())
            : _saved.isEmpty
                ? const Center(
                    child: Text('保存された構築がありません。\n右上の＋で新規作成できます。',
                        textAlign: TextAlign.center,
                        style: TextStyle(color: Colors.black54)))
                : ListView.separated(
                    padding: const EdgeInsets.symmetric(vertical: 4),
                    itemCount: _saved.length,
                    separatorBuilder: (_, __) => const Divider(height: 1),
                    itemBuilder: (_, i) => _card(_saved[i]),
                  ),
      ),
    );
  }

  Widget _card(SavedParty s) {
    final isUsing = s.id == _usingId;
    final selected = _selected.contains(s.id);
    return InkWell(
      onTap: () => _selectionMode ? _toggleSelect(s.id) : _openDetail(s),
      onLongPress: () => _toggleSelect(s.id),
      child: Container(
        color: selected
            ? Colors.indigo.withValues(alpha: 0.12)
            : isUsing
                ? Colors.indigo.withValues(alpha: 0.06)
                : null,
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
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
                Container(
                  padding:
                      const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                  decoration: BoxDecoration(
                    color: Colors.indigo.withValues(alpha: 0.1),
                    borderRadius: BorderRadius.circular(4),
                  ),
                  child: Text(s.label.isEmpty ? '（無題）' : s.label,
                      style: const TextStyle(
                          fontSize: 12, fontWeight: FontWeight.bold)),
                ),
                if (isUsing) ...[
                  const SizedBox(width: 6),
                  Container(
                    padding:
                        const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                    decoration: BoxDecoration(
                      color: Colors.indigo,
                      borderRadius: BorderRadius.circular(4),
                    ),
                    child: const Text('使用中',
                        style: TextStyle(
                            fontSize: 10,
                            color: Colors.white,
                            fontWeight: FontWeight.bold)),
                  ),
                ],
                const Spacer(),
                if (!_selectionMode) ...[
                  if (!isUsing)
                    FilledButton.tonalIcon(
                      style: FilledButton.styleFrom(
                          visualDensity: VisualDensity.compact),
                      onPressed: () => _use(s),
                      icon: const Icon(Icons.check, size: 16),
                      label: const Text('使用'),
                    ),
                  IconButton(
                      icon: const Icon(Icons.delete_outline, size: 18),
                      visualDensity: VisualDensity.compact,
                      onPressed: () => _delete(s)),
                ],
              ],
            ),
            Row(
              children: [
                for (final p in s.party)
                  if (p.name.isNotEmpty)
                    Padding(
                      padding: const EdgeInsets.only(right: 2),
                      child: Image.asset(p.imageAsset,
                          width: 30,
                          height: 30,
                          errorBuilder: (_, __, ___) =>
                              const SizedBox(width: 30)),
                    ),
              ],
            ),
            if (s.memo.isNotEmpty)
              Padding(
                padding: const EdgeInsets.only(top: 2),
                child: Text(s.memo,
                    maxLines: 2,
                    overflow: TextOverflow.ellipsis,
                    style:
                        const TextStyle(fontSize: 11, color: Colors.black54)),
              ),
          ],
        ),
      ),
    );
  }
}

/// 保存パーティの詳細編集（番号/連番/タイトル/メモ・6体の D&D 並べ替え・個別編集）。
class _PartyDetailEditor extends StatefulWidget {
  const _PartyDetailEditor({required this.saved});
  final SavedParty saved;

  @override
  State<_PartyDetailEditor> createState() => _PartyDetailEditorState();
}

class _PartyDetailEditorState extends State<_PartyDetailEditor> {
  late List<BattlePokemon> _party;
  late final _numC = TextEditingController(text: widget.saved.num);
  late final _subC = TextEditingController(text: widget.saved.subnum);
  late final _titleC = TextEditingController(text: widget.saved.title);
  late final _memoC = TextEditingController(text: widget.saved.memo);
  bool _isUsing = false; // このパーティが使用中か（チェックボックスで表示・設定）

  @override
  void initState() {
    super.initState();
    _party = [
      for (final p in widget.saved.party) BattlePokemon.fromJson(p.toJson())
    ];
    while (_party.length < 6) {
      _party.add(BattlePokemon(
        name: '',
        pid: '0000-0',
        baseStats: const [0, 0, 0, 0, 0, 0],
        type1: PokeType.none,
        abilityOptions: const ['—'],
        moves: List.generate(4, (_) => emptyMove()),
      ));
    }
    PartyStore.instance.loadUsingPartyId().then((id) {
      if (mounted) setState(() => _isUsing = id == widget.saved.id);
    });
  }

  Future<void> _editPokemon(int i) async {
    final edited = await Navigator.of(context).push<BattlePokemon>(
      MaterialPageRoute(builder: (_) => PokemonEditScreen(pokemon: _party[i])),
    );
    if (edited != null) setState(() => _party[i] = edited);
  }

  /// ポケモンをダブルタップでボックスへ追加（個体をそのまま保存）。
  Future<void> _addToBox(int i) async {
    final p = _party[i];
    if (p.name.isEmpty) return;
    await PartyStore.instance
        .saveBoxPokemon(BattlePokemon.fromJson(p.toJson()));
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(SnackBar(
        duration: const Duration(milliseconds: 1000),
        content: Text('${p.name} をボックスに追加しました')));
  }

  /// HOME/SVのパーティ画面スクショ2枚からこのパーティ6体を取り込む（自パOCR）。
  Future<void> _importFromScreenshots() async {
    final slots = await Navigator.of(context).push<List<MyPartySlot>>(
        MaterialPageRoute(builder: (_) => const MyPartyImportScreen()));
    if (slots == null || !mounted) return;
    final built = await buildPartyFromSlots(slots);
    if (!mounted) return;
    setState(() {
      for (var i = 0; i < built.length && i < _party.length; i++) {
        if (built[i].name.isNotEmpty) _party[i] = built[i];
      }
    });
  }

  Future<void> _persist() async {
    await PartyStore.instance.savePartyEntry(
      id: widget.saved.id,
      num: _numC.text.trim(),
      subnum: _subC.text.trim(),
      title: _titleC.text.trim(),
      memo: _memoC.text.trim(),
      party: _party,
    );
  }

  /// 番号(P番号)＋連番を確定する。必須・一意（被りは上書き確認）。
  /// 両方未入力なら「最新番号の次の連番」を自動採番（確認あり）。
  /// 保存を続行してよければ true、中断なら false。
  Future<bool> _resolveNumbering() async {
    final all = await PartyStore.instance.listSavedParties();
    final others = all.where((p) => p.id != widget.saved.id).toList();
    var num = _numC.text.trim();
    var sub = _subC.text.trim();

    if (num.isEmpty && sub.isEmpty) {
      // 自動採番：最大(番号,連番)の次の連番。無ければ 1-1。
      var maxNum = 0, maxSub = 0;
      for (final p in others) {
        final n = int.tryParse(p.num) ?? 0;
        final s = int.tryParse(p.subnum) ?? 0;
        if (n > maxNum || (n == maxNum && s > maxSub)) {
          maxNum = n;
          maxSub = s;
        }
      }
      final an = maxNum == 0 ? 1 : maxNum;
      final asub = maxNum == 0 ? 1 : maxSub + 1;
      if (!mounted) return false;
      final ok = await _confirm('番号の自動採番',
          '番号が未入力のため $an-$asub で作成します。よろしいですか？');
      if (ok != true) return false;
      num = '$an';
      sub = '$asub';
      _numC.text = num;
      _subC.text = sub;
    } else if (sub.isEmpty) {
      // 番号だけ入力 → その番号内の次の連番を自動採番。
      var maxSub = 0;
      for (final p in others) {
        if (p.num == num) {
          final s = int.tryParse(p.subnum) ?? 0;
          if (s > maxSub) maxSub = s;
        }
      }
      final asub = maxSub + 1;
      if (!mounted) return false;
      final ok = await _confirm('連番の自動採番',
          '連番が未入力のため $num-$asub で作成します。よろしいですか？');
      if (ok != true) return false;
      sub = '$asub';
      _subC.text = sub;
    } else if (num.isEmpty) {
      // 連番だけ入力 → 番号が必要なのでエラー。
      _toast('番号を入力してください（番号だけなら連番は自動採番されます）');
      return false;
    }

    // 一意チェック：他に同じ番号-連番があれば上書き確認。
    final dup = others.where((p) => p.num == num && p.subnum == sub).toList();
    if (dup.isNotEmpty) {
      if (!mounted) return false;
      final ok = await _confirm(
          '上書きの確認', '番号 $num-$sub は既に存在します。上書きしますか？');
      if (ok != true) return false;
      for (final d in dup) {
        await PartyStore.instance.deletePartyEntry(d.id);
      }
    }
    return true;
  }

  Future<bool?> _confirm(String title, String message) => showDialog<bool>(
        context: context,
        builder: (ctx) => AlertDialog(
          title: Text(title),
          content: Text(message),
          actions: [
            TextButton(
                onPressed: () => Navigator.pop(ctx, false),
                child: const Text('キャンセル')),
            FilledButton(
                onPressed: () => Navigator.pop(ctx, true),
                child: const Text('OK')),
          ],
        ),
      );

  void _toast(String msg) => ScaffoldMessenger.of(context)
      .showSnackBar(SnackBar(content: Text(msg)));

  /// 保存（＋使用中チェックの状態を反映）。使用中にした場合は Top へ転送する。
  Future<void> _save() async {
    if (!await _resolveNumbering()) return;
    await _persist();
    if (_isUsing) {
      await PartyStore.instance.saveUsingPartyId(widget.saved.id);
      if (mounted) {
        Navigator.of(context).pop(SavedParty(
          id: widget.saved.id,
          num: _numC.text.trim(),
          subnum: _subC.text.trim(),
          title: _titleC.text.trim(),
          memo: _memoC.text.trim(),
          party: _party,
          modified: DateTime.now(),
        )); // Top へ反映（メタ付き）
      }
    } else {
      // チェックを外したら、自分が使用中だった場合は解除。
      if (await PartyStore.instance.loadUsingPartyId() == widget.saved.id) {
        await PartyStore.instance.saveUsingPartyId('');
      }
      if (mounted) Navigator.of(context).pop(true);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('パーティ詳細'),
        actions: [
          // 自パOCR取込（HOME/SVスクショ2枚→6体）。
          IconButton(
            icon: const Icon(Icons.photo_library),
            tooltip: 'スクショから取込',
            onPressed: _importFromScreenshots,
          ),
          // 使用中かどうかをチェックボックスで明示・切替（背景に埋もれないチップ表示）。
          Padding(
            padding: const EdgeInsets.symmetric(vertical: 8),
            child: InkWell(
              onTap: () => setState(() => _isUsing = !_isUsing),
              borderRadius: BorderRadius.circular(16),
              child: Container(
                padding:
                    const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
                decoration: BoxDecoration(
                  color: _isUsing ? Colors.indigo : Colors.white,
                  borderRadius: BorderRadius.circular(16),
                  border: Border.all(
                      color: _isUsing ? Colors.indigo : Colors.black38),
                ),
                child: Row(mainAxisSize: MainAxisSize.min, children: [
                  Icon(
                      _isUsing
                          ? Icons.check_box
                          : Icons.check_box_outline_blank,
                      color: _isUsing ? Colors.white : Colors.black54,
                      size: 18),
                  const SizedBox(width: 4),
                  Text('使用中',
                      style: TextStyle(
                          fontSize: 13,
                          fontWeight: FontWeight.bold,
                          color: _isUsing ? Colors.white : Colors.black87)),
                ]),
              ),
            ),
          ),
          IconButton(
              tooltip: '保存', icon: const Icon(Icons.check), onPressed: _save),
        ],
      ),
      body: SafeArea(
        child: ListView(
          padding: const EdgeInsets.all(12),
          children: [
            Row(
              children: [
                SizedBox(
                    width: 70,
                    child: TextField(
                        controller: _numC,
                        keyboardType: TextInputType.number,
                        decoration: const InputDecoration(
                            labelText: '番号', isDense: true))),
                const SizedBox(width: 8),
                SizedBox(
                    width: 70,
                    child: TextField(
                        controller: _subC,
                        keyboardType: TextInputType.number,
                        decoration: const InputDecoration(
                            labelText: '連番', isDense: true))),
                const SizedBox(width: 8),
                Expanded(
                    child: TextField(
                        controller: _titleC,
                        decoration: const InputDecoration(
                            labelText: 'タイトル', isDense: true))),
              ],
            ),
            const SizedBox(height: 8),
            TextField(
                controller: _memoC,
                minLines: 1,
                maxLines: 3,
                decoration:
                    const InputDecoration(labelText: 'パーティメモ', isDense: true)),
            const SizedBox(height: 8),
            const Text('ポケモン（タップで個別編集・長押しドラッグで並べ替え）',
                style: TextStyle(fontSize: 11, color: Colors.black54)),
            const SizedBox(height: 4),
            // 3体ずつ2段で表示（スクロールを抑える）。
            for (int r = 0; r < 2; r++)
              Padding(
                padding: const EdgeInsets.only(bottom: 6),
                child: Row(
                  children: [
                    for (int c = 0; c < 3; c++) ...[
                      if (c > 0) const SizedBox(width: 6),
                      Expanded(child: _slotCell(r * 3 + c)),
                    ],
                  ],
                ),
              ),
          ],
        ),
      ),
    );
  }

  Widget _slotCell(int i) {
    final p = _party[i];
    final card = _slotCard(p);
    return DragTarget<int>(
      onWillAcceptWithDetails: (d) => d.data != i,
      onAcceptWithDetails: (d) => setState(() {
        // ドロップ先と入れ替え（6枠の単純スワップ）。
        final from = d.data;
        final tmp = _party[from];
        _party[from] = _party[i];
        _party[i] = tmp;
      }),
      builder: (ctx, cand, rej) {
        final hovering = cand.isNotEmpty;
        return LongPressDraggable<int>(
          data: i,
          feedback: Material(
            color: Colors.transparent,
            child: SizedBox(width: 140, child: _slotCard(p, dragging: true)),
          ),
          childWhenDragging: Opacity(opacity: 0.3, child: card),
          child: InkWell(
            onTap: () => _editPokemon(i),
            onDoubleTap: () => _addToBox(i),
            borderRadius: BorderRadius.circular(8),
            child: DecoratedBox(
              decoration: BoxDecoration(
                borderRadius: BorderRadius.circular(8),
                border: Border.all(
                    color: hovering ? Colors.indigo : Colors.transparent,
                    width: 2),
              ),
              child: card,
            ),
          ),
        );
      },
    );
  }

  Widget _slotCard(BattlePokemon p, {bool dragging = false}) {
    return Container(
      padding: const EdgeInsets.all(6),
      decoration: BoxDecoration(
        color: dragging ? Colors.indigo.withValues(alpha: 0.08) : Colors.white,
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: Colors.black26),
      ),
      child: Row(
        children: [
          SizedBox(
            width: 40,
            height: 40,
            child: p.name.isEmpty
                ? const Icon(Icons.add, size: 16, color: Colors.black26)
                : Image.asset(p.imageAsset,
                    errorBuilder: (_, __, ___) => const SizedBox.shrink()),
          ),
          const SizedBox(width: 4),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                Text(p.name.isEmpty ? '＋ 選択' : p.name,
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: TextStyle(
                        fontSize: 12,
                        fontWeight: FontWeight.w600,
                        color: p.name.isEmpty ? Colors.black38 : Colors.black87)),
                if (p.name.isNotEmpty)
                  Text('${p.nature} / ${p.item}',
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style:
                          const TextStyle(fontSize: 9, color: Colors.black54)),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

/// ポケモン個別編集（種族は検索窓＝Top と同じ pickPokemon。性格/持ち物/特性/努力値/技/メモ）。
class PokemonEditScreen extends StatefulWidget {
  const PokemonEditScreen({super.key, required this.pokemon});
  final BattlePokemon pokemon;

  @override
  State<PokemonEditScreen> createState() => _PokemonEditScreenState();
}

class _PokemonEditScreenState extends State<PokemonEditScreen> {
  late BattlePokemon _p;
  late final _memoC = TextEditingController(text: widget.pokemon.memo);

  @override
  void initState() {
    super.initState();
    _p = BattlePokemon.fromJson(widget.pokemon.toJson());
  }

  static const _evLabels = ['HP', 'こうげき', 'ぼうぎょ', 'とくこう', 'とくぼう', 'すばやさ'];

  Future<void> _pickSpecies() async {
    final pid = await pickPokemon(context); // Top と同じ検索窓
    if (pid == null) return;
    final np = await PokeDb.instance.buildPokemon(pid);
    if (np == null) return;
    np.memo = _p.memo; // メモは引き継ぐ
    await _applyHomeDefaults(np); // 特性/持ち物/性格/努力値/技を HOME 使用率上位で初期化
    if (mounted) setState(() => _p = np);
  }

  /// 種族選択時の初期値を HOME 使用率の上位で埋める（旧 champ-edge の登録時補完に相当）。
  Future<void> _applyHomeDefaults(BattlePokemon p) async {
    await HomeStats.instance.load();
    final s = HomeStats.instance;
    final nat = s.entries(p.name, HomeCategory.nature);
    if (nat.isNotEmpty) p.nature = nat.first.value;
    final item = s.entries(p.name, HomeCategory.item);
    if (item.isNotEmpty) p.item = item.first.value;
    final abil = s.entries(p.name, HomeCategory.ability);
    if (abil.isNotEmpty && p.abilityOptions.contains(abil.first.value)) {
      p.ability = abil.first.value;
    }
    for (final e in s.entries(p.name, HomeCategory.ev)) {
      final ev = HomeStats.parseDoryoku(e.value);
      if (ev.fold<int>(0, (a, b) => a + b) > 0) {
        p.ev = ev;
        break;
      }
    }
    // 技：使用率上位を最大4つ（プレイヤーの構築なので変化技も含める）。
    final moves = <BattleMove>[];
    for (final e in s.entries(p.name, HomeCategory.waza)) {
      final mv = await PokeDb.instance.moveByName(e.value);
      if (mv != null) {
        moves.add(mv);
        if (moves.length >= 4) break;
      }
    }
    while (moves.length < 4) {
      moves.add(emptyMove());
    }
    p.moves = moves;
  }

  Future<void> _pickNature() async {
    // Top と同じ表形式（↑行×↓列）のピッカーを共用。
    final v = await pickNature(context, _p.nature);
    if (v != null) setState(() => _p.nature = v);
  }

  Future<void> _pickAbility() async {
    final v = await showDialog<String>(
      context: context,
      builder: (ctx) => SimpleDialog(
        title: const Text('とくせい', style: TextStyle(fontSize: 14)),
        children: [
          for (final a in _p.abilityOptions)
            SimpleDialogOption(
                onPressed: () => Navigator.pop(ctx, a), child: Text(a)),
        ],
      ),
    );
    if (v != null) setState(() => _p.ability = v);
  }

  Future<void> _pickItem() async {
    final items = await PokeDb.instance.itemNames();
    final usage = {
      for (final e in HomeStats.instance.entries(_p.name, HomeCategory.item))
        e.value: e.pct
    };
    if (!mounted) return;
    final v = await _searchSheet(
        title: '持ち物', options: items, usage: usage, hint: '持ち物を検索');
    if (v != null) setState(() => _p.item = v);
  }

  Future<void> _pickMoveAt(int idx) async {
    final v = await _moveSheet();
    if (v != null) {
      setState(() {
        while (_p.moves.length <= idx) {
          _p.moves.add(emptyMove());
        }
        _p.moves[idx] = v;
      });
    }
  }

  /// 文字入力検索つきの汎用ボトムシート（持ち物等）。使用率があれば降順。
  Future<String?> _searchSheet({
    required String title,
    required List<String> options,
    required String hint,
    Map<String, double>? usage,
  }) {
    String query = '';
    return showModalBottomSheet<String>(
      context: context,
      isScrollControlled: true,
      builder: (_) => StatefulBuilder(
        builder: (ctx, setSheet) {
          var filtered = query.isEmpty
              ? [...options]
              : options.where((o) => o.contains(query)).toList();
          if (usage != null) {
            filtered.sort(
                (a, b) => (usage[b] ?? -1).compareTo(usage[a] ?? -1));
          }
          return SafeArea(
            child: Padding(
              padding: EdgeInsets.only(
                  bottom: MediaQuery.of(ctx).viewInsets.bottom),
              child: SizedBox(
                height: 380,
                child: Column(
                  children: [
                    Padding(
                      padding: const EdgeInsets.fromLTRB(12, 12, 12, 4),
                      child: TextField(
                        autofocus: true,
                        decoration: InputDecoration(
                            isDense: true,
                            prefixIcon: const Icon(Icons.search, size: 18),
                            hintText: hint,
                            border: const OutlineInputBorder()),
                        onChanged: (v) => setSheet(() => query = v),
                      ),
                    ),
                    Expanded(
                      child: ListView(
                        children: [
                          for (final o in filtered)
                            ListTile(
                              dense: true,
                              title: Text(o == 'なし' ? 'もちものなし' : o),
                              trailing: usage?[o] != null
                                  ? Text('${usage![o]!.toStringAsFixed(1)}%',
                                      style: const TextStyle(
                                          fontSize: 12,
                                          color: Colors.blueGrey))
                                  : null,
                              onTap: () => Navigator.pop(ctx, o),
                            ),
                        ],
                      ),
                    ),
                  ],
                ),
              ),
            ),
          );
        },
      ),
    );
  }

  /// 技検索ボトムシート（DB 検索＋HOME 使用率上位を先頭に。Top と同等）。
  Future<BattleMove?> _moveSheet() {
    String query = '';
    List<BattleMove> filtered = const [];
    bool started = false;
    final home = HomeStats.instance.entries(_p.name, HomeCategory.waza);
    return showModalBottomSheet<BattleMove>(
      context: context,
      isScrollControlled: true,
      builder: (_) => StatefulBuilder(
        builder: (ctx, setSheet) {
          Future<void> run() async {
            final res = await PokeDb.instance.searchMoves(query);
            setSheet(() => filtered = res);
          }

          if (!started) {
            started = true;
            run();
          }
          final showHome = query.isEmpty && home.isNotEmpty;
          return SafeArea(
            child: Padding(
              padding: EdgeInsets.only(
                  bottom: MediaQuery.of(ctx).viewInsets.bottom),
              child: SizedBox(
                height: 380,
                child: Column(
                  children: [
                    Padding(
                      padding: const EdgeInsets.fromLTRB(12, 12, 12, 4),
                      child: TextField(
                        autofocus: true,
                        decoration: const InputDecoration(
                            isDense: true,
                            prefixIcon: Icon(Icons.search, size: 18),
                            hintText: '技名で検索（例: じしん）',
                            border: OutlineInputBorder()),
                        onChanged: (v) {
                          query = v;
                          run();
                        },
                      ),
                    ),
                    Expanded(
                      child: ListView(
                        children: [
                          if (showHome) ...[
                            const Padding(
                              padding: EdgeInsets.fromLTRB(12, 6, 12, 2),
                              child: Text('HOME 使用率上位',
                                  style: TextStyle(
                                      fontSize: 11,
                                      fontWeight: FontWeight.bold,
                                      color: Colors.blueGrey)),
                            ),
                            for (final e in home)
                              ListTile(
                                dense: true,
                                leading: const Icon(Icons.home_filled,
                                    size: 16, color: Colors.blueGrey),
                                title: Text(e.value),
                                trailing: Text('${e.pct.toStringAsFixed(1)}%',
                                    style: const TextStyle(
                                        fontSize: 11, color: Colors.blueGrey)),
                                onTap: () async {
                                  final mv = await PokeDb.instance
                                      .moveByName(e.value);
                                  if (mv != null && ctx.mounted) {
                                    Navigator.pop(ctx, mv);
                                  }
                                },
                              ),
                            const Divider(height: 8),
                          ],
                          for (final mv in filtered)
                            ListTile(
                              dense: true,
                              title: Text(mv.name),
                              subtitle: Text('${mv.category.jp} / 威力${mv.power}',
                                  style: const TextStyle(fontSize: 10)),
                              onTap: () => Navigator.pop(ctx, mv),
                            ),
                        ],
                      ),
                    ),
                  ],
                ),
              ),
            ),
          );
        },
      ),
    );
  }

  void _save() {
    _p.memo = _memoC.text.trim();
    Navigator.of(context).pop(_p);
  }

  @override
  Widget build(BuildContext context) {
    final p = _p;
    final empty = p.name.isEmpty;
    return Scaffold(
      appBar: AppBar(
        title: const Text('ポケモン編集'),
        actions: [
          IconButton(
              tooltip: '確定', icon: const Icon(Icons.check), onPressed: _save),
        ],
      ),
      body: SafeArea(
        child: ListView(
          padding: const EdgeInsets.all(12),
          children: [
            // 種族（検索窓）＋ 名前の横にメモ。
            Row(
              children: [
                InkWell(
                  onTap: _pickSpecies,
                  borderRadius: BorderRadius.circular(8),
                  child: Container(
                    width: 52,
                    height: 52,
                    decoration: BoxDecoration(
                      color: Colors.white,
                      borderRadius: BorderRadius.circular(8),
                      border: Border.all(color: Colors.black26),
                    ),
                    child: empty
                        ? const Icon(Icons.search, color: Colors.black38)
                        : Image.asset(p.imageAsset,
                            errorBuilder: (_, __, ___) =>
                                const SizedBox.shrink()),
                  ),
                ),
                const SizedBox(width: 8),
                InkWell(
                  onTap: _pickSpecies,
                  child: Text(empty ? '検索' : p.name,
                      style: const TextStyle(
                          fontSize: 15, fontWeight: FontWeight.bold)),
                ),
                const SizedBox(width: 8),
                Expanded(
                  child: TextField(
                    controller: _memoC,
                    decoration: const InputDecoration(
                        labelText: 'メモ', isDense: true),
                  ),
                ),
              ],
            ),
            if (!empty) ...[
              const SizedBox(height: 8),
              // 性格・特性・持ち物を1列に。
              Row(children: [
                Expanded(child: _tapField('せいかく', p.nature, _pickNature)),
                const SizedBox(width: 6),
                Expanded(child: _tapField('とくせい', p.ability, _pickAbility)),
                const SizedBox(width: 6),
                Expanded(child: _tapField('もちもの', p.item, _pickItem)),
              ]),
              const SizedBox(height: 8),
              // 努力値（2列。左列＝HP/こうげき/ぼうぎょ、右列＝とくこう/とくぼう/すばやさ）。
              for (int r = 0; r < 3; r++)
                Row(children: [
                  Expanded(child: _evCell(r)),
                  const SizedBox(width: 8),
                  Expanded(child: _evCell(3 + r)),
                ]),
              Align(
                alignment: Alignment.centerRight,
                child: Text('努力値合計 ${_p.ev.fold<int>(0, (a, b) => a + b)}',
                    style: const TextStyle(
                        fontSize: 11,
                        color: Colors.black54,
                        fontWeight: FontWeight.bold)),
              ),
              const SizedBox(height: 8),
              // 技（ラベル無し・2列×2段・空欄は技1〜4のヒント）。
              for (int r = 0; r < 2; r++)
                Row(children: [
                  Expanded(child: _moveCell(r * 2)),
                  const SizedBox(width: 8),
                  Expanded(child: _moveCell(r * 2 + 1)),
                ]),
            ],
          ],
        ),
      ),
    );
  }

  /// コンパクトなタップ選択フィールド（枠付き・ラベル小・値＋▾）。
  Widget _tapField(String label, String value, VoidCallback onTap) {
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(6),
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(6),
          border: Border.all(color: Colors.black26),
        ),
        child: Row(
          children: [
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(label,
                      style: const TextStyle(
                          fontSize: 9, color: Colors.black45)),
                  Text(value.isEmpty ? '—' : value,
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: const TextStyle(
                          fontSize: 13, fontWeight: FontWeight.w600)),
                ],
              ),
            ),
            const Icon(Icons.arrow_drop_down, size: 18, color: Colors.black38),
          ],
        ),
      ),
    );
  }

  /// 努力値1能力のコンパクトセル（ラベル＋ 0/−/値/＋/32）。
  Widget _evCell(int i) {
    Widget btn(String t, VoidCallback onTap) => InkWell(
          onTap: onTap,
          borderRadius: BorderRadius.circular(5),
          child: Container(
            width: 24,
            height: 26,
            alignment: Alignment.center,
            decoration: BoxDecoration(
                color: Colors.blueGrey.withValues(alpha: 0.12),
                borderRadius: BorderRadius.circular(5)),
            child: Text(t, style: const TextStyle(fontSize: 11)),
          ),
        );
    // 種族値・実数値（実数値は努力値に応じて動的に変化する）。
    final base = i < _p.baseStats.length ? _p.baseStats[i] : 0;
    final actual = i < _p.stats.length ? _p.stats[i] : 0;
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 2),
      child: FittedBox(
        fit: BoxFit.scaleDown,
        alignment: Alignment.centerLeft,
        child: Row(
          children: [
            // ラベル＋種族値（ラベル下に小さく種族値）。
            SizedBox(
                width: 50,
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Text(_evLabels[i],
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                        style: const TextStyle(fontSize: 11)),
                    Text('$base',
                        style: const TextStyle(
                            fontSize: 10,
                            color: Color(0xFF1F3A73),
                            fontWeight: FontWeight.w600)),
                  ],
                )),
            btn('0', () => setState(() => _p.ev[i] = 0)),
            const SizedBox(width: 3),
            btn('−',
                () => setState(() => _p.ev[i] = (_p.ev[i] - 1).clamp(0, 32))),
            SizedBox(
                width: 24,
                child: Text('${_p.ev[i]}',
                    textAlign: TextAlign.center,
                    style: const TextStyle(
                        fontSize: 13, fontWeight: FontWeight.bold))),
            btn('＋',
                () => setState(() => _p.ev[i] = (_p.ev[i] + 1).clamp(0, 32))),
            const SizedBox(width: 3),
            btn('32', () => setState(() => _p.ev[i] = 32)),
            const SizedBox(width: 5),
            // 実数値（茶系・右端）。
            SizedBox(
                width: 30,
                child: Text('$actual',
                    textAlign: TextAlign.center,
                    style: const TextStyle(
                        fontSize: 12,
                        color: Color(0xFF9C4221),
                        fontWeight: FontWeight.bold))),
          ],
        ),
      ),
    );
  }

  /// 技1枠のコンパクトセル（枠付き・タップで検索）。
  Widget _moveCell(int i) {
    final mv = i < _p.moves.length ? _p.moves[i] : emptyMove();
    return InkWell(
      onTap: () => _pickMoveAt(i),
      borderRadius: BorderRadius.circular(6),
      child: Container(
        margin: const EdgeInsets.symmetric(vertical: 2),
        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 6),
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(6),
          border: Border.all(color: Colors.black26),
        ),
        child: Row(
          children: [
            Expanded(
                child: Text(mv.isEmpty ? '技${i + 1}' : mv.name,
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: TextStyle(
                        fontSize: 13,
                        fontWeight: FontWeight.w600,
                        color: mv.isEmpty ? Colors.black38 : Colors.black87))),
            const Icon(Icons.search, size: 15, color: Colors.black38),
          ],
        ),
      ),
    );
  }
}
