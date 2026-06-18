import '../model/battle_record.dart';

/// パーティ一致の種別（旧 champ-edge の「並びまで一致／中身だけ同じ」）。
enum PartyMatch { exactOrder, sameSet, none }

/// target（相手パーティ6枠）と candidate（候補パーティ6枠）の一致種別を返す。
/// '-1'/空は無視し、メガ統合の有無を選べる。
///
/// - 構成（多重集合）が一致し並び（出現順）も同じ → exactOrder（並びまで一致）
/// - 構成のみ一致 → sameSet（中身だけ同じ）
/// - それ以外 → none
PartyMatch matchParty(List<String> target, List<String> candidate,
    {bool megaMerge = true}) {
  String norm(String p) => megaMerge ? normalizeMegaForm(p) : p;
  List<String> clean(List<String> xs) =>
      [for (final x in xs) if (x != '-1' && x.isNotEmpty) norm(x)];
  final t = clean(target);
  final c = clean(candidate);
  if (t.isEmpty || c.isEmpty) return PartyMatch.none;
  // 構成（多重集合）一致＝ソート列の一致。
  final ts = [...t]..sort();
  final cs = [...c]..sort();
  if (!_listEquals(ts, cs)) return PartyMatch.none;
  // 並び（出現順）も一致なら exactOrder。
  return _listEquals(t, c) ? PartyMatch.exactOrder : PartyMatch.sameSet;
}

bool _listEquals(List<String> a, List<String> b) {
  if (a.length != b.length) return false;
  for (var i = 0; i < a.length; i++) {
    if (a[i] != b[i]) return false;
  }
  return true;
}
