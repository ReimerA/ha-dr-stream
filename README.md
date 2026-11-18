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
[![Open in HACS](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=ReimerA&repository=ha-dr-stream&category=integration)

Or by hand:
1. HACS → ⋮ → Custom repositories → add `https://github.com/ReimerA/ha-dr-stream`, type *Integration*.
2. Install **DR TV & Radio** and restart Home Assistant.

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

# Home Assistant's validator (the same check CI runs)
docker run --rm -v "$PWD":/github/workspace ghcr.io/home-assistant/hassfest

# Check that DR's real API still matches what the integration expects
python scripts/check_dr_api.py
```

GitHub Actions runs on every push and pull request:

| Workflow | What it does |
|---|---|
| `tests.yml` | ruff lint and format check, pytest with at least 95% coverage |
| `validate.yml` | hassfest (Home Assistant's checker) and the HACS validator; also weekly |
| `dr-api.yml` | Daily call to DR's real API, so changes on DR's side are noticed |
| `release.yml` | Publishes a GitHub release when a version tag is pushed |

## Releasing

HACS offers new versions to users from GitHub releases.

1. Move the items under `[Unreleased]` in `CHANGELOG.md` into a new
   `## [x.y.z]` section.
2. Set the same `"version": "x.y.z"` in `custom_components/dr_tv/manifest.json`.
3. Commit, then tag and push: `git tag vx.y.z && git push origin main vx.y.z`.

The release workflow runs all checks, verifies that the tag, manifest and
changelog agree, and creates the GitHub release with the changelog section as
release notes.

Versions follow [Semantic Versioning](https://semver.org/): bump the patch
number (0.3.1) for fixes, the minor number (0.4.0) for new features, and the
major number for changes that require users to do something.

## License

Apache License 2.0; see [LICENSE](LICENSE). The bundled hls.js is also
Apache-2.0 ([its license](custom_components/dr_tv/frontend/hls.js-LICENSE)).

This project is not affiliated with or endorsed by DR. The DR logo in
`custom_components/dr_tv/brand/` is DR's trademark and is used only to
identify the service; it is not covered by this project's license.
