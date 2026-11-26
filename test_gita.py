"""Offline test of the Gita app under Lua 5.4 (lupa), against the data section xtpack builds.

    python -I test_gita.py

The host is stood in for by stubs that behave like the device's:
- ctx.package:open_text over the very files xtpack packs (with its banks.tsv), with seek;
  SEEK_BROKEN makes seek fail, to check the read-from-the-top fallback, and every byte read is
  counted (0.2 read up to 900 KB for one verse when seek failed: 15 s on the device);
- ctx.budget:extend is counted (the slow steps ask for more time);
- every ctx call must be a method call, every frame starts with gg:clear, text goes at whole
  pixels; the draw commands of a screen are counted (the host draws about 1024).
"""
import json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, 'kit'))
sys.path.insert(0, os.path.join(HERE, 'tools'))
from harness import Game          # noqa: E402
import xtpack                     # noqa: E402

BLOBS = {name: data.decode('latin-1') for name, data in xtpack.collect_data_files(HERE)}

STUBS = r'''
SEEK_BROKEN, bytes_read, extends = false, 0, 0
calls = {}
local base = gg
gg = setmetatable({}, { __index = function(_, k)
  calls[#calls + 1] = k
  local f = base[k]
  if k == 'text' then
    return function(self, x, y, s, o)
      assert(self == gg, 'gg:text must be a method call')
      assert(math.type(x) == 'integer' and math.type(y) == 'integer', 'text at a fractional place: ' .. tostring(x) .. ',' .. tostring(y))
      return f(self, x, y, s, o)
    end
  end
  return f
end })
ctx.package = {}
function ctx.package.open_text(self, name, opts)
  assert(self == ctx.package, 'open_text must be a method call')
  local blob = py_blob(name)
  if not blob then return nil, 'not_found' end
  local pos, r = 0, {}
  function r.seek(me, off)
    assert(me == r, 'seek must be a method call')
    if SEEK_BROKEN then error('seek not supported') end
    pos = off
  end
  function r.read_line(me)
    assert(me == r, 'read_line must be a method call')
    if pos >= #blob then return nil end
    local e = blob:find('\n', pos + 1, true)
    local line = blob:sub(pos + 1, (e or (#blob + 1)) - 1)
    bytes_read = bytes_read + #line + 1
    pos = e or #blob
    assert(not (opts and opts.max_line_bytes) or #line <= opts.max_line_bytes, 'line longer than max_line_bytes')
    return line
  end
  function r.close(me) assert(me == r) end
  return r
end
ctx.budget = { extend = function(self) assert(self == ctx.budget, 'budget:extend must be a method call'); extends = extends + 1 end }
ctx.fonts.size = function(self, n) assert(self == ctx.fonts); return ctx.fonts.medium end
'''


def py_blob(name):
    return BLOBS.get(name)


def new_game():
    def before(g):
        g.L.globals().py_blob = py_blob
        g.L.execute(STUBS)
    return Game(HERE, stubs='', encoding='latin-1', before_load=before)


def u(s):
    """a string the app drew (latin-1 in Python) as the UTF-8 text it is"""
    return s.encode('latin-1').decode('utf-8', 'replace')


def draw(g):
    g.L.execute('calls = {}')
    t = [u(x) for x in g.texts()]
    assert g.g.calls[1] == 'clear', 'every frame must start with gg:clear: the host keeps the last frame'
    assert not any(x.startswith('ERR') for x in t), [x for x in t if x.startswith('ERR')]
    return t


def screen(g):
    return str(g.api.S.screen)


def hold(g, x, y):
    g.L.eval('function(x, y) on_input(ctx, {type="pointer", phase="down", x=x, y=y}); '
             'on_input(ctx, {type="pointer", phase="hold", x=x, y=y}); '
             'on_input(ctx, {type="pointer", phase="up", gesture="long", x=x, y=y}) end')(x, y)


