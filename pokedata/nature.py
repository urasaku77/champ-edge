from collections import namedtuple

from pokedata.stats import Stats, StatsKey

__Nature = namedtuple("__Nature", ["up", "down"])
__natures = {
    "さみしがり": __Nature(StatsKey.A, StatsKey.B),
    "いじっぱり": __Nature(StatsKey.A, StatsKey.C),
    "やんちゃ": __Nature(StatsKey.A, StatsKey.D),
    "ゆうかん": __Nature(StatsKey.A, StatsKey.S),
    "ずぶとい": __Nature(StatsKey.B, StatsKey.A),
    "わんぱく": __Nature(StatsKey.B, StatsKey.C),
    "のうてんき": __Nature(StatsKey.B, StatsKey.D),
    "のんき": __Nature(StatsKey.B, StatsKey.S),
    "ひかえめ": __Nature(StatsKey.C, StatsKey.A),
    "おっとり": __Nature(StatsKey.C, StatsKey.B),
    "うっかりや": __Nature(StatsKey.C, StatsKey.D),
    "れいせい": __Nature(StatsKey.C, StatsKey.S),
    "おだやか": __Nature(StatsKey.D, StatsKey.A),
    "おとなしい": __Nature(StatsKey.D, StatsKey.B),
    "しんちょう": __Nature(StatsKey.D, StatsKey.C),
    "なまいき": __Nature(StatsKey.D, StatsKey.S),
    "おくびょう": __Nature(StatsKey.S, StatsKey.A),
    "せっかち": __Nature(StatsKey.S, StatsKey.B),
    "ようき": __Nature(StatsKey.S, StatsKey.C),
    "むじゃき": __Nature(StatsKey.S, StatsKey.D),
}


def get_seikaku_from_arrows(up_key: StatsKey, down_key: StatsKey) -> str:
    """Return the nature name that has (up_key ↑, down_key ↓), or 'まじめ'."""
    for name, nat in __natures.items():
        if nat.up == up_key and nat.down == down_key:
            return name
    return "まじめ"


def get_seikaku_list() -> list[str]:
    return [x for x in __natures.keys()]


def get_seikaku_hosei(seikaku: str, key: StatsKey) -> float:
    if seikaku not in __natures:
        return 1.0
    values: __Nature = __natures[seikaku]
    return 1.1 if values.up == key else 0.9 if values.down == key else 1.0


def get_default_doryoku(seikaku: str, syuzoku: Stats) -> Stats:
    doryoku = Stats()
    if seikaku == "ようき":
        doryoku.set_values(a=32, s=32)
    if seikaku == "おくびょう":
        doryoku.set_values(c=32, s=32)
    if seikaku == "ゆうかん":
        doryoku.set_values(h=32, a=32)
    if seikaku == "れいせい":
        doryoku.set_values(h=32, c=32)
    if seikaku in ["ずぶとい", "わんぱく", "のんき"]:
        doryoku.set_values(h=32, b=32)
    if seikaku in ["おだやか", "しんちょう", "なまいき"]:
        doryoku.set_values(h=32, d=32)
    if seikaku in ["いじっぱり", "さみしがり", "やんちゃ"]:
        doryoku.set_values(
            a=32, s=32 if syuzoku.S >= 90 else 0, h=32 if syuzoku.S < 90 else 0
        )
    if seikaku in ["ひかえめ", "おっとり", "うっかりや"]:
        doryoku.set_values(
            c=32, s=32 if syuzoku.S >= 90 else 0, h=32 if syuzoku.S < 90 else 0
        )
    if seikaku in ["せっかち", "むじゃき"]:
        doryoku.set_values(
            a=32 if syuzoku.A > syuzoku.C else 0,
            c=32 if syuzoku.C > syuzoku.A else 0,
            s=32,
        )
    return doryoku
