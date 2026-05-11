# coding: utf-8
"""
Party image OCR parser for Pokémon HOME / SV party screen screenshots.
Requires Tesseract with Japanese language pack ('jpn').
Tesseract folder is configured via recog/setting.json (モード切替 > Tesseractフォルダ).
"""

import difflib
import os
import re
import sqlite3
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import jaconv
import numpy as np
from PIL import Image

from pokedata.nature import get_seikaku_from_arrows
from pokedata.stats import StatsKey
from recog.recog import get_tesseract_path

try:
    import pytesseract

    _TESSERACT_IMPORTED = True
except ImportError:
    _TESSERACT_IMPORTED = False


# ---------------------------------------------------------------------------
# Tesseract setup
# ---------------------------------------------------------------------------


def _configure_tesseract() -> None:
    if not _TESSERACT_IMPORTED:
        return
    path = get_tesseract_path()
    if path:
        exe = "tesseract.exe" if sys.platform == "win32" else "tesseract"
        pytesseract.pytesseract.tesseract_cmd = os.path.join(path, exe)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_LEFT_STATS = [StatsKey.H, StatsKey.A, StatsKey.B]
_RIGHT_STATS = [StatsKey.C, StatsKey.D, StatsKey.S]
_EV_LABELS = ["H", "A", "B", "C", "D", "S"]
_EV_KEYS = [StatsKey.H, StatsKey.A, StatsKey.B, StatsKey.C, StatsKey.D, StatsKey.S]

# Cached reference lists loaded lazily
_pokemon_names: list[str] = []
_waza_names: list[str] = []
_ability_names: list[str] = []
_item_names: list[str] = []


def _load_reference_lists() -> None:
    global _pokemon_names, _waza_names, _ability_names, _item_names
    if _pokemon_names:
        return
    import glob as _g

    from component.parts.const import ALL_ITEM_COMBOBOX_VALUES
    from database.pokemon import DB_pokemon

    # image/pokemon/ に画像が存在するポケモン名のみ（図鑑外・未実装ポケを除外）
    seen: set[str] = set()
    img_names: list[str] = []
    for fp in sorted(_g.glob("image/pokemon/*.png")):
        stem = Path(fp).stem
        parts = stem.split("-")
        if len(parts) == 2:
            pid = f"{int(parts[0])}-{int(parts[1])}"
            pname = DB_pokemon.get_pokemon_name_by_pid(pid)
            if pname and pname not in seen:
                img_names.append(pname)
                seen.add(pname)
    _pokemon_names = img_names
    _waza_names = list(DB_pokemon.get_waza_namedict().values())
    _item_names = list(ALL_ITEM_COMBOBOX_VALUES)

    conn = sqlite3.connect("database/pokemon.db")
    conn.row_factory = sqlite3.Row
    abilities: set[str] = set()
    for col in ("ability1", "ability2", "ability3"):
        for row in conn.execute(
            f'SELECT DISTINCT {col} FROM pokemon_data WHERE {col} != ""'
        ):
            val = row[0].strip()
            if val:
                abilities.add(val)
    conn.close()
    _ability_names = sorted(abilities)


# Crop ratio relative to card height: captures the sprite area without name text
_SPRITE_CW_RATIO = 0.55
_SPRITE_CH_RATIO = 0.65

# ---------------------------------------------------------------------------
# Multi-signal Pokemon identification
# ---------------------------------------------------------------------------

_RANKING_FILE = "stats/ranking.txt"
_TYPE_ICON_DIR = "image/typeicon"
# 名前行のタイプアイコン走査領域 (x1, y1, x2, y2) — スプライト右端から技アイコン手前まで
_TYPE_ICON_SCAN = (200, 3, 450, 48)

_ranking_cache: list[str] = []
_type_icon_tpl: dict[str, "np.ndarray"] = {}
# スプライトテンプレートキャッシュ: pid → (gray, alpha_mask or None)
_pokemon_sprite_cache: dict[str, tuple["np.ndarray", "np.ndarray | None"]] = {}
# home_waza.csv のキャッシュ: {ポケモン名: {技名, ...}}
_home_waza_cache: dict[str, set[str]] = {}


def _load_ranking() -> list[str]:
    """stats/ranking.txt を読み込み 'no-form' 形式のPIDリストを返す。"""
    global _ranking_cache
    if _ranking_cache:
        return _ranking_cache
    try:
        with open(_RANKING_FILE, encoding="utf-8") as f:
            pids: list[str] = []
            for line in f:
                line = line.strip()
                if not line:
                    continue
                parts = line.split("-")
                if len(parts) == 2:
                    pids.append(f"{int(parts[0])}-{int(parts[1])}")
        _ranking_cache = pids
    except Exception:
        pass
    return _ranking_cache


