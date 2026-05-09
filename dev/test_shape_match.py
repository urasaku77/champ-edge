"""
Test tight-bbox shape matching against image/pokemon/*.png.
Uses IMG_7619.JPG (the same party screenshot tested before).
Prints per-card top-5 matches with scores (silhouette + gray + edge).
"""
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import glob

import cv2
from PIL import Image

from party.image_parser import (
    _MATCH_SIZE,
    _detect_cards,
    _extract_card_sprite_gray,
    _extract_card_sprite_mask,
    _extract_template_gray,
    _extract_template_mask,
    _path_to_pid,
    _resize_with_pad,
)

IMG_PATH = r"C:\Users\okada\Desktop\IMG_7619.JPG"
TEMPLATE_DIR = "image/pokemon"
TOP_N = 5


def match_all(card: Image.Image):
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))

    q_mask = _extract_card_sprite_mask(card, cv2)
    q_gray = _extract_card_sprite_gray(card, cv2)
    if q_mask is None and q_gray is None:
        return []

    q_sil = _resize_with_pad(q_mask, _MATCH_SIZE, cv2) if q_mask is not None else None
    if q_gray is not None:
        q_c = clahe.apply(_resize_with_pad(q_gray, _MATCH_SIZE, cv2))
        q_e = cv2.Canny(q_c, 20, 80)
    else:
        q_c = q_e = None

    results = []
    for tpl_path in glob.glob(f"{TEMPLATE_DIR}/*"):
        try:
            scores = []
            if q_sil is not None:
                t_mask = _extract_template_mask(tpl_path, cv2)
                if t_mask is not None and t_mask.size > 0:
                    t_sil = _resize_with_pad(t_mask, _MATCH_SIZE, cv2)
                    _, vs, _, _ = cv2.minMaxLoc(
                        cv2.matchTemplate(q_sil, t_sil, cv2.TM_CCOEFF_NORMED)
                    )
                    scores.append(("sil", vs))

            if q_c is not None:
                t_raw = _extract_template_gray(tpl_path, cv2)
                if t_raw is not None and t_raw.size > 0:
                    t_c = clahe.apply(_resize_with_pad(t_raw, _MATCH_SIZE, cv2))
                    t_e = cv2.Canny(t_c, 20, 80)
                    _, vc, _, _ = cv2.minMaxLoc(
                        cv2.matchTemplate(q_c, t_c, cv2.TM_CCOEFF_NORMED)
                    )
                    _, ve, _, _ = cv2.minMaxLoc(
                        cv2.matchTemplate(q_e, t_e, cv2.TM_CCOEFF_NORMED)
                    )
                    scores.extend([("gray", vc), ("edge", ve)])

            if not scores:
                continue
            best_score = max(v for _, v in scores)
            results.append((best_score, tpl_path, {k: v for k, v in scores}))
        except Exception:
            continue

    results.sort(reverse=True)
    return results[:TOP_N]


def main():
    img = Image.open(IMG_PATH)
    cards = _detect_cards(img)
    print(f"カード数: {len(cards)}")

    expected = ["ガブリアス", "ミミロップ", "イダイトウ♂", "?", "キラフロル", "アシレーヌ"]

    from database.pokemon import DB_pokemon

    for i, card in enumerate(cards):
        print(f"\n=== Card {i+1} (期待: {expected[i]}) ===")

        q_mask = _extract_card_sprite_mask(card, cv2)
        q_gray = _extract_card_sprite_gray(card, cv2)
        if q_mask is not None:
            cv2.imwrite(f"dev/debug_card{i+1}_mask.png", q_mask)
            padded = _resize_with_pad(q_mask, _MATCH_SIZE, cv2)
            cv2.imwrite(f"dev/debug_card{i+1}_mask_padded.png", padded)
            print(f"  mask: {q_mask.shape[1]}x{q_mask.shape[0]}px")
        else:
            print("  mask: 抽出失敗")
        if q_gray is not None:
            cv2.imwrite(f"dev/debug_card{i+1}_sprite_bbox.png", q_gray)

        tops = match_all(card)
        for rank, (val, path, scores) in enumerate(tops, 1):
            try:
                pid = _path_to_pid(path)
                name = DB_pokemon.get_pokemon_name_by_pid(pid)
            except Exception:
                name = path
            score_str = "  ".join(f"{k}={v:.3f}" for k, v in scores.items())
            print(f"  #{rank}  best={val:.3f}  {score_str}  {name}")

    print("\n=== 完了 ===")


if __name__ == "__main__":
    main()
