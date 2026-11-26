"""Build sources/gita.json: the 700 verses with their words, from two open sources.

    python -I tools/build_data.py

- Annie Besant's translation (4th edition, 1922; public domain), as proofread on Wikisource:
  the Devanagari verse, the speaker lines, her English translation and her footnotes.
- The Digital Corpus of Sanskrit (Oliver Hellwig, CC BY 4.0): every word of the Gita split out
  of sandhi, with its base form (lemma), grammar, an English sense and dictionary meanings.

The two are matched by sound, not by verse number (the corpus leaves some verses unnumbered):
both are written in SLP1 (one letter per sound), joined without spaces, and aligned with
difflib. Each printed word of Besant's text then knows the corpus words that make it up: its
padachheda.

Input: sources/cache/ (tools/fetch_sources.py). Output: sources/gita.json.
"""
import csv, difflib, html, json, os, re, sys
from collections import Counter, defaultdict

from indic_transliteration import sanscript as S

HERE = os.path.dirname(os.path.abspath(__file__))
APP = os.path.dirname(HERE)
CACHE = os.path.join(APP, 'sources', 'cache')
OUT = os.path.join(APP, 'sources', 'gita.json')

VERSES = [47, 72, 43, 42, 29, 47, 30, 28, 34, 42, 55, 20, 34, 27, 20, 24, 28, 78]   # the usual 700
DEVA_DIGITS = str.maketrans('०१२३४५६७८९', '0123456789')
DEVA = re.compile('[ऀ-ॿ]')


def deva(iast):
    return S.transliterate(iast, S.IAST, S.DEVANAGARI)


def pada_form(iast):
    """a word as a padachheda prints it: a final s or r as visarga (kutas -> kutaḥ)"""
    return re.sub(r'(?<=[aāiīuūeo])[sr]$', 'ḥ', iast) if len(iast) > 1 else iast


def slp_of_deva(s):
    return S.transliterate(s, S.DEVANAGARI, S.SLP1)


def slp_of_iast(s):
    return S.transliterate(s, S.IAST, S.SLP1)


def norm(slp):
    """the sounds alone: no spaces, avagraha or punctuation; a nasal before a consonant as anusvara"""
    s = re.sub(r"[^A-Za-z]", '', slp)
    s = re.sub(r'[NYRnm](?=[kKgGNcCjJYwWqQRtTdDnpPbBmyrlvSzsh])', 'M', s)
    return s.replace('~', '')


# ---------------------------------------------------------------- Besant (Wikisource)

def page_lines(path):
    h = json.load(open(path, encoding='utf-8'))['parse']['text']['*']
    h = re.sub(r'<style.*?</style>', '', h, flags=re.S)
    h = re.sub(r'<sup[^>]*class="reference"[^>]*>.*?</sup>',
               lambda m: '[%s]' % (re.search(r'\[(\d+)\]', html.unescape(re.sub('<[^>]+>', '', m.group(0)))) or [0, '?'])[1],
               h, flags=re.S)
    h = re.sub(r'<(br|/p|/div|/li|/h\d|/tr)[^>]*>', '\n', h)
    t = html.unescape(re.sub(r'<[^>]+>', '', h))
    # a page break inside a line: "griev ​ ed" (a word split over two pages) or "word ​ word"
    t = re.sub(r'([a-z]) ?​ ?([a-z])', lambda m: m.group(1) + m.group(2), t)
    t = t.replace('​', ' ')
    return [re.sub(r'\s+', ' ', l).strip() for l in t.split('\n') if l.strip()]


VERSE_END = re.compile(r'॥\s*([०-९]+)\s*॥\s*$')
# "(12)", "(4-6)"; the transcription also has "(42" and "32)"
EN_END = re.compile(r'\(?(\d+)(?:\s*[-–]\s*(\d+))?\)?\s*$')
SAID = re.compile(r'^([A-Z][A-Za-zâîûÂÎÛ\- ]+) said:$')
MISMATCH = []          # (chapter, verse the English follows, number printed with it)


