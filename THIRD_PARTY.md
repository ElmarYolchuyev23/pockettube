# Third-party components

The repository doesn't contain these programs, except the Inter font. The installer downloads yt-dlp and deno from their official release pages;
mpv, Python, pygame, ffmpeg and the DejaVu fonts come with the console firmware.

| Component | Where it comes from | License |
|---|---|---|
| [yt-dlp](https://github.com/yt-dlp/yt-dlp) | installer, GitHub Releases → `pockettube/ytdlp_src` | The Unlicense (public domain) |
| [yt-dlp-ejs](https://github.com/yt-dlp/ejs) (bundled in the yt-dlp release) | together with yt-dlp | The Unlicense / MIT (see the project) |
| [deno](https://github.com/denoland/deno) | installer, GitHub Releases → `pockettube/bin/deno` | MIT |
| [mpv](https://mpv.io) | console firmware | GPL-2.0-or-later / LGPL-2.1-or-later |
| [FFmpeg](https://ffmpeg.org) | console firmware | LGPL-2.1-or-later / GPL-2.0-or-later |
| [pygame](https://www.pygame.org) | console firmware | LGPL-2.1 |
| [DejaVu Fonts](https://dejavu-fonts.github.io) | console firmware (fallback font) | Bitstream Vera / DejaVu (free) |
| [Inter](https://rsms.me/inter/) 4.1 (Regular, SemiBold) | bundled in the repository, `pockettube/assets/fonts` | SIL Open Font License 1.1 (`assets/fonts/Inter-LICENSE.txt`) |

### PortMaster and muOS packages

These packages run on PortMaster's `python_3.11` runtime instead of the firmware's Python, so they bundle a few more components (`packaging/portmaster/vendor`, licenses in `packaging/portmaster/licenses`):

| Component | Where it comes from | License |
|---|---|---|
| [yt-dlp](https://github.com/yt-dlp/yt-dlp) | official release, unpacked into `pockettube/ytdlp_src` at build time | The Unlicense |
| [pygame](https://www.pygame.org) 2.6.1 for aarch64 / Python 3.11 | Cebion's build from the Angry Drunken Dwarves PortMaster port, against the system SDL2 | LGPL-2.1 |
| [OpenSSL](https://www.openssl.org) 1.1 (`libssl.so.1.1`, `libcrypto.so.1.1`) | aarch64 build; the runtime needs it and newer firmware only ships OpenSSL 3 | OpenSSL / SSLeay |
| [libffi](https://sourceware.org/libffi/) 7 | aarch64 build, needed by the runtime | MIT |
| [certifi](https://github.com/certifi/python-certifi) | CA certificates, used when the firmware has no certificate bundle | MPL-2.0 |

PocketTube's own code is released under the MIT license (see [LICENSE](LICENSE)).

## Images in screenshots and carousel art

The screenshots (`docs/screenshots`, `pockettube-screenshot.png`) use demo data with thumbnails of freely licensed films (stored in `tools/demo`):

| Film | Author | License |
|---|---|---|
| Big Buck Bunny, Sintel, Tears of Steel | Blender Foundation | CC BY 3.0 |
| Cosmos Laundromat, Spring, Charge | Blender Foundation / Blender Studio | CC BY 4.0 |
| Artemis II mission animation | NASA | public domain (NASA media usage guidelines) |

The PocketTube logo and carousel art are original work under the project's MIT license.

## Disclaimer

PocketTube is an unofficial client. It is not affiliated with or endorsed by YouTube or Google.
"YouTube" is a trademark of Google LLC. Use the app in line with the YouTube Terms of Service and the laws of your country,
and only download content you have the right to download.
