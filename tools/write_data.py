"""Write the app's data files (data/) from sources/gita.json: plain text, no pictures.

    python -I tools/write_data.py      # after build_data.py

The reader draws Devanagari itself with the .ttf picked in Ink App settings (Tiro Devanagari Hindi,
checked on the device: conjuncts and vowel signs come out right), so the Devanagari goes in as
UTF-8 text and the app lays it out.

The verses are cut into many small files: when the reader cannot seek in a file, the app reads it
from the top up to the verse, and that must stay quick (0.2's 900 KB files took up to 15 s).

data/chapters.txt   line 0: 0<TAB>0<TAB>The Bhagavad Gita<TAB>श्रीमद्भगवद्गीता
                    then n<TAB>verses<TAB>title<TAB>Devanagari name
data/index.txt      "cc vvv fff oooooo": verse k is record k (fixed width): chapter, verse, file, byte offset
data/vNNN.txt       a verse is one V line, then one T line per printed word:
  V<TAB>ref<TAB>speaker<TAB>english<TAB>notes<TAB>shloka<TAB>n
    notes separated by \\x1f; shloka = lines separated by \\x1e, a line = items separated by \\x1f,
    an item is a printed word, or punctuation marked with a leading ~ (। or ॥ १२ ॥)
  T<TAB>printed word<TAB>padas<TAB>words
    padas: pada\\x1fgloss, separated by \\x1e (the padachheda of this word, with the short meaning)
    words: label\\x1fgrammar\\x1fsense\\x1fmeaning, separated by \\x1e (the word page)
English is folded to the letters the reader's system font has (Krishna, Ârya), as Besant writes it.
"""
import json, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
APP = os.path.dirname(HERE)
SRC = os.path.join(APP, 'sources', 'gita.json')
DATA = os.path.join(APP, 'data')
sys.path.insert(0, HERE)
from gloss import pada_gloss  # noqa: E402

FILES_MAX = 110              # xtpack takes 128 data files; a few are left for chapters.txt, index.txt
SMALL = {'of', 'the', 'and', 'by', 'from', 'between', 'a', 'to', 'in'}
MEAN_MAX = 160               # dictionary meanings on the word page are cut here

# IAST letters the reader's system font may lack, written the way Besant writes them (Krishna, Ârya)
FOLD = [('ṛ', 'ri'), ('Ṛ', 'Ri'), ('ṝ', 'rî'), ('ḷ', 'li'), ('ṣ', 'sh'), ('Ṣ', 'Sh'), ('ś', 'sh'), ('Ś', 'Sh'),
        ('ṇ', 'n'), ('Ṇ', 'N'), ('ṭ', 't'), ('Ṭ', 'T'), ('ḍ', 'd'), ('Ḍ', 'D'), ('ḥ', 'h'), ('ṃ', 'm'),
        ('ṁ', 'm'), ('ṅ', 'n'), ('ñ', 'n'), ('ā', 'â'), ('Ā', 'Â'), ('ī', 'î'), ('Ī', 'Î'), ('ū', 'û'),
        ('Ū', 'Û'), ('ē', 'e'), ('ō', 'o'), ('’', "'"), ('‘', "'"), ('“', '"'),
        ('”', '"'), ('—', ' - '), ('–', '-'), ('ﾱ', 'li')]


def clean(s):
    s = re.sub(r'[\t\n\r\x1e\x1f]+', ' ', s or '').strip()
    for a, b in FOLD:
        s = s.replace(a, b)
    return s


def deva(s):
    return re.sub(r'[\t\n\r\x1e\x1f~]+', ' ', s or '').strip()


def merge_tail(row):
    """'॥', '१२', '॥' at the end of a line as one item, so the verse number never breaks"""
    if len(row) >= 3 and row[-1]['d'] == '॥' and row[-3]['d'] == '॥' and 'w' not in row[-2]:
        return row[:-3] + [{'d': '॥ %s ॥' % row[-2]['d']}]
    return row


def groups(t):
    """the DCS words of a printed word, cut into padas: compound members and a negative prefix go
    with the word after them (as build_data.py joins them for the padachheda)"""
    out, cur = [], []
    for w in t['w']:
        cur.append(w)
        if not (w['gram'].startswith('first part of a compound') or w['gram'] == 'negative prefix'):
            out.append(cur); cur = []
    if cur:
        out.append(cur)
    return out


def cut(s, n):
    s = clean(s)
    if len(s) <= n:
        return s
    s = s[:n]
    return (s.rsplit(';', 1)[0] if ';' in s else s.rsplit(' ', 1)[0]).rstrip(' ;,')


