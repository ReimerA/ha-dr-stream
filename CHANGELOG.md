# Changelog

All notable changes to this project are documented here.
Versions follow [Semantic Versioning](https://semver.org/): MAJOR.MINOR.PATCH.

## [Unreleased]

### Changed
- Reverted 0.5.1's radio fix, which did not work. DR's radio API now asks for
  an API key on some of its servers and rejects many requests, whatever the
  client. When that happens the built-in station list is used, so radio keeps
  playing.

## [0.5.1] - 2026-11-23

### Fixed
- Radio stations, logos and P4/P5 regions load from DR again. DR's radio API
  started rejecting Home Assistant's requests, so only the built-in station
  list was shown.
- Updated the built-in stream addresses for DR Ramasjang and DRTV Ekstra,
  which DR has moved.

## [0.5.0] - 2026-11-18

### Changed (breaking)
- The integration's internal name is now `dr` instead of `dr_tv`, because it
  covers radio too. Home Assistant sees it as a new integration: delete DR TV
  & Radio, remove and re-download it in HACS, restart and add it again. See "Upgrading from 0.4.x" in
  the README.
- Media links are now `media-source://dr/tv/dr1` and
  `media-source://dr/radio/p1`. TV channels use readable names (`dr1`, `dr2`,
  `ramasjang`, `tva`, `drtv-ekstra`) instead of DR's numbers, and the old
  `media-source://dr_tv/...` forms no longer work.
- The card's `channel:` option also accepts these names (`channel: dr1`).

## [0.4.2] - 2026-11-18

### Changed
- The DR TV and DR Radio folders in the Media panel show DR's "DR TV" and
  "DR LYD" logos instead of a plain folder.

## [0.4.1] - 2026-11-18

### Added
- The DR logo for the integration, shown in Settings → Integrations, the
  Media panel and HACS/Marketplace (Home Assistant 2026.3 or newer).

## [0.4.0] - 2026-11-18

First public release, installable through HACS as a custom repository.
It includes everything from the earlier, unpublished versions (see
CHANGELOG.md): DR TV and DR Radio in the Media panel, and the DR TV
dashboard card (`custom:dr-tv-card`).

### Added
- Apache-2.0 license.
- GitHub Actions: tests and lint, Home Assistant (hassfest) and HACS
  validation, tagged releases, and a daily check of DR's live API.
- Integration categories (TV streaming, music & radio services) in the
  manifest.

## [0.3.0]

### Added
- DR Radio in the Media panel: P1, P2, P3, P6, P8, LYD ekstra and the
  regional P4 and P5 stations (as folders), playing as MP3.

### Changed
- The Media panel entry is now "DR", with "DR TV" and "DR Radio" folders.
  TV links of the form `media-source://dr_tv/<channel id>` keep working.
- The integration is now called "DR TV & Radio".

## [0.2.0]

### Added
- The DR TV dashboard card: channel tiles with what's on now; tap one to
  play the live channel inside the card.

### Removed
- The `media_player.dr_tv` entity. It had no real on/off state. Existing
  installs are migrated automatically and the entity is removed.

## [0.1.0]

### Added
- First version: DR TV channels in the Media panel and a media player entity.
