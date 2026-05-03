#!/usr/bin/env python3
"""champs.pokedb.tokyo からポケモンデータをスクレイピングして CSV に保存する

取得対象:
  home_waza.csv      技
  home_tokusei.csv   特性
  home_motimono.csv  持ち物
  home_seikaku.csv   性格
  home_doryoku.csv   努力値（個別上位10件）

CSV フォーマット: ポケモン名, 値, パーセント
"""
import csv
import os
import re
import ssl
import sys
import time
import urllib.request
from html.parser import HTMLParser

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database.pokemon import DB_pokemon

_SSL_CTX = ssl._create_unverified_context()
_HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; svcalc/1.0)"}

CSV_PATHS = {
    "waza":     "stats/home_waza.csv",
    "tokusei":  "stats/home_tokusei.csv",
    "motimono": "stats/home_motimono.csv",
    "seikaku":  "stats/home_seikaku.csv",
    "doryoku":  "stats/home_doryoku.csv",
}

_PCT_RE  = re.compile(r"^\d+\.\d+%$")   # "99.0%" 結合形式
_PCT_NUM = re.compile(r"^\d+\.\d+$")    # "99.0"  分割形式の数値部分
_STAT_LETTERS = frozenset("HABCDS")
# 合算ラベル: "AS", "AS + h", "HB + bd" など（大文字 + オプションの +小文字）
_AGG_RE = re.compile(r"^[A-Z]+(\s*\+\s*[a-z]+)*$")

# ページ上の実際のセクション見出しトークン
_SECTION_KEYS = ["技", "特性", "能力補正", "持ち物", "能力ポイント"]


# ──────────────────────────────────────────────
# HTML テキスト抽出
# ──────────────────────────────────────────────

class _TextExtractor(HTMLParser):
    """script/style を除いた可視テキストを収集する"""
    _SKIP = {"script", "style", "noscript"}

    def __init__(self):
        super().__init__()
        self._depth = 0
        self.tokens: list[str] = []

    def handle_starttag(self, tag, attrs):
        if tag in self._SKIP:
            self._depth += 1

    def handle_endtag(self, tag):
        if tag in self._SKIP and self._depth > 0:
            self._depth -= 1

    def handle_data(self, data):
        if self._depth == 0:
            text = data.strip()
            if text:
                self.tokens.append(text)


def _fetch_tokens(pid: str, season: str) -> list[str]:
    url = f"https://champs.pokedb.tokyo/pokemon/show/{pid}?season={season}&rule=0"
    req = urllib.request.Request(url, headers=_HEADERS)
    with urllib.request.urlopen(req, context=_SSL_CTX) as resp:
        html = resp.read().decode("utf-8")
    p = _TextExtractor()
    p.feed(html)
    return p.tokens


# ──────────────────────────────────────────────
# セクション解析
# ──────────────────────────────────────────────

def _section_range(tokens: list[str], keyword: str, start_from: int = 0) -> tuple[int, int]:
    """keyword と完全一致するトークンの直後から次のセクション見出しまでの範囲を返す。
    start_from 以降でのみ検索する（誤マッチ防止用）。
    """
    start = None
    for i in range(start_from, len(tokens)):
        if tokens[i] == keyword:
            start = i + 1
            break
    if start is None:
        return (0, 0)
    other_keys = [k for k in _SECTION_KEYS if k != keyword]
    end = len(tokens)
    for i in range(start, len(tokens)):
        if tokens[i] in other_keys:
            end = i
            break
    return (start, end)


