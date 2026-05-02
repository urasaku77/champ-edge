import os
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

URL = "https://bulbapedia.bulbagarden.net/wiki/Regulation_Set_M-A"
SAVE_DIR = os.path.join(os.path.dirname(__file__), "regulation_images")

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}


def fetch_page(url):
    resp = requests.get(url, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    return resp.text


def find_target_imgs(html):
    soup = BeautifulSoup(html, "html.parser")
    imgs = []

    # 指定のstyleを持つdiv.roundy を探す
    for div in soup.find_all("div", class_="roundy"):
        style = div.get("style", "")
        if "#564DA3" in style and "#AFA7FC" in style:
            for img in div.find_all("img"):
                src = img.get("src", "")
                if src:
                    imgs.append(src)

    if not imgs:
        # フォールバック: roundyクラスのdiv内の全img
        print(
            "[INFO] 指定スタイルのdivが見つかりませんでした。roundy内の全imgを対象にします。"
        )
        for div in soup.find_all("div", class_="roundy"):
            for img in div.find_all("img"):
                src = img.get("src", "")
                if src:
                    imgs.append(src)

    return list(dict.fromkeys(imgs))  # 重複除去・順序保持


def resolve_url(src, base_url):
    if src.startswith("//"):
        return "https:" + src
    if src.startswith("http"):
        return src
    return urljoin(base_url, src)


def download_image(img_url, save_dir, idx):
    resp = requests.get(img_url, headers=HEADERS, timeout=30)
    resp.raise_for_status()

    parsed = urlparse(img_url)
    filename = os.path.basename(parsed.path)
    # ファイル名が重複する場合に連番を付ける
    base, ext = os.path.splitext(filename)
    save_path = os.path.join(save_dir, filename)
    if os.path.exists(save_path):
        save_path = os.path.join(save_dir, f"{base}_{idx}{ext}")

    with open(save_path, "wb") as f:
        f.write(resp.content)
    return save_path


def main():
    os.makedirs(SAVE_DIR, exist_ok=True)
    print(f"ページを取得中: {URL}")
    html = fetch_page(URL)

    srcs = find_target_imgs(html)
    if not srcs:
        print("対象の画像が見つかりませんでした。")
        return

    print(f"{len(srcs)} 件の画像を検出しました。ダウンロード開始...")
    ok, fail = 0, 0
    for i, src in enumerate(srcs, 1):
        img_url = resolve_url(src, URL)
        try:
            path = download_image(img_url, SAVE_DIR, i)
            print(f"  [{i}/{len(srcs)}] 保存: {os.path.basename(path)}")
            ok += 1
        except Exception as e:
            print(f"  [{i}/{len(srcs)}] 失敗: {img_url}  ({e})")
            fail += 1

    print(f"\n完了: 成功 {ok} 件 / 失敗 {fail} 件")
    print(f"保存先: {SAVE_DIR}")


if __name__ == "__main__":
    main()
