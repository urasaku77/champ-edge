import 'dart:typed_data';

import 'package:flutter/material.dart';
import 'package:image_picker/image_picker.dart';

import '../data/my_party_ocr.dart';

/// 自分パーティ取込画面。HOME/SV のパーティ画面スクショ2枚
/// （能力タブ・ステータスタブ）を選び、6体の種族・特性・持ち物・技・
/// 努力値・性格を読み取って返す。結果は呼び出し側（ホーム）が自分パーティへ反映。
class MyPartyImportScreen extends StatefulWidget {
  const MyPartyImportScreen({super.key});

  @override
  State<MyPartyImportScreen> createState() => _MyPartyImportScreenState();
}

class _MyPartyImportScreenState extends State<MyPartyImportScreen> {
  String? _abilityPath;
  Uint8List? _abilityBytes;
  String? _statusPath;
  Uint8List? _statusBytes;
  bool _busy = false;
  List<MyPartySlot>? _result;

  Future<void> _pick(bool ability) async {
    final x = await ImagePicker().pickImage(source: ImageSource.gallery);
    if (x == null) return;
    final bytes = await x.readAsBytes();
    setState(() {
      if (ability) {
        _abilityPath = x.path;
        _abilityBytes = bytes;
      } else {
        _statusPath = x.path;
        _statusBytes = bytes;
      }
    });
  }

  Future<void> _run() async {
    if (_abilityPath == null && _statusPath == null) return;
    setState(() => _busy = true);
    final slots = await MyPartyOcr.instance.parse(
      abilityPath: _abilityPath,
      abilityBytes: _abilityBytes,
      statusPath: _statusPath,
      statusBytes: _statusBytes,
    );
    if (mounted) {
      setState(() {
        _busy = false;
        _result = slots;
      });
    }
  }

  static const _evLabel = ['H', 'A', 'B', 'C', 'D', 'S'];

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('自分パーティ取込', style: TextStyle(fontSize: 16)),
        actions: [
          if (_result != null)
            TextButton(
              onPressed: () => Navigator.of(context).pop(_result),
              child: const Text('適用', style: TextStyle(color: Colors.white)),
            ),
        ],
      ),
      body: _busy
          ? const Center(child: CircularProgressIndicator())
          : _result != null
              ? _resultList()
              : _pickView(),
    );
  }

  Widget _pickView() {
    return Padding(
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          const Text('HOME/SVのパーティ画面スクショを2枚選びます。\n'
              '「能力」タブと「ステータス」タブを撮ってください。\n'
              '（片方だけでも取込可能）'),
          const SizedBox(height: 16),
          OutlinedButton.icon(
            icon: Icon(
                _abilityPath != null ? Icons.check_circle : Icons.photo_library,
                color: _abilityPath != null ? Colors.green : null),
            label: Text(_abilityPath != null ? '能力タブ：選択済み' : '能力タブを選ぶ'),
            onPressed: () => _pick(true),
          ),
          const SizedBox(height: 8),
          OutlinedButton.icon(
            icon: Icon(
                _statusPath != null ? Icons.check_circle : Icons.photo_library,
                color: _statusPath != null ? Colors.green : null),
            label: Text(_statusPath != null ? 'ステータスタブ：選択済み' : 'ステータスタブを選ぶ'),
            onPressed: () => _pick(false),
          ),
          const SizedBox(height: 24),
          FilledButton(
            onPressed:
                (_abilityPath != null || _statusPath != null) ? _run : null,
            child: const Text('読み取る'),
          ),
        ],
      ),
    );
  }

  Widget _resultList() {
    final slots = _result!;
    return ListView.builder(
      padding: const EdgeInsets.all(8),
      itemCount: slots.length,
      itemBuilder: (_, i) {
        final s = slots[i];
        final evStr = [
          for (var k = 0; k < 6; k++)
            if (s.evs[k] > 0) '${_evLabel[k]}${s.evs[k]}'
        ].join(' ');
        return Card(
          margin: const EdgeInsets.symmetric(vertical: 4),
          child: ListTile(
            title: Text(s.name.isEmpty ? '（未認識）' : s.name,
                style: const TextStyle(fontWeight: FontWeight.bold)),
            subtitle: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text('特性: ${s.ability}  持ち物: ${s.item}'),
                Text('性格: ${s.nature}  努力値: $evStr'),
                Text('技: ${s.moves.where((m) => m.isNotEmpty).join(' / ')}'),
              ],
            ),
          ),
        );
      },
    );
  }
}