def _load_type_icon_templates() -> dict[str, "np.ndarray"]:
    """image/typeicon/*.png をBGRで読み込んで返す（透明部分は白でコンポジット）。"""
    global _type_icon_tpl
    if _type_icon_tpl:
        return _type_icon_tpl
    try:
        import glob as _g

        import cv2

        for path in _g.glob(f"{_TYPE_ICON_DIR}/*.png"):
            name = os.path.splitext(os.path.basename(path))[0]
            if name == "なし":
                continue
            raw = cv2.imdecode(np.fromfile(path, dtype=np.uint8), cv2.IMREAD_UNCHANGED)
            if raw is None:
                continue
            if raw.ndim == 3 and raw.shape[2] == 4:
                alpha = raw[:, :, 3:4].astype(np.float32) / 255.0
                bgr = raw[:, :, :3].astype(np.float32)
                white = np.ones_like(bgr) * 255.0
                bgr = (bgr * alpha + white * (1.0 - alpha)).astype(np.uint8)
            else:
                bgr = raw[:, :, :3]
            _type_icon_tpl[name] = bgr
    except Exception:
        pass
    return _type_icon_tpl


_TYPE_ICON_SCALES = [0.4, 0.5, 0.6, 0.7, 0.8]
_SPRITE_SCALES = [0.5, 0.6, 0.7, 0.8, 0.9, 1.0, 1.2, 1.5, 2.0]
_TYPE_MATCH_THRESHOLD = 0.35
_TYPE_TOP_N = 2


def _detect_types_from_card(card: Image.Image) -> set[str]:
    """タイプアイコン領域に全テンプレートをマッチングしてタイプを検出する。"""
    try:
        import cv2

        templates = _load_type_icon_templates()
        if not templates:
            return set()

        x1, y1, x2, y2 = _TYPE_ICON_SCAN
        region = cv2.cvtColor(np.array(card.crop((x1, y1, x2, y2))), cv2.COLOR_RGB2BGR)
        rh, rw = region.shape[:2]

        scores: dict[str, float] = {}
        for type_name, tpl in templates.items():
            best = 0.0
            for sc in _TYPE_ICON_SCALES:
                th = max(1, int(tpl.shape[0] * sc))
                tw = max(1, int(tpl.shape[1] * sc))
                if th > rh or tw > rw:
                    continue
                t = cv2.resize(tpl, (tw, th))
                res = cv2.matchTemplate(region, t, cv2.TM_CCOEFF_NORMED)
                _, v, _, _ = cv2.minMaxLoc(res)
                best = max(best, v)
            scores[type_name] = best

        ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        return {t for t, s in ranked[:_TYPE_TOP_N] if s >= _TYPE_MATCH_THRESHOLD}
    except Exception:
        return set()


def _load_pokemon_sprite_templates() -> dict[str, tuple["np.ndarray", "np.ndarray | None"]]:
    """image/pokemon/*.png のアルファチャンネル（シルエット）をテンプレートとしてキャッシュ。
    カード上のポケモンは白シルエットとして表示されるため、アルファ形状と対応する。"""
    global _pokemon_sprite_cache
    if _pokemon_sprite_cache:
        return _pokemon_sprite_cache
    try:
        import glob as _g

        import cv2

        for fp in _g.glob("image/pokemon/*.png"):
            stem = Path(fp).stem
            parts = stem.split("-")
            if len(parts) != 2:
                continue
            pid = f"{int(parts[0])}-{int(parts[1])}"
            raw = cv2.imdecode(np.fromfile(fp, dtype=np.uint8), cv2.IMREAD_UNCHANGED)
            if raw is None:
                continue
            if raw.ndim == 3 and raw.shape[2] == 4:
                # アルファ値をそのままシルエット強度として使用
                sil = raw[:, :, 3]
            else:
                # アルファなし画像は輝度をシルエットとして使用
                gray = cv2.cvtColor(raw[:, :, :3], cv2.COLOR_BGR2GRAY) if raw.ndim == 3 else raw
                sil = gray
            _pokemon_sprite_cache[pid] = (sil, None)
    except Exception:
        pass
    return _pokemon_sprite_cache


