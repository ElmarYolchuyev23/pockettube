# Changelog

## Unreleased

- Interface font is now Inter (bundled in `assets/fonts`); DejaVu Sans stays as a fallback.
- One focus style everywhere: a purple ring that glides to the selected item; lists scroll smoothly under it.

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
