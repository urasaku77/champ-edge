import 'package:flutter/services.dart';

class PlatformChannels {
  static const MethodChannel _channel = MethodChannel('champ_edge_mobile/platform');

  static Future<String> requestScreenshotImport() async {
    try {
      final result = await _channel.invokeMethod<String>('requestScreenshotImport');
      return result ?? 'ネイティブ機能からの応答なし';
    } on PlatformException catch (e) {
      return 'ネイティブ呼び出しエラー: ${e.message}';
    }
  }
}
