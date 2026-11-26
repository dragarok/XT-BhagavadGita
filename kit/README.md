# kit: the build kit (vendored)

The tools that turn this app into an `.xtapp` and test it offline. They are copied from other
projects and adapted for this app (paths, and fixes found on the reader). Their MIT licences are here.

| File | What it does | From |
|---|---|---|
| `xtpack.py` | Packs the app as an `.xtapp`, encrypted for the key every X4 Pro carries | [omer-faruq-xteink/touch-licorice-apps](https://github.com/omer-faruq-xteink/touch-licorice-apps) `04d46f0`, MIT (`LICENSE-touch-licorice-apps`) |
| `gamekit.lua` | Shared Lua helpers (fonts, wrapping, buttons, key filtering); `bundle.py` puts it in front of `src/main.lua` | same |
| `bundle.py` | Makes `index.lua`: the reader has no `require` for package files | same |
| `harness.py` | Runs the app under Lua 5.4 (lupa) with a stand-in for the reader's API | same |
| `lualint55.py` | Catches Lua 5.4 code that the reader's Lua 5.5 rejects | same |
| `xtapp.py`, `mksd.py` | The `.xtapp` container format, used by `xtpack.py` | [kycube/x4pro-emu](https://github.com/kycube/x4pro-emu), MIT (`LICENSE-x4pro-emu`) |

Some of these files say "XTOS Licorice". That is the same firmware as XT Licorice.