def besant_chapter(n):
    """The English paragraph after a verse is that verse's translation. Its printed number is only
    used for verses translated together ("(4-6)"): the transcription has a few wrong numbers
    ("(20)" after 17.19), a missing one (11.8) and broken brackets."""
    lines = page_lines(os.path.join(CACHE, 'besant', 'd%02dh.json' % n))
    i = next(k for k, l in enumerate(lines) if re.match(r'^[A-Z\-]+ DISCOURSE\.?$', l))
    verses, cur, speaker, en_speaker, en_buf, notes = {}, [], None, None, [], []
    colophon_deva, colophon_en, title = [], [], ''
    stage, last_v = 'body', None
    pending = []          # verses printed since the last English paragraph

    def flush(marker):
        nonlocal en_buf, en_speaker, pending
        if not en_buf:
            return
        text = ' '.join(en_buf)
        targets = pending or ([last_v] if last_v else [])
        if marker:
            text = EN_END.sub('', text).strip()
            a, b = int(marker.group(1)), int(marker.group(2) or marker.group(1))
            if b != a and set(range(a, b + 1)) <= set(verses):
                targets = list(range(a, b + 1))
            elif targets and a != targets[-1]:
                MISMATCH.append((n, targets[-1], a))
        elif targets:
            MISMATCH.append((n, targets[-1], None))
        for k, v in enumerate(targets):
            verses[v]['en'] = text if k == 0 else ''
            verses[v]['en_range'] = (targets[0], targets[-1]) if len(targets) > 1 else None
            if k == 0:
                verses[v]['en_speaker'] = en_speaker
        en_buf, en_speaker, pending = [], None, []

    for l in lines[i + 1:]:
        if l.startswith('↑'):
            notes.append(re.sub(r'^↑\s*(\d+\.\d+\s+)*', '', l).strip())
            continue
        if stage == 'colophon':
            if DEVA.search(l):
                colophon_deva.append(l)
            elif l.startswith('Thus'):
                colophon_en.append(l)
            elif colophon_en and l.isupper():
                title = l.strip(' .')
            elif colophon_en and not title:
                colophon_en.append(l)
            continue
        if DEVA.search(l):
            flush(None)
            if l.startswith('इति श्रीमद्भगवद्गीता'):
                stage = 'colophon'; colophon_deva.append(l); continue
            if re.search(r'उवाच\s*।?\s*$', l) and not cur:
                speaker = l; continue
            cur.append(l)
            m = VERSE_END.search(l)
            if m:
                v = int(m.group(1).translate(DEVA_DIGITS))
                verses[v] = {'v': v, 'deva': cur, 'speaker': speaker}
                cur, speaker, last_v = [], None, v
                pending.append(v)
            continue
        m = SAID.match(l)
        if m:
            en_speaker = l; continue
        if l in ('Layout 2',) or re.match(r'^[A-Z\'\- .]+$', l):
            continue
        en_buf.append(l)
        m = EN_END.search(l)
        if m and re.search(r'[\(\)]\s*$|\(\d+\s*$', l):
            flush(m)
    flush(None)
    return {'verses': [verses[k] for k in sorted(verses)], 'notes': notes, 'title': title,
            'colophon_deva': colophon_deva, 'colophon_en': ' '.join(colophon_en)}


# ---------------------------------------------------------------- DCS (CoNLL-U)

def dcs_chapter(n):
    """sentences of tokens; a token is a printed string of the corpus with its words"""
    sents, cur, rng = [], None, None
    for line in open(os.path.join(CACHE, 'dcs', 'bg%02d.conllu' % n), encoding='utf-8'):
        line = line.rstrip('\n')
        if line.startswith('# text = '):
            cur = {'text': line[9:], 'tokens': []}; sents.append(cur); rng = None; continue
        if not line or line.startswith('#'):
            continue
        f = line.split('\t')
        if '-' in f[0]:
            a, b = map(int, f[0].split('-'))
            rng = {'form': f[1], 'words': [], 'end': b}
            cur['tokens'].append(rng); continue
        if '.' in f[0]:
            continue
        misc = dict(kv.split('=', 1) for kv in f[9].split('|') if '=' in kv)
        w = {'form': f[1], 'lemma': f[2], 'upos': f[3], 'feats': f[5] if f[5] != '_' else '',
             'lemma_id': misc.get('LemmaId', ''), 'sem': misc.get('WordSem', ''),
             'unsandhied': misc.get('Unsandhied', f[1])}
        if rng and int(f[0]) <= rng['end']:
            rng['words'].append(w)
            if int(f[0]) == rng['end']:
                rng = None
        else:
            cur['tokens'].append({'form': f[1], 'words': [w]})
    return sents


# ---------------------------------------------------------------- grammar and meanings

