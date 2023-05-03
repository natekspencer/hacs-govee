"""The Govee integration."""
import logging

from govee_api_laggat import Govee
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_API_KEY, Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import PlatformNotReady
import voluptuous as vol

from .const import DOMAIN
from .learning_storage import GoveeLearningStorage

_LOGGER = logging.getLogger(__name__)
CONFIG_SCHEMA = vol.Schema({DOMAIN: vol.Schema({})}, extra=vol.ALLOW_EXTRA)

# supported platforms
PLATFORMS = [Platform.LIGHT, Platform.SWITCH]


def is_online(online: bool) -> None:
    """Log online/offline change."""
    msg = "API is offline."
    if online:
        msg = "API is back online."
    _LOGGER.warning(msg)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Govee from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    # get vars from ConfigFlow/OptionsFlow
    config = entry.data
    options = entry.options
    api_key = options.get(CONF_API_KEY, config.get(CONF_API_KEY, ""))

    # Setup connection with devices/cloud
    hub = await Govee.create(
        api_key, learning_storage=GoveeLearningStorage(hass.config.config_dir)
    )
    # keep reference for disposing
    hass.data[DOMAIN]["hub"] = hub

    # inform when api is offline/online
    hub.events.online += is_online

    # Verify that passed in configuration works
    _, err = await hub.get_devices()
    if err:
        _LOGGER.warning("Could not connect to Govee API: %s", err)
        await hub.rate_limit_delay()
        await async_unload_entry(hass, entry)
        raise PlatformNotReady()

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if unload_ok:
        hub = hass.data[DOMAIN].pop("hub")
        await hub.close()

    return unload_ok
