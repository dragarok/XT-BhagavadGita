"""Short English glosses for the word-by-word line: one per pada (a word of the padachheda).

    from gloss import pada_gloss
    pada_gloss(words)      # the DCS words of one pada -> 'in action-fruits', 'O son of Kunti', 'we will be'

The base meaning comes from glossary.tsv when the lemma is there (the Gita's ~500 commonest words), else
from the corpus's sense or first dictionary meaning. The grammar (the 'gram' label build_data.py
writes) then shapes it:
- nouns: plural, and a case word: with (instrumental), for (dative), from (ablative), of (genitive),
  in (locative), O (vocative);
- personal pronouns by case: I / me / by me / for me / from me / my / in me;
- verbs: person and tense: 'I was', 'you will fight', 'is said', 'fight!', 'let it be', 'should know';
- participles: 'seen', 'seeing', 'having seen', 'to be seen', 'to see'.
A compound joins its members with hyphens, a negative prefix gives 'not'.
"""
import os, re

HERE = os.path.dirname(os.path.abspath(__file__))
CASES = ('nominative', 'accusative', 'instrumental', 'dative', 'ablative', 'genitive', 'locative', 'vocative')
CASE_WORD = {'instrumental': 'with', 'dative': 'for', 'ablative': 'from', 'genitive': 'of', 'locative': 'in'}


def load_glossary(path=os.path.join(HERE, 'glossary.tsv')):
    words, compounds = {}, {}
    for line in open(path, encoding='utf-8'):
        line = line.rstrip('\n')
        if not line.strip() or line.startswith('#'):
            continue
        key, _, gloss = line.partition('\t')
        if not gloss:
            raise ValueError('glossary.tsv: no tab in %r' % line)
        (compounds if '+' in key else words)[key.strip()] = gloss.strip()
    return words, compounds


GLOSSARY, COMPOUNDS = load_glossary()

# ------------------------------------------------------------------ English verbs

IRREGULAR = {  # base: (past, past participle)
    'abide': ('abode', 'abided'), 'arise': ('arose', 'arisen'), 'be': ('was', 'been'), 'bear': ('bore', 'borne'),
    'become': ('became', 'become'), 'begin': ('began', 'begun'), 'behold': ('beheld', 'beheld'),
    'bind': ('bound', 'bound'), 'blow': ('blew', 'blown'), 'bring': ('brought', 'brought'),
    'burn': ('burnt', 'burnt'), 'cast': ('cast', 'cast'), 'cling': ('clung', 'clung'), 'come': ('came', 'come'),
    'cut': ('cut', 'cut'), 'do': ('did', 'done'), 'draw': ('drew', 'drawn'), 'dwell': ('dwelt', 'dwelt'),
    'eat': ('ate', 'eaten'), 'fall': ('fell', 'fallen'), 'feel': ('felt', 'felt'), 'fight': ('fought', 'fought'),
    'find': ('found', 'found'), 'forsake': ('forsook', 'forsaken'), 'give': ('gave', 'given'),
    'go': ('went', 'gone'), 'grow': ('grew', 'grown'), 'have': ('had', 'had'), 'hear': ('heard', 'heard'),
    'hold': ('held', 'held'), 'know': ('knew', 'known'), 'lead': ('led', 'led'), 'leave': ('left', 'left'),
    'lose': ('lost', 'lost'), 'make': ('made', 'made'), 'mean': ('meant', 'meant'), 'put': ('put', 'put'),
    'rise': ('rose', 'risen'), 'say': ('said', 'said'), 'see': ('saw', 'seen'), 'seek': ('sought', 'sought'),
    'shake': ('shook', 'shaken'), 'shine': ('shone', 'shone'), 'sit': ('sat', 'sat'), 'slay': ('slew', 'slain'),
    'speak': ('spoke', 'spoken'), 'stand': ('stood', 'stood'), 'strike': ('struck', 'struck'),
    'take': ('took', 'taken'), 'teach': ('taught', 'taught'), 'tell': ('told', 'told'),
    'think': ('thought', 'thought'), 'throw': ('threw', 'thrown'), 'understand': ('understood', 'understood'),
    'win': ('won', 'won'), 'overcome': ('overcame', 'overcome'), 'undertake': ('undertook', 'undertaken'),
    'forget': ('forgot', 'forgotten'), 'keep': ('kept', 'kept'), 'sleep': ('slept', 'slept'),
    'spring': ('sprang', 'sprung'), 'get': ('got', 'got'), 'withdraw': ('withdrew', 'withdrawn'),
    'shed': ('shed', 'shed'), 'spread': ('spread', 'spread'), 'beget': ('begot', 'begotten'),
    'meet': ('met', 'met'), 'can': ('could', 'been able'), 'ought': ('ought', 'ought'), 'lie': ('lay', 'lain'), 'dry': ('dried', 'dried'),
}
DOUBLE = {'control', 'excel', 'compel', 'stop', 'admit', 'commit', 'permit', 'omit', 'prefer', 'refer',
          'occur', 'beg', 'drop', 'plan', 'regret', 'rob', 'shun', 'stir', 'abhor', 'wet', 'repel', 'expel'}