def _match_pokemon_sprite(card: Image.Image) -> list[tuple[float, str]]:
    """スプライト領域に全 image/pokemon/ テンプレートをマッチングしてスコア順に返す。"""
    try:
        import cv2

        w, h = card.size
        cw = min(int(h * _SPRITE_CW_RATIO), w)
        ch = min(int(h * _SPRITE_CH_RATIO), h)
        region = cv2.cvtColor(np.array(card.crop((0, 0, cw, ch))), cv2.COLOR_RGB2GRAY)
        rh, rw = region.shape

        templates = _load_pokemon_sprite_templates()
        results: list[tuple[float, str]] = []

        for pid, (tpl_gray, _) in templates.items():
            best = 0.0
            for sc in _SPRITE_SCALES:
                th = max(1, int(tpl_gray.shape[0] * sc))
                tw = max(1, int(tpl_gray.shape[1] * sc))
                if th > rh or tw > rw or th < 10 or tw < 10:
                    continue
                t = cv2.resize(tpl_gray, (tw, th))
                res = cv2.matchTemplate(region, t, cv2.TM_CCOEFF_NORMED)
                _, v, _, _ = cv2.minMaxLoc(res)
                best = max(best, v)
            if best > 0:
                results.append((best, pid))

        results.sort(reverse=True)
        return results
    except Exception:
        return []


def _ability_matches_pokemon(pokemon_name: str, abil_name: str) -> bool:
    """OCR名とOCR特性が矛盾しないか確認する。特性不明またはDBに見つからない場合はTrueを返す。"""
    if not abil_name:
        return True
    try:
        from database.pokemon import DB_pokemon

        pid = DB_pokemon.get_pokemon_pid_by_name(pokemon_name)
        if not pid:
            return True
        parts = pid.split("-")
        if len(parts) != 2:
            return True
        conn = sqlite3.connect("database/pokemon.db")
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT ability1, ability2, ability3 FROM pokemon_data WHERE no=?",
            (int(parts[0]),),
        ).fetchall()
        conn.close()
        if not rows:
            return True
        return any(abil_name in (r["ability1"], r["ability2"], r["ability3"]) for r in rows)
    except Exception:
        return True


def _pids_with_ability(abil_name: str) -> set[str]:
    """ability1/2/3 が abil_name に一致するポケモンの 'no-form' PIDセットを返す。"""
    try:
        conn = sqlite3.connect("database/pokemon.db")
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT no, form FROM pokemon_data "
            "WHERE ability1=? OR ability2=? OR ability3=?",
            (abil_name, abil_name, abil_name),
        ).fetchall()
        conn.close()
        return {f"{r['no']}-{r['form']}" for r in rows}
    except Exception:
        return set()


def _filter_by_types(pids: list[str], types: set[str]) -> list[str]:
    """type1/type2 が全検出タイプを含むPIDのみ残す。"""
    if not types:
        return pids
    try:
        conn = sqlite3.connect("database/pokemon.db")
        conn.row_factory = sqlite3.Row
        result: list[str] = []
        for pid in pids:
            parts = pid.split("-")
            if len(parts) != 2:
                continue
            row = conn.execute(
                "SELECT type1, type2 FROM pokemon_data WHERE no=? AND form=?",
                (int(parts[0]), int(parts[1])),
            ).fetchone()
            if not row:
                continue
            pokemon_types = {row["type1"], row["type2"]} - {""}
            if types.issubset(pokemon_types):
                result.append(pid)
        conn.close()
        return result
    except Exception:
        return pids


def _load_home_waza() -> dict[str, set[str]]:
    """stats/home_waza.csv を読み込み {ポケモン名: {技名, ...}} を返す。"""
    global _home_waza_cache
    if _home_waza_cache:
        return _home_waza_cache
    try:
        import csv

        result: dict[str, set[str]] = {}
        with open("stats/home_waza.csv", encoding="utf-8") as f:
            for row in csv.reader(f):
                if len(row) >= 2:
                    pname, wname = row[0].strip(), row[1].strip()
                    if pname and wname:
                        result.setdefault(pname, set()).add(wname)
        _home_waza_cache = result
    except Exception:
        pass
    return _home_waza_cache


