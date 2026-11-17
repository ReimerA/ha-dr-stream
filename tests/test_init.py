"""Tests for the DR TV integration."""

from __future__ import annotations

from homeassistant import config_entries
from homeassistant.components.media_player import (
    ATTR_INPUT_SOURCE,
    ATTR_INPUT_SOURCE_LIST,
    ATTR_MEDIA_TITLE,
    DOMAIN as MP_DOMAIN,
    SERVICE_SELECT_SOURCE,
)
from homeassistant.components.media_source import (
    async_browse_media,
    async_resolve_media,
)
from homeassistant.const import ATTR_ENTITY_ID, STATE_OFF, STATE_PLAYING
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.helpers import issue_registry as ir
from homeassistant.setup import async_setup_component
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.dr_tv.const import (
    API_BASE,
    DOMAIN,
    FAILURES_BEFORE_ISSUE,
    FALLBACK_CHANNELS,
    ISSUE_API_UNAVAILABLE,
)

from .conftest import channel_payload, schedule_payload

ENTITY_ID = "media_player.dr_tv"


async def _setup(hass: HomeAssistant) -> MockConfigEntry:
    entry = MockConfigEntry(domain=DOMAIN, title="DR TV", unique_id=DOMAIN)
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry


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


async def test_media_player(hass: HomeAssistant, mock_dr_api) -> None:
    await _setup(hass)

    state = hass.states.get(ENTITY_ID)
    assert state.state == STATE_PLAYING
    assert state.attributes[ATTR_INPUT_SOURCE] == "DR1"
    assert state.attributes[ATTR_INPUT_SOURCE_LIST] == [
        c["title"] for c in FALLBACK_CHANNELS.values()
    ]
    assert state.attributes[ATTR_MEDIA_TITLE] == "TV Avisen"
    assert state.attributes["next_title"] == "Aftenshowet"
    assert state.attributes["stream_url"] == FALLBACK_CHANNELS["20875"]["stream_url"]
    assert "Width=640&Height=360" in state.attributes["entity_picture"]

    await hass.services.async_call(
        MP_DOMAIN,
        SERVICE_SELECT_SOURCE,
        {ATTR_ENTITY_ID: ENTITY_ID, ATTR_INPUT_SOURCE: "DR2"},
        blocking=True,
    )
    state = hass.states.get(ENTITY_ID)
    assert state.attributes[ATTR_INPUT_SOURCE] == "DR2"
    assert state.attributes[ATTR_MEDIA_TITLE] == "Deadline"

    await hass.services.async_call(
        MP_DOMAIN, "turn_off", {ATTR_ENTITY_ID: ENTITY_ID}, blocking=True
    )
    assert hass.states.get(ENTITY_ID).state == STATE_OFF


async def test_dr_down_uses_fallback_and_raises_issue(
    hass: HomeAssistant, aioclient_mock
) -> None:
    for channel_id in FALLBACK_CHANNELS:
        aioclient_mock.get(f"{API_BASE}/items/{channel_id}", status=500)
    aioclient_mock.get(f"{API_BASE}/schedules", status=500)

    entry = await _setup(hass)
    coordinator = entry.runtime_data

    state = hass.states.get(ENTITY_ID)
    assert state.state == STATE_PLAYING
    assert state.attributes[ATTR_INPUT_SOURCE] == "DR1"
    assert state.attributes[ATTR_MEDIA_TITLE] == "DR1"
    assert state.attributes["stream_url"] == FALLBACK_CHANNELS["20875"]["stream_url"]

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
    await coordinator.async_refresh()
    await hass.async_block_till_done()
    assert issues.async_get_issue(DOMAIN, ISSUE_API_UNAVAILABLE) is None
    assert hass.states.get(ENTITY_ID).attributes[ATTR_MEDIA_TITLE] == "TV Avisen"


async def test_media_source(hass: HomeAssistant, mock_dr_api) -> None:
    assert await async_setup_component(hass, "media_source", {})
    await _setup(hass)

    root = await async_browse_media(hass, f"media-source://{DOMAIN}")
    titles = [child.title for child in root.children]
    assert "DR1: TV Avisen" in titles
    assert len(titles) == len(FALLBACK_CHANNELS)
    # Every tile has a picture, without quotes (they break the frontend's CSS).
    assert all(c.thumbnail and "'" not in c.thumbnail for c in root.children)

    resolved = await async_resolve_media(hass, f"media-source://{DOMAIN}/20876", None)
    assert resolved.url == FALLBACK_CHANNELS["20876"]["stream_url"]
    assert resolved.mime_type == "application/x-mpegURL"
