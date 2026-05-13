import os, sys
os.chdir(r'e:\champ-edge')
sys.path.insert(0, r'e:\champ-edge')

from pokedata.pokemon import Pokemon

names = ['マスカーニャ', 'ルカリオ', 'ガブリアス', 'アシレーヌ', 'リザードン',
         'ミミッキュ', 'ドラパルト', 'ドドゲザン', 'アーマーガア', 'カイリュー',
         'ハバタクカミ', 'サーフゴー', 'イエッサン♀', 'イダイトウ♂']
for name in names:
    try:
        p = Pokemon.by_name(name)
        print(f'{name}: pid={p.pid}, no={p.no}')
    except Exception as e:
        print(f'{name}: ERROR {e}')