def swipe(g, gesture):
    g.L.eval('function(gs) on_input(ctx, {type="pointer", phase="up", gesture=gs, x=240, y=400}) end')(gesture)


def page_items(g, kind=None):
    items = list(g.api.verse_pages()[int(g.api.S.page)].values())
    return [it for it in items if kind is None or it.kind == kind]


def check_glosses():
    """the word-by-word glosses of a few verses, straight from tools/gloss.py"""
    from gloss import pada_gloss
    from write_data import groups
    src = json.load(open(os.path.join(HERE, 'sources', 'gita.json'), encoding='utf-8'))

    def glosses(c, v):
        out = {}
        for line in src['chapters'][c - 1]['verses'][v - 1]['lines']:
            for t in line:
                if 'w' in t:
                    for p, gr in zip(t['p'] or [t['d']], groups(t)):
                        out[p] = pada_gloss(gr)
        return out
    g = glosses(2, 12)
    assert (g['आसम्'], g['भविष्यामः'], g['जनाधिपाः']) == ('I was', 'we will be', 'kings'), g
    g = glosses(2, 2)
    assert (g['अर्जुन'], g['उवाच'], g['विषमे']) == ('O Arjuna', 'said', 'in crisis'), g
    g = glosses(2, 47)
    assert (g['फलेषु'], g['कर्म-फल-हेतुः'], g['ते'], g['अस्तु']) == ('in fruits', 'action-fruit-cause', 'your', 'let it be'), g
    g = glosses(18, 66)
    assert (g['मोक्षयिष्यामि'], g['शुचः'], g['सर्व-पापेभ्यः']) == ('I will liberate', 'grieve', 'from all-sins'), g
    g = glosses(2, 20)
    assert (g['हन्यमाने'], g['म्रियते']) == ('being slain', 'dies'), g


def check_data():
    sizes = {n: len(b.encode('latin-1')) for n, b in BLOBS.items()}
    verse_files = [n for n in sizes if n.startswith('v')]
    assert len(sizes) <= 128 and len(verse_files) >= 90, len(sizes)
    assert max(sizes[n] for n in verse_files) <= 20_000, max(sizes.values())
    return len(verse_files), max(sizes[n] for n in verse_files)


