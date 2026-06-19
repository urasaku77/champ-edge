import 'dart:typed_data';

import 'package:flutter/material.dart';
import 'package:image_picker/image_picker.dart';

import '../data/my_party_ocr.dart';

/// 自分パーティ取込画面。HOME/SV のパーティ画面スクショ2枚
/// （能力タブ・ステータスタブ）を選び、6体を読み取って**確認画面を出さずに**
/// そのまま返す（呼び出し側＝ホームが自分パーティへ即反映）。相手取込と同様の挙動。
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

  Future<void> _runAndApply() async {
    if (_abilityPath == null && _statusPath == null) return;
    setState(() => _busy = true);
    final slots = await MyPartyOcr.instance.parse(
      abilityPath: _abilityPath,
      abilityBytes: _abilityBytes,
      statusPath: _statusPath,
      statusBytes: _statusBytes,
    );
    // 確認画面は出さず、読み取った値をそのまま返す（ホームが反映）。
    if (mounted) Navigator.of(context).pop(slots);
  }

  @override
  Widget build(BuildContext context) {
    final ready = _abilityPath != null || _statusPath != null;
    return Scaffold(
      appBar: AppBar(
          title: const Text('自分パーティ取込', style: TextStyle(fontSize: 16))),
      body: _busy
          ? const Center(
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  CircularProgressIndicator(),
                  SizedBox(height: 12),
                  Text('読み取り中…'),
                ],
              ),
            )
          : Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  const Text('HOME/SVのパーティ画面スクショを選びます。\n'
                      '「能力」タブと「ステータス」タブの2枚を選んでください。\n'
                      '（片方だけでも取込可・読み取った値はそのまま反映されます）'),
                  const SizedBox(height: 16),
                  OutlinedButton.icon(
                    icon: Icon(
                        _abilityPath != null
                            ? Icons.check_circle
                            : Icons.photo_library,
                        color: _abilityPath != null ? Colors.green : null),
                    label: Text(
                        _abilityPath != null ? '能力タブ：選択済み' : '能力タブを選ぶ'),
                    onPressed: () => _pick(true),
                  ),
                  const SizedBox(height: 8),
                  OutlinedButton.icon(
                    icon: Icon(
                        _statusPath != null
                            ? Icons.check_circle
                            : Icons.photo_library,
                        color: _statusPath != null ? Colors.green : null),
                    label: Text(_statusPath != null
                        ? 'ステータスタブ：選択済み'
                        : 'ステータスタブを選ぶ'),
                    onPressed: () => _pick(false),
                  ),
                  const SizedBox(height: 24),
                  FilledButton(
                    onPressed: ready ? _runAndApply : null,
                    child: const Text('読み取って反映'),
                  ),
                ],
              ),
            ),
    );
  }
}