CASES = {'Nom': 'nominative', 'Acc': 'accusative', 'Ins': 'instrumental', 'Dat': 'dative', 'Abl': 'ablative',
         'Gen': 'genitive', 'Loc': 'locative', 'Voc': 'vocative'}
GENDERS = {'Masc': 'masculine', 'Fem': 'feminine', 'Neut': 'neuter'}
NUMBERS = {'Sing': 'singular', 'Dual': 'dual', 'Plur': 'plural'}
TENSES = {'Pres': 'present', 'Impf': 'imperfect', 'Past': 'perfect', 'Fut': 'future', 'Aor': 'aorist', 'Pqp': 'pluperfect'}
MOODS = {'Ind': '', 'Imp': 'imperative', 'Opt': 'optative', 'Sub': 'subjunctive', 'Cnd': 'conditional',
         'Prec': 'precative', 'Jus': 'injunctive'}
UPOS = {'NOUN': 'noun', 'PROPN': 'name', 'ADJ': 'adjective', 'PRON': 'pronoun', 'DET': 'pronoun', 'NUM': 'number',
        'VERB': 'verb', 'AUX': 'verb', 'ADV': 'adverb', 'PART': 'particle', 'CONJ': 'conjunction',
        'CCONJ': 'conjunction', 'SCONJ': 'conjunction', 'ADP': 'preposition', 'INTJ': 'interjection'}
PERSONS = {'1': '1st person', '2': '2nd person', '3': '3rd person'}


def grammar(w):
    f = dict(kv.split('=', 1) for kv in w['feats'].split('|') if '=' in kv)
    pos = UPOS.get(w['upos'], w['upos'].lower())
    if f.get('Case') == 'Cpd':
        return 'first part of a compound' + (f' ({pos})' if pos not in ('noun',) else '')
    vf = f.get('VerbForm')
    if vf == 'Part':
        t = {'Past': 'past', 'Pres': 'present', 'Fut': 'future', 'Perf': 'perfect'}.get(f.get('Tense', ''), '')
        head = ' '.join(x for x in [t, 'participle'] if x)
    elif vf == 'Conv':
        head = 'absolutive (having ...)'
    elif vf == 'Inf':
        head = 'infinitive'
    elif vf == 'Gdv':
        head = 'gerundive (to be ...)'
    elif w['upos'] in ('VERB', 'AUX') and ('Person' in f or 'Tense' in f):
        bits = [TENSES.get(f.get('Tense', ''), ''), MOODS.get(f.get('Mood', ''), ''),
                PERSONS.get(f.get('Person', ''), ''), NUMBERS.get(f.get('Number', ''), '')]
        if f.get('Voice') == 'Pass':
            bits.insert(0, 'passive')
        return 'verb: ' + ' '.join(b for b in bits if b)
    else:
        head = pos
    rest = [GENDERS.get(f.get('Gender', ''), ''), CASES.get(f.get('Case', ''), ''), NUMBERS.get(f.get('Number', ''), '')]
    rest = ' '.join(r for r in rest if r)
    return head + (', ' + rest if rest else '')


def load_lookups(ids_needed, sems_needed):
    meanings, senses = {}, {}
    with open(os.path.join(CACHE, 'dcs', 'dictionary.csv'), encoding='utf-8', errors='replace') as fh:
        for row in csv.reader(fh, delimiter='\t'):
            if row and row[0] in ids_needed and len(row) >= 5:
                meanings[row[0]] = row[4]
    with open(os.path.join(CACHE, 'dcs', 'word-senses.csv'), encoding='utf-8', errors='replace') as fh:
        for row in csv.reader(fh, delimiter='\t'):
            if row and row[0] in sems_needed and len(row) >= 3:
                senses[row[0]] = (row[1], row[2])
    return meanings, senses


GERMAN = re.compile(r'\b(sich|der|die|das|und|von|mit|ein|eine|zu|als|auf|für|Wasser)\b|[äöüß]')


def clean_meaning(m, n=4):
    out = []
    for part in m.split(';'):
        p = part.strip()
        if not p or '￼' in p or '￤' in p or '�' in p or GERMAN.search(p) or p.startswith('[gramm'):
            continue
        p = re.sub(r'\s+', ' ', p)
        if p not in out:
            out.append(p)
        if len(out) >= n:
            break
    return '; '.join(out)


# ---------------------------------------------------------------- matching

