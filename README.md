# DR TV & Radio for Home Assistant

A custom integration for watching DR's live TV channels (DR1, DR2,
DR Ramasjang, TVA Live, DRTV Ekstra) and listening to DR's radio stations
(P1, P2, P3, P4 and P5 with all their regions, P6, P8 and more) in Home
Assistant, without scripts, helpers or YAML.

## What you get

- **A DR TV dashboard card.** It shows every channel with its logo, the programme
  that's on now and a progress bar. Tap a channel and the live video plays inside
  the card. Under the video you see the title, the time slot and what's next.
  The card ships with the integration and registers itself, so there's no
  resource to add.
- **DR in the Media panel**, with two folders:
  - **DR TV**: the live channels as HLS video, playable in the browser or on
    Chromecast and many smart TVs.
  - **DR Radio**: the radio stations as MP3, playable in the browser, which
    keeps playing in the bottom bar while you browse, or on Sonos, Chromecast,
    Google and other speakers. P4 and P5 are folders with their regional
    stations. DR's radio schedule needs an API key, so stations show their
    name and logo but not the current programme.

  To start one from an automation, use `media_player.play_media` with
  `media-source://dr_tv/tv/20875` (DR1) or `media-source://dr_tv/radio/p1` (P1).
  The older `media-source://dr_tv/20875` form still works.
- **Resilience.** If DR's API is down, the last known data or the built-in
  channel and station lists are kept, so streams keep working. After repeated failures a
  repair notice appears under Settings → Repairs, and it clears by itself.

The integration has no entities. A TV channel isn't a device with a state.

## Install

### HACS (custom repository)
1. HACS → ⋮ → Custom repositories → add this repo's URL, type *Integration*.
2. Install **DR TV** and restart Home Assistant.

### Manual
Copy `custom_components/dr_tv` into your Home Assistant `config/custom_components/`
and restart.

Then go to **Settings → Devices & services → Add integration → DR TV**.
There's nothing to configure.

## The card

Edit a dashboard → **Add card** → search for **DR TV**, or in YAML:

```yaml
type: custom:dr-tv-card
channel: DR1      # optional: the channel selected when the card loads
autoplay: false   # optional: start playing (muted, as browsers require)
```

## How it works

| File | Role |
|---|---|
| `api.py` | Talks to DR's TV API (`production-cdn.dr-massive.com`) and radio API (`api.dr.dk/radio/v4/channels`). No Home Assistant code, so it's easy to test on its own. |
| `coordinator.py` | A `DataUpdateCoordinator`: fetches the TV schedule every 5 minutes and TV channels and radio stations every 6 hours, keeps the last data on errors, and raises or clears the repair issue. |
| `websocket.py` | The `dr_tv/channels` websocket command the card uses: channels, now, next and stream URLs. |
| `frontend/dr-tv-card.js` | The card: plain JavaScript, no build step. It plays video with hls.js, or natively on Safari and iOS. |
| `frontend/hls.min.js` | [hls.js](https://github.com/video-dev/hls.js) 1.7.4 (Apache-2.0), bundled so nothing loads from a CDN. |
| `media_source.py` | The DR entry in the Media panel: DR TV (HLS video) and DR Radio (MP3), with P4 and P5 regions as folders. |
| `__init__.py` | Serves the card, registers it on all dashboards, and migrates old installs (removes the v0.1 media player). |
| `config_flow.py` | Lets you add the integration from the UI. |

DR's API is unofficial and undocumented. It needs no login, but it may change.

## Development

```bash
# Run a local Home Assistant with the integration mounted (http://localhost:8123)
docker compose up -d
docker compose restart          # after Python changes; card changes need only a browser reload

# Tests and lint (Home Assistant needs Python 3.13)
docker run --rm -v "$PWD":/src -w /src python:3.13 bash -c \
  "pip install -q -r requirements_test.txt ruff && pytest -q && ruff check . && ruff format --check ."
```
