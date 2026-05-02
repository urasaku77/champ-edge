import json
import sys
import time
from functools import reduce

from selenium import webdriver
from selenium.webdriver.common.by import By

sys.path.append("../champ-edge")
from pokedata.pokemon import Pokemon

_BATTLE_SEASON_FILE = "stats/battle_season.txt"
_RANKING_JSON_FILE = "stats/ranking.json"
_RANKING_TXT_FILE = "stats/ranking.txt"


def _load_battle_seasons() -> list[str]:
    with open(_BATTLE_SEASON_FILE, encoding="utf-8") as f:
        return [line.strip() for line in f if line.strip()]


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
        seasons = _load_battle_seasons()
        if not seasons:
            print("battle_season.txt が空です")
            return

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

        try:
            for season in seasons:
                driver.get(
                    f"https://champs.pokedb.tokyo/pokemon/show/{pid}?season={season}&rule=0"
                )

                trainer_classes = driver.find_elements(
                    By.XPATH, "//div[@class='trainer-team is-flex']"
                )
                count = 0
                for trainer in trainer_classes:
                    if count >= num:
                        break

                    icon_classes = trainer.find_elements(
                        By.XPATH, ".//div[@class='team-pokemon']"
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

                    elements = trainer.find_elements(
                        By.XPATH,
                        ".//a[contains(@class,'link-team-article')]",
                    )
                    article_url = elements[0].get_attribute("href") if elements else ""

                    if article_url and article_url not in seen_urls and len(icons) == 6:
                        seen_urls.add(article_url)
                        results.append({"url": article_url, "icons": icons})
                        count += 1

                time.sleep(0.5)
        except Exception as e:
            print(f"  取得失敗 {pid}: {e}")

        return results


if __name__ == "__main__":
    search = Search()
    search.search_latest_party()