MODAL = {'can', 'ought', 'must', 'should'}
# verbs DCS marks passive that read as active in English (Sanskrit middle voice): mriyate 'dies'
NO_PASSIVE = {'die', 'perish', 'arise', 'grow', 'fall', 'go', 'come', 'move', 'dwell', 'abide', 'tremble', 'rejoice'}


def past(v):
    if v in IRREGULAR:
        return IRREGULAR[v][0]
    if v in DOUBLE:
        return v + v[-1] + 'ed'
    if v.endswith('e'):
        return v + 'd'
    if re.search(r'[^aeiou]y$', v):
        return v[:-1] + 'ied'
    return v + 'ed'


def participle(v):
    return IRREGULAR[v][1] if v in IRREGULAR else past(v)


def ing(v):
    if v == 'be' or v.endswith(('ee', 'ye', 'oe')):
        return v + 'ing'
    if v.endswith('ie'):
        return v[:-2] + 'ying'
    if v.endswith('e'):
        return v[:-1] + 'ing'
    if v in DOUBLE:
        return v + v[-1] + 'ing'
    return v + 'ing'


def third(v):
    if v in MODAL:
        return v
    special = {'be': 'is', 'have': 'has', 'do': 'does', 'go': 'goes'}
    if v in special:
        return special[v]
    if re.search(r'(s|x|z|ch|sh|o)$', v):
        return v + 'es'
    if re.search(r'[^aeiou]y$', v):
        return v[:-1] + 'ies'
    return v + 's'


def split_verb(base):
    head, _, rest = base.partition(' ')
    return head, (' ' + rest if rest else '')


def person_of(label):
    m = re.search(r'(1st|2nd|3rd) person (singular|dual|plural)', label)
    return (m.group(1)[0], m.group(2)) if m else ('3', 'singular')


def subject(p, n):
    if p == '1':
        return 'I' if n == 'singular' else 'we'
    if p == '2':
        return 'you'
    return ''


def be_form(p, n, tense):
    if tense == 'past':
        return 'was' if n == 'singular' and p != '2' else 'were'
    if p == '1' and n == 'singular':
        return 'am'
    return 'is' if p == '3' and n == 'singular' else 'are'


def finite(base, label):
    """'say' + 'verb: perfect 3rd person singular' -> 'said'"""
    head, rest = split_verb(base)
    p, n = person_of(label)
    subj = subject(p, n)
    passive = 'passive' in label and head not in NO_PASSIVE and head != 'be'
    if 'future' in label:
        tense = 'future'
    elif re.search(r'\b(imperfect|perfect|aorist)\b', label) and 'injunctive' not in label:
        tense = 'past'
    else:
        tense = 'present'
    if passive:
        pp = participle(head) + rest
        if 'imperative' in label:
            return 'let it be ' + pp
        if tense == 'future':
            out = 'will be ' + pp
        else:
            out = be_form(p, n, tense) + ' ' + pp
        return (subj + ' ' + out).strip()
    if 'imperative' in label:
        if p == '2':
            return base + '!'
        if p == '1':
            return ('let me ' if n == 'singular' else 'let us ') + base
        return ('let it ' if n == 'singular' else 'let them ') + base
    if 'optative' in label:
        out = ('could ' + rest.strip()) if head == 'can' else 'should ' + base
    elif 'conditional' in label:
        out = 'would ' + base
    elif 'injunctive' in label:
        return base                           # with mā: 'not grieve', no subject
    elif tense == 'future':
        out = 'will ' + base
    elif head == 'be':
        out = be_form(p, n, tense) + rest
    elif tense == 'past':
        out = past(head) + rest
    else:
        out = (third(head) if p == '3' and n == 'singular' else head) + rest
    return (subj + ' ' + out).strip()