def main():
    check_glosses()
    nfiles, biggest = check_data()
    g = new_game()
    api = g.api

    # home: the title in Devanagari, 18 chapters, nothing read yet
    t = draw(g)
    assert 'श्रीमद्भगवद्गीता' in t, t
    assert 'The Despondency of Arjuna' in t and 'The Yoga of Liberation by Renunciation' in t, t
    assert 'Start at 1.1' in t, t
    assert g.commands() < 1024

    # chapter 2, then verse 12
    g.tap(100, 112 + 34 + 10)
    t = draw(g)
    assert screen(g) == 'chapter' and 'Chapter 2' in t and 'साङ्ख्ययोगः' in t and '72' in t, t
    g.tap_label('12')
    t = draw(g)
    assert screen(g) == 'verse' and 'Bhagavad Gita 2.12' in t, t
    assert 'त्वेवाहं' in t and '॥ १२ ॥' in t, t                     # the shloka
    assert 'आसम्' in t and 'I was' in t and 'we will be' in t, t     # the padachheda and its meanings
    assert any(x.startswith('Nor at any time verily was I not') for x in t), t
    assert g.commands() < 1024

    # a long press on the second printed word of the shloka (त्वेवाहं): tu + eva + aham
    row = page_items(g, 'deva')[0]
    unit = [x for x in row.units.values() if x.k == 2][0]
    hold(g, int(unit.x) + int(unit.w) // 2, int(row.y) + int(row.h) // 2)
    t = draw(g)
    assert screen(g) == 'word' and int(api.S.tok) == 2, (screen(g), api.S.tok)
    assert 'त्वेवाहं' in t and 'तु' in t and 'अहम्  (मद्)' in t, t
    assert 'pronoun, nominative singular' in t and 'particle' in t, t
    assert any('I; we' in x for x in t), t
    g.tap_label('Word >')
    t = draw(g)
    assert int(api.S.tok) == 3 and any('ever' in x for x in t), t
    g.key('back')
    draw(g)
    assert screen(g) == 'verse'

    # a long press on every word of the padachheda, or on its meaning under it, finds its word
    pada_rows = page_items(g, 'pada')
    assert pada_rows, 'the padachheda is on the first page'
    for row in pada_rows:
        for unit in row.units.values():
            for y in (int(row.y) + 6, int(row.y) + int(row.h) - 10):      # the word, its meaning
                hold(g, int(unit.x) + int(unit.w) // 2, y)
                assert screen(g) == 'word' and int(api.S.tok) == int(unit.k), (unit.s, y, api.S.tok)
                g.key('back')
    assert screen(g) == 'verse'

    # the padachheda switch
    g.tap_label('Pada: on')
    t = draw(g)
    assert 'Pada: off' in t and 'I was' not in t and 'आसम्' not in t, t
    g.tap_label('Pada: off')
    t = draw(g)
    assert 'I was' in t

    # side keys and swipes: 2.72 -> 3.1 and back
    api.open_verse(2, 72, 1)
    for _ in range(4):
        if int(api.S.c) == 3:
            break
        g.key('right')
    assert (int(api.S.c), int(api.S.v)) == (3, 1), (api.S.c, api.S.v)
    swipe(g, 'swipe_right')
    assert (int(api.S.c), int(api.S.v)) == (2, 72), (api.S.c, api.S.v)
    swipe(g, 'swipe_left')
    draw(g)

    # Back goes up: verse -> chapter -> home; Back on home leaves the app
    g.key('back')
    assert screen(g) == 'chapter'
    g.key('back')
    assert screen(g) == 'home'
    g.advance(1000)
    assert g.L.eval('function() return on_input(ctx, {type="key", key="back"}) end')() is False

    # the device sends a press of Back as two events, down and up, and leaves the app when the up
    # is passed on (on_input returns false). The up that follows the press which brought you Home
    # must not leave (in 0.1.1 it did); a new press on Home must, up included (0.3.0 swallowed it)
    press = g.L.eval('function(ph) return on_input(ctx, {type="key", key="back", phase=ph}) end')
    api.open_verse(3, 1, 1)                      # the last verse read stays 3.1
    for want in ('chapter', 'home'):
        g.advance(1000)
        assert press('down') is True and screen(g) == want, (want, screen(g))
        assert press('up') is True and screen(g) == want, (want, screen(g))
    g.advance(1000)
    assert press('down') is False, 'a new press of Back on Home is passed on'
    assert press('up') is False, 'and so is its release: the reader leaves on the release'
    g.advance(1000)
    g.tap(100, 112 + 10)                         # the app is still usable if the host stays
    assert screen(g) == 'chapter'
    g.advance(1000)
    assert press('down') is True and press('up') is True and screen(g) == 'home'

    # settings are kept
    g.tap_label('Settings')
    draw(g)
    g.tap_label('Notes: on')
    g.tap_label('English text size: medium')
    g.tap_label('Devanagari size: medium')
    t = draw(g)
    assert 'Notes: off' in t and 'English text size: large' in t and 'Devanagari size: large' in t, t
    assert 'Padachheda and meanings: on' in t and not any('text test' in x for x in t), t
    g.key('back')
    store = str(g.store['config.txt'])
    assert 'notes=0' in store and 'size=large' in store and 'dsize=large' in store and 'last=3.1' in store, store
    g.L.eval('function() on_leave() end')()
    g.restart()
    api = g.api
    t = draw(g)
    assert 'Continue 3.1' in t, t
    g.tap_label('Continue 3.1')
    draw(g)
    assert (screen(g), int(api.S.c), int(api.S.v)) == ('verse', 3, 1)
    assert int(g.g.extends) > 0, 'the slow steps ask the host for more time'

    # every verse opens and draws, with its first and last word, within the host's limits; with
    # notes on and the largest sizes, so the long verses take two pages
    api.cfg.notes = True
    worst_cmds, multi, worst_read = 0, 0, 0
    chapters = [(int(api.D.chapters[c].n), int(api.D.chapters[c].count)) for c in range(1, 19)]
    assert sum(n for _c, n in chapters) == 701, chapters
    for c, n in chapters:
        for v in range(1, n + 1):
            g.L.execute('bytes_read = 0')
            assert api.open_verse(c, v, 1), (c, v, api.S.err)
            worst_read = max(worst_read, int(g.g.bytes_read))
            npages = len(list(api.verse_pages().values()))
            multi += npages > 1
            for p in range(1, npages + 1):
                api.S.page = p
                draw(g)
                worst_cmds = max(worst_cmds, g.commands())
            ntok = int(api.D.verse.ntok)
            assert ntok > 0, (c, v)
            for k in sorted({1, ntok}):
                api.open_word(k)
                assert screen(g) == 'word', (c, v, k, api.S.err)
                draw(g)
                worst_cmds = max(worst_cmds, g.commands())
    assert worst_cmds < 1024, worst_cmds
    assert multi > 0, 'some verses in the largest sizes take two pages'

    # the translation is never cut between two pages (unless it is longer than a page)
    for c, v in ((11, 32), (2, 2), (18, 78)):
        api.open_verse(c, v, 1)
        pages = [list(pg.values()) for pg in api.verse_pages().values()]
        where = {i for i, pg in enumerate(pages) for it in pg if it.kind == 'text' and it.block == 'en'}
        assert len(where) == 1, (c, v, where)

    # paging: Next goes through the pages of a verse, then to the next verse
    found = next((c, v) for c, n in chapters for v in range(1, n + 1)
                 if api.open_verse(c, v, 1) and len(list(api.verse_pages().values())) > 1)
    c, v = found
    api.open_verse(c, v, 1)
    t = draw(g)
    assert any(x.startswith('1/') for x in t), t
    g.key('right')
    assert (int(api.S.c), int(api.S.v), int(api.S.page)) == (c, v, 2), (api.S.c, api.S.v, api.S.page)
    g.key('left')
    assert int(api.S.page) == 1

    # a host without seek: the files are read from the top, and that stays small
    g.L.execute('SEEK_BROKEN = true')
    worst_noseek = 0
    for c, n in chapters:
        for v in range(1, n + 1):
            g.L.execute('bytes_read = 0')
            assert api.open_verse(c, v, 1), (c, v)
            worst_noseek = max(worst_noseek, int(g.g.bytes_read))
    api.open_word(int(api.D.verse.ntok))
    draw(g)
    assert screen(g) == 'word'
    assert worst_noseek <= 22_000 + 13_000, worst_noseek        # a verse file + the index file
    g.L.execute('SEEK_BROKEN = false')

    # no undefined globals were read
    g.L.execute('''
      local allowed = { kit = true, on_draw = true, on_input = true, on_load = true, on_leave = true, __TEST = true }
      undef = {}
      setmetatable(_G, { __index = function(_, k) if not allowed[k] then undef[#undef + 1] = tostring(k) end end })
    ''')
    g.restart()
    for c, v in ((2, 2), (13, 1)):
        g.api.open_verse(c, v, 1); draw(g); g.api.open_word(1); draw(g)
    g.key('back'); g.key('back'); g.key('back')
    draw(g)
    undef = list(g.g.undef.values())
    assert not undef, undef

    print(f'gita: 701 verses open; worst screen {worst_cmds} draw commands; {multi} verses take two pages '
          f'in the largest sizes; {nfiles} verse files of at most {biggest} B; a verse reads at most '
          f'{worst_read} B ({worst_noseek} B without seek)')
    print('gita tests passed')


if __name__ == '__main__':
    main()
