import 'dart:convert';

import 'package:google_sign_in/google_sign_in.dart';
import 'package:http/http.dart' as http;

import 'auth_service.dart';

/// 本人の Google Drive（アプリ専用フォルダ appDataFolder）へバックアップ JSON を
/// 保存/取得する最小クライアント。運営者からは見えない本人専用領域。
///
/// 認可は Google サインイン済みアカウントに drive.appdata スコープを付与して行う。
/// （Apple サインインのユーザーは Google 認可が別途必要になる＝運用は Google 推奨）
class DriveSync {
  DriveSync._();
  static final DriveSync instance = DriveSync._();

  static const _scope = 'https://www.googleapis.com/auth/drive.appdata';
  static const _fileName = 'champedge_backup.json';

  /// 既に Drive 認可済みか（プロンプトを出さずに確認）。
  Future<bool> isAuthorized() async {
    await AuthService.instance.ensureGoogleInitialized();
    final authz = await GoogleSignIn.instance.authorizationClient
        .authorizationForScopes([_scope]);
    return authz != null;
  }

  Future<String> _token({bool prompt = true}) async {
    await AuthService.instance.ensureGoogleInitialized();
    final client = GoogleSignIn.instance.authorizationClient;
    var authz = await client.authorizationForScopes([_scope]);
    if (authz == null && prompt) authz = await client.authorizeScopes([_scope]);
    if (authz == null) {
      throw StateError('Google ドライブの利用許可が必要です。');
    }
    return authz.accessToken;
  }

  Map<String, String> _auth(String token) => {'Authorization': 'Bearer $token'};

  Future<({String id, DateTime? modified})?> _find(String token) async {
    final uri = Uri.parse(
      'https://www.googleapis.com/drive/v3/files'
      '?spaces=appDataFolder'
      "&q=${Uri.encodeQueryComponent("name='$_fileName'")}"
      '&fields=${Uri.encodeQueryComponent("files(id,modifiedTime)")}',
    );
    final res = await http.get(uri, headers: _auth(token));
    if (res.statusCode != 200) return null;
    final files = (jsonDecode(res.body)['files'] as List?) ?? const [];
    if (files.isEmpty) return null;
    final f = files.first as Map<String, dynamic>;
    return (
      id: f['id'] as String,
      modified: DateTime.tryParse(f['modifiedTime'] as String? ?? ''),
    );
  }

  /// バックアップ JSON を保存（既存があれば上書き）。
  Future<void> upload(String content) async {
    final token = await _token();
    final existing = await _find(token);
    if (existing == null) {
      const boundary = 'champedgeBoundary7723';
      final meta = jsonEncode({
        'name': _fileName,
        'parents': ['appDataFolder'],
      });
      final body = '--$boundary\r\n'
          'Content-Type: application/json; charset=UTF-8\r\n\r\n$meta\r\n'
          '--$boundary\r\n'
          'Content-Type: application/json; charset=UTF-8\r\n\r\n$content\r\n'
          '--$boundary--';
      final res = await http.post(
        Uri.parse(
            'https://www.googleapis.com/upload/drive/v3/files?uploadType=multipart'),
        headers: {
          ..._auth(token),
          'Content-Type': 'multipart/related; boundary=$boundary',
        },
        body: body,
      );
      if (res.statusCode >= 300) {
        throw StateError('アップロードに失敗しました（${res.statusCode}）。');
      }
    } else {
      final res = await http.patch(
        Uri.parse('https://www.googleapis.com/upload/drive/v3/files/'
            '${existing.id}?uploadType=media'),
        headers: {..._auth(token), 'Content-Type': 'application/json'},
        body: content,
      );
      if (res.statusCode >= 300) {
        throw StateError('更新に失敗しました（${res.statusCode}）。');
      }
    }
  }

  /// バックアップ JSON を取得（無ければ null）。
  Future<String?> download() async {
    final token = await _token();
    final existing = await _find(token);
    if (existing == null) return null;
    final res = await http.get(
      Uri.parse('https://www.googleapis.com/drive/v3/files/'
          '${existing.id}?alt=media'),
      headers: _auth(token),
    );
    if (res.statusCode != 200) return null;
    return utf8.decode(res.bodyBytes);
  }

  /// クラウド上のバックアップの最終更新時刻（無ければ null）。
  Future<DateTime?> lastBackupTime() async {
    final token = await _token(prompt: false);
    final existing = await _find(token);
    return existing?.modified;
  }
}
