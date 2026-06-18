/// 旧 `calc.py` は `decimal.Decimal` の `quantize` で整数へ丸めている。
/// ここでは同じ結果を整数演算で再現する（浮動小数の誤差を避けるため）。
///
/// 対象の丸めモードは 3 種類:
/// - ROUND_FLOOR        … 切り捨て（負数は -∞ 方向だが本計算は非負のみ）
/// - ROUND_HALF_UP      … 四捨五入
/// - ROUND_HALF_DOWN    … 五捨五超入（ちょうど 0.5 は切り捨て、それ超で切り上げ）
///
/// いずれも `value * num / den` を計算してから丸める形に統一する。
library;

/// `floor(num / den)`（num, den は非負）。
int floorDiv(int num, int den) => num ~/ den;

/// `floor(value * mulNum / mulDen)`。
int floorMul(int value, int mulNum, int mulDen) =>
    (value * mulNum) ~/ mulDen;

/// 四捨五入: `round_half_up(num / den)`（非負）。
int roundHalfUpDiv(int num, int den) => (2 * num + den) ~/ (2 * den);

/// 四捨五入: `round_half_up(value * mulNum / mulDen)`。
int roundHalfUp(int value, int mulNum, int mulDen) =>
    roundHalfUpDiv(value * mulNum, mulDen);

/// 五捨五超入: ちょうど中央値は切り捨て、それを超えるときだけ切り上げ（非負）。
int roundHalfDownDiv(int num, int den) {
  final int q = num ~/ den;
  final int r = num % den;
  final int twice = 2 * r;
  if (twice > den) return q + 1;
  return q; // r*2 <= den のときは切り捨て（ちょうど 0.5 含む）
}

/// 五捨五超入: `round_half_down(value * mulNum / mulDen)`。
int roundHalfDown(int value, int mulNum, int mulDen) =>
    roundHalfDownDiv(value * mulNum, mulDen);

/// 4096 系補正の合算。
///
/// `calc.py` の各 hosei 関数末尾と同じ:
/// `hosei_total = round_half_up(hosei_total * value / 4096)` を順に適用し、
/// 初期値は 4096。引数 `values` は補正倍率（×4096 表現）のリスト。
int combineHosei(Iterable<int> values) {
  int total = 4096;
  for (final int v in values) {
    total = roundHalfUp(total, v, 4096);
  }
  return total;
}
