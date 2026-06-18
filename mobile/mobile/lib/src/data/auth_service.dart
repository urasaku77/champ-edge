import 'dart:io' show Platform;

import 'package:firebase_auth/firebase_auth.dart';
import 'package:firebase_core/firebase_core.dart';
import 'package:flutter/foundation.dart';
import 'package:google_sign_in/google_sign_in.dart';

import '../../firebase_options.dart';

/// 認証（Google／将来 Apple）。Firebase Auth を用いる。
///
/// 招待制の allowlist 判定・招待コード消費は [InviteService] が担当し、本サービスは
/// 「サインインしているか」までを扱う。未サインインでもローカル機能は全て使える。
class AuthService {
  AuthService._();
  static final AuthService instance = AuthService._();

  // GoogleService-Info.plist / google-services.json 由来のクライアントID。
  static const String _iosClientId =
      '994765802690-0ftq4l4db02ot0s6hf2k9b5erluvh4mq.apps.googleusercontent.com';
  // Web(サーバー)クライアントID。idToken の audience に使う。
  static const String _webServerClientId =
      '994765802690-gq1fv7u8uoou4egk89ch6iin8l5amru5.apps.googleusercontent.com';

  bool _gsiInitialized = false;

  /// Firebase を初期化（冪等）。成功で true。失敗時は false を返し、ゲートが再試行を促す。
  Future<bool> ensureFirebaseInitialized() async {
    if (Firebase.apps.isNotEmpty) return true;
    try {
      await Firebase.initializeApp(
        options: DefaultFirebaseOptions.currentPlatform,
      );
      return true;
    } catch (e) {
      debugPrint('[AuthService] Firebase init failed: $e');
      return false;
    }
  }

  FirebaseAuth get _auth => FirebaseAuth.instance;

  User? get currentUser => _auth.currentUser;
  Stream<User?> authStateChanges() => _auth.authStateChanges();

  /// GoogleSignIn を初期化（冪等）。Google 認証・Drive 認可の前に必要。
  Future<void> ensureGoogleInitialized() async {
    if (_gsiInitialized) return;
    await GoogleSignIn.instance.initialize(
      clientId: Platform.isIOS ? _iosClientId : null,
      serverClientId: _webServerClientId,
    );
    _gsiInitialized = true;
  }

  /// Google でサインイン。成功すると Firebase の [User] を返す。
  /// キャンセル時は null、その他の失敗は例外を投げる。
  Future<User?> signInWithGoogle() async {
    await ensureGoogleInitialized();
    final GoogleSignInAccount account;
    try {
      account = await GoogleSignIn.instance.authenticate();
    } on GoogleSignInException catch (e) {
      if (e.code == GoogleSignInExceptionCode.canceled) return null;
      rethrow;
    }
    final idToken = account.authentication.idToken;
    if (idToken == null) {
      throw StateError('Google idToken を取得できませんでした。');
    }
    final credential = GoogleAuthProvider.credential(idToken: idToken);
    final result = await _auth.signInWithCredential(credential);
    return result.user;
  }

  /// Apple でサインイン（iOS ネイティブ）。キャンセル時は null。
  /// 事前条件：Apple Developer で App ID に Sign in with Apple 有効、
  /// Firebase で Apple プロバイダ有効、Xcode に Sign in with Apple ケイパビリティ。
  Future<User?> signInWithApple() async {
    final provider = AppleAuthProvider()
      ..addScope('email')
      ..addScope('name');
    try {
      final result = await _auth.signInWithProvider(provider);
      return result.user;
    } on FirebaseAuthException catch (e) {
      if (e.code == 'canceled' || e.code == 'web-context-canceled') return null;
      rethrow;
    }
  }

  Future<void> signOut() async {
    try {
      await GoogleSignIn.instance.signOut();
    } catch (e) {
      debugPrint('[AuthService] google signOut failed: $e');
    }
    await _auth.signOut();
  }
}