def _identify_pokemon(
    card: Image.Image,
    name_raw: str,
    abil: str,
    item: str,
    moves: list[str],
) -> str:
    """①〜⑦のシグナルを順に適用してポケモン名を確定する。

    ① image/pokemon/ テンプレートマッチ → スコア順候補リスト
    ② ポケモン名OCR 完全一致 → 即確定
    ③ 特性フィルタ
    ④ タイプアイコン（テンプレートマッチ）
       ①-④ で候補が1件 → 確定
    ⑤ メガストーン → 即確定
    ⑥ HOME技フィルタ
    ⑦ HOMEランキング順で最終選択
    """
    from database.pokemon import DB_pokemon

    _load_reference_lists()

    # ① スプライトテンプレートマッチング → スコア順候補リスト
    sprite_matches = _match_pokemon_sprite(card)
    img_pids = set(_load_pokemon_sprite_templates().keys())
    candidates: list[str] = [pid for _, pid in sprite_matches] if sprite_matches else list(img_pids)

    # ② ポケモン名OCR（タイプアイコン等のノイズをカタカナ・漢字のみ抽出して除去）
    # + 特性クロスバリデーション（ニックネーム衝突防止）
    _name_norm = _normalize(name_raw)
    name_clean = "".join(
        ch for ch in _name_norm
        if (0x30A0 <= ord(ch) <= 0x30FF and ord(ch) != 0x30FB)
        or 0x4E00 <= ord(ch) <= 0x9FFF
        or ch in "♂♀（）"
    )
    ocr_name = _closest_match(name_clean, _pokemon_names, cutoff=0.85) if name_clean else ""
    if ocr_name and _ability_matches_pokemon(ocr_name, abil):
        return ocr_name

    # ③ 特性フィルタ（空になる場合は無視）
    if abil:
        abil_pids = _pids_with_ability(abil)
        filtered = [p for p in candidates if p in abil_pids]
        if filtered:
            candidates = filtered

    # ④ タイプアイコンフィルタ（空になる場合は無視）
    detected_types = _detect_types_from_card(card)
    if detected_types:
        type_filtered = _filter_by_types(candidates, detected_types)
        if type_filtered:
            candidates = type_filtered

    # ①-④ で1候補に絞れたら確定
    if len(candidates) == 1:
        return DB_pokemon.get_pokemon_name_by_pid(candidates[0]) or ""

    # ⑤ メガストーン → 直接特定
    if item and "ナイト" in item:
        stem = re.sub(r"ナイト[XYＸＹxy]?$", "", item).strip()
        if stem:
            mega_name = _closest_match(stem, _pokemon_names, cutoff=0.45)
            if mega_name:
                return mega_name

    # ⑥ HOME技フィルタ（空になる場合は無視）
    ocr_moves = {m for m in moves if m}
    if ocr_moves:
        home_waza = _load_home_waza()
        move_filtered = [
            pid for pid in candidates
            if ocr_moves & home_waza.get(DB_pokemon.get_pokemon_name_by_pid(pid) or "", set())
        ]
        if move_filtered:
            candidates = move_filtered

    # ⑦ HOMEランキング順で最終選択
    ranking = _load_ranking()
    if ranking:
        ranking_idx = {pid: i for i, pid in enumerate(ranking)}
        candidates.sort(key=lambda p: ranking_idx.get(p, len(ranking)))

    return DB_pokemon.get_pokemon_name_by_pid(candidates[0]) or "" if candidates else ""


# ---------------------------------------------------------------------------
# Text normalization & fuzzy match
# ---------------------------------------------------------------------------


def _normalize(text: str) -> str:
    """Strip, convert half-width kana to full-width, remove spaces."""
    text = text.strip()
    text = jaconv.h2z(text, kana=True, ascii=False, digit=False)
    text = text.replace(" ", "").replace("　", "")
    return text


def _closest_match(text: str, candidates: list[str], cutoff: float = 0.45) -> str:
    """Return the closest candidate by difflib ratio, or '' if below cutoff."""
    text = _normalize(text)
    if not text or not candidates:
        return ""
    matches = difflib.get_close_matches(text, candidates, n=1, cutoff=cutoff)
    if matches:
        return matches[0]
    # Lower-cutoff fallback for very short strings
    if len(text) <= 3:
        best = max(
            candidates, key=lambda c: difflib.SequenceMatcher(None, text, c).ratio()
        )
        ratio = difflib.SequenceMatcher(None, text, best).ratio()
        if ratio >= 0.3:
            return best
    return ""


# ---------------------------------------------------------------------------
# Image preprocessing (white text on dark background)
# ---------------------------------------------------------------------------


def _preprocess_white_text(img: Image.Image, scale: int = 3) -> Image.Image:
    """Extract white/near-white text (R,G,B > 170) for name/ability/item/move OCR."""
    arr = np.array(img.convert("RGB"))
    r, g, b = arr[:, :, 0], arr[:, :, 1], arr[:, :, 2]
    white_mask = (r > 170) & (g > 170) & (b > 170)
    binary = np.zeros(arr.shape[:2], dtype=np.uint8)
    binary[white_mask] = 255
    result = Image.fromarray(binary)
    w, h = result.size
    result = result.resize((w * scale, h * scale), Image.NEAREST)
    result = Image.fromarray(255 - np.array(result))
    return result.convert("RGB")


