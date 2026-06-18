import 'dart:io';
import 'dart:math';

import 'package:cloud_firestore/cloud_firestore.dart';
import 'package:firebase_auth/firebase_auth.dart';
import 'package:path/path.dart' as p;
import 'package:path_provider/path_provider.dart';

/// 招待コードの検証・消費と allowlist（users）判定。
///
/// データモデル（FIREBASE_ADMIN.md / firestore.rules と一致）：
/// - invites/{code} : { email, createdBy, createdAt, used, usedBy, usedAt, expiresAt? }
/// - users/{uid}    : { name, email, createdAt, inviteCode }  存在＝利用許可
/// - admins/{uid}   : 存在＝管理者
class InviteService {
  InviteService._();
  static final InviteService instance = InviteService._();

  FirebaseFirestore get _db => FirebaseFirestore.instance;

  // 一度オンラインで許可確認できたら、その uid をローカルに記録しておく。
  // オフライン起動時はこの記録にフォールバックし、認証済みユーザーを締め出さない。
  Future<File> _verifiedFile() async {
    final dir = await getApplicationDocumentsDirectory();
    return File(p.join(dir.path, 'cloud_verified.txt'));
  }

  Future<void> _writeVerified(String uid) async {
    try {
      await (await _verifiedFile()).writeAsString(uid);
    } catch (_) {}
  }

  Future<bool> _verifiedLocally(String uid) async {
    try {
      final f = await _verifiedFile();
      if (await f.exists()) return (await f.readAsString()).trim() == uid;
    } catch (_) {}
    return false;
  }

  /// allowlist 判定。
  /// - オンラインで Firestore を確認できた：allowed / denied（成功時はローカルにも記録）
  /// - 確認できない（オフライン等）：過去に確認済みなら allowed、未確認なら unknown
  ///   （unknown は「拒否」ではなく「今は判定不能」。ゲートは再試行を促す）
  Future<AllowStatus> allowStatus(String uid) async {
    try {
      final doc = await _db.collection('users').doc(uid).get();
      if (doc.exists) {
        await _writeVerified(uid);
        return AllowStatus.allowed;
      }
      return AllowStatus.denied;
    } catch (_) {
      return await _verifiedLocally(uid)
          ? AllowStatus.allowed
          : AllowStatus.unknown;
    }
  }

  /// 管理者か（users/{uid}.role == 'admin'）。
  Future<bool> isAdmin(String uid) async {
    final doc = await _db.collection('users').doc(uid).get();
    return doc.exists && (doc.data()?['role'] == 'admin');
  }

  /// 招待コードを検証して消費し、users に登録する。
  /// トランザクションで invites を used に更新し users/{uid} を作成する。
  Future<RedeemResult> redeem(String code, User user) async {
    // コード照合のみ（メール一致は不要）。Apple のメール非公開でも動く。
    final email = user.email ?? '';
    final trimmed = code.trim();
    if (trimmed.isEmpty) return RedeemResult.error('招待コードを入力してください。');

    final inviteRef = _db.collection('invites').doc(trimmed);
    final userRef = _db.collection('users').doc(user.uid);

    try {
      final result = await _db.runTransaction<RedeemResult>((tx) async {
        final invite = await tx.get(inviteRef);
        if (!invite.exists) {
          return RedeemResult.error('招待コードが見つかりません。');
        }
        final data = invite.data()!;
        if (data['used'] == true) {
          return RedeemResult.error('この招待コードは既に使用されています。');
        }
        final expiresAt = data['expiresAt'];
        if (expiresAt is Timestamp &&
            expiresAt.toDate().isBefore(DateTime.now())) {
          return RedeemResult.error('この招待コードは有効期限切れです。');
        }

        tx.update(inviteRef, {
          'used': true,
          'usedBy': user.uid,
          'usedAt': FieldValue.serverTimestamp(),
        });
        final inviteName = (data['name'] as String?)?.trim();
        tx.set(userRef, {
          // 招待時に管理者が入れた名前を優先（無ければ Google 表示名）
          'name': (inviteName != null && inviteName.isNotEmpty)
              ? inviteName
              : (user.displayName ?? ''),
          'email': email,
          'createdAt': FieldValue.serverTimestamp(),
          'inviteCode': trimmed,
          'role': 'user', // 一般ユーザー（管理者昇格は Console のみ）
        });
        return RedeemResult.success();
      });
      if (result.ok) await _writeVerified(user.uid);
      return result;
    } on FirebaseException catch (e) {
      return RedeemResult.error('登録に失敗しました（${e.code}）。');
    }
  }

