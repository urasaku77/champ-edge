## Why

ダメージ計算バグ。テラスは「当面対象外（P4）」のはずだが、サンプルパーティが各ポケモンに `tera` を
設定しており、`toAttacker`/`toDefender` がそれをエンジンへ渡してテラス相性が**実際に計算へ反映**されていた。
このため、例えば tera=はがね のガブリアスに対し はどうだん（かくとう）が 2倍・あくのはどう（あく）が 0.5倍 と
なり、同威力・同タイプ不一致の技が違うダメージになっていた（はどうだんが本来の2倍）。

## What Changes

- **テラスをダメージ計算に渡さない**：`BattlePokemon.toAttacker/toDefender` で `tera: PokeType.none` を渡し、
  テラス相性を無効化する（エンジンのテラス対応コードは P4 再導入用に温存）。`tera` フィールドの保持・
  サンプルの設定はそのまま（計算に効かないだけ）。

## Capabilities

### Modified Capabilities
- `battle-screen-ui`: 「天候・フィールド・壁の指定」にテラスは計算に影響しない旨を明記する。

## Impact

- `mobile/lib/src/model/battle_pokemon.dart`（toAttacker/toDefender で tera=none）
- `mobile/test/tera_disabled_test.dart`（新規・回帰防止）
