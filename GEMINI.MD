# Antigravity System Instructions & Memory Log

## 1. Project Overview

* **Name:** Vavoo IPTV Playlist Generator
* **Scope:** Automated M3U8 playlist generation for Italian IPTV channels
* **Stack:** Python 3
* **Deployment:** GitHub Actions (daily auto-generation)

## 2. Architecture

### Playlist Generator (`python_iptv/src/`)

* `generate_playlist_cli.py` — CLI entry point
* `playlist_generator.py` — Core generator (channel fetching, EPG mapping, M3U8 output)
* `epg_manager.py` — EPG data fetching and caching (XMLTV format)
* `data_manager.py` — Logo management and EPG name resolution

## 3. Key Decisions

* **Multi-group support:** Channels can appear in multiple bouquets simultaneously (e.g. CINE34 in TV Sat + Cinema)
* **Bouquets:** TV Sat, Cinema, Serie TV, Sport, Kids, Documentary, Music, News
* **EPG Sources:** `iptv-epg.org` (primary) + `epgshare01.online` (backup)
* **Channel ordering:** Follows Tivùsat numbering (`TIVUSAT_ORDER` dict)

## 4. Running

```bash
# Generate playlist
cd python_iptv && .venv\Scripts\python.exe generate_playlist_cli.py
```

## 5. Persistent Memory Log

* **2026-02-23:** Optimized codebase — removed PyQt6 Player, Xtream API server, and all unused dependencies.
* **2026-02-23:** Fixed HISTORY EPG mapping and updated NOVE to `Nove.it`.
* **2026-02-24:** Multi-group channel support: channels appear in all matching bouquets.
* **2026-02-24:** Added Kids bouquet, expanded Cinema/Serie TV/Sport/Documentary/Music/News.
* **2026-02-24:** Added 30+ EPG entries (INTER TV, MOTOR TREND, EUROSPORT, FOOD NETWORK, HGTV, LA7D, etc.)
* **2026-02-24:** Built professional IPTV Web Player (Flask + HLS.js + EPG + Subtitles).
* **2026-02-24:** Fixed stream proxy CORS & playback issues by spoofing Vavoo's native `okhttp/4.11.0` User-Agent and resolving relative stream segments against the HTTP 302 redirected edge server URLs.
