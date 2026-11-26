-- Bhagavad Gita for the X4 Pro (XT Licorice, API 2.18), offline.
--
-- A verse shows the Sanskrit in Devanagari, its padachheda with a short English meaning under
-- every word (on or off), Annie Besant's translation and her notes. A long press on a word of the
-- verse (or of its padachheda) opens that word's page: the words it is made of, each with its
-- base form, grammar and dictionary meanings.
--
-- The Devanagari is text, drawn by the reader with the .ttf picked in Ink App settings (kit.font
-- with a pixel size): with Tiro Devanagari Hindi the reader joins the letters correctly. The app
-- lays out every word itself, so it knows where each one is for the long press.
--
-- Data (apps/gita/data, read with ctx.package:open_text):
--   chapters.txt   n, verses, title, Devanagari name
--   index.txt      record file: verse k -> its data file and byte offset
--   vNNN.txt       a V line per verse, then one T line per printed word (small files: when the
--                  reader cannot seek, the file is read from the top, and that stays quick)
-- The slow work (reading a verse, laying it out) runs when a verse is opened, not while drawing,
-- and asks the host for more time (ctx.budget:extend): a callback gets about one second.
-- Every ctx.* function is a method: colon calls everywhere.

local W, H = 480, 800
local M = 12                          -- side margin
local CW = W - 2 * M                  -- content width
local TOP, BAR_Y = 54, 744            -- content between the title bar and the button bar
local CFG_FILE = 'config.txt'
local SIZES = { 'small', 'medium', 'large' }
-- Devanagari pixel sizes: shloka, padachheda, a word on its page, the word page's heading
local DEVA = { small = { 24, 20, 26, 28 }, medium = { 28, 24, 30, 32 }, large = { 32, 28, 34, 36 } }
local UNIT_GAP = 16                   -- between the words of the padachheda

local cfg = { pada = true, en = true, notes = true, size = 'medium', dsize = 'medium', last = '' }
local S = { screen = 'home', back_to = 'home', c = 1, v = 1, page = 1, tok = 1, wpage = 1, err = nil, held = false,
            leaving = false }
local D = { chapters = {}, start = {}, total = 0, stride = {}, title = '', verse = nil }
local V = {}                          -- the verse screen's pages (V.pages), the word page's (V.wpages)
local FONTS = {}                      -- fonts by name or pixel size (opening a .ttf size is slow)

------------------------------------------------------------------ helpers

local function refresh() pcall(function() ctx:invalidate() end) end
local function more_time() pcall(function() ctx.budget:extend() end) end
local function font(name)
  local f = FONTS[name]
  if f == nil then f = kit.font(name) or false; FONTS[name] = f end
  return f or nil
