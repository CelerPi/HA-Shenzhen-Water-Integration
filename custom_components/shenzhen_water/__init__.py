from __future__ import annotations

from datetime import timedelta
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import ShenzhenWaterApiClient, ShenzhenWaterApiError
from .const import (
    CONF_BASE_URL,
    CONF_CHANNEL,
    CONF_CUSTOMER_CODES,
    CONF_GUID,
    CONF_MOBILE,
    CONF_TENANT_ID,
    CONF_TOKEN,
    DATA_COORDINATOR,
    DEFAULT_BASE_URL,
    DEFAULT_CHANNEL,
    DEFAULT_TENANT_ID,
    DOMAIN,
)

PLATFORMS = [Platform.SENSOR]
_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    session = async_get_clientsession(hass)
    client = ShenzhenWaterApiClient(
        session,
        base_url=entry.data.get(CONF_BASE_URL, DEFAULT_BASE_URL),
        mobile=entry.data[CONF_MOBILE],
        customer_codes=list(entry.data[CONF_CUSTOMER_CODES]),
        tenant_id=entry.data.get(CONF_TENANT_ID, DEFAULT_TENANT_ID),
        channel=entry.data.get(CONF_CHANNEL, DEFAULT_CHANNEL),
        token=entry.data.get(CONF_TOKEN),
        guid=entry.data.get(CONF_GUID),
    )

    async def async_update_data():
        try:
            return await client.async_fetch()
        except ShenzhenWaterApiError as err:
            raise UpdateFailed(str(err)) from err

    coordinator = DataUpdateCoordinator(
        hass,
        _LOGGER,
        name=DOMAIN,
        update_method=async_update_data,
        update_interval=timedelta(hours=12),
    )
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = {DATA_COORDINATOR: coordinator}
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok
