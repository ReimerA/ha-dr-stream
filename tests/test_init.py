"""Tests for the DR TV integration."""

from __future__ import annotations

from homeassistant import config_entries
from homeassistant.components.media_player import BrowseError
from homeassistant.components.media_source import (
    Unresolvable,
    async_browse_media,
    async_resolve_media,
)
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.helpers import (
    device_registry as dr,
    entity_registry as er,
    issue_registry as ir,
)
from homeassistant.setup import async_setup_component
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.dr_tv.const import (
    API_BASE,
    DOMAIN,
    FAILURES_BEFORE_ISSUE,
    FALLBACK_CHANNELS,
    FALLBACK_RADIO,
    ISSUE_API_UNAVAILABLE,
    RADIO_API_URL,
)

from .conftest import channel_payload, radio_payload, schedule_payload


async def _setup(hass: HomeAssistant, version: int = 2) -> MockConfigEntry:
    entry = MockConfigEntry(
        domain=DOMAIN, title="DR TV", unique_id=DOMAIN, version=version
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry


async def _channels(hass: HomeAssistant, hass_ws_client) -> dict[str, dict]:
    client = await hass_ws_client(hass)
    await client.send_json_auto_id({"type": "dr_tv/channels"})
    msg = await client.receive_json()
    assert msg["success"], msg
    return {c["title"]: c for c in msg["result"]["channels"]}


async def test_config_flow(hass: HomeAssistant, mock_dr_api) -> None:
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {})
    assert result["type"] is FlowResultType.CREATE_ENTRY

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.ABORT


async def test_channels_websocket(
    hass: HomeAssistant, mock_dr_api, hass_ws_client
) -> None:
    await _setup(hass)
    channels = await _channels(hass, hass_ws_client)

    assert list(channels) == [c["title"] for c in FALLBACK_CHANNELS.values()]
    dr1 = channels["DR1"]
    assert dr1["stream_url"] == FALLBACK_CHANNELS["20875"]["stream_url"]
    assert dr1["now"]["title"] == "TV Avisen"
    assert dr1["next"]["title"] == "Aftenshowet"
    assert "Width=640&Height=360" in dr1["now"]["image"]
    assert "'" not in dr1["now"]["image"]
    assert channels["DR2"]["now"]["title"] == "Deadline"
    # No schedule for this channel in the canned data.
    assert channels["DR Ramasjang"]["now"] is None

    # The integration has no entities any more.
    assert hass.states.async_all() == []


async def test_channels_websocket_not_loaded(
    hass: HomeAssistant, hass_ws_client
) -> None:
    assert await async_setup_component(hass, DOMAIN, {})
    client = await hass_ws_client(hass)
    await client.send_json_auto_id({"type": "dr_tv/channels"})
    msg = await client.receive_json()
    assert not msg["success"]
    assert msg["error"]["code"] == "not_loaded"


async def test_card_is_served(hass: HomeAssistant, mock_dr_api, hass_client) -> None:
    await _setup(hass)
    client = await hass_client()
    for path in ("/dr_tv/dr-tv-card.js", "/dr_tv/hls.min.js"):
        resp = await client.get(path)
        assert resp.status == 200, path


async def test_dr_down_uses_fallback_and_raises_issue(
    hass: HomeAssistant, aioclient_mock, hass_ws_client
) -> None:
    for channel_id in FALLBACK_CHANNELS:
        aioclient_mock.get(f"{API_BASE}/items/{channel_id}", status=500)
    aioclient_mock.get(f"{API_BASE}/schedules", status=500)
    aioclient_mock.get(RADIO_API_URL, status=500)

    entry = await _setup(hass)
    coordinator = entry.runtime_data

    # Streams still work from the built-in channel list.
    channels = await _channels(hass, hass_ws_client)
    assert channels["DR1"]["stream_url"] == FALLBACK_CHANNELS["20875"]["stream_url"]
    assert channels["DR1"]["now"] is None

    issues = ir.async_get(hass)
    for _ in range(1, FAILURES_BEFORE_ISSUE):
        assert issues.async_get_issue(DOMAIN, ISSUE_API_UNAVAILABLE) is None
        await coordinator.async_refresh()
        await hass.async_block_till_done()
    assert issues.async_get_issue(DOMAIN, ISSUE_API_UNAVAILABLE) is not None

    # DR comes back: the issue goes away and programme info returns.
    aioclient_mock.clear_requests()
    for channel_id in FALLBACK_CHANNELS:
        aioclient_mock.get(
            f"{API_BASE}/items/{channel_id}", json=channel_payload(channel_id)
        )
    aioclient_mock.get(f"{API_BASE}/schedules", json=schedule_payload())
    aioclient_mock.get(RADIO_API_URL, json=radio_payload())
    await coordinator.async_refresh()
    await hass.async_block_till_done()
    assert issues.async_get_issue(DOMAIN, ISSUE_API_UNAVAILABLE) is None
    channels = await _channels(hass, hass_ws_client)
    assert channels["DR1"]["now"]["title"] == "TV Avisen"