def _parse_pairs(tokens: list[str], start: int, end: int, limit: int = 10) -> list[tuple[str, str]]:
    """技・特性・持ち物用。(名前, パーセント数値文字列) ペアを最大 limit 件返す。

    パーセントは結合形式 "99.0%" と分割形式 "99.0" + "%" の両方に対応。
    """
    results: list[tuple[str, str]] = []
    i = start
    while i < end and len(results) < limit:
        t = tokens[i]
        nxt  = tokens[i + 1] if i + 1 < end else ""
        nxt2 = tokens[i + 2] if i + 2 < end else ""
        # パーセント・数値・ランク番号はスキップ
        if t == "%" or _PCT_RE.match(t) or _PCT_NUM.match(t) or re.match(r"^\d+$", t):
            i += 1
            continue
        if _PCT_RE.match(nxt):                          # 結合形式: 名前 + "99.0%"
            results.append((t, nxt.rstrip("%")))
            i += 2
        elif _PCT_NUM.match(nxt) and nxt2 == "%":       # 分割形式: 名前 + "99.0" + "%"
            results.append((t, nxt))
            i += 3
        else:
            i += 1
    return results


def _parse_seikaku(tokens: list[str], start: int, end: int, limit: int = 10) -> list[tuple[str, str]]:
    """性格セクション: rank, name, '(', 'X↑', 'Y↓', ')', pct, pct_dup の形式

    名前と % の間に括弧・矢印トークンが挟まるため、
    名前の直後 8 トークン以内の最初の % を採用する。
    """
    results: list[tuple[str, str]] = []
    i = start
    _SKIP = {"(", ")", "%"}
    while i < end and len(results) < limit:
        t = tokens[i]
        if (re.match(r"^\d+$", t) or t in _SKIP
                or "↑" in t or "↓" in t
                or _PCT_RE.match(t) or _PCT_NUM.match(t)):
            i += 1
            continue
        # 直後 8 トークン以内の最初の % を探す
        found = False
        for j in range(i + 1, min(i + 9, end)):
            tj = tokens[j]
            if _PCT_RE.match(tj):
                results.append((t, tj.rstrip("%")))
                i = j + 1
                found = True
                break
            elif _PCT_NUM.match(tj) and j + 1 < end and tokens[j + 1] == "%":
                results.append((t, tj))
                i = j + 2
                found = True
                break
        if not found:
            i += 1
    return results


def _parse_doryoku(tokens: list[str], start: int, end: int, limit: int = 10) -> list[tuple[str, str]]:
    """能力ポイントセクション: 個別形式（例 H2A32S32）を上位 limit 件取得

    ページ構造:
      (合算ラベル)(pct)[(stat_letter)(value)]... を繰り返す
      合算ラベル: "AS", "AS + h", "HB + bd" など (_AGG_RE にマッチ)
      個別 stat: 1文字の HABCDS + 数値 の交互列
    """
    results: list[tuple[str, str]] = []
    i = start
    while i < end and len(results) < limit:
        t = tokens[i]
        nxt = tokens[i + 1] if i + 1 < end else ""
        # スキップ: タブ/余り/+/ランク番号/パーセント/件を合算
        if (t in ("合算", "個別", "+", "余り")
                or re.match(r"^\d+$", t)
                or "件を合算" in t
                or t == "%" or _PCT_RE.match(t) or _PCT_NUM.match(t)):
            i += 1
            continue
        # 合算ラベル + パーセント → 続く個別 stat 列を結合して記録
        if _AGG_RE.match(t) and _PCT_RE.match(nxt):
            pct = nxt.rstrip("%")
            i += 2
            stat_parts: list[str] = []
            while i < end:
                st = tokens[i]
                st_nxt = tokens[i + 1] if i + 1 < end else ""
                if len(st) == 1 and st in _STAT_LETTERS and re.match(r"^\d+$", st_nxt):
                    stat_parts.append(st + st_nxt)
                    i += 2
                else:
                    break
            if stat_parts:
                results.append(("".join(stat_parts), pct))
        else:
            i += 1
    return results


# ──────────────────────────────────────────────
# ポケモン名取得
# ──────────────────────────────────────────────

def _get_name(pid: str, tokens: list[str]) -> str:
    """ranking.txt 形式 (0445-00) → DB 名前取得。失敗時はタイトルから抽出"""
    try:
        no, form = pid.split("-")
        return DB_pokemon.get_pokemon_name_by_pid(f"{int(no)}-{int(form)}")
    except Exception:
        pass
    for t in tokens[:20]:
        m = re.match(r"^(.+?)の", t)
        if m:
            return m.group(1)
    return pid


