"""
test1.jpeg の右側パーティ欄から6匹の位置と縮小率を求める。
マルチスケール・テンプレートマッチング + グリッド推定で各スロットに絞って検索。
"""
from pathlib import Path

import cv2
import numpy as np

IMG_DIR = Path("e:/champ-edge/regulation_images")
SCREENSHOT = IMG_DIR / "test1.jpeg"

# 期待されるポケモン（上から順）
TARGETS = ["0445", "0748", "0823", "0006", "0149", "0887"]

# 探索スケール範囲（参照画像は100x100px）
SCALES = np.arange(0.5, 1.5, 0.02)

# スクリーンショットの右側エリア（全体幅1920）
ROI_X_START = 1600
ROI_X_END   = 1920


def match_in_region(gray_full, template_bgr, x1, y1, x2, y2, scales=SCALES):
    """指定領域内でマルチスケールマッチングし最良スケール・位置を返す"""
    roi = gray_full[y1:y2, x1:x2]
    tmpl_gray = cv2.cvtColor(template_bgr, cv2.COLOR_BGR2GRAY)
    h, w = tmpl_gray.shape[:2]

    best_val = -1
    best_loc = (0, 0)
    best_scale = 1.0

    for scale in scales:
        new_w = max(1, int(w * scale))
        new_h = max(1, int(h * scale))
        resized = cv2.resize(tmpl_gray, (new_w, new_h))

        if resized.shape[0] > roi.shape[0] or resized.shape[1] > roi.shape[1]:
            continue

        result = cv2.matchTemplate(roi, resized, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, max_loc = cv2.minMaxLoc(result)

        if max_val > best_val:
            best_val = max_val
            best_loc = max_loc
            best_scale = scale

    mw = int(w * best_scale)
    mh = int(h * best_scale)
    # ROI相対座標 → 全体座標
    abs_x = best_loc[0] + x1
    abs_y = best_loc[1] + y1
    cx = abs_x + mw // 2
    cy = abs_y + mh // 2
    return best_val, (abs_x, abs_y), best_scale, (mw, mh), (cx, cy)


def estimate_grid(results_so_far):
    """検出済み結果からスロット間隔とY起点を推定する"""
    ys = sorted([r["center"][1] for r in results_so_far])
    if len(ys) >= 2:
        gaps = [ys[i+1] - ys[i] for i in range(len(ys)-1)]
        spacing = int(np.median(gaps))
    else:
        spacing = 127  # デフォルト推定値
    return spacing


def main():
    screenshot = cv2.imread(str(SCREENSHOT))
    if screenshot is None:
        print(f"ERROR: {SCREENSHOT} が読めません")
        return

    sh, sw = screenshot.shape[:2]
    print(f"スクリーンショット: {sw}x{sh}px")
    print("参照画像: 100x100px\n")

    gray_full = cv2.cvtColor(screenshot, cv2.COLOR_BGR2GRAY)

    # ステップ1: まず全スロット全体を広く検索（Y全域、右端エリアのみ）
    # 初回は各ポケモンをフル高さで検索し中心Yを収集
    print("=== ステップ1: 各ポケモンの初期検索（右パネル全体） ===")
    raw_results = []
    for pid in TARGETS:
        candidates = sorted(IMG_DIR.glob(f"{pid}.png"))
        if not candidates:
            print(f"  {pid}: 参照画像が見つかりません")
            raw_results.append(None)
            continue
        tmpl = cv2.imread(str(candidates[0]))
        val, (ax, ay), scale, (mw, mh), (cx, cy) = match_in_region(
            gray_full, tmpl,
            ROI_X_START, 0, ROI_X_END, sh
        )
        raw_results.append({
            "id": pid, "score": val, "top_left": (ax, ay),
            "center": (cx, cy), "match_size": (mw, mh), "scale": scale,
            "tmpl": tmpl,
        })
        print(f"  {pid}  score={val:.4f}  center=({cx},{cy})  scale=x{scale:.2f}")

    # ステップ2: 高スコアの結果からグリッド間隔を推定
    good = [r for r in raw_results if r and r["score"] >= 0.80]
    spacing = estimate_grid(good)
    print(f"\nグリッド間隔推定: {spacing}px")

    # ステップ3: グリッドに基づいて各スロットのY範囲を決定し再検索
    # 最もスコアの高い2点を使って起点を確定
    anchors = sorted(good, key=lambda r: r["score"], reverse=True)[:2]
    anchors_cy = sorted([a["center"][1] for a in anchors])

    # 1番目スロットのcenter_yを逆算
    # 例: 2番目のスロットのy=338 で spacing=126 → 1番のy=212
    # Targetのindexから何番目スロットかを決定
    anchor_slot_indices = [TARGETS.index(a["id"]) for a in sorted(anchors, key=lambda r: r["center"][1])]
    slot0_cy = anchors_cy[0] - anchor_slot_indices[0] * spacing
    print(f"スロット0中心Y推定: {slot0_cy:.0f}px\n")

    print(f"{'ポケモン':>8}  {'スコア':>6}  {'左上(x,y)':>14}  {'中心(x,y)':>14}  {'サイズ':>10}  {'縮小率':>6}")
    print("-" * 80)

    final_results = []
    for i, pid in enumerate(TARGETS):
        expected_cy = int(slot0_cy + i * spacing)
        margin = int(spacing * 0.6)
        y1 = max(0, expected_cy - margin)
        y2 = min(sh, expected_cy + margin)

        r0 = raw_results[i]
        if r0 is None:
            continue
        tmpl = r0["tmpl"]

        val, (ax, ay), scale, (mw, mh), (cx, cy) = match_in_region(
            gray_full, tmpl,
            ROI_X_START, y1, ROI_X_END, y2
        )

        final_results.append({
            "id": pid, "score": val, "top_left": (ax, ay),
            "center": (cx, cy), "match_size": (mw, mh), "scale": scale,
        })
        print(f"  {pid}  {val:.4f}  ({ax:4d},{ay:4d})  ({cx:4d},{cy:4d})  {mw}x{mh}px  x{scale:.2f}")

    # サマリ
    print("\n=== サマリ ===")
    scales_list = [r["scale"] for r in final_results]
    print(f"縮小率: min={min(scales_list):.2f}, max={max(scales_list):.2f}, 平均={np.mean(scales_list):.2f}")
    print(f"参照画像 100px × {np.mean(scales_list):.2f} ≒ {100*np.mean(scales_list):.0f}px がゲーム内アイコンサイズ")

    print("\n[将来の検出用パラメータ]")
    print(f"ROI_X_START = {ROI_X_START}")
    print(f"スロット0中心Y = {slot0_cy:.0f}")
    print(f"スロット間隔   = {spacing}px")
    print(f"推奨スケール範囲 = {min(scales_list):.2f} ~ {max(scales_list):.2f}")

    # 可視化
    vis = screenshot.copy()
    for r in final_results:
        x, y = r["top_left"]
        mw, mh = r["match_size"]
        cv2.rectangle(vis, (x, y), (x + mw, y + mh), (0, 255, 0), 2)
        cv2.putText(vis, r["id"], (x, max(0, y - 4)), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)

    out_path = IMG_DIR / "test1_detected.png"
    cv2.imwrite(str(out_path), vis)
    print(f"\n可視化: {out_path}")


if __name__ == "__main__":
    main()
