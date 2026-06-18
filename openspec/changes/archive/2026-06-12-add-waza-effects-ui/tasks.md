# タスク: add-waza-effects-ui

## 1. 効果テーブルの移植（waza_effects.dart）

- [x] 1.1 `WazaEffectKind` に `selfRank` / `opponentRank` / `typeChange` を追加（toggle は addPower で近似）
- [x] 1.2 `waza.py` の self_buff/self_debuff/opponent_buff/opponent_debuff（"AS+1" 形式）を
  `parseRankSpec` で [H,A,B,C,D,S] 段階差分へ展開して移植
- [x] 1.3 きょけんとつげき「受×2」は addPower ×1/×2 のトグルで近似。※オーラぐるま（はらぺこ＝あく
  タイプ化）・じこあんじ/スキルスワップ/コートチェンジ（能力コピー系）は本 change では未対応（後続）
- [x] 1.4 タイプ変更技（みずびたし=相手みず、もえつきる/でんこうそうげき=自分のほのお/でんき除去）を
  typeChange として定義
- [x] 1.5 ユニットテスト（`test/waza_effects_test.dart`）：parseRankSpec・各種別の解決を検証

## 2. モデル・適用ロジック

- [x] 2.1 トグル効果は `BattleMove.effectValue` 0↔1 で適用状態を管理（`WazaEffect.isToggle`/`next`）
- [x] 2.2 ランク変化：対象（self=攻撃側 / opponent=防御側）の boosts に段階差分を加算/復元（−6〜+6 clamp）
- [x] 2.3 受×2 は addPower で近似（エンジン経路はそのまま）。※オーラぐるま等は後続
- [x] 2.4 タイプ変更：対象ポケモンの type1/type2 を書き換え、`typeBackup` で解除時に復元

## 3. UI（home_screen.dart の効果ボタン）

- [x] 3.1 効果ボタンを種別で分岐：×n（既存）／＋・−（ランク）／型（タイプ変更）
- [x] 3.2 色・ラベルを種別で出し分け（×n=藍/teal、自分ランク=緑、相手ランク=橙、タイプ=紫）。
  トグル ON は塗りつぶしで適用状態を表示
- [x] 3.3 タップで適用/解除（トグル）。ランクは boosts、タイプは type へ反映し再計算
- [x] 3.4 ポケモン選択切替時の自動リセットは本 change のスコープ外（再タップ解除で代替。手動ランクとの
  競合を避けるため、自動リセットは後続 change で検討）

## 4. 検証

- [x] 4.1 効果テーブル/パーサのテスト追加（ランク差分の damage 反映は既存 boost テストで担保）
- [x] 4.2 `flutter analyze` クリーン・全285テストパス・横画面シミュレータで＋/−/型ボタン表示を確認
- [x] 4.3 spec/tasks を実装に同期（簡略/後続を明記）
