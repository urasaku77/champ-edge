"""
ポケモン徹底攻略(yakkun.com) SV/SWSH/USUM の全特性効果テキストを取得してCSVに出力。

優先順位: SV > SWSH > USUM
- SV:   https://yakkun.com/sv/ability_list.htm
- SWSH: https://yakkun.com/swsh/ability_list.htm
- USUM: https://yakkun.com/sm/ability_list.htm

出力: dev/ability_effects_yakkun.csv (ability_id, ability_name, effect)
"""

import csv
import re
import sys
import time
import urllib.request

sys.stdout.reconfigure(encoding="utf-8")

OUTPUT_CSV = "dev/ability_effects_yakkun.csv"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept-Language": "ja,en-US;q=0.7",
}
SLEEP_SEC = 0.4

PATTERN = re.compile(
    r'<td[^>]*class="c1"[^>]*><a href="[^"]*tokusei=(\d+)"[^>]*>([^<]+)</a></td>\s*<td[^>]*>(.*?)</td>',
    re.S,
)


def fetch(url: str) -> str:
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=10) as r:
        return r.read().decode("euc-jp", errors="replace")


def parse_ability_page(text: str) -> dict[str, tuple[str, str]]:
    """ability_id -> (ability_name, effect) を返す。"""
    result: dict[str, tuple[str, str]] = {}
    for m in PATTERN.finditer(text):
        ability_id = m.group(1)
        name = re.sub(r"<[^>]+>", "", m.group(2)).strip()
        effect = re.sub(r"<[^>]+>", "", m.group(3)).strip()
        effect = re.sub(r"\s+", " ", effect)
        if name and effect:
            result[ability_id] = (name, effect)
    return result


def main():
    # ── USUM（最低優先） ──
    print("USUM 取得中...")
    usum = parse_ability_page(fetch("https://yakkun.com/sm/ability_list.htm"))
    print(f"  USUM: {len(usum)}件")
    time.sleep(SLEEP_SEC)

    # ── SWSH（中優先） ──
    print("SWSH 取得中...")
    swsh = parse_ability_page(fetch("https://yakkun.com/swsh/ability_list.htm"))
    print(f"  SWSH: {len(swsh)}件")
    time.sleep(SLEEP_SEC)

    # ── SV（最高優先） ──
    print("SV 取得中...")
    sv = parse_ability_page(fetch("https://yakkun.com/sv/ability_list.htm"))
    print(f"  SV: {len(sv)}件")

    # ── マージ（USUM → SWSH → SV で上書き） ──
    merged: dict[str, tuple[str, str]] = {}
    for aid, (name, eff) in usum.items():
        merged[aid] = (name, eff)
    for aid, (name, eff) in swsh.items():
        merged[aid] = (name, eff)
    for aid, (name, eff) in sv.items():
        merged[aid] = (name, eff)

    # ── CSV出力（ability_idでソート） ──
    rows = sorted(
        [{"ability_id": aid, "ability_name": name, "effect": eff}
         for aid, (name, eff) in merged.items()],
        key=lambda r: int(r["ability_id"]),
    )

    with open(OUTPUT_CSV, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["ability_id", "ability_name", "effect"])
        writer.writeheader()
        writer.writerows(rows)

    print("-" * 60)
    print(f"合計: {len(rows)}件")
    print(f"CSV出力: {OUTPUT_CSV}")


if __name__ == "__main__":
    main()