end
local function width(name, s) return kit.width(font(name), s) end
local function lh(name) return kit.line_h(name) end
-- a Devanagari line: room above and below for the vowel signs (kept: asking the font is slow)
local DLH = {}
local function dlh(p)
  local v = DLH[p]
  if not v then
    local f = font(p)
    local ok, h = pcall(function() return tonumber(f.line_height) end)
    v = math.max((ok and h) or (p * 5 // 4), p * 3 // 2)
    DLH[p] = v
  end
  return v
end
local function split(s, sep)
  local out = {}
  if s == nil or s == '' then return out end
  for part in (s .. sep):gmatch('(.-)' .. sep) do out[#out + 1] = part end
  return out
end
local function bool(s) return s == '1' or s == 'true' end
local function px(i) return DEVA[cfg.dsize][i] end

local function load_cfg()
  local t = kit.kv(kit.read(CFG_FILE))
  if t.pada then cfg.pada = bool(t.pada) end
  if t.en then cfg.en = bool(t.en) end
  if t.notes then cfg.notes = bool(t.notes) end
  if DEVA[t.size or ''] then cfg.size = t.size end
  if DEVA[t.dsize or ''] then cfg.dsize = t.dsize end
  if t.last and t.last:match('^%d+%.%d+$') then cfg.last = t.last end
end
local function save_cfg()
  kit.write(CFG_FILE, string.format('pada=%s\nen=%s\nnotes=%s\nsize=%s\ndsize=%s\nlast=%s\n',
    cfg.pada and '1' or '0', cfg.en and '1' or '0', cfg.notes and '1' or '0', cfg.size, cfg.dsize, cfg.last))
end

------------------------------------------------------------------ data

local function open_text(name)
  local pk = ctx.package
  if not pk then return nil end
  local ok, r = pcall(function() return pk:open_text(name, { max_bytes = 2000000, max_line_bytes = 32768 }) end)
  if ok and r ~= nil and type(r) ~= 'string' then return r end
  return nil
end
local function close(r) pcall(function() r:close() end) end

-- the first line at byte offset off, and the more(first) lines after it. ok(first) says the
-- seek landed right; when the host cannot seek, the file is read from the top, counting bytes
-- up to the offset (every line ends in one "\n"). The files are small, so that stays quick.
local function read_block(r, more, out)
  local first = r:read_line()
  if first == nil then return end
  out[1] = first
  for _i = 1, more(first) do
    local l = r:read_line()
    if l == nil then break end
    out[#out + 1] = l
  end
end
function D.lines(name, off, ok, more)
  more = more or function() return 0 end
  local r = open_text(name)
  if not r then return nil end
  local out = {}
  local good = pcall(function() r:seek(off); read_block(r, more, out) end)
  close(r)
  if good and out[1] and ok(out[1]) then return out end
  r = open_text(name)
  if not r then return nil end
  out = {}
  pcall(function()
    local pos = 0
    while pos < off do
      local l = r:read_line()
      if l == nil then return end
      pos = pos + #l + 1
    end
    if pos == off then read_block(r, more, out) end
  end)
  close(r)
  return (out[1] and ok(out[1])) and out or nil
end

-- the stride of the record files, from the banks.tsv that xtpack writes
local function load_banks()
  D.stride = { ['index.txt'] = 18 }
  local r = open_text('banks.tsv')
  if not r then return end
  pcall(function()
    while true do
      local l = r:read_line()
      if l == nil then break end
      local name, _count, stride = l:match('^([^\t]+)\t(%d+)\t(%d+)')
      if name and tonumber(stride) > 0 then D.stride[name] = tonumber(stride) end
    end
  end)
  close(r)
end

local function load_chapters()
  D.chapters, D.start, D.total = {}, {}, 0
  local r = open_text('chapters.txt')
  if not r then return false end
  pcall(function()
    while true do
      local l = r:read_line()
      if l == nil then break end
      local f = split(l, '\t')
      local n = tonumber(f[1])
      if n == 0 then D.title = f[4] or ''
      elseif n then D.chapters[n] = { n = n, count = tonumber(f[2]) or 0, title = f[3] or '', name = f[4] or '' } end
    end
  end)
  close(r)
  for c = 1, #D.chapters do
    D.start[c] = D.total
    D.total = D.total + D.chapters[c].count
  end
  return #D.chapters > 0
end

-- line k of a record file (every line stride - 1 bytes long)
local function record(name, k)
  local stride = D.stride[name]
  local lines = D.lines(name, (k - 1) * stride, function(l) return #l == stride - 1 end)
  return lines and lines[1]
end

-- the verse c.v with its printed words, or nil and a reason
function D.load_verse(c, v)
  local ch = D.chapters[c]
  if not ch or v < 1 or v > ch.count then return nil, 'no such verse' end
  local ref = c .. '.' .. v
  local rec = record('index.txt', D.start[c] + v)
  local cc, vv, ff, off = (rec or ''):match('^(%d+) (%d+) (%d+) (%d+)$')
  if not cc or tonumber(cc) ~= c or tonumber(vv) ~= v then return nil, 'index: ' .. tostring(rec) end
  local file = string.format('v%03d.txt', tonumber(ff))
  local head = 'V\t' .. ref .. '\t'
  local lines = D.lines(file, tonumber(off), function(l) return l:sub(1, #head) == head end,
    function(first) return tonumber(first:match('\t(%d+)$')) or 0 end)
  if not lines then return nil, 'verse ' .. ref .. ' not found' end
  local f = split(lines[1], '\t')
  local vs = { c = c, v = v, ref = ref, speaker = f[3] or '', en = f[4] or '', notes = split(f[5] or '', '\x1f'),
               lines = {}, toks = {}, ntok = tonumber(f[7]) or 0 }
  for i = 2, #lines do
    local t = split(lines[i], '\t')
    if t[1] == 'T' then
      local tok = { printed = t[2] or '', padas = {}, words = {} }
      for _j, p in ipairs(split(t[3] or '', '\x1e')) do
        local q = split(p, '\x1f')
        tok.padas[#tok.padas + 1] = { d = q[1] or '', g = q[2] or '' }
      end
      for _j, w in ipairs(split(t[4] or '', '\x1e')) do
        local q = split(w, '\x1f')
        tok.words[#tok.words + 1] = { label = q[1] or '', gram = q[2] or '', sense = q[3] or '', mean = q[4] or '' }
      end
      vs.toks[#vs.toks + 1] = tok
    end
  end
  local k = 0
  for _i, line in ipairs(split(f[6] or '', '\x1e')) do
    local items = {}
    for _j, it in ipairs(split(line, '\x1f')) do
      if it:sub(1, 1) == '~' then items[#items + 1] = { s = it:sub(2) }
      else k = k + 1; items[#items + 1] = { s = it, k = k } end
    end
    vs.lines[#vs.lines + 1] = items
  end
  vs.ntok = math.min(vs.ntok, #vs.toks)
  return vs
end

------------------------------------------------------------------ verse layout

-- items of width w cut into rows no wider than CW; a line that must wrap is cut into rows of
-- about equal width, so no word is left alone on the last row
local function rows_of(units, gap)
  local total = 0
  for i, u in ipairs(units) do total = total + u.w + (i > 1 and gap or 0) end
  local n = math.max(1, -((-total) // CW))
  local target = n > 1 and math.min(CW, total / n * 1.1 + gap) or CW
  local rows, row, x = {}, {}, 0
  for _i, u in ipairs(units) do
    if #row > 0 and (x + u.w > CW or x + u.w > target) then rows[#rows + 1] = row; row, x = {}, 0 end
    row[#row + 1] = u
    x = x + u.w + gap
  end
  if #row > 0 then rows[#rows + 1] = row end
  -- never a row of punctuation alone: the word before it goes down with it
  local last = rows[#rows]
  if #rows > 1 and not last[1].k and #rows[#rows - 1] > 1 then
    local only_punct = true
    for _i, u in ipairs(last) do if u.k then only_punct = false end end
    if only_punct then table.insert(last, 1, table.remove(rows[#rows - 1])) end
  end
  return rows
end

-- x of each unit, the row centred
local function place(row, gap)
  local w = 0
  for i, u in ipairs(row) do w = w + u.w + (i > 1 and gap or 0) end
  local x = M + (CW - w) // 2
  for _i, u in ipairs(row) do u.x = math.floor(x); x = x + u.w + gap end
end

-- the verse as pages of items: shloka rows, padachheda rows, speaker, translation, notes
local function layout_verse()
  more_time()
  local vs = D.verse
  local items = {}
  local spx, ppx = px(1), px(2)
  local sp = width(spx, ' ')
  if sp < 4 then sp = spx // 3 end
  for _i, line in ipairs(vs.lines) do
    local units = {}
    for _j, it in ipairs(line) do units[#units + 1] = { s = it.s, k = it.k, w = width(spx, it.s) } end
    for _j, row in ipairs(rows_of(units, sp)) do
      place(row, sp)
      items[#items + 1] = { kind = 'deva', units = row, px = spx, h = dlh(spx) }
    end
  end
  items[#items + 1] = { kind = 'gap', h = 6 }
  if cfg.pada then
    items[#items + 1] = { kind = 'rule', h = 20 }
    local glh = lh('small')
    for _i, line in ipairs(vs.lines) do
      local units = {}
      for _j, it in ipairs(line) do
        local tok = it.k and vs.toks[it.k]
        for _p, pd in ipairs(tok and tok.padas or {}) do
          local dw = width(ppx, pd.d)
          local gl = pd.g ~= '' and kit.wrap(pd.g, 'small', math.min(CW, math.max(dw, 150))) or {}
          while #gl > 3 do table.remove(gl) end
          local w = dw
          for _q, l in ipairs(gl) do w = math.max(w, width('small', l)) end
          units[#units + 1] = { s = pd.d, dw = dw, gl = gl, k = it.k, w = math.min(CW, w) }
        end
      end
      for _j, row in ipairs(rows_of(units, UNIT_GAP)) do
        place(row, UNIT_GAP)
        local n = 0
        for _q, u in ipairs(row) do n = math.max(n, #u.gl) end
        -- the meaning right under its word, and more room before the next row, so it reads as one
        local goff = ppx * 5 // 4 + 2
        items[#items + 1] = { kind = 'pada', units = row, px = ppx, glh = glh, goff = goff, h = goff + n * glh + 14 }
      end
    end
  end
  local function text(s, fname, block)
    for _i, l in ipairs(kit.wrap(s, fname, CW)) do
      items[#items + 1] = { kind = 'text', s = l, font = fname, h = lh(fname) + 2, x = M, block = block }
    end
  end
  if cfg.en and vs.en ~= '' then
    items[#items + 1] = { kind = 'rule', h = 14, block = 'en' }
    if vs.speaker ~= '' then text(vs.speaker, 'small', 'en') end
    text(vs.en, cfg.size, 'en')
  end
  if cfg.notes and #vs.notes > 0 then
    items[#items + 1] = { kind = 'gap', h = 10 }
    for i, n in ipairs(vs.notes) do text((#vs.notes > 1 and (i .. '. ') or 'Note: ') .. n, 'small') end
  end
  -- the translation stays in one piece: when it does not fit under the padachheda but fits on a
  -- page of its own, it starts the next page
  local block_h, started = {}, {}
  for _i, it in ipairs(items) do
    if it.block then block_h[it.block] = (block_h[it.block] or 0) + it.h end
  end
  local pages, cur, y = {}, {}, TOP + 6
  for _i, it in ipairs(items) do
    local spacer = it.kind == 'rule' or it.kind == 'gap'
    local need = it.h
    if it.block and not started[it.block] then
      started[it.block] = true
      if block_h[it.block] <= BAR_Y - 4 - (TOP + 6) then need = block_h[it.block] end
    end
    if y + need > BAR_Y - 4 and #cur > 0 then
      pages[#pages + 1] = cur; cur, y = {}, TOP + 6
    end
    if not (spacer and #cur == 0) then       -- a page never starts with a rule or a gap
      it.y = y
      cur[#cur + 1] = it
      y = y + it.h
    end
  end
  if #cur > 0 then pages[#pages + 1] = cur end
  V.pages = pages
  if S.page > #pages then S.page = #pages end
end

local function verse_pages()
  if not V.pages then layout_verse() end
  return V.pages
end

-- the printed word under (x, y) on the verse screen: the row under y, then the nearest word in it
local function word_at(x, y)
  for _i, it in ipairs(verse_pages()[S.page] or {}) do
    if (it.kind == 'deva' or it.kind == 'pada') and y >= it.y and y < it.y + it.h then
      local best, bd = nil, nil
      for _j, u in ipairs(it.units) do
        if u.k then
          local d = x < u.x and u.x - x or (x > u.x + u.w and x - u.x - u.w or 0)
          if not bd or d < bd then best, bd = u.k, d end
        end
      end
      return best
    end
  end
end

------------------------------------------------------------------ navigation

local function chapter_of(c) return D.chapters[c] end

local function open_verse(c, v, page)
  more_time()
  local vs, err = D.load_verse(c, v)
  if not vs then S.err = err; return false end
  D.verse = vs
  S.c, S.v, S.page, S.screen = c, v, page or 1, 'verse'
  V.pages = nil
  verse_pages()                       -- laid out now, so drawing has nothing slow to do
  cfg.last = vs.ref
  save_cfg()
  return true
end

local function step_verse(d)
  local c, v = S.c, S.v + d
  if v < 1 then
    if c == 1 then return end
    c = c - 1; v = chapter_of(c).count
  elseif v > chapter_of(c).count then
    if c == #D.chapters then return end
    c = c + 1; v = 1
  end
  open_verse(c, v, 1)
end

local function page_verse(d)
  local n = #verse_pages()
  if d > 0 and S.page < n then S.page = S.page + 1
  elseif d < 0 and S.page > 1 then S.page = S.page - 1
  else step_verse(d) end
end

-- the word page: the printed word, then a row per word it is made of: the word (with its base
-- form), its grammar and meaning
local function layout_word()
  local tok = D.verse.toks[S.tok]
  local rows = {}
  local wlh = dlh(px(3))
  for i, wd in ipairs(tok.words) do
    local lines = { wd.gram }
    local m = wd.sense ~= '' and wd.sense or ''
    if wd.mean ~= '' and wd.mean ~= wd.sense then m = (m ~= '' and (m .. ' - ') or '') .. wd.mean end
    for _j, l in ipairs(kit.wrap(m, 'small', CW - 16)) do
      if #lines >= 4 then break end
      lines[#lines + 1] = l
    end
    rows[#rows + 1] = { idx = i, label = wd.label, lines = lines, h = wlh + #lines * (lh('small') + 1) + 10 }
  end
  local y0 = TOP + dlh(px(4)) + 14
  local pages, cur, y = {}, {}, y0
  for _i, r in ipairs(rows) do
    if (#cur >= 6 or y + r.h > BAR_Y - 4) and #cur > 0 then pages[#pages + 1] = cur; cur, y = {}, y0 end
    r.y = y; cur[#cur + 1] = r; y = y + r.h
  end
  if #cur > 0 then pages[#pages + 1] = cur end
  V.wpages = pages
end

local function open_word(k)
  local vs = D.verse
  if not vs or k < 1 or k > vs.ntok then return end
  more_time()
  S.tok, S.wpage, S.screen = k, 1, 'word'
  layout_word()
end

local function page_word(d)
  local n = #V.wpages
  if d > 0 and S.wpage < n then S.wpage = S.wpage + 1
  elseif d < 0 and S.wpage > 1 then S.wpage = S.wpage - 1
  else
    local k = S.tok + d
    if k >= 1 and k <= D.verse.ntok then open_word(k) end
  end
end

local function back_to_verse() S.screen = 'verse' end

------------------------------------------------------------------ drawing

local function bar(gg, labels)
  local n = #labels
  local bw = math.floor((CW - (n - 1) * 8) / n)
  for i, l in ipairs(labels) do
    kit.button(gg, M + (i - 1) * (bw + 8), BAR_Y + 4, bw, 48, l, { font = 'medium' })
  end
end
local function bar_hit(x, y, n)
  if y < BAR_Y then return nil end
  local bw = math.floor((CW - (n - 1) * 8) / n)
  local i = math.floor((x - M) / (bw + 8)) + 1
  if i >= 1 and i <= n then return i end
end
local function title_bar(gg, left, right)
  gg:text(M, 14, left, { font = font('medium') })
  if right then gg:text(W - M - width('small', right), 18, right, { font = font('small') }) end
  gg:line(M, TOP - 6, W - M, TOP - 6)
end
local function centred(gg, s, fname, y)
  gg:text(M + math.floor(math.max(0, (CW - width(fname, s)) / 2)), y, s, { font = font(fname) })
end
local function fit(s, fname, maxw)
  if width(fname, s) <= maxw then return s end
  while #s > 1 and width(fname, s .. '~') > maxw do s = kit.drop_last(s) end
  return s .. '~'
end

local function home_rows() return 112, 34 end
local function draw_home(gg)
  if D.title ~= '' then centred(gg, D.title, px(4), 6) end   -- sizes the verses use: each new .ttf size is slow
  centred(gg, 'Bhagavad Gita - Besant translation, padachheda', 'small', 66)
  gg:line(M, 96, W - M, 96)
  local y0, rh = home_rows()
  for c = 1, #D.chapters do
    local ch = D.chapters[c]
    local y = y0 + (c - 1) * rh
    gg:text(M, y + 6, tostring(c), { font = font('medium') })
    local cnt = tostring(ch.count)
    gg:text(W - M - width('small', cnt), y + 9, cnt, { font = font('small') })
    gg:text(M + 34, y + 6, fit(ch.title, 'medium', CW - 34 - 40), { font = font('medium') })
  end
  bar(gg, { cfg.last ~= '' and ('Continue ' .. cfg.last) or 'Start at 1.1', 'Settings' })
end

local function grid_geom(ch)
  local cols = ch.count > 60 and 7 or 6
  local cw = math.floor((CW - (cols - 1) * 6) / cols)
  return cols, cw, 42, 6, 150
end
local function draw_chapter(gg)
  local ch = chapter_of(S.c)
  title_bar(gg, 'Chapter ' .. S.c, ch.count .. ' verses')
  for i, l in ipairs(kit.wrap(ch.title, 'small', CW)) do
    if i > 2 then break end
    gg:text(M, TOP + (i - 1) * (lh('small') + 2), l, { font = font('small') })
  end
  if ch.name ~= '' then centred(gg, ch.name, px(1), TOP + 46) end
  local cols, cw, chh, gap, y0 = grid_geom(ch)
  local last_c, last_v = cfg.last:match('^(%d+)%.(%d+)$')
  for v = 1, ch.count do
    local r, col = (v - 1) // cols, (v - 1) % cols
    local x, y = M + col * (cw + gap), y0 + r * (chh + gap)
    local here = tonumber(last_c) == S.c and tonumber(last_v) == v
    kit.button(gg, x, y, cw, chh, tostring(v), { font = 'medium', line_width = here and 4 or 1 })
  end
  bar(gg, { 'Back', 'From 1' })
end

local function draw_verse(gg)
  local vs = D.verse
  local pages = verse_pages()
  local ch = chapter_of(vs.c)
  title_bar(gg, 'Bhagavad Gita ' .. vs.ref, (#pages > 1 and (S.page .. '/' .. #pages .. '   ') or '') .. vs.v .. ' of ' .. ch.count)
  for _i, it in ipairs(pages[S.page] or {}) do
    if it.kind == 'deva' then
      local f = font(it.px)
      for _j, u in ipairs(it.units) do gg:text(u.x, it.y, u.s, { font = f }) end
    elseif it.kind == 'pada' then
      local f, g = font(it.px), font('small')
      local gy = it.y + it.goff
      for _j, u in ipairs(it.units) do
        gg:text(math.floor(u.x + (u.w - u.dw) / 2), it.y, u.s, { font = f })
        for q, l in ipairs(u.gl) do
          gg:text(math.floor(u.x + (u.w - width('small', l)) / 2), gy + (q - 1) * it.glh, l, { font = g })
        end
      end
    elseif it.kind == 'rule' then
      gg:line(M + 140, it.y + it.h // 2, W - M - 140, it.y + it.h // 2)
    elseif it.kind == 'text' then
      gg:text(it.x, it.y, it.s, { font = font(it.font) })
    end
  end
  bar(gg, { '< Prev', cfg.pada and 'Pada: on' or 'Pada: off', 'Next >' })
end

local function draw_word(gg)
  local vs = D.verse
  local tok = vs.toks[S.tok]
  local pages = V.wpages or {}
  if S.wpage > #pages then S.wpage = math.max(1, #pages) end
  title_bar(gg, vs.ref .. '  word ' .. S.tok .. ' of ' .. vs.ntok, #pages > 1 and (S.wpage .. '/' .. #pages) or nil)
  centred(gg, tok.printed, px(4), TOP + 4)
  gg:line(M, TOP + dlh(px(4)) + 8, W - M, TOP + dlh(px(4)) + 8)
  local wf, sf, wlh = font(px(3)), font('small'), dlh(px(3))
  for _i, r in ipairs(pages[S.wpage] or {}) do
    gg:text(M, r.y, r.label, { font = wf })
    local y = r.y + wlh
    for _j, l in ipairs(r.lines) do
      gg:text(M + 16, y, l, { font = sf })
      y = y + lh('small') + 1
    end
  end
  if #tok.words == 0 then gg:text(M, TOP + 80, 'No word analysis for this word.', { font = font('medium') }) end
  bar(gg, { '< Word', 'Back', 'Word >' })
end

local SETTINGS = {
  { 'pada', function() return 'Padachheda and meanings: ' .. (cfg.pada and 'on' or 'off') end },
  { 'en', function() return 'Translation: ' .. (cfg.en and 'on' or 'off') end },
  { 'notes', function() return 'Notes: ' .. (cfg.notes and 'on' or 'off') end },
  { 'size', function() return 'English text size: ' .. cfg.size end },
  { 'dsize', function() return 'Devanagari size: ' .. cfg.dsize end },
  { 'about', function() return 'About and sources' end },
}
local function settings_rect(i) return M, TOP + 16 + (i - 1) * 70, CW, 58 end
local function draw_settings(gg)
  title_bar(gg, 'Settings')
  for i, s in ipairs(SETTINGS) do
    local x, y, w, h = settings_rect(i)
    kit.button(gg, x, y, w, h, s[2](), { font = 'medium' })
  end
  local y = TOP + 16 + #SETTINGS * 70 + 6
  for _i, l in ipairs(kit.wrap('Long press a word of a verse to open its page. The Devanagari is drawn with the .ttf font '
      .. 'picked in Ink App settings: Tiro Devanagari Hindi.', 'small', CW)) do
    gg:text(M, y, l, { font = font('small') }); y = y + lh('small') + 2
  end
  bar(gg, { 'Back' })
end

local ABOUT = {
  'Sanskrit text and translation: Annie Besant, The Bhagavad-Gita, 4th edition (1922), public domain, as proofread on Wikisource.',
  'Padachheda, grammar and meanings: the Digital Corpus of Sanskrit (DCS), Oliver Hellwig 2010-2024, CC BY 4.0.',
  'The short meaning under each word is a gloss made for this app from that analysis. Long press a word for its full grammar and dictionary meanings.',
  'Devanagari: drawn by the reader with the .ttf picked in Ink App settings (Tiro Devanagari Hindi, SIL Open Font License).',
  'Chapter 13 follows Besant\'s numbering (35 verses: Arjuna\'s question is verse 1).',
  'Everything is on the reader: no Wi-Fi is used.',
}
local function draw_about(gg)
  title_bar(gg, 'About and sources')
  local y = TOP + 6
  for _i, p in ipairs(ABOUT) do
    for _j, l in ipairs(kit.wrap(p, 'small', CW)) do
      gg:text(M, y, l, { font = font('small') }); y = y + lh('small') + 2
    end
    y = y + 10
  end
  bar(gg, { 'Back' })
end

local DRAW = { home = draw_home, chapter = draw_chapter, verse = draw_verse, word = draw_word,
               settings = draw_settings, about = draw_about }

------------------------------------------------------------------ input

local function toggle(key)
  if key == 'size' or key == 'dsize' then
    local i = 1
    for k, s in ipairs(SIZES) do if s == cfg[key] then i = k end end
    cfg[key] = SIZES[i % #SIZES + 1]
  else
    cfg[key] = not cfg[key]
  end
  V.pages = nil
  save_cfg()
  if S.screen == 'verse' then verse_pages() end
end

local function open_settings(from) S.back_to, S.screen = from, 'settings' end
local function leave_settings()
  S.screen = S.back_to or 'home'
  if S.screen == 'verse' then V.pages = nil; verse_pages() end
end
local function go_home() S.screen = 'home' end
local function go_chapter(c) more_time(); S.c = c; S.screen = 'chapter' end

local function continue_reading()
  local c, v = cfg.last:match('^(%d+)%.(%d+)$')
  open_verse(tonumber(c) or 1, tonumber(v) or 1, 1)
end

local function tap(x, y)
  local sc = S.screen
  if sc == 'home' then
    local b = bar_hit(x, y, 2)
    if b == 1 then continue_reading() elseif b == 2 then open_settings('home')
    else
      local y0, rh = home_rows()
      local c = math.floor((y - y0) / rh) + 1
      if y >= y0 and c >= 1 and c <= #D.chapters then go_chapter(c) end
    end
  elseif sc == 'chapter' then
    local b = bar_hit(x, y, 2)
    if b == 1 then go_home() elseif b == 2 then open_verse(S.c, 1, 1)
    else
      local ch = chapter_of(S.c)
      local cols, cw, chh, gap, y0 = grid_geom(ch)
      if y >= y0 and x >= M then
        local col = math.floor((x - M) / (cw + gap))
        local r = math.floor((y - y0) / (chh + gap))
        local v = r * cols + col + 1
        if col < cols and v >= 1 and v <= ch.count then open_verse(S.c, v, 1) end
      end
    end
  elseif sc == 'verse' then
    local b = bar_hit(x, y, 3)
    if b == 1 then page_verse(-1) elseif b == 3 then page_verse(1)
    elseif b == 2 then toggle('pada')
    elseif y < TOP then go_chapter(S.c) end
  elseif sc == 'word' then
    local b = bar_hit(x, y, 3)
    if b == 1 then page_word(-1) elseif b == 3 then page_word(1) elseif b == 2 then back_to_verse() end
  elseif sc == 'settings' then
    if bar_hit(x, y, 1) then leave_settings(); return end
    for i, s in ipairs(SETTINGS) do
      local rx, ry, rw, rh = settings_rect(i)
      if x >= rx and x < rx + rw and y >= ry and y < ry + rh then
        if s[1] == 'about' then S.screen = 'about' else toggle(s[1]) end
      end
    end
  elseif sc == 'about' then
    if bar_hit(x, y, 1) then S.screen = 'settings' end
  end
end

local function long_press(x, y)
  if S.screen == 'verse' then
    local k = word_at(x, y)
    if k then open_word(k) end
  end
end

local function back()
  local sc = S.screen
  if sc == 'word' then back_to_verse()
  elseif sc == 'verse' then go_chapter(S.c)
  elseif sc == 'chapter' then go_home()
  elseif sc == 'settings' then leave_settings()
  elseif sc == 'about' then S.screen = 'settings'
  end
end

local function step(d)
  if S.screen == 'verse' then page_verse(d)
  elseif S.screen == 'word' then page_word(d)
  elseif S.screen == 'chapter' then
    local c = S.c + d
    if c >= 1 and c <= #D.chapters then go_chapter(c) end
  end
end

-- the release of a button, whatever the host calls the field
local function key_release(ev)
  local ph = ev.phase or ev.action or ev.state
  return ph == 'up' or ph == 'release' or ph == 'released' or ev.pressed == false or ev.down == false
end

function on_input(c, ev)
  if type(ev) == 'table' and ev.type == 'key' then
    -- Back on Home leaves the app. The reader leaves when the app passes on (returns false for)
    -- the RELEASE of the button, so a Back press made on Home is passed on with its repeats and
    -- its release. Only a press made on Home: the release of the Back press that brought you
    -- Home must not leave (0.1.1 left from the chapter screen).
    if ev.key == 'back' and S.leaving and S.screen == 'home' then
      if key_release(ev) then S.leaving = false end
      return false
    end
    -- a button sends several events per press (down, up, repeats); only the first one counts
    if not kit.key_accepted(ev) then return true end
    if ev.key == 'back' and S.screen == 'home' then S.leaving = true; return false end
    S.leaving = false
  end
  local ok, e = pcall(function()
    if type(ev) ~= 'table' then return end
    if ev.type == 'pointer' then
      if ev.gesture == 'long' or ev.phase == 'hold' then
        if not S.held then long_press(ev.x or 0, ev.y or 0) end
        S.held = (ev.phase ~= 'up')
        return
      end
      if ev.phase ~= 'up' then return end
      if S.held then S.held = false; return end
      S.err = nil
      local g = ev.gesture
      if g == 'swipe_left' or g == 'swipe_up' then step(1)
      elseif g == 'swipe_right' or g == 'swipe_down' then step(-1)
      else tap(ev.x or 0, ev.y or 0) end
    elseif ev.type == 'key' then
      S.err = nil
      local k = ev.key
      if k == 'back' then back()
      elseif k == 'right' or k == 'down' then step(1)
      elseif k == 'left' or k == 'up' then step(-1) end
    end
  end)
  if not ok then S.err = tostring(e) end
  refresh()
  return true
end

function on_draw(c, gg)
  pcall(function() gg:clear(0) end)   -- the host keeps the last frame: without this, screens pile up
  local ok, e = pcall(function()
    if #D.chapters == 0 then
      gg:text(M, 100, 'The Gita data is missing from this package.', { font = font('medium') })
      return
    end
    local f = DRAW[S.screen] or draw_home
    f(gg)
  end)
  if not ok then S.err = tostring(e) end
  if S.err then
    gg:text(M, BAR_Y - 26, kit.short('ERR ' .. S.err, 60), { font = font('small') })
  end
end

function on_load(c)
  more_time()                         -- the first .ttf sizes open here
  load_cfg()
  load_banks()
  if not load_chapters() then S.err = 'no data' end
end

function on_leave()
  pcall(save_cfg)
end

__TEST = __TEST or {}
__TEST.api = { S = S, D = D, V = V, cfg = cfg, word_at = word_at, verse_pages = verse_pages,
               open_verse = open_verse, open_word = open_word, V_reset = function() V.pages = nil end }
