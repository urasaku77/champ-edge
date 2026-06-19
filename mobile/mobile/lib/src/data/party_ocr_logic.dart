/// 自分パーティ画面OCRの確定的ロジック（純粋関数）。
///
/// image_parser.py の `_parse_ev` と `pokedata/nature.py: get_seikaku_from_arrows`
/// を Dart へ移植。OCRエンジンに依存しない部分なので単体テスト可能。
library;

/// ステータス行の数字トークン列から努力値(0–32)を取り出す。
/// _parse_ev の移植：右から ≤32 の最初のトークンを採用。隣接1桁2つは
/// 分割された2桁努力値の可能性があるため結合を試す。連結("18732")は
/// 末尾2桁→1桁の順で分離（"18732"→32 を優先）。
int parseEv(String text) {
  final nums =
      RegExp(r'\d+').allMatches(text).map((m) => m.group(0)!).toList();
  if (nums.isEmpty) return 0;
  for (var i = nums.length - 1; i >= 0; i--) {
    final v = int.parse(nums[i]);
    if (v <= 32) {
      if (i > 0 && nums[i].length == 1 && nums[i - 1].length == 1) {
        final combined = int.parse(nums[i - 1] + nums[i]);
        if (combined <= 32) return combined;
      }
      return v;
    }
  }
  final last = int.parse(nums.last);
  for (final digits in [2, 1]) {
    final mod = digits == 2 ? 100 : 10;
    final evPart = last % mod;
    final statPart = last ~/ mod;
    if (evPart <= 32 && statPart >= 40) return evPart;
  }
  return 0;
}

/// 性格表：性格名 → (上昇ステータス, 下降ステータス)。キーは H/A/B/C/D/S。
const Map<String, List<String>> kNatureArrows = {
  'さみしがり': ['A', 'B'],
  'いじっぱり': ['A', 'C'],
  'やんちゃ': ['A', 'D'],
  'ゆうかん': ['A', 'S'],
  'ずぶとい': ['B', 'A'],
  'わんぱく': ['B', 'C'],
  'のうてんき': ['B', 'D'],
  'のんき': ['B', 'S'],
  'ひかえめ': ['C', 'A'],
  'おっとり': ['C', 'B'],
  'うっかりや': ['C', 'D'],
  'れいせい': ['C', 'S'],
  'おだやか': ['D', 'A'],
  'おとなしい': ['D', 'B'],
  'しんちょう': ['D', 'C'],
  'なまいき': ['D', 'S'],
  'おくびょう': ['S', 'A'],
  'せっかち': ['S', 'B'],
  'ようき': ['S', 'C'],
  'むじゃき': ['S', 'D'],
};

/// 上昇↑/下降↓のステータスキーから性格名を返す。無補正/不明は 'まじめ'。
String natureFromArrows(String? up, String? down) {
  if (up == null || down == null || up == down) return 'まじめ';
  for (final e in kNatureArrows.entries) {
    if (e.value[0] == up && e.value[1] == down) return e.key;
  }
  return 'まじめ';
}