def tokens_of_line(line):
    """the printed words of a Devanagari line; dandas and the verse number are their own tokens"""
    out = []
    for t in line.split(' '):
        if not t:
            continue
        if t in ('।', '॥') or re.fullmatch('[०-९]+', t):
            out.append({'d': t, 'p': True})
        elif t.endswith('।') and len(t) > 1:
            out.append({'d': t[:-1], 'p': False}); out.append({'d': '।', 'p': True})
        else:
            out.append({'d': t, 'p': False})
    return out


def match_chapter(bverses, sents):
    """map each printed Besant word to the corpus tokens that make it up"""
    # Besant stream
    b_chars, b_owner = [], []
    btoks = []                      # (verse index, line index, token index)
    for vi, v in enumerate(bverses):
        lines = ([v['speaker']] if v.get('speaker') else []) + v['deva']
        v['lines'] = [tokens_of_line(l) for l in lines]
        for li, toks in enumerate(v['lines']):
            for ti, t in enumerate(toks):
                if t['p']:
                    continue
                s = norm(slp_of_deva(t['d']))
                btoks.append((vi, li, ti))
                for ch in s:
                    b_chars.append(ch); b_owner.append(len(btoks) - 1)
    # corpus stream
    d_chars, d_owner, dtoks = [], [], []
    for si, s in enumerate(sents):
        for k, t in enumerate(s['tokens']):
            dtoks.append((si, k))
            for ch in norm(slp_of_iast(t['form'])):
                d_chars.append(ch); d_owner.append(len(dtoks) - 1)
    sm = difflib.SequenceMatcher(None, ''.join(b_chars), ''.join(d_chars), autojunk=False)
    overlap = defaultdict(Counter)          # corpus token -> Counter(besant token)
    for a, b, size in sm.get_matching_blocks():
        for k in range(size):
            overlap[d_owner[b + k]][b_owner[a + k]] += 1
    ratio = sum(bl.size for bl in sm.get_matching_blocks()) / max(1, len(b_chars))
    # each corpus token goes to the printed word it overlaps most; one with no overlap follows its neighbour
    owner = [None] * len(dtoks)
    for d, c in overlap.items():
        owner[d] = c.most_common(1)[0][0]
    last = None
    for d in range(len(dtoks)):
        if owner[d] is None:
            owner[d] = last
        last = owner[d]
    nxt = None
    for d in range(len(dtoks) - 1, -1, -1):
        if owner[d] is None:
            owner[d] = nxt
        nxt = owner[d]
    of_btok = defaultdict(list)
    for d, o in enumerate(owner):
        if o is not None:
            of_btok[o].append(d)
    return btoks, dtoks, of_btok, ratio


def is_neg(w):
    return w['lemma'] in ('a', 'an') and w['upos'] == 'PART'


def pada_split(words):
    """the words of a printed word as padas: a compound member (Case=Cpd) or the negative prefix
    a/an joins the word after it; returns lists of word indices"""
    padas, cur = [], []
    for i, w in enumerate(words):
        cur.append(i)
        if not (('Case=Cpd' in w['feats'] or is_neg(w)) and i + 1 < len(words)):
            padas.append(cur); cur = []
    if cur:
        padas.append(cur)
    return padas


def pada_deva(words, idx):
    """compound members joined with a hyphen, the negative prefix with nothing: अनार्य-जुष्टम्"""
    out = ''                     # joined in IAST first: an + ārya is anārya (अनार्य), not अन्आर्य
    for j, i in enumerate(idx):
        if j and not is_neg(words[idx[j - 1]]):
            out += '-'
        out += pada_form(words[i]['unsandhied']) if j == len(idx) - 1 else words[i]['unsandhied']
    return deva(out)


def word_info(w, meanings, senses):
    sem = [senses[x] for x in w['sem'].split(',') if x in senses]
    info = {'iast': pada_form(w['unsandhied']), 'd': deva(pada_form(w['unsandhied'])),
            'lemma': w['lemma'], 'ld': deva(w['lemma']), 'gram': grammar(w),
            'sense': sem[0][0] if sem else '', 'mean': clean_meaning(meanings.get(w['lemma_id'], ''))}
    if is_neg(w):
        info.update(gram='negative prefix', sense='not', mean='not; un-; in-')
    return info