# ──────────────────────────────────────────────
# CSV 書き込み
# ──────────────────────────────────────────────

def _append_csv(path: str, rows: list[list]):
    if not rows:
        return
    with open(path, "a", newline="", encoding="utf-8") as f:
        csv.writer(f, lineterminator="\n").writerows(rows)


# ──────────────────────────────────────────────
# ランキングリスト取得
# ──────────────────────────────────────────────

_LIST_URL = "https://champs.pokedb.tokyo/pokemon/list?rule=0"
_PID_RE    = re.compile(r"/pokemon/show/(\d{4}-\d{2})")
_SEASON_RE = re.compile(r"season=(\d+)")


def _fetch_ranking() -> tuple[list[str], str]:
    """ランキングページから (pid リスト, シーズン番号) を取得する"""
    req = urllib.request.Request(_LIST_URL, headers=_HEADERS)
    with urllib.request.urlopen(req, context=_SSL_CTX) as resp:
        html = resp.read().decode("utf-8")
    pids = _PID_RE.findall(html)
    m = _SEASON_RE.search(html)
    season = m.group(1) if m else "1"
    return pids, season


# ──────────────────────────────────────────────
# メイン処理
# ──────────────────────────────────────────────

def scrape_one(pid: str, season: str) -> str | None:
    """1体をスクレイピングして各 CSV に追記する。ポケモン名を返す"""
    try:
        tokens = _fetch_tokens(pid, season)
    except Exception as e:
        print(f"  取得失敗 {pid}: {e}")
        return None

    name = _get_name(pid, tokens)

    # 技セクションを基準点として検出（使用データ部の先頭）
    waza_s, waza_e = _section_range(tokens, "技")
    anchor = waza_s - 1 if waza_s > 0 else 0  # 技トークン自体の位置

    _append_csv(CSV_PATHS["waza"],     [[name, n, p] for n, p in _parse_pairs(tokens, waza_s, waza_e)])

    # 残セクションは技以降から検索（ページ上部の基本情報との誤マッチ防止）
    s, e = _section_range(tokens, "特性", anchor)
    _append_csv(CSV_PATHS["tokusei"],  [[name, n, p] for n, p in _parse_pairs(tokens, s, e)])

    s, e = _section_range(tokens, "持ち物", anchor)
    _append_csv(CSV_PATHS["motimono"], [[name, n, p] for n, p in _parse_pairs(tokens, s, e)])

    s, e = _section_range(tokens, "能力補正", anchor)
    _append_csv(CSV_PATHS["seikaku"],  [[name, n, p] for n, p in _parse_seikaku(tokens, s, e)])

    s, e = _section_range(tokens, "能力ポイント", anchor)
    _append_csv(CSV_PATHS["doryoku"],  [[name, n, p] for n, p in _parse_doryoku(tokens, s, e)])

    return name


def main():
    print("ランキングリストを取得中...")
    pids, season = _fetch_ranking()

    seasons = [season]
    if int(season) > 1:
        seasons.append(str(int(season) - 1))

    print(f"シーズン {', '.join(seasons)}、{len(pids)} 体分のデータを取得します")

    # ranking.txt を最新のランキング順で上書き
    with open("stats/ranking.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(pids) + "\n")
    # season.txt も更新
    with open("stats/season.txt", "w", encoding="utf-8") as f:
        f.write(season)

    for path in CSV_PATHS.values():
        if os.path.isfile(path):
            os.remove(path)

    for i, pid in enumerate(pids, 1):
        for s in seasons:
            name = scrape_one(pid, s)
        label = f"{name} ({pid})" if name else pid
        print(f"  [{i}/{len(pids)}] {label}")
        time.sleep(0.5)

    print("CSV 更新完了")


if __name__ == "__main__":
    main()
