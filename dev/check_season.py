import sys

sys.stdout.reconfigure(encoding="utf-8")
sys.path.append("../champ-edge")

from selenium import webdriver

from stats.search import Search, _load_season

season = int(_load_season())
seasons = [str(season)]
if season > 1:
    seasons.append(str(season - 1))

options = webdriver.ChromeOptions()
options.add_argument("--headless")
driver = webdriver.Chrome(options=options)

try:
    parties = Search()._scrape_parties(driver, "0445-00", seasons, num=200)
finally:
    driver.quit()

print(f"取得件数: {len(parties)}")
for r in parties:
    print(f"  {r['url']}")
