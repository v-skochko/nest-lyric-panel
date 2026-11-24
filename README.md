# Nest Lyric Panel

A Home Assistant integration and dashboard card for time-synced and plain song lyrics. It uses a media player's metadata, looks up lyrics in LRCLIB, and can optionally ask a self-hosted English-to-Ukrainian translation endpoint for translations.

> Early preview: the project has not yet been validated on every Home Assistant installation or hardware. It does not include song lyrics or model weights.

## Features

- LRCLIB lookup by artist, track, album and duration; exact metadata is important.
- Timestamped lyrics follow the playback position. Plain lyrics can be scrolled manually.
- Configurable timing offset and maximum difference between lyrics and track durations.
- One reusable card with a compact display option for Nest Hub and a layout for larger displays.
- Optional English-to-Ukrainian translation via a separate compatible endpoint. Without it, original lyrics still work.
- English and Ukrainian interface text. Five numeric modes are shared by the card and the backend.

The card needs a media player that exposes `media_title` and `media_artist`. Synchronization also requires a track duration, playback position, position update timestamp and matching timed lyrics.

## Installation

Requires Home Assistant 2026.11 or later. The Marketplace is available in Home Assistant 2026.11. This repository is intended to be added as a **custom integration repository**; it is not automatically part of the public catalog.

1. In **Settings → Marketplace**, add `https://github.com/v-skochko/nest-lyric-panel` as a custom repository of type **Integration**, then install it. A GitHub connection may be needed for custom repositories.
2. Restart Home Assistant. In **Settings → Devices & services**, add **Nest Lyric Panel**. Translation is off by default.
3. In **Settings → Dashboards → Resources**, add `/nest_lyric_panel/nest-lyric-panel.js?v=0.1.1` as a **JavaScript module**. The integration must be loaded to serve this file. Reload the browser or restart the Cast view.
4. Add the card using YAML:

```yaml
type: custom:nest-lyric-panel-card
entity: media_player.living_room
language: en
card_height: 400px
font_size: 30
translation_font_size: 18
sync_offset: 0
show_mode: true
```

For manual installation, copy `custom_components/nest_lyric_panel` to the corresponding `custom_components` directory in your Home Assistant configuration, then follow steps 2–4. The dashboard resource is a separate step even when the integration is installed by Marketplace.

The card uses the `nest-lyric-panel-card` tag and `nest_lyric_panel` domain. It is separate from the earlier private version using `music-plus-lyrics` and `vasyl_lyrics`; update dashboard configurations explicitly when migrating. Back up the old configuration first.

## Options

Integration options are under **Settings → Devices & services → Nest Lyric Panel → Configure**:

| Option | Default | Meaning |
| --- | --- | --- |
| Translation endpoint URL | empty | Optional HTTP(S) URL, without embedded credentials; blank disables translation. |
| Maximum duration difference | 2 seconds | Timed lyrics are treated as unsynchronized if durations differ by more than this. |
| Lyrics cache duration | 60 minutes | Per-instance in-memory lookup cache; 0 disables effective caching. |

The optional endpoint must accept a POST body like `{"q":["Hello"],"source":"en","target":"uk","format":"text"}` and return `{"translatedText":["Привіт"]}`. Only English-to-Ukrainian is supported at present. Changes to options take effect for new requests; refresh a card to re-evaluate the current track.

Card options:

| Option | Default | Meaning |
| --- | --- | --- |
| `entity` | required | Media player entity ID. |
| `language` | HA interface language | `en` or `uk`; other languages fall back to English. |
| `card_height` | `320px` | Positive height in `px`, `%`, or `vh`. |
| `font_size` | 22 | Original text size in pixels, 12–48. |
| `translation_font_size` | 12 | Translation size in pixels, 10–40. |
| `sync_offset` | 0 | Seconds to advance the highlighting; a negative value delays it. |
| `show_mode` | true | Show the mode indicator. |
| `fit_synced` | false | Fit synchronized original lines to available width. |
| `nest_style` | false | Use the compact white-panel style; with `fit_synced`, viewports up to 1124 CSS px wrap long originals. |

On compact displays translations remain on one line and long translations can be scrolled horizontally. Longer plain lyrics use two columns with manual vertical scrolling.

## Optional local translation

The `translator/` directory contains an optional Docker Compose service, separate from the integration. It uses `Xenova/opus-mt-en-uk`, runs on CPU and unloads the model after 10 idle minutes. The first translation downloads model files into a Docker volume and may take time; later cold starts load from that cache.

```sh
cd translator
docker compose up -d --build
```

By default the port binds to loopback only. If Home Assistant is on another host, set `OPUS_BIND_ADDRESS` to the Docker host's LAN address and use that address and port 5002 in the integration's translation endpoint URL. The server has **no authentication**; keep it on a trusted network, restrict access with a firewall, and never expose it to the Internet. Manage or rebuild the container through Docker/Portainer. An updated project version may require rebuilding the image.

Language detection is deliberately simple: text containing non-ASCII letters is not sent to the English translator. This prevents many unwanted translations but can misclassify another language written without accented characters.

## Modes and WebSocket API

The integration exposes the following Home Assistant WebSocket commands; these are not Home Assistant sensor entities:

- `nest_lyric_panel/lookup`: accepts `artist`, `title`, optional `album` and `duration`; returns `status`, lyrics, source and duration when available. `incomplete` means the source failed, not that lyrics were absent.
- `nest_lyric_panel/mode`: accepts lookup status, text, timestamp presence and durations; returns one integer:
  - `0`: lyrics not found.
  - `1`: synchronized, English, translation configured.
  - `2`: synchronized, original only.
  - `3`: unsynchronized, English, translation configured.
  - `4`: unsynchronized, original only.
- `nest_lyric_panel/translate`: accepts up to four `text` lines and `full_text`; returns translated lines or `skipped`. Translation failures are reported as errors.

Each client derives the mode for its own player and track. There is no single global Home Assistant helper, so two players may have different modes. Modes 1 and 3 describe translation eligibility/configuration, not a guarantee that the external translator is online.

## Privacy and sources

The integration sends artist, title, album and duration to LRCLIB. If translation is enabled, selected lyrics are sent to the configured endpoint. Lyrics are temporarily cached in Home Assistant memory; the repository does not store songs or lyrics. Respect the terms and copyright of each source. The optional translator downloads model files from Hugging Face.

The private installation's Pisni.in.ua fallback is not included in this initial public package: its terms permit personal noncommercial use, but explicit permission for automated access by this distributable has not been established.

## Development

```sh
python3 -m unittest discover -s tests -v
node --check custom_components/nest_lyric_panel/frontend/nest-lyric-panel.js
CHROME=/path/to/chromium python3 tests/browser_check.py
```

See [NOTICE.md](NOTICE.md) and [LICENSE](LICENSE) for licensing and attribution. Nest Lyric Panel is not affiliated with Home Assistant, Music Assistant, LRCLIB, or the model authors.