# ---------------------------------------------------------------------------
# OCR helpers
# ---------------------------------------------------------------------------


def _ocr_block(img: Image.Image) -> str:
    _configure_tesseract()
    prep = _preprocess_white_text(img)
    return pytesseract.image_to_string(
        prep, lang="jpn", config="--psm 6 --oem 3"
    ).strip()


def _ocr_line(img: Image.Image) -> str:
    _configure_tesseract()
    prep = _preprocess_white_text(img)
    return pytesseract.image_to_string(
        prep, lang="jpn", config="--psm 7 --oem 3"
    ).strip()


def _ocr_ev_row(img: Image.Image) -> str:
    """OCR a full stat row for the white stat-value + EV digits.

    Multi-threshold strategy — rules applied in order:

    Rule 1  ev170==0: trust if "0" is explicit; else fall back to thr=190.
    Rule A  Split-stat artefact: thr=170 splits a 2-digit stat (e.g. "81"→"8 1")
            and the trailing "1" is mistaken for EV=1.  thr=190 reads the stat
            whole and shows EV as a standalone "0" token → use thr=190 (ev=0).
    Rule 2  ev190 > ev170: thr=190 recovered a digit dropped by cleanup.
    Rule B  Single-digit cleanup distortion ("8"→"9"): ev170/ev190 disagree on
            a single non-zero digit → trust thr=190 (no cleanup).
    Rule C  Concatenation artefact: all thr=170 tokens are >32, meaning the EV
            digit was merged with the stat (e.g. "2169" for stat 216, EV 9 or
            "169" for stat 169, EV 32 in accent colour).  Try thr=150 which
            captures slightly-dimmer coloured EV digits; if it returns a larger
            value it found the real EV.
    """
    _configure_tesseract()
    arr_img = np.array(img.convert("RGB"))
    r, g, b = arr_img[:, :, 0], arr_img[:, :, 1], arr_img[:, :, 2]

    def _run(thr: int, cleanup: bool) -> str:
        wm = (r > thr) & (g > thr) & (b > thr)
        binary = np.zeros(arr_img.shape[:2], dtype=np.uint8)
        binary[wm] = 255
        if cleanup:
            col_frac = binary.mean(axis=0) / 255.0
            for xc in range(binary.shape[1] - 1, -1, -1):
                if col_frac[xc] > 0.85:
                    binary[:, xc] = 0
                else:
                    break
        result = Image.fromarray(binary)
        result = result.resize((result.width * 5, result.height * 5), Image.NEAREST)
        result = Image.fromarray(255 - np.array(result))
        padded = Image.new("RGB", (result.width + 50, result.height), (255, 255, 255))
        padded.paste(result.convert("RGB"), (0, 0))
        raw = pytesseract.image_to_string(
            padded, lang="jpn", config="--psm 7 --oem 3"
        ).strip()
        return re.sub(r"[^\d]", " ", raw).strip()

    text170 = _run(170, cleanup=True)
    ev170 = _parse_ev(text170)
    text190 = _run(190, cleanup=False)
    ev190 = _parse_ev(text190)

    # Rule 1
    if ev170 == 0:
        if "0" in re.findall(r"\d", text170):
            return text170
        return text190

    # Rule A: single-digit ev170 arises from a split stat number (e.g. "8","1"
    # for stat=81); thr=190 reads the stat whole and shows "0" as its own token.
    nums190 = re.findall(r"\d+", text190)
    if (
        len(str(ev170)) == 1
        and ev190 == 0
        and "0" in nums190
        and any(int(n) >= 40 for n in nums190)
    ):
        return text190

    # Rule 2
    if ev190 > ev170:
        if str(ev190).startswith(str(ev170)):
            return text190
        if len(str(ev170)) == 1 and len(str(ev190)) == 1:
            return text190

    # Rule B
    if len(str(ev170)) == 1 and len(str(ev190)) == 1 and ev190 != ev170 and ev190 > 0:
        return text190

    # Rule C: all thr=170 tokens are large (EV merged into stat or dim digit).
    # thr=150 captures slightly-dimmer coloured digits; prefer if larger.
    nums170 = re.findall(r"\d+", text170)
    if ev170 > 0 and nums170 and all(int(n) > 32 for n in nums170):
        text150 = _run(150, cleanup=False)
        ev150 = _parse_ev(text150)
        if ev150 > ev170:
            return text150

    return text170


