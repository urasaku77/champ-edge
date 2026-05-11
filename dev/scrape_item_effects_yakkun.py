"""
ポケモン徹底攻略(yakkun.com) SV/SWSH/USUM の全アイテム効果テキストを取得してCSVに出力。

優先順位: SV > SWSH > USUM
- SV:   個別ページ https://yakkun.com/sv/item.htm?no={id}
- SWSH: 一覧ページ https://yakkun.com/swsh/item_list.htm[?mode=XXX]
- USUM: 一覧ページ https://yakkun.com/sm/item_list.htm[?mode=XXX]

出力: dev/item_effects_yakkun.csv (item_id, item_name, effect, source)
"""

import csv
import re
import sys
import time
import urllib.request

sys.stdout.reconfigure(encoding="utf-8")

OUTPUT_CSV = "dev/item_effects_yakkun.csv"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept-Language": "ja,en-US;q=0.7",
}
SLEEP_SEC = 0.4


def fetch(url: str) -> str:
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=10) as r:
        return r.read().decode("euc-jp", errors="replace")


# ─── SV ──────────────────────────────────────────────────

def get_sv_item_list() -> list[tuple[str, str]]:
    text = fetch("https://yakkun.com/sv/item.htm")
    return re.findall(r'href="\./item\.htm\?no=(\d+)">([^<]+)</a>', text)


def get_sv_effect(item_id: str) -> str:
    try:
        text = fetch(f"https://yakkun.com/sv/item.htm?no={item_id}")
    except Exception:
        return ""
    m = re.search(
        r'<h2[^>]*id="effect"[^>]*>効果</h2>\s*<div[^>]*>\s*<p[^>]*>(.*?)</p>',
        text, re.S
    )
    if not m:
        m = re.search(r'<h2[^>]*id="effect"[^>]*>.*?<p[^>]*>(.*?)</p>', text, re.S)
    if not m:
        return ""
    clean = re.sub(r"<[^>]+>", "", m.group(1))
    return re.sub(r"\s+", " ", clean).strip()


# ─── SWSH / USUM 共通（一覧ページから直接取得）────────────────

def parse_list_page(text: str) -> dict[str, tuple[str, str]]:
    """
    id="item-{id}" を持つ行から {item_id: (item_name, effect)} を返す。
    構造:
      <td class="c1" rowspan="2" id="item-{id}"><a>名前</a> or テキスト</td>
      <td>効果テキスト</td>
    """
    result: dict[str, tuple[str, str]] = {}
    pattern = re.compile(
        r'<td[^>]+id="item-(\d+)"[^>]*>(.*?)</td>\s*<td[^>]*>(.*?)</td>',
        re.S
    )
    for m in pattern.finditer(text):
        item_id = m.group(1)
        name_raw = re.sub(r"<[^>]+>", "", m.group(2)).strip()
        effect_raw = re.sub(r"<[^>]+>", "", m.group(3)).strip()
        effect_raw = re.sub(r"\s+", " ", effect_raw)
        if name_raw and effect_raw:
            result[item_id] = (name_raw, effect_raw)
    return result


def get_all_from_list_site(base_url: str, modes: list[str]) -> dict[str, tuple[str, str]]:
    """baseページ + 各modeページを取得してマージ。"""
    result: dict[str, tuple[str, str]] = {}
    urls = [base_url] + [f"{base_url}?mode={m}" for m in modes]
    for url in urls:
        try:
            text = fetch(url)
            result.update(parse_list_page(text))
            time.sleep(SLEEP_SEC)
        except Exception as e:
            print(f"  WARN: {url} -> {e}")
    return result


# ─── メイン ─────────────────────────────────────────────

def main():
    # ── USUM（最低優先） ──
    print("USUM 取得中...")
    usum_modes = ["z", "mega", "berry", "ball", "usum_im", "im"]
    usum = get_all_from_list_site("https://yakkun.com/sm/item_list.htm", usum_modes)
    print(f"  USUM: {len(usum)}件")

    # ── SWSH（中優先） ──
    print("SWSH 取得中...")
    swsh_modes = ["berry", "ball", "im"]
    swsh = get_all_from_list_site("https://yakkun.com/swsh/item_list.htm", swsh_modes)
    print(f"  SWSH: {len(swsh)}件")

    # USUM + SWSH マージ（SWSH優先）
    merged: dict[str, tuple[str, str, str]] = {}  # id -> (name, effect, source)
    for iid, (name, eff) in usum.items():
        merged[iid] = (name, eff, "USUM")
    for iid, (name, eff) in swsh.items():
        merged[iid] = (name, eff, "SWSH")

    # ── SV（最高優先・個別ページ） ──
    print("SV アイテム一覧取得中...")
    sv_items = get_sv_item_list()
    print(f"  SV一覧: {len(sv_items)}件")
    print("SV 個別ページ取得中...")

    for i, (item_id, item_name) in enumerate(sv_items):
        print(f"  [{i+1:3}/{len(sv_items)}] id={item_id} {item_name} ...", end=" ", flush=True)
        effect = get_sv_effect(item_id)
        if effect:
            merged[item_id] = (item_name, effect, "SV")
            print(f"OK: {effect[:40]!r}")
        else:
            # 効果ページがなければSWSH/USUMを残す
            if item_id in merged:
                print(f"SV空→{merged[item_id][2]}継続")
            else:
                merged[item_id] = (item_name, "", "SV_EMPTY")
                print("NOT FOUND")
        time.sleep(SLEEP_SEC)

    # ── CSV出力（item_idでソート） ──
    rows = sorted(
        [{"item_id": iid, "item_name": name, "effect": eff, "source": src}
         for iid, (name, eff, src) in merged.items()],
        key=lambda r: int(r["item_id"])
    )

    with open(OUTPUT_CSV, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["item_id", "item_name", "effect", "source"])
        writer.writeheader()
        writer.writerows(rows)

    sv_c   = sum(1 for r in rows if r["source"] == "SV")
    swsh_c = sum(1 for r in rows if r["source"] == "SWSH")
    usum_c = sum(1 for r in rows if r["source"] == "USUM")
    empty  = sum(1 for r in rows if not r["effect"])
    print("-" * 60)
    print(f"合計: {len(rows)}件 (SV={sv_c}, SWSH={swsh_c}, USUM={usum_c}, 空={empty})")
    print(f"CSV出力: {OUTPUT_CSV}")


if __name__ == "__main__":
    main()
