// Firebase 初期化オプション（手動生成。flutterfire configure 相当）。
// 値は GoogleService-Info.plist / google-services.json（project: champedge）に由来。
// API キーはクライアント識別子であり機密ではない（アクセス制御は Firestore ルールで行う）。
import 'package:firebase_core/firebase_core.dart' show FirebaseOptions;
import 'package:flutter/foundation.dart'
    show defaultTargetPlatform, kIsWeb, TargetPlatform;

class DefaultFirebaseOptions {
  static FirebaseOptions get currentPlatform {
    if (kIsWeb) {
      throw UnsupportedError('Web はサポート対象外です。');
    }
    switch (defaultTargetPlatform) {
      case TargetPlatform.android:
        return android;
      case TargetPlatform.iOS:
        return ios;
      default:
        throw UnsupportedError(
          '${defaultTargetPlatform.name} はサポート対象外です（iOS/Android のみ）。',
        );
    }
  }

  static const FirebaseOptions android = FirebaseOptions(
    apiKey: 'AIzaSyDyzvdvjyFa_c3CMkdvxQHy-7BsavPAL8Q',
    appId: '1:994765802690:android:b1c075882a3ebded8fbf5b',
    messagingSenderId: '994765802690',
    projectId: 'champedge',
    storageBucket: 'champedge.firebasestorage.app',
  );

  static const FirebaseOptions ios = FirebaseOptions(
    apiKey: 'AIzaSyCLSw1_-PEFx-vQt_oyFoiYlxMYHAqiKTg',
    appId: '1:994765802690:ios:f610df09d29c45548fbf5b',
    messagingSenderId: '994765802690',
    projectId: 'champedge',
    storageBucket: 'champedge.firebasestorage.app',
    iosBundleId: 'io.github.urasaku77.champedge',
  );
}
