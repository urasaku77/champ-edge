"""
IMG_7612.JPG を使って capture.py の検知ロジックをOBSなしでテストする。
"""
import os
import sys
import types

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import cv2
from recog.capture import Capture

IMG_PATH = r"C:\Users\okada\Desktop\IMG_7612.JPG"


def load_image(path: str) -> cv2.typing.MatLike:
    img = cv2.imread(path)
    if img is None:
        raise FileNotFoundError(f"画像が読めません: {path}")
    return img


def patch_screenshot(capture: Capture, img):
    """get_screenshot をファイル読み込みで完全置き換え（全呼び出しに適用）"""
    def _fake_get_screenshot(self):
        self.img = img
    capture.get_screenshot = types.MethodType(_fake_get_screenshot, capture)


def main():
    img = load_image(IMG_PATH)
    h, w = img.shape[:2]
    print(f"画像サイズ: {w}x{h}px")

    capture = Capture()
    patch_screenshot(capture, img)

    print(f"現在のフェーズ: {capture.phase}")

    # --- chose_pokemon テスト ---
    print("\n=== chose_pokemon() (選出画面検知) ===")
    capture.img = img
    detected = capture.chose_pokemon()
    print(f"  結果: {'[OK] 検知あり' if detected else '[NG] 検知なし'}")

    c = capture.coords.dicCoord["sensyutu"]
    crop = img[c.top:c.bottom, c.left:c.right]
    print(f"  sensyutu 座標: top={c.top} bottom={c.bottom} left={c.left} right={c.right} -> {crop.shape[1]}x{crop.shape[0]}px")
    cv2.imwrite("dev/debug_sensyutu_crop.jpg", crop)
    print("  sensyutu クロップ保存: dev/debug_sensyutu_crop.jpg")

    # --- sensyutu フェーズ処理テスト ---
    print("\n=== image_recognize() フェーズ処理 ===")

    capture.phase = "sensyutu"
    capture.party_recognized = False
    result = capture.image_recognize()
    print(f"\n[sensyutu フェーズ]")
    print(f"  戻り値の型: {type(result).__name__}")
    print(f"  処理後フェーズ: {capture.phase}")

    if isinstance(result, tuple):
        party, tn = result
        print(f"  TN: '{tn}'")
        print(f"  パーティ認識数: {len([p for p in party if not p.is_empty])}/6")
        for i, p in enumerate(party):
            print(f"    [{i+1}] {p.name if not p.is_empty else '(空)'}")
    elif isinstance(result, list):
        print(f"  banme_list: {result}")
    elif result is None:
        print("  -> None (sensyutu 未検知 -> rate フェーズへ移行)")

    # --- rate フェーズテスト ---
    print("\n[rate フェーズ]")
    capture.phase = "rate"
    result_rate = capture.image_recognize()
    print(f"  戻り値: {result_rate}")
    print(f"  処理後フェーズ: {capture.phase}")

    # --- battle フェーズテスト ---
    print("\n[battle フェーズ]")
    capture.phase = "battle"
    result_battle = capture.image_recognize()
    print(f"  戻り値: {result_battle}")
    print(f"  処理後フェーズ: {capture.phase}")

    # --- 各座標クロップの可視化 ---
    print("\n=== 座標クロップ画像を保存 ===")
    debug_crops = {
        "rate": capture.coords.dicCoord["rate"],
        "battle": capture.coords.dicCoord["battle"],
        "opoPoke1": capture.coords.dicCoord["opoPoke1"],
        "opoPoke2": capture.coords.dicCoord["opoPoke2"],
        "opoTn": capture.coords.dicCoord["opoTn"],
    }
    for name, coord in debug_crops.items():
        crop = img[coord.top:coord.bottom, coord.left:coord.right]
        out = f"dev/debug_{name}_crop.jpg"
        cv2.imwrite(out, crop)
        print(f"  {name}: {crop.shape[1]}x{crop.shape[0]}px -> {out}")

    print("\n=== テスト完了 ===")


if __name__ == "__main__":
    main()
