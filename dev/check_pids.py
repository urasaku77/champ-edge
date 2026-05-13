import os, sys
os.chdir(r"e:\champ-edge")
sys.path.insert(0, r"e:\champ-edge")
from database.pokemon import DB_pokemon

for pid in ["956-0", "959-0", "964-0", "968-0", "970-0", "981-0", "1013-0", "1018-0", "1019-0"]:
    name = DB_pokemon.get_pokemon_name_by_pid(pid)
    print(f"{pid}: {name}")
