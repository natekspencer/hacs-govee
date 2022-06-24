"""Govee switch."""
import logging

from govee_api_laggat import Govee

from homeassistant.components.switch import SwitchDeviceClass, SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .entity import GoveeEntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up the Govee switch platform."""
    _LOGGER.debug("Setting up Govee switches")
    hub: Govee = hass.data[DOMAIN]["hub"]
    async_add_entities(
        [
            GoveeSwitchEntity(hub, entry.title, device, entry)
            for device in hub.devices
            if device.support_turn and not device.support_brightness
        ],
        update_before_add=True,
    )


class GoveeSwitchEntity(GoveeEntity, SwitchEntity):
    """Representation of a stateful switch entity."""

    _attr_device_class = SwitchDeviceClass.OUTLET