def verse_records(ch, v):
    ref = '%d.%d' % (ch['n'], v['v'])
    lines, toks = [], []
    for row in v['lines']:
        items = []
        for t in merge_tail(row):
            if 'w' in t:
                toks.append(t)
                items.append(deva(t['d']))
            else:
                items.append('~' + deva(t['d']))
        lines.append('\x1f'.join(items))
    notes = '\x1f'.join(clean(n) for n in v['notes'])
    out = ['\t'.join(['V', ref, clean(v.get('en_speaker') or ''), clean(v['en']), notes, '\x1e'.join(lines),
                      str(len(toks))])]
    for t in toks:
        padas, gs = t['p'] or [t['d']], groups(t)
        if len(padas) == len(gs):
            units = [(p, pada_gloss(g)) for p, g in zip(padas, gs)]
        else:                              # no split for this word: one gloss for all of it
            units = [(t['d'], ' '.join(pada_gloss(g) for g in gs))]
        words = []
        for w in t['w']:
            label = w['d'] if w['ld'] in (w['d'], '') else '%s  (%s)' % (w['d'], w['ld'])
            words.append('\x1f'.join([deva(label), clean(w['gram']), cut(w['sense'], 60), cut(w['mean'], MEAN_MAX)]))
        out.append('\t'.join(['T', deva(t['d']), '\x1e'.join(deva(p) + '\x1f' + clean(g) for p, g in units),
                              '\x1e'.join(words)]))
    return ref, out


def chapter_name(ch):
    """the colophon's "... अर्जुनविषादयोगो नाम": the word before नाम; after an avagraha (ऽ) the elided
    अ comes back (संवादेऽर्जुन... is संवादे + अर्जुन...)"""
    m = re.search(r'(\S+)ो\s*नाम', ' '.join(ch['colophon_deva']))
    if not m:
        return ''
    name = m.group(1)
    if 'ऽ' in name:
        name = 'अ' + name.split('ऽ')[-1]
    return name + 'ः'


def main():
    src = json.load(open(SRC, encoding='utf-8'))
    os.makedirs(DATA, exist_ok=True)
    for f in os.listdir(DATA):           # this script's files, and those of the picture versions (0.1, 0.2)
        if re.match(r'^(v\d\d\d|gita\d\d|pool\d\d|poolidx|index|chapters)\.txt$', f):
            os.remove(os.path.join(DATA, f))
    verses = []
    for ch in src['chapters']:
        for v in ch['verses']:
            ref, lines = verse_records(ch, v)
            verses.append((ch['n'], v['v'], ('\n'.join(lines) + '\n').encode('utf-8')))
    total = sum(len(b) for _c, _v, b in verses)
    target = max(12_000, total // FILES_MAX + 1)
    while True:                          # files as small as the file count allows
        index, files, cur, cur_bytes = [], [], [], 0
        for c, v, blob in verses:
            if cur and cur_bytes + len(blob) > target:
                files.append(cur); cur, cur_bytes = [], 0
            index.append((c, v, len(files) + 1, cur_bytes))
            cur.append(blob); cur_bytes += len(blob)
        if cur:
            files.append(cur)
        if len(files) <= FILES_MAX:
            break
        target = int(target * 1.05)
    for k, parts in enumerate(files):
        open(os.path.join(DATA, 'v%03d.txt' % (k + 1)), 'wb').write(b''.join(parts))
    with open(os.path.join(DATA, 'index.txt'), 'w', encoding='ascii', newline='\n') as fh:
        for c, v, f, off in index:
            fh.write('%02d %03d %03d %06d\n' % (c, v, f, off))
    with open(os.path.join(DATA, 'chapters.txt'), 'w', encoding='utf-8', newline='\n') as fh:
        fh.write('0\t0\tThe Bhagavad Gita\tश्रीमद्भगवद्गीता\n')
        for ch in src['chapters']:
            title = ' '.join(w if k == 0 or w.lower() not in SMALL else w.lower()
                             for k, w in enumerate(ch['title'].replace('INDESCTRUCTIBLE', 'INDESTRUCTIBLE').title().split()))
            fh.write('%d\t%d\t%s\t%s\n' % (ch['n'], len(ch['verses']), title, chapter_name(ch)))
    biggest = max(sum(len(p) for p in parts) for parts in files)
    longest = max(len(l) for _c, _v, b in verses for l in b.split(b'\n'))
    print(f'{len(index)} verses in {len(files)} files of at most {biggest} bytes, {total / 1e6:.2f} MB; '
          f'longest line {longest} B')


if __name__ == '__main__':
    main()
