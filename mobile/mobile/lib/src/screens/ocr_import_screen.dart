import 'dart:typed_data';

import 'package:flutter/material.dart';
import 'package:image_picker/image_picker.dart';

import '../data/sprite_template_matcher.dart';

/// スクショから相手パーティを取り込む画面（#3）。
///
/// 起動直後にスクショを取得する（[initialImage] があればそれを使い、無ければ即ギャラリーを
/// 開く＝中間ページを挟まない）。取得後は相手6体を matchTemplate（グレー＋CLAHE）で照合し、
/// 各スロットの**最上位候補を確信度に関わらず自動選択**して即 Top へ戻す。
/// 取り込み結果の修正は Top 画面側（相手パネルのタップ）で行う前提。
class OcrImportScreen extends StatefulWidget {
  const OcrImportScreen({super.key, this.initialImage});

  /// 渡されると起動直後にこの画像を解析する（ピッカーを開かない）。
  /// 編集ボタン長押しで取得した「最新スクショ」を流し込む用途。
  final Uint8List? initialImage;

  @override
  State<OcrImportScreen> createState() => _OcrImportScreenState();
}

class _OcrImportScreenState extends State<OcrImportScreen> {
  int _progress = 0;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) => _run());
  }

  /// スクショを取得→6スロット照合→最上位候補を自動選択して Top へ戻す。
  Future<void> _run() async {
    var bytes = widget.initialImage;
    if (bytes == null) {
      // ダブルタップ／メニュー経由：中間ページを出さず即ギャラリーを開く。
      final x = await ImagePicker().pickImage(source: ImageSource.gallery);
      if (x == null) {
        // キャンセル時はそのまま Top へ戻る（何も変更しない）。
        if (mounted) Navigator.of(context).pop();
        return;
      }
      bytes = await x.readAsBytes();
    }
    final results = await SpriteTemplateMatcher.instance.matchScreenshot(
      bytes,
      onProgress: (done, total) {
        if (mounted) setState(() => _progress = done);
      },
    );
    // 各スロット最上位候補をそのまま採用（閾値ゲートなし）。候補なしは空文字。
    final pids = <String>[
      for (final r in results)
        r.candidates.isNotEmpty ? r.candidates.first.pid : '',
    ];
    if (mounted) Navigator.of(context).pop(pids);
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('スクショ取込（相手）', style: TextStyle(fontSize: 16)),
      ),
      body: Center(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const CircularProgressIndicator(),
            const SizedBox(height: 12),
            Text('解析中… $_progress/${SpriteTemplateMatcher.slotCount}'),
          ],
        ),
      ),
    );
  }
}