def nonfinite(base, label, form=''):
    """participles, absolutive, gerundive, infinitive (form: the IAST word, for a passive participle)"""
    head, rest = split_verb(base)
    state = head == 'be' and rest                 # 'be born': the participle is 'born'
    pp = rest.strip() if state else participle(head) + rest
    if label.startswith('present participle'):
        if re.search(r'yam[āa][nṇ]', form) and not state and head not in NO_PASSIVE:
            return 'being ' + pp                 # hanyamāna: 'being slain'
        return ing(head) + rest
    if label.startswith('absolutive'):
        return 'having ' + ('been ' + pp if state else pp)
    if label.startswith('gerundive'):
        return 'to be ' + pp
    if label.startswith('infinitive'):
        return 'to ' + base
    if label.startswith('future participle'):
        return 'about to ' + base
    return pp                                    # past participle, and a verb as a compound member

# ------------------------------------------------------------------ nouns and pronouns

PRONOUNS = {  # by case: nominative, accusative, instrumental, dative, ablative, genitive, locative
    'mad': {'singular': 'I me|by me|for me|from me|my|in me', 'plural': 'we us|by us|for us|from us|our|in us'},
    'tvad': {'singular': 'you you|by you|for you|from you|your|in you', 'plural': 'you you|by you|for you|from you|your|in you'},
    'tad:masculine': {'singular': 'he him|by him|for him|from him|his|in him', 'plural': 'they them|by them|for them|from them|their|in them'},
    'tad:feminine': {'singular': 'she her|by her|for her|from her|her|in her', 'plural': 'they them|by them|for them|from them|their|in them'},
    'tad:neuter': {'singular': 'that that|by that|for that|from that|of that|in that', 'plural': 'those those|by those|for those|from those|of those|in those'},
    'enad:masculine': {'singular': 'he him|by him|for him|from him|his|in him', 'plural': 'they them|by them|for them|from them|their|in them'},
    'enad': {'singular': 'it it|by it|for it|from it|its|in it', 'plural': 'they them|by them|for them|from them|their|in them'},
    'yad': {'singular': 'who whom|by whom|for whom|from whom|whose|in whom', 'plural': 'who whom|by whom|for whom|from whom|whose|in whom'},
    'yad:neuter': {'singular': 'which which|by which|for which|from which|of which|in which', 'plural': 'which which|by which|for which|from which|of which|in which'},
    'ka': {'singular': 'who whom|by whom|for whom|from whom|whose|in whom', 'plural': 'who whom|by whom|for whom|from whom|whose|in whom'},
    'ka:neuter': {'singular': 'what what|by what|for what|from what|of what|in what', 'plural': 'what what|by what|for what|from what|of what|in what'},
    'idam': {'singular': 'this this|by this|for this|from this|of this|in this', 'plural': 'these these|by these|for these|from these|of these|in these'},
    'etad': {'singular': 'this this|by this|for this|from this|of this|in this', 'plural': 'these these|by these|for these|from these|of these|in these'},
    'adas': {'singular': 'that that|by that|for that|from that|of that|in that', 'plural': 'those those|by those|for those|from those|of those|in those'},
}
STEM = {'mad': 'my', 'tvad': 'your', 'tad': 'that', 'yad': 'which', 'idam': 'this', 'etad': 'this', 'ka': 'what'}
PLURAL_WORD = {'anya': 'others', 'sarva': 'all', 'eka': 'some', 'man': 'men', 'woman': 'women',
               'person': 'people', 'child': 'children', 'foot': 'feet', 'self': 'selves', 'sense': 'senses'}


def pronoun_form(lemma, label):
    gender = next((g for g in ('masculine', 'feminine', 'neuter') if g in label), '')
    table = PRONOUNS.get(lemma + ':' + gender) or PRONOUNS.get(lemma)
    case = next((c for c in CASES if c in label), None)
    if not table or not case or case == 'vocative':
        return None
    number = 'singular' if 'singular' in label else 'plural'
    nom, _, rest = table[number].partition(' ')
    forms = [nom] + rest.split('|')
    return forms[CASES.index(case)]