  // ---- 管理者用（users.role == 'admin' のみルールで許可される） ----

  /// 招待コードを発行（対象 Gmail＋表示名）。生成したコード文字列を返す。
  /// ここで入れた name は登録時に users/{uid}.name として採用される。
  Future<String> issueInvite(String email, String name) async {
    final code = _generateCode();
    await _db.collection('invites').doc(code).set({
      'email': email.trim().toLowerCase(),
      'name': name.trim(),
      'used': false,
      'usedBy': null,
      'usedAt': null,
      'createdBy': FirebaseAuth.instance.currentUser?.uid,
      'createdAt': FieldValue.serverTimestamp(),
    });
    return code;
  }

  /// 自分の users ドキュメント（表示名取得などに使用）。
  Future<UserEntry?> getUser(String uid) async {
    final d = await _db.collection('users').doc(uid).get();
    final m = d.data();
    if (m == null) return null;
    return UserEntry.fromMap(uid, m);
  }

  static String _generateCode() {
    // 紛らわしい文字（0/O/1/I 等）を除外した 8 桁。
    const chars = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789';
    final r = Random.secure();
    return List.generate(8, (_) => chars[r.nextInt(chars.length)]).join();
  }

  /// 登録ユーザー一覧（登録日の新しい順）。
  Future<List<UserEntry>> listUsers() async {
    final snap = await _db.collection('users').get();
    final list = snap.docs.map(UserEntry.fromDoc).toList();
    list.sort((a, b) => (b.createdAt ?? DateTime(0))
        .compareTo(a.createdAt ?? DateTime(0)));
    return list;
  }

  /// 招待コード一覧（作成日の新しい順）。
  Future<List<InviteEntry>> listInvites() async {
    final snap = await _db.collection('invites').get();
    final list = snap.docs.map(InviteEntry.fromDoc).toList();
    list.sort((a, b) => (b.createdAt ?? DateTime(0))
        .compareTo(a.createdAt ?? DateTime(0)));
    return list;
  }

  /// ユーザーを無効化（allowlist から削除）。
  Future<void> removeUser(String uid) =>
      _db.collection('users').doc(uid).delete();

  /// 招待コードを削除。
  Future<void> deleteInvite(String code) =>
      _db.collection('invites').doc(code).delete();
}

DateTime? _ts(dynamic v) => v is Timestamp ? v.toDate() : null;

class UserEntry {
  final String uid;
  final String name;
  final String email;
  final String role;
  final DateTime? createdAt;
  const UserEntry({
    required this.uid,
    required this.name,
    required this.email,
    required this.role,
    required this.createdAt,
  });
  factory UserEntry.fromDoc(QueryDocumentSnapshot<Map<String, dynamic>> d) =>
      UserEntry.fromMap(d.id, d.data());
  factory UserEntry.fromMap(String uid, Map<String, dynamic> m) => UserEntry(
        uid: uid,
        name: (m['name'] as String?) ?? '',
        email: (m['email'] as String?) ?? '',
        role: (m['role'] as String?) ?? 'user',
        createdAt: _ts(m['createdAt']),
      );
  bool get isAdmin => role == 'admin';
}

class InviteEntry {
  final String code;
  final String email;
  final String name;
  final bool used;
  final DateTime? createdAt;
  const InviteEntry({
    required this.code,
    required this.email,
    required this.name,
    required this.used,
    required this.createdAt,
  });
  factory InviteEntry.fromDoc(QueryDocumentSnapshot<Map<String, dynamic>> d) {
    final m = d.data();
    return InviteEntry(
      code: d.id,
      email: (m['email'] as String?) ?? '',
      name: (m['name'] as String?) ?? '',
      used: m['used'] == true,
      createdAt: _ts(m['createdAt']),
    );
  }
}

/// allowlist 判定の結果。unknown は「拒否」ではなく接続不能による判定不能。
enum AllowStatus { allowed, denied, unknown }

class RedeemResult {
  final bool ok;
  final String? message;
  const RedeemResult._(this.ok, this.message);
  factory RedeemResult.success() => const RedeemResult._(true, null);
  factory RedeemResult.error(String m) => RedeemResult._(false, m);
}