def build():
    chapters, report = [], []
    all_ids, all_sems = set(), set()
    raw = []
    for n in range(1, 19):
        b = besant_chapter(n)
        sents = dcs_chapter(n)
        btoks, dtoks, of_btok, ratio = match_chapter(b['verses'], sents)
        raw.append((n, b, sents, btoks, dtoks, of_btok))
        for s in sents:
            for t in s['tokens']:
                for w in t['words']:
                    all_ids.add(w['lemma_id']); all_sems.update(x for x in w['sem'].split(',') if x)
        nums = [v['v'] for v in b['verses']]
        report.append(f'ch {n:2}: {len(b["verses"])} verses (want {VERSES[n - 1]}), '
                      f'{len(b["notes"])} notes, match {ratio:.3f}, '
                      f'gaps {sorted(set(range(1, max(nums) + 1)) - set(nums))}, '
                      f'no en {[v["v"] for v in b["verses"] if v.get("en") is None]}')
    meanings, senses = load_lookups(all_ids, all_sems)
    for n, b, sents, btoks, dtoks, of_btok in raw:
        verses = []
        bt_index = {k: i for i, k in enumerate(btoks)}
        for vi, v in enumerate(b['verses']):
            lines_out = []
            for li, toks in enumerate(v['lines']):
                row = []
                for ti, t in enumerate(toks):
                    item = {'d': t['d']}
                    if not t['p']:
                        raw_words = []
                        for d in of_btok.get(bt_index[(vi, li, ti)], []):
                            si, k = dtoks[d]
                            raw_words += sents[si]['tokens'][k]['words']
                        item['w'] = [word_info(w, meanings, senses) for w in raw_words]
                        item['p'] = [pada_deva(raw_words, p) for p in pada_split(raw_words)]
                    row.append(item)
                lines_out.append(row)
            notes_idx = [int(x) for x in re.findall(r'\[(\d+)\]', v.get('en') or '')]
            en = re.sub(r'\s*\[\d+\]', '', v.get('en') or '').strip()
            verses.append({
                'v': v['v'], 'speaker': bool(v.get('speaker')), 'en_speaker': v.get('en_speaker'),
                'lines': lines_out, 'en': en, 'en_range': v.get('en_range'),
                'notes': [b['notes'][k - 1] for k in notes_idx if 0 < k <= len(b['notes'])],
            })
        chapters.append({'n': n, 'title': b['title'], 'colophon_deva': b['colophon_deva'],
                         'colophon_en': b['colophon_en'], 'verses': verses})
    # a printed word the matching left without words (mostly speaker lines) borrows the analysis
    # of the same printed word elsewhere in the Gita
    seen = {}
    for c in chapters:
        for v in c['verses']:
            for row in v['lines']:
                for t in row:
                    if t.get('w'):
                        seen.setdefault(t['d'], (t['w'], t['p']))
    borrowed = 0
    for c in chapters:
        for v in c['verses']:
            for row in v['lines']:
                for t in row:
                    if 'w' in t and not t['w'] and t['d'] in seen:
                        t['w'], t['p'] = seen[t['d']]; borrowed += 1
    report.append(f'{borrowed} printed words borrowed their analysis from another verse')
    return chapters, report


if __name__ == '__main__':
    chapters, report = build()
    print('\n'.join(report))
    total = sum(len(c['verses']) for c in chapters)
    empty = [f"{c['n']}.{v['v']}" for c in chapters for v in c['verses'] if not any(t.get('w') for row in v['lines'] for t in row)]
    unmatched = sum(1 for c in chapters for v in c['verses'] for row in v['lines'] for t in row if 'w' in t and not t['w'])
    words = sum(1 for c in chapters for v in c['verses'] for row in v['lines'] for t in row if 'w' in t)
    print(f'{total} verses; {len(empty)} without words {empty[:10]}; printed words without a split: {unmatched} of {words}')
    json.dump({'chapters': chapters,
               'sources': {
                   'translation': 'Annie Besant, The Bhagavad-Gita, 4th edition (1922), public domain; '
                                  'text as proofread on Wikisource (en.wikisource.org, "Bhagavad-Gita (Besant 4th)")',
                   'words': 'Digital Corpus of Sanskrit (DCS), Oliver Hellwig 2010-2024, CC BY 4.0 '
                            '(github.com/OliverHellwig/sanskrit)'}},
              open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
    print('wrote', OUT, os.path.getsize(OUT), 'bytes')
