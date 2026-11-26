"""Download the Gita app's sources into sources/cache/ (kept out of git).

    python -I tools/fetch_sources.py

- Annie Besant's translation, 4th edition (1922, public domain): the 18 chapters as Wikisource
  renders them (MediaWiki API, action=parse). One request every few seconds: the API answers
  "too many requests" to faster clients.
- The Digital Corpus of Sanskrit (Oliver Hellwig, CC BY 4.0): the Gita's 18 chapters in CoNLL-U
  and the lookup tables dictionary.csv and word-senses.csv (about 21 MB together).
- Tiro Devanagari Hindi and Sanskrit (SIL Open Font License) from google/fonts.

Files already present are kept. Nothing here comes from heritage.iitk.ac.in: its licence (HCAL)
forbids copying its modern translations by automated means.
"""
import json, os, sys, time, unicodedata, urllib.parse, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(os.path.dirname(HERE), 'sources', 'cache')
UA = {'User-Agent': 'personal-offline-reader/0.1'}
DCS = 'https://raw.githubusercontent.com/OliverHellwig/sanskrit/master/dcs/data/conllu/'
DCS_TREE = 'https://api.github.com/repos/OliverHellwig/sanskrit/git/trees/master?recursive=1'
FONTS = 'https://raw.githubusercontent.com/google/fonts/main/ofl/'


def get(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=120) as r:
        return r.read()


def save(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    open(path, 'wb').write(data)
    print(f'  {os.path.relpath(path, CACHE)}  {len(data)} bytes')


def besant():
    for n in range(1, 19):
        path = os.path.join(CACHE, 'besant', 'd%02dh.json' % n)
        if os.path.exists(path) and os.path.getsize(path) > 5000:
            continue
        q = urllib.parse.urlencode({'action': 'parse', 'page': f'Bhagavad-Gita (Besant 4th)/Discourse {n}',
                                    'prop': 'text', 'format': 'json'})
        for attempt in range(5):
            data = get('https://en.wikisource.org/w/api.php?' + q)
            if b'"parse"' in data[:200]:
                save(path, data); break
            time.sleep(45)                    # rate limited: wait and ask again
        else:
            sys.exit(f'Wikisource kept refusing chapter {n}')
        time.sleep(3)


def dcs():
    tree = None
    for n in range(1, 19):
        path = os.path.join(CACHE, 'dcs', 'bg%02d.conllu' % n)
        if os.path.exists(path):
            continue
        if tree is None:
            tree = [t['path'] for t in json.loads(get(DCS_TREE))['tree']]
        nfc = lambda p: unicodedata.normalize('NFC', p)          # GitHub may give either form
        name = next(p for p in tree if nfc(p).startswith('dcs/data/conllu/files/')
                    and f'MBh, 6, BhaGī {n}-' in nfc(p) and p.endswith('.conllu'))
        save(path, get('https://raw.githubusercontent.com/OliverHellwig/sanskrit/master/' + urllib.parse.quote(name)))
    for f in ('dictionary.csv', 'word-senses.csv'):
        path = os.path.join(CACHE, 'dcs', f)
        if not os.path.exists(path):
            save(path, get(DCS + 'lookup/' + f))


def fonts():
    for f in ('tirodevanagarihindi/TiroDevanagariHindi-Regular.ttf',
              'tirodevanagarisanskrit/TiroDevanagariSanskrit-Regular.ttf', 'tirodevanagarisanskrit/OFL.txt'):
        path = os.path.join(CACHE, 'fonts', os.path.basename(f))
        if not os.path.exists(path):
            save(path, get(FONTS + f))


if __name__ == '__main__':
    print('Besant (Wikisource)'); besant()
    print('Digital Corpus of Sanskrit'); dcs()
    print('Tiro Devanagari'); fonts()
    print('done:', CACHE)
