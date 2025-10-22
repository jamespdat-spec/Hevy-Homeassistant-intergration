from __future__ import annotations
import logging
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN, CONF_API_KEY, CONF_EMAIL, CONF_PASSWORD, CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL_MIN
from .hevy_api import HevyClient, HevyAuth

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[str] = ["sensor"]

class HevyCoordinator(DataUpdateCoordinator):
    def __init__(self, hass: HomeAssistant, client: HevyClient, update_minutes: int) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name="Hevy Coordinator",
            update_interval=timedelta(minutes=update_minutes),
        )
        self.client = client
        self.data = {}

    async def _async_update_data(self):
        try:
            account = await self.client.get_account()
            count = await self.client.get_workout_count()
            latest = await self.client.latest_workout_summary()
            weekly = await self.client.weekly_volume()

            self.data = {
                "account": account,
                "workout_count": count,
                "latest": latest,
                "weekly_volume": weekly,
            }
            return self.data
        except Exception as err:
            raise UpdateFailed(str(err)) from err

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    session = async_get_clientsession(hass)
    auth = HevyAuth(
        api_key=entry.data[CONF_API_KEY],
        email_or_username=entry.data[CONF_EMAIL],
        password=entry.data[CONF_PASSWORD],
    )
    client = HevyClient(session, auth)

    update_minutes = entry.options.get(CONF_UPDATE_INTERVAL, entry.data.get(CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL_MIN))
    coordinator = HevyCoordinator(hass, client, update_minutes)

    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    async def _handle_refresh(call):
        await coordinator.async_request_refresh()

    hass.services.async_register(DOMAIN, "refresh", _handle_refresh)

    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)
    return unload_ok