async def test_migration_removes_old_media_player(
    hass: HomeAssistant, mock_dr_api
) -> None:
    entry = MockConfigEntry(domain=DOMAIN, title="DR TV", unique_id=DOMAIN, version=1)
    entry.add_to_hass(hass)
    dev_reg = dr.async_get(hass)
    device = dev_reg.async_get_or_create(
        config_entry_id=entry.entry_id, identifiers={(DOMAIN, entry.entry_id)}
    )
    ent_reg = er.async_get(hass)
    ent_reg.async_get_or_create(
        "media_player",
        DOMAIN,
        f"{entry.entry_id}_player",
        config_entry=entry,
        device_id=device.id,
    )

    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    assert entry.version == 2
    assert er.async_entries_for_config_entry(ent_reg, entry.entry_id) == []
    assert dev_reg.async_get(device.id) is None


async def test_media_source_root(hass: HomeAssistant, mock_dr_api) -> None:
    assert await async_setup_component(hass, "media_source", {})
    await _setup(hass)

    root = await async_browse_media(hass, f"media-source://{DOMAIN}")
    assert root.title == "DR"
    assert [c.title for c in root.children] == ["DR TV", "DR Radio"]


async def test_media_source_tv(hass: HomeAssistant, mock_dr_api) -> None:
    assert await async_setup_component(hass, "media_source", {})
    await _setup(hass)

    tv = await async_browse_media(hass, f"media-source://{DOMAIN}/tv")
    titles = [child.title for child in tv.children]
    assert "DR1: TV Avisen" in titles
    assert len(titles) == len(FALLBACK_CHANNELS)
    # Every tile has a picture, without quotes (they break the frontend's CSS).
    assert all(c.thumbnail and "'" not in c.thumbnail for c in tv.children)

    for media_id in ("tv/20876", "20876"):  # "20876" is the pre-radio form
        resolved = await async_resolve_media(
            hass, f"media-source://{DOMAIN}/{media_id}", None
        )
        assert resolved.url == FALLBACK_CHANNELS["20876"]["stream_url"]
        assert resolved.mime_type == "application/x-mpegURL"


async def test_media_source_radio(hass: HomeAssistant, mock_dr_api) -> None:
    assert await async_setup_component(hass, "media_source", {})
    await _setup(hass)

    radio = await async_browse_media(hass, f"media-source://{DOMAIN}/radio")
    # Sorted by DR's order; P4's regions are one folder; feeds without an
    # MP3 stream are left out.
    assert [(c.title, c.can_play, c.can_expand) for c in radio.children] == [
        ("P1", True, False),
        ("P4", False, True),
    ]
    p1 = radio.children[0]
    assert p1.thumbnail == "https://asset.dr.dk/drlyd/images/urn:dr:radio:image:p1"

    p4 = await async_browse_media(hass, f"media-source://{DOMAIN}/radio/group/p4")
    assert [c.title for c in p4.children] == ["P4 Fyn", "P4 København"]
    # A region without its own image uses P4's.
    assert p4.children[0].thumbnail.endswith("urn:dr:radio:image:p4")
    assert p4.children[1].thumbnail.endswith("urn:dr:radio:image:p4kbh")

    resolved = await async_resolve_media(
        hass, f"media-source://{DOMAIN}/radio/p4fyn", None
    )
    # The highest-bitrate MP3 stream.
    assert resolved.url == "https://live-icy.dr.dk/A/A07H.mp3"
    assert resolved.mime_type == "audio/mpeg"


async def test_media_source_radio_fallback(hass: HomeAssistant, mock_dr_api) -> None:
    mock_dr_api.clear_requests()
    for channel_id in FALLBACK_CHANNELS:
        mock_dr_api.get(
            f"{API_BASE}/items/{channel_id}", json=channel_payload(channel_id)
        )
    mock_dr_api.get(f"{API_BASE}/schedules", json=schedule_payload())
    mock_dr_api.get(RADIO_API_URL, status=500)
    assert await async_setup_component(hass, "media_source", {})
    await _setup(hass)

    radio = await async_browse_media(hass, f"media-source://{DOMAIN}/radio")
    titles = [c.title for c in radio.children]
    assert titles[:5] == ["LYD ekstra", "LYD ekstra 2", "P1", "P2", "P3"]
    assert "P4" in titles and "P5" in titles
    resolved = await async_resolve_media(
        hass, f"media-source://{DOMAIN}/radio/p1", None
    )
    assert resolved.url == next(r[2] for r in FALLBACK_RADIO if r[0] == "p1")


async def test_media_source_unknown(hass: HomeAssistant, mock_dr_api) -> None:
    assert await async_setup_component(hass, "media_source", {})
    await _setup(hass)
    for media_id in ("radio/nope", "tv/nope", "radio/group/p4"):
        with pytest.raises(Unresolvable):
            await async_resolve_media(hass, f"media-source://{DOMAIN}/{media_id}", None)
    with pytest.raises(BrowseError):
        await async_browse_media(hass, f"media-source://{DOMAIN}/radio/group/nope")