def _parse_ev(text: str) -> int:
    """Extract EV value (0–32) from the digit tokens in a stat row.

    The row OCR produces the stat value (e.g. 187) followed by the EV (e.g. 32),
    sometimes with a space, sometimes concatenated ("18732").
    Strategy:
      1. Walk tokens right-to-left; find first token ≤ 32.
         If that token AND the previous token are both single digits,
         concatenate them — OCR sometimes splits a two-digit EV like "21"
         into "2" and "1".
      2. Concatenated: try 2-digit split first, then 1-digit
         (prefer 2-digit so "18732" → EV=32, not EV=2).
    """
    nums = re.findall(r"\d+", text)
    if not nums:
        return 0
    for i in reversed(range(len(nums))):
        v = int(nums[i])
        if v <= 32:
            # Two adjacent single-digit tokens may be a split 2-digit EV (e.g. "2","1" → 21)
            if i > 0 and len(nums[i]) == 1 and len(nums[i - 1]) == 1:
                combined = int(nums[i - 1] + nums[i])
                if combined <= 32:
                    return combined
            return v
    last = int(nums[-1])
    for digits in (2, 1):
        ev_part = last % (10**digits)
        stat_part = last // (10**digits)
        if ev_part <= 32 and stat_part >= 40:
            return ev_part
    return 0


# ---------------------------------------------------------------------------
# Card boundary detection
# ---------------------------------------------------------------------------