def plural(g):
    if g in PLURAL_WORD:
        return PLURAL_WORD[g]
    head, sep, last = g.rpartition(' ')
    if ' of ' in g:                               # 'son of Kunti' -> 'sons of Kunti'
        a, _, b = g.partition(' of ')
        return plural(a) + ' of ' + b
    if last in PLURAL_WORD:
        return head + sep + PLURAL_WORD[last]
    if not last or not last[-1].isalpha() or last[0].isupper():
        return g if not last[:1].isupper() else g + 's'
    if re.search(r'(s|x|z|ch|sh)$', last):
        last += 'es'
    elif re.search(r'[^aeiou]y$', last):
        last = last[:-1] + 'ies'
    elif last.endswith('ness') or last in ('knowledge', 'wisdom', 'peace', 'goodness', 'passion', 'darkness'):
        pass
    else:
        last += 's'
    return head + sep + last

# ------------------------------------------------------------------ meanings

def short(s, limit=26):
    s = re.sub(r'\([^)]*\)|\[[^\]]*\]', '', s or '')
    s = re.sub(r'\s+', ' ', s).strip(' ,;.-')
    s = re.sub(r'^(name of|patr\. of|metron\. from|epithet of)\s+', '', s)
    s = re.sub(r'^(a|an|the|to)\s+', '', s)
    s = re.split(r'\s*[;,]\s*|\s+or\s+', s)[0].strip()
    if len(s) > limit:
        s = s[:limit].rsplit(' ', 1)[0]
    return s


def base_meaning(w):
    lemma = w['lemma'].replace('\uffb1', 'ḷ')          # DCS writes ḷ as a halfwidth sign
    if lemma in GLOSSARY:
        return GLOSSARY[lemma]
    for s in (w.get('sense') or '', (w.get('mean') or '').split(';')[0]):
        s = short(s)
        if s and not re.search(r'[A-Z]{2}|\?', s):
            return s
    return ''

# ------------------------------------------------------------------ one word, one pada

def word_gloss(w, last):
    """(case word, gloss) of one DCS word; the case word goes before the whole pada"""
    label, lemma = w['gram'], w['lemma']
    if label.startswith('first part of a compound'):
        if '(verb)' in label:
            return '', nonfinite(base_meaning(w), 'past participle')
        return '', STEM.get(lemma) or base_meaning(w)
    if label.startswith('verb'):
        return '', finite(base_meaning(w) or 'be', label)
    if re.match(r'(present |past |future )?participle|absolutive|gerundive|infinitive', label):
        g = nonfinite(base_meaning(w) or 'be', label, w.get('iast') or '')
        return ('O' if 'vocative' in label else ''), g
    if label.startswith('pronoun'):
        p = pronoun_form(lemma, label)
        if p:
            return '', p
    g = base_meaning(w)
    case = next((c for c in CASES if c in label), None)
    many = 'plural' in label or 'dual' in label
    if case == 'vocative':
        return 'O', g
    if label.startswith('noun'):
        if many:
            g = plural(g)
        return CASE_WORD.get(case, ''), g
    if many and lemma in PLURAL_WORD:
        g = PLURAL_WORD[lemma]
    return '', g


def join(parts):
    out = ''
    for p in parts:
        if not out:
            out = p
        elif p.startswith('-'):
            out += p[1:]
        elif out.endswith('not'):
            out += ' ' + p
        else:
            out += '-' + p
    return out


def pada_gloss(words):
    """the gloss of one pada: its words are compound members and negative prefixes, then the last word"""
    words = [w for w in words if w]
    if not words:
        return ''
    key = '+'.join(w['lemma'] for w in words if w['gram'] != 'negative prefix')
    case_word, last = word_gloss(words[-1], True)
    if key in COMPOUNDS and len(words) > 1:
        core = COMPOUNDS[key]
        if 'plural' in words[-1]['gram'] and words[-1]['gram'].startswith('noun'):
            core = plural(core)
        return (case_word + ' ' + core).strip()
    parts = []
    for w in words[:-1]:
        if w['gram'] == 'negative prefix':
            parts.append('not')
        else:
            parts.append(word_gloss(w, False)[1] or '?')
    parts.append(last or '?')
    return (case_word + ' ' + join(parts)).strip()
