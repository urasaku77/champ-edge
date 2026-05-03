import json
import sys
from functools import reduce

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

sys.path.append("../champ-edge")
from pokedata.pokemon import Pokemon

_SEASON_FILE = "stats/season.txt"
_RANKING_JSON_FILE = "stats/ranking.json"
_RANKING_TXT_FILE = "stats/ranking.txt"


def _load_season() -> str:
    with open(_SEASON_FILE, encoding="utf-8") as f:
        return f.read().strip()


def get_similar_party(pids: list[Pokemon]) -> list:
    with open(_RANKING_JSON_FILE, encoding="utf-8") as f:
        rankings = json.load(f)

    ranking_map: dict[str, list[dict]] = {r["pid"]: r["parties"] for r in rankings}
    url_to_party: dict[str, dict] = {}
    all_url_sets: list[set] = []
    has_undefine = False
    undefine_urls: set[str] = set()

    for pid in pids:
        if 892 == pid.no:
            has_undefine = True
            for key in ("0892-00", "0892-01"):
                for party in ranking_map.get(key, []):
                    undefine_urls.add(party["url"])
                    url_to_party[party["url"]] = party
        else:
            key = str(pid.no).zfill(4) + "-" + str(pid.form).zfill(2)
            parties = ranking_map.get(key, [])
            urls: set[str] = set()
            for party in parties:
                urls.add(party["url"])
                url_to_party[party["url"]] = party
            if urls:
                all_url_sets.append(urls)

    if not all_url_sets and not has_undefine:
        return []

    if all_url_sets:
        result_urls = reduce(set.intersection, all_url_sets)
    else:
        result_urls = set()

    if has_undefine:
        result_urls = (result_urls & undefine_urls) if result_urls else undefine_urls

    return [url_to_party[url] for url in result_urls if url in url_to_party]


class Search:
    def search_latest_party(self):
        season = int(_load_season())
        seasons = [str(season)]
        if season > 1:
            seasons.append(str(season - 1))

        with open(_RANKING_TXT_FILE, encoding="utf-8") as f:
            pids = [line.strip() for line in f if line.strip()]

        options = webdriver.ChromeOptions()
        options.add_argument("--headless")
        driver = webdriver.Chrome(options=options)

        print(f"構築記事一覧取得処理開始（シーズン: {', '.join(seasons)}）")
        party_list = []
        try:
            for i, pid in enumerate(pids):
                num = 200 if i < 30 else 50 if i < 100 else 10
                print(f"{i+1}/{len(pids)}：{pid}")
                parties = self._scrape_parties(driver, pid, seasons, num)
                party_list.append({"pid": pid, "parties": parties})
        finally:
            driver.quit()

        print("読み込み完了")
        with open(_RANKING_JSON_FILE, "w", encoding="utf-8") as f:
            json.dump(party_list, f, indent=2, ensure_ascii=False)
        print("書き込み完了")

    def _scrape_parties(self, driver, pid: str, seasons: list[str], num: int) -> list[dict]:
        results: list[dict] = []
        seen_urls: set[str] = set()

        for season in seasons:
            try:
                driver.get(
                    f"https://champs.pokedb.tokyo/pokemon/show/{pid}?season={season}&rule=0"
                )

                try:
                    WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located(
                            (By.CLASS_NAME, "trainer-card")
                        )
                    )
                except Exception:
                    continue

                # 「全件表示」ボタンがあればクリックして全件ロード
                initial_count = len(driver.find_elements(By.CLASS_NAME, "trainer-card"))
                show_all = driver.find_elements(
                    By.XPATH, "//button[.//span[text()='全件表示']]"
                )
                if show_all:
                    try:
                        driver.execute_script("arguments[0].click();", show_all[0])
                        WebDriverWait(driver, 10).until(
                            lambda d, n=initial_count: len(d.find_elements(By.CLASS_NAME, "trainer-card")) > n
                        )
                    except Exception:
                        pass

                trainer_classes = driver.find_elements(By.CLASS_NAME, "trainer-card")
                count = 0
                for trainer in trainer_classes:
                    if count >= num:
                        break

                    icon_classes = trainer.find_elements(
                        By.CLASS_NAME, "trainer-card-team__pokemon"
                    )
                    icons = []
                    for icon_el in icon_classes:
                        try:
                            href = icon_el.find_element(By.TAG_NAME, "a").get_attribute("href")
                            no = href.split("show/")[1].split("-")[0]
                            form_str = href.split(f"{no}-")[1].split("?")[0].lstrip("0")
                            form = form_str if form_str else "0"
                            icons.append(f"{int(no)}-{form}")
                        except Exception:
                            continue

                    article_divs = trainer.find_elements(
                        By.CLASS_NAME, "trainer-card-team__article"
                    )
                    article_url = ""
                    if article_divs:
                        a_tags = article_divs[0].find_elements(By.TAG_NAME, "a")
                        if a_tags:
                            article_url = a_tags[0].get_attribute("href")

                    if article_url and article_url not in seen_urls and len(icons) == 6:
                        seen_urls.add(article_url)
                        results.append({"url": article_url, "icons": icons})
                        count += 1

            except Exception as e:
                print(f"  取得失敗 {pid} season={season}: {e}")

        return results


if __name__ == "__main__":
    search = Search()
    search.search_latest_party()
