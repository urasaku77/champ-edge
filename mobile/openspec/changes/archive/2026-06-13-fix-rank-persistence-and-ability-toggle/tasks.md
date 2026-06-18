# タスク: fix-rank-persistence-and-ability-toggle

## 1. ランク変化の永続化（バグ修正）

- [x] 1.1 切替時の `resetAppearAbility` で相手のランクを巻き戻さない（フラグだけ下ろし、トレース/メタモンは復元）
- [x] 1.2 `_resetMoveToggles` で selfRank/opponentRank は巻き戻さない（自分のランクは boosts クリア、相手のランクは残す）
- [x] 1.3 切替時に場を離れる側自身の boosts をクリア（既存）

## 2. 登場時ランク特性の拡張・無効化

- [x] 2.1 `applyAppearAbility` に ふとうのけん(自A+1)・ふくつのたて(自B+1)・ダウンロード(相手防御<特防で自A、他は自C +1) を追加
- [x] 2.2 `appearRankAbilities` 集合・`appearRankApplied`/`abilityDisabled` フィールド導入（`abilityDisabled` は永続）
- [x] 2.3 特性チップ長押し詳細に「登場時のランク効果を無効化」スイッチを追加
- [x] 2.4 登場時特性ロジックを純粋関数 `appear_ability.dart` に切り出す

## 3. キングシールド

- [x] 3.1 キングシールドの効果（接触技を受けると相手の『こうげき』-1）を opponentRank 技として追加

## 4. 天候/フィールドのクリア

- [x] 4.0 中央列の天候/フィールドのドロップダウンを長押しで「なし」にクリア（`_centerSelect` に onClear）

## 5. 検証

- [x] 4.1 `appear_ability_test.dart` 追加（いかく永続/無効化/ふとうのけん/ふくつのたて/ダウンロード/二重適用防止）
- [x] 4.2 analyze クリーン・全テストパス・ビルド＆再起動
- [x] 4.3 spec/tasks 同期