def _detect_cards(img: Image.Image, rows: int = 3, cols: int = 2) -> list[Image.Image]:
    """
    Detect the 6 card regions in a Pokémon HOME / SV party screen.

    Uses the purple card background to find card boundaries automatically,
    then finds the gap rows between card rows to produce clean crops.
    """
    arr = np.array(img.convert("RGB"), dtype=np.float32)
    h, w = arr.shape[:2]
    r, g, b = arr[:, :, 0], arr[:, :, 1], arr[:, :, 2]

    # Purple card background detection
    is_card = (b > 100) & (b > g + 20) & (r > 80) & (b < 250) & (g < 200)

    mid = w // 2
    left_frac = is_card[:, :mid].sum(axis=1) / (w // 2)
    right_frac = is_card[:, mid:].sum(axis=1) / (w // 2)
    col_frac = is_card.sum(axis=0) / h

    # Rows where both columns have purple = actual card rows (not header)
    both_purple = (left_frac > 0.05) & (right_frac > 0.05)

    # Split into contiguous segments → each segment is one card row
    row_segments: list[tuple[int, int]] = []
    in_seg = False
    seg_start = 0
    for y in range(h):
        if both_purple[y] and not in_seg:
            seg_start = y
            in_seg = True
        elif not both_purple[y] and in_seg:
            row_segments.append((seg_start, y))
            in_seg = False
    if in_seg:
        row_segments.append((seg_start, h))

    # Keep the `rows` largest segments (ignore header / tiny fragments)
    row_segments.sort(key=lambda s: s[1] - s[0], reverse=True)
    row_segments = sorted(row_segments[:rows], key=lambda s: s[0])

    # Column boundaries from col_frac
    thresh = 0.05
    cols_match = np.where(col_frac > thresh)[0]
    if len(cols_match) < 10:
        # Fallback column bounds
        x1_all, x2_all = int(w * 0.09), int(w * 0.91)
    else:
        x1_all = int(cols_match[0])
        x2_all = int(cols_match[-1]) + 1

    # Find the column gap (gap between left and right card columns)
    # Within the detected range find the lowest-density column
    col_in_range = col_frac[x1_all:x2_all]
    # Search for gap in middle third
    search_start = len(col_in_range) // 3
    search_end = 2 * len(col_in_range) // 3
    mid_region = col_in_range[search_start:search_end]
    gap_rel = int(np.argmin(mid_region)) + search_start
    x_mid = x1_all + gap_rel

    # Crop 6 cards (trim 4px top/bottom to remove bright border rows that
    # become black bands in OCR preprocessing and displace text lines)
    trim = 4
    card_crops: list[Image.Image] = []
    for y1, y2 in row_segments:
        card_crops.append(img.crop((x1_all, y1 + trim, x_mid, y2 - trim)))
        card_crops.append(img.crop((x_mid, y1 + trim, x2_all, y2 - trim)))

    return card_crops


# ---------------------------------------------------------------------------
# Card parsing
# ---------------------------------------------------------------------------


def _parse_info_card(card: Image.Image) -> dict:
    """
    Parse one info card (能力タブ):
      Left half  → name / ability / item  (3 lines via psm 6)
      Right half → 4 moves               (each row individually)
    """
    _load_reference_lists()

    w, h = card.size
    left = card.crop((0, 0, w // 2, h))
    right = card.crop((w // 2, 0, w, h))

    # OCR left half as a block → split into lines, take first 3.
    # Two noise filters:
    #  1. Lines with ≤ 2 characters: icon/border artifacts.
    #  2. Lines with fewer than 2 kana characters (hiragana U+3040-309F or
    #     katakana U+30A0-30FF): all Pokémon names, abilities, and items in
    #     SV contain kana, so lines without kana are UI-background OCR noise
    #     (e.g. "EPREEREEE昌還EEEE還還還" which has only ASCII/kanji).
    raw_left = _ocr_block(left)
    left_lines = [
        ln
        for line in raw_left.splitlines()
        if len((ln := line.strip())) > 2 and sum(1 for c in ln if "぀" <= c <= "ヿ") >= 2
    ]

    name_raw = left_lines[0] if len(left_lines) > 0 else ""
    abil_raw = left_lines[1] if len(left_lines) > 1 else ""
    item_raw = left_lines[2] if len(left_lines) > 2 else ""

    # OCR the right half as a block (psm 6) using three skip amounts and
    # taking whichever produces the most lines.  Different type-icon colors
    # bleed differently: skip=0 is needed for water/some types (first move
    # visible at the far left), skip=0.25 is needed for poison/ghost types
    # whose icon otherwise swallows the first move line entirely.
    best_lines: list[str] = []
    for skip_pct in (0.0, 0.18, 0.25):
        skip = max(1, int(right.size[0] * skip_pct)) if skip_pct > 0 else 0
        area = right.crop((skip, 0, right.size[0], h)) if skip > 0 else right.copy()
        raw = _ocr_block(area)
        lines = [ln for ln in raw.splitlines() if ln.strip()]
        if len(lines) > len(best_lines):
            best_lines = lines
    moves_raw = (best_lines + [""] * 4)[:4]

    abil = _closest_match(abil_raw, _ability_names, cutoff=0.40)
    item = _closest_match(item_raw, _item_names, cutoff=0.40)
    moves = [_closest_match(m, _waza_names, cutoff=0.40) for m in moves_raw]

    name = _identify_pokemon(card, name_raw, abil, item, moves)

    # 画像ファイルのないフォームは、実際に画像が存在するフォームの名前に差し替える
    if name:
        try:
            from component.parts.images import resolve_pid_by_image
            from database.pokemon import DB_pokemon

            pid = DB_pokemon.get_pokemon_pid_by_name(name)
            actual_pid = resolve_pid_by_image(pid)
            if actual_pid != pid:
                name = DB_pokemon.get_pokemon_name_by_pid(actual_pid)
        except Exception:
            pass

    return {"name": name, "ability": abil, "item": item, "moves": moves}


def _detect_arrow(row_img: Image.Image) -> Optional[str]:
    """
    Detect nature ↑/↓ arrow in a stat row.
    UP (↑): pink/salmon — R > 160 and R > G + 45
    DOWN (↓): bright cyan — G > 200 and B > 200 and G > R + 30
    Checks the left 60% of the row to avoid the orange stat bar (x ≥ 72%).
    """
    arr = np.array(row_img.convert("RGB"))
    _, w_row = arr.shape[:2]
    region = arr[:, : max(1, int(w_row * 0.60)), :]

    r = region[:, :, 0].astype(float)
    g = region[:, :, 1].astype(float)
    b = region[:, :, 2].astype(float)

    up_px = int(((r > 160) & (r > g + 45)).sum())
    down_px = int(((g > 200) & (b > 200) & (g > r + 30)).sum())

    if up_px > 5 and up_px > down_px:
        return "up"
    if down_px > 5 and down_px > up_px:
        return "down"
    return None


def _parse_ev_card(card: Image.Image) -> dict:
    """
    Parse one EV card (ステータスタブ).

    Layout (fraction of card height):
      Top ~27%  : Pokémon name/icon area (skip)
      Bottom 73%: Stats in 2 columns × 3 rows
        Left  column → H / A / B
        Right column → C / D / S
    Each stat row: icon | name | [↑↓?] | actual_value ——bar—— ev_value

    Arrow detection uses max-pixel selection: multiple rows may weakly match
    the arrow color (false positives), so we pick the row with the most
    matching pixels rather than the first one found.
    """
    w, h = card.size
    stat_top = int(h * 0.27)

    evs: dict[StatsKey, int] = {}
    up_counts: dict[StatsKey, int] = {}
    down_counts: dict[StatsKey, int] = {}

    for half_x, stat_keys in [
        (0, _LEFT_STATS),
        (w // 2, _RIGHT_STATS),
    ]:
        half = card.crop((half_x, stat_top, half_x + w // 2, h))
        half_h = half.size[1]
        row_h = max(1, half_h // 3)

        for i, key in enumerate(stat_keys):
            y0 = i * row_h
            y1 = min((i + 1) * row_h, half_h)
            row = half.crop((0, y0, half.size[0], y1))

            arr = np.array(row.convert("RGB"))
            _, w_row = arr.shape[:2]
            region = arr[:, : max(1, int(w_row * 0.60)), :]
            r = region[:, :, 0].astype(float)
            g = region[:, :, 1].astype(float)
            b = region[:, :, 2].astype(float)
            up_px = int(((r > 160) & (r > g + 45)).sum())
            down_px = int(((g > 200) & (b > 200) & (g > r + 30)).sum())
            if up_px > 5:
                up_counts[key] = up_px
            if down_px > 5:
                down_counts[key] = down_px

            text = _ocr_ev_row(row)
            evs[key] = _parse_ev(text)

    # Use the stat row with the MOST matching pixels as the canonical arrow.
    # This suppresses false positives (low pixel count) in favour of the row
    # that genuinely contains the pink ↑ or cyan ↓ arrow glyph.
    up_key = max(up_counts, key=up_counts.get) if up_counts else None
    down_key = max(down_counts, key=down_counts.get) if down_counts else None
    nature = (
        get_seikaku_from_arrows(up_key, down_key) if up_key and down_key else "まじめ"
    )

    return {"evs": evs, "nature": nature}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


@dataclass
class CardData:
    name: str = ""
    ability: str = ""
    item: str = ""
    moves: list[str] = field(default_factory=lambda: ["", "", "", ""])
    nature: str = "まじめ"
    evs: dict = field(default_factory=dict)  # {StatsKey: int}

    def ev_str(self) -> str:
        result = ""
        for label, key in zip(_EV_LABELS, _EV_KEYS, strict=True):
            val = self.evs.get(key, 0)
            if val > 0:
                result += f"{label}{val}"
        return result


def check_available() -> tuple[bool, str]:
    """Return (ok, reason). ok=True means Tesseract with 'jpn' is ready."""
    if not _TESSERACT_IMPORTED:
        return (
            False,
            "pytesseract がインストールされていません (pip install pytesseract)",
        )
    _configure_tesseract()
    cmd = getattr(pytesseract.pytesseract, "tesseract_cmd", "tesseract")
    try:
        langs = pytesseract.get_languages()
    except Exception as e:
        return False, f"Tesseract 実行エラー (コマンド: {cmd})\n{e}"
    if "jpn" not in langs:
        return False, f"日本語パック (jpn) が見つかりません。検出言語: {langs}"
    return True, ""


def parse_party_images(
    img1_path: Optional[str],
    img2_path: Optional[str],
    rows: int = 3,
    cols: int = 2,
    progress_callback=None,
) -> list[CardData]:
    """
    Parse party screen screenshots and return up to 6 CardData objects.

    img1: 能力タブ  (Pokémon name / ability / item / 4 moves)
    img2: ステータスタブ (EV values and nature arrows)
    Either image may be None; at least one must be provided.
    Pokémon name is readable from either image.
    """
    if not img1_path and not img2_path:
        raise RuntimeError("少なくとも1枚の画像を選択してください。")

    ok, reason = check_available()
    if not ok:
        raise RuntimeError(reason)

    cards1 = _detect_cards(Image.open(img1_path), rows, cols) if img1_path else None
    cards2 = _detect_cards(Image.open(img2_path), rows, cols) if img2_path else None

    count = min(6, len(cards1) if cards1 else 6, len(cards2) if cards2 else 6)

    results: list[CardData] = []
    for i in range(count):
        if cards1 and cards2:
            info = _parse_info_card(cards1[i])
            ev_data = _parse_ev_card(cards2[i])
        elif cards1:
            info = _parse_info_card(cards1[i])
            ev_data = {"nature": "まじめ", "evs": {k: 0 for k in _EV_KEYS}}
        else:
            name_info = _parse_info_card(cards2[i])
            info = {
                "name": name_info["name"],
                "ability": "",
                "item": "",
                "moves": ["", "", "", ""],
            }
            ev_data = _parse_ev_card(cards2[i])

        card = CardData(
            name=info["name"],
            ability=info["ability"],
            item=info["item"],
            moves=info["moves"],
            nature=ev_data["nature"],
            evs=ev_data["evs"],
        )
        results.append(card)
        if progress_callback:
            progress_callback(i, card.name)

    return results
