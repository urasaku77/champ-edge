"""
対戦待ち画面スクショから相手パーティを検出する。
グリッド固定スロット + グレースケール + 固定スケールのテンプレートマッチング。
"""
from pathlib import Path

import cv2
import numpy as np

IMG_DIR = Path("e:/champ-edge/regulation_images")

# test1.jpeg 解析から得たグリッドパラメータ
SLOT_CENTER_X = 1673
SLOT0_CENTER_Y = 212
SLOT_SPACING = 126
NUM_SLOTS = 6
SCALE = 1.06
ICON_SIZE = int(round(100 * SCALE))  # 106px
SEARCH_MARGIN = 40  # スロット中心から±px の探索範囲

# 上位N件を表示
TOP_N = 3


def load_references(img_dir: Path) -> dict[str, np.ndarray]:
    """regulation_images 内の全参照画像をグレースケール+リサイズで読み込む"""
    refs = {}
    for p in sorted(img_dir.glob("*.png")):
        if p.stem.startswith("test"):
            continue
        img = cv2.imread(str(p), cv2.IMREAD_GRAYSCALE)
        if img is None:
            continue
        resized = cv2.resize(img, (ICON_SIZE, ICON_SIZE), interpolation=cv2.INTER_AREA)
        refs[p.stem] = resized
    return refs


def slot_bbox(slot_idx: int) -> tuple[int, int, int, int]:
    """スロット番号 → 探索領域 (x1, y1, x2, y2)"""
    cx = SLOT_CENTER_X
    cy = SLOT0_CENTER_Y + slot_idx * SLOT_SPACING
    half = ICON_SIZE // 2 + SEARCH_MARGIN
    return (cx - half, cy - half, cx + half, cy + half)


def match_slot(
    gray_full: np.ndarray, slot_idx: int, refs: dict[str, np.ndarray]
) -> list[tuple[float, str]]:
    """1スロットに対して全参照画像でマッチングし、スコア降順リストを返す"""
    x1, y1, x2, y2 = slot_bbox(slot_idx)
    h, w = gray_full.shape[:2]
    x1, y1 = max(0, x1), max(0, y1)
    x2, y2 = min(w, x2), min(h, y2)
    roi = gray_full[y1:y2, x1:x2]

    scores = []
    for name, tmpl in refs.items():
        if tmpl.shape[0] > roi.shape[0] or tmpl.shape[1] > roi.shape[1]:
            continue
        result = cv2.matchTemplate(roi, tmpl, cv2.TM_CCOEFF_NORMED)
        score = float(result.max())
        scores.append((score, name))

    scores.sort(reverse=True)
    return scores


def draw_result(screenshot: np.ndarray, best_matches: list[str]) -> np.ndarray:
    vis = screenshot.copy()
    for i, name in enumerate(best_matches):
        cx = SLOT_CENTER_X
        cy = SLOT0_CENTER_Y + i * SLOT_SPACING
        half = ICON_SIZE // 2
        cv2.rectangle(
            vis, (cx - half, cy - half), (cx + half, cy + half), (0, 255, 0), 2
        )
        cv2.putText(
            vis,
            name,
            (cx - half, cy - half - 4),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.45,
            (0, 255, 0),
            1,
        )
    return vis


def detect(screenshot_path: Path):
    screenshot = cv2.imread(str(screenshot_path))
    if screenshot is None:
        print(f"ERROR: {screenshot_path} が読めません")
        return

    gray_full = cv2.cvtColor(screenshot, cv2.COLOR_BGR2GRAY)

    print("参照画像を読み込み中... ", end="", flush=True)
    refs = load_references(IMG_DIR)
    print(f"{len(refs)} 枚")

    print(
        f"\nスクショ: {screenshot_path.name}  ({screenshot.shape[1]}x{screenshot.shape[0]}px)"
    )
    print(
        f"グリッド: slot0_cy={SLOT0_CENTER_Y}, spacing={SLOT_SPACING}, icon={ICON_SIZE}px\n"
    )

    best_matches = []
    print(
        f"{'スロット':>4}  {'1位':>18}  {'スコア':>6}  │  {'2位':>18}  {'スコア':>6}  │  {'3位':>18}  {'スコア':>6}"
    )
    print("─" * 90)

    for i in range(NUM_SLOTS):
        scores = match_slot(gray_full, i, refs)
        top = scores[:TOP_N]
        best_matches.append(top[0][1])

        cols = []
        for score, name in top:
            cols.append(f"{name:>18}  {score:.4f}")
        print(f"  [{i+1}]  " + "  │  ".join(cols))

    # 可視化
    vis = draw_result(screenshot, best_matches)
    out_path = screenshot_path.parent / (screenshot_path.stem + "_detected.png")
    cv2.imwrite(str(out_path), vis)
    print(f"\n可視化: {out_path}")

    return best_matches


if __name__ == "__main__":
    detect(IMG_DIR / "test2.jpeg")
