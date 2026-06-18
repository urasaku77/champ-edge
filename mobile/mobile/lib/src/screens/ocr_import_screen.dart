import 'dart:typed_data';

import 'package:flutter/material.dart';
import 'package:image/image.dart' as img;
import 'package:image_picker/image_picker.dart';

import '../data/sprite_template_matcher.dart';
import 'pokemon_picker.dart';

/// スクショから相手パーティを取り込む画面（#3）。
/// 選出画面のスクショを選ぶと、相手6体を元 champ-edge と同方式の
/// matchTemplate（グレー＋CLAHE）で自動照合し、確信度が高いものは自動確定。
/// 低いスロットは候補から手選択／検索で補正できる。「適用」で相手へ反映。
class OcrImportScreen extends StatefulWidget {
  const OcrImportScreen({super.key});

  @override
  State<OcrImportScreen> createState() => _OcrImportScreenState();
}

// 自動確定の閾値（検証: 登録済み正解は0.84〜0.97、非該当は≤0.79）。
const double _kConfident = 0.80;

class _Slot {
  Uint8List? thumb;
  List<MatchResult> candidates = const [];
  String? selectedPid;
}

class _OcrImportScreenState extends State<OcrImportScreen> {
  final List<_Slot> _slots =
      List.generate(SpriteTemplateMatcher.slotCount, (_) => _Slot());
  bool _busy = false;
  bool _hasImage = false;
  int _progress = 0;

  Future<void> _pick() async {
    final x = await ImagePicker().pickImage(source: ImageSource.gallery);
    if (x == null) return;
    setState(() {
      _busy = true;
      _progress = 0;
    });
    final bytes = await x.readAsBytes();
    // サムネイル切り出し（表示用・照合とは独立）
    _buildThumbs(bytes);
    final results = await SpriteTemplateMatcher.instance.matchScreenshot(
      bytes,
      onProgress: (done, total) {
        if (mounted) setState(() => _progress = done);
      },
    );
    for (var i = 0; i < _slots.length && i < results.length; i++) {
      final s = _slots[i];
      s.candidates = results[i];
      s.selectedPid = (s.candidates.isNotEmpty &&
              s.candidates.first.score >= _kConfident)
          ? s.candidates.first.pid
          : null;
    }
    if (mounted) {
      setState(() {
        _busy = false;
        _hasImage = true;
      });
    }
  }

  void _buildThumbs(Uint8List bytes) {
    final im = img.decodeImage(bytes);
    if (im == null) return;
    final w = im.width, h = im.height;
    final x0 = (w * 0.772).round();
    final cw = (w * (0.846 - 0.772)).round();
    for (var i = 0; i < _slots.length; i++) {
      var y0 = (h * 0.05 + h * 0.1385 * i).round();
      var ch = (h * 0.20).round();
      if (y0 + ch > h) ch = h - y0;
      if (ch < 8 || x0 + cw > w) continue;
      final c = img.copyCrop(im, x: x0, y: y0, width: cw, height: ch);
      _slots[i].thumb = Uint8List.fromList(img.encodePng(c));
    }
  }

  Future<void> _searchSlot(int i) async {
    final pid = await pickPokemon(context);
    if (pid != null) setState(() => _slots[i].selectedPid = pid);
  }

  void _apply() {
    Navigator.of(context).pop([for (final s in _slots) s.selectedPid ?? '']);
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('スクショ取込（相手）', style: TextStyle(fontSize: 16)),
        actions: [
          if (_hasImage)
            TextButton(
              onPressed: _apply,
              child: const Text('適用', style: TextStyle(color: Colors.white)),
            ),
        ],
      ),
      body: _busy
          ? Center(
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  const CircularProgressIndicator(),
                  const SizedBox(height: 12),
                  Text('解析中… $_progress/${SpriteTemplateMatcher.slotCount}'),
                ],
              ),
            )
          : !_hasImage
              ? Center(
                  child: Column(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      const Padding(
                        padding: EdgeInsets.all(24),
                        child: Text(
                          '選出画面のスクショを選んでください。\n相手6体を自動で読み取ります。\n（外れたスロットは候補タップ／検索で修正）',
                          textAlign: TextAlign.center,
                        ),
                      ),
                      FilledButton.icon(
                        onPressed: _pick,
                        icon: const Icon(Icons.photo_library),
                        label: const Text('スクショを選ぶ'),
                      ),
                    ],
                  ),
                )
              : ListView.builder(
                  padding: const EdgeInsets.all(8),
                  itemCount: _slots.length,
                  itemBuilder: (_, i) => _slotRow(i),
                ),
    );
  }

  Widget _slotRow(int i) {
    final s = _slots[i];
    final top = s.candidates.isNotEmpty ? s.candidates.first : null;
    final confident = top != null && top.score >= _kConfident;
    return Card(
      margin: const EdgeInsets.symmetric(vertical: 4),
      child: Padding(
        padding: const EdgeInsets.all(8),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Container(
              width: 56,
              height: 56,
              color: Colors.black12,
              child: s.thumb != null
                  ? Image.memory(s.thumb!, fit: BoxFit.contain)
                  : null,
            ),
            const SizedBox(width: 8),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      Text(
                        confident
                            ? '自動判定'
                            : (top == null ? '候補なし' : '要確認'),
                        style: TextStyle(
                          fontSize: 12,
                          color: confident ? Colors.green : Colors.orange,
                          fontWeight: FontWeight.bold,
                        ),
                      ),
                      if (top != null)
                        Text('  (最大 ${(top.score * 100).round()}%)',
                            style: const TextStyle(
                                fontSize: 11, color: Colors.black54)),
                      const Spacer(),
                      IconButton(
                        tooltip: '検索で選ぶ',
                        icon: const Icon(Icons.search, size: 20),
                        onPressed: () => _searchSlot(i),
                      ),
                    ],
                  ),
                  Wrap(
                    spacing: 4,
                    runSpacing: 4,
                    children: [
                      for (final c in s.candidates) _candIcon(i, c.pid),
                      if (s.selectedPid != null &&
                          !s.candidates.any((c) => c.pid == s.selectedPid))
                        _candIcon(i, s.selectedPid!),
                    ],
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _candIcon(int i, String pid) {
    final sel = _slots[i].selectedPid == pid;
    return GestureDetector(
      onTap: () => setState(() => _slots[i].selectedPid = pid),
      child: Container(
        width: 44,
        height: 44,
        decoration: BoxDecoration(
          border: Border.all(
              color: sel ? Colors.orange : Colors.black26,
              width: sel ? 2.5 : 1),
          borderRadius: BorderRadius.circular(6),
        ),
        child: Image.asset('assets/pokemon/$pid.png',
            fit: BoxFit.contain,
            errorBuilder: (_, __, ___) => const SizedBox.shrink()),
      ),
    );
  }
}
