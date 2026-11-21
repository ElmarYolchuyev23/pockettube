# Changelog

## Unreleased

- One release for all firmware: `build.py` now makes the KNULLI installer archive, a PortMaster port (muOS, ROCKNIX, ArkOS, AmberELEC and others) and a muOS app (`.muxapp`) from the same source.
- Runs on firmware other than Batocera / KNULLI: downloads and music stay in the app folder when there is no `/userdata`, DejaVu is looked up in the usual font folders, and screens other than 640×480 get the interface scaled to fit.
- Related videos work again: they now come from YouTube's watch-page data, since YouTube stopped serving the video's mix playlist to yt-dlp. The old way stays as a fallback.
- Turkish interface and a Turkish Q on-screen keyboard (the keyboard key cycles EN → RU → TR).
- Interface font is now Inter (bundled in `assets/fonts`); DejaVu Sans stays as a fallback.
- One focus style everywhere: a purple ring that glides to the selected item; lists scroll smoothly under it.
- Thumbnails have anti-aliased rounded corners; duration badges are translucent; the focused Home card grows slightly and its progress bar sits inside the thumbnail.
- Loading placeholders shimmer.
- Header: inactive tabs are plain text and the active-tab pill glides on L1/R1.
- Home shows a Watch later row and only the sections that have something in them; on first run it shows a single welcome state.
- Video screen: the background takes on the thumbnail's colours, and the channel gets a letter avatar.
- Empty History, Downloads, playlists and search results show an icon and a hint for what to do next.
- Faster drawing: rendered text and wrapped titles are cached, so a frame takes about a fifth of the time it did in 1.0.
- `tools/perf.py`: frame-time benchmark to run on the handheld.

## 1.0

- New name and look: **PocketTube**, with its own logo and a purple accent instead of the YouTube-style red.
- The app now lives in `/userdata/system/pockettube` and starts from **Ports → PocketTube**. The installer backs up an older install (`ytclient`, `YouTube.sh`) and moves its history, playlists, downloads and settings over.
- MIT license, English README with screenshots, FAQ and build instructions.

## 0.7

- Playlists tab: Watch later and your own playlists; save any video with Y; play a whole playlist with START.
- Related videos on the video screen; "Continue watching" on Home shows unfinished videos.
- Audio-only playback (START on the video screen or the player menu); the screen turns off and wakes on any button.
- Sleep timer in the player menu.
- Audio-only downloads (m4a with title and artist tags) into `/userdata/music/youtube`.
- Search filters: sort, upload date, duration, type (videos, live, playlists); playlists from search can be opened and saved.

## 0.6

- New player overlay: progress bar with chapter marks, speed 0.5×–2×, subtitles (manual, automatic and auto-translated), chapters, seek feedback, first-run controls help.
- Downloads keep chapters and subtitles for offline viewing.
- Full Russian ЙЦУКЕН keyboard and a keyboard layout setting; scrollable settings.

## 0.5

- English and Russian interface, switchable in settings.
- English repository and installer.

## 0.4

- 720p quality, with deno used only when YouTube hides 720p without it.
- Menu sounds.
- Ports carousel artwork and metadata.
- Installer (`install.sh`) and archive builder (`build.py`).
