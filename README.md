# DR TV for Home Assistant

A custom integration that brings DR's live TV channels (DR1, DR2, DR Ramasjang,
TVA Live, DRTV Ekstra) into Home Assistant without scripts, helpers or YAML.

## What you get

- **`media_player.dr_tv`**: one entity for all channels.
  - The channels are its **sources**. Switch channel with the standard
    `media_player.select_source` action or from any media card.
  - `media_title`, the picture and the progress bar show the programme that's
    on air now, and update by themselves when the programme changes.
  - Attributes: `stream_url` (HLS), `stream_url_subtitles`, `description`,
    `next_title` and `next_start`.
- **DR TV in the Media panel**: browse the channels and play them in the
  browser or on any player that supports HLS (Chromecast, many smart TVs).
- **Resilience**: if DR's API is down, the last known data or the built-in
  channel list is kept, so streams keep working. After repeated failures a
  repair notice appears under Settings → Repairs, and it clears by itself.

## Install

### HACS (custom repository)
1. HACS → ⋮ → Custom repositories → add this repo's URL, type *Integration*.
2. Install **DR TV** and restart Home Assistant.

### Manual
Copy `custom_components/dr_tv` into your Home Assistant `config/custom_components/`
and restart.

Then go to **Settings → Devices & services → Add integration → DR TV**.
There's nothing to configure.

## Dashboard example

```yaml
type: media-control
entity: media_player.dr_tv
```

## How it works

| File | Role |
|---|---|
| `api.py` | Talks to DR's API (`production-cdn.dr-massive.com`). No Home Assistant code, so it's easy to test on its own. |
| `coordinator.py` | A `DataUpdateCoordinator`: fetches the schedule every 5 minutes and channel info every 6 hours, keeps the last data on errors, and raises or clears the repair issue. |
| `media_player.py` | The entity. It reads from the coordinator and adds no polling of its own. |
| `media_source.py` | Lists the channels in the Media panel and resolves them to HLS streams. |
| `config_flow.py` | Lets you add the integration from the UI. |

DR's API is unofficial and undocumented. It needs no login, but it may change.

## Development

```bash
# Run a local Home Assistant with the integration mounted (http://localhost:8123)
docker compose up -d
docker compose restart          # after code changes

# Tests and lint (Home Assistant needs Python 3.13)
docker run --rm -v "$PWD":/src -w /src python:3.13 bash -c \
  "pip install -q -r requirements_test.txt ruff && pytest -q && ruff check . && ruff format --check ."
```
