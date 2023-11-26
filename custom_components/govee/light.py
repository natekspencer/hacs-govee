"""Govee platform."""
from __future__ import annotations

import logging

from govee_api_laggat import Govee
from homeassistant.components.light import (
    SUPPORT_BRIGHTNESS,
    SUPPORT_COLOR,
    SUPPORT_COLOR_TEMP,
    LightEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util import color

from .const import COLOR_TEMP_KELVIN_MAX, COLOR_TEMP_KELVIN_MIN, DOMAIN
from .entity import GoveeEntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up the Govee Light platform."""
    _LOGGER.debug("Setting up Govee lights")
    hub: Govee = hass.data[DOMAIN]["hub"]
    async_add_entities(
        [
            GoveeLightEntity(hub, entry.title, device, entry)
            for device in hub.devices
            if device.support_brightness
        ],
        update_before_add=True,
    )


class GoveeLightEntity(GoveeEntity, LightEntity):
    """Representation of a stateful light entity."""

    @property
    def supported_features(self) -> int:
        """Flag supported features."""
        support_flags = 0
        if self._device.support_brightness:
            support_flags |= SUPPORT_BRIGHTNESS
        if self._device.support_color:
            support_flags |= SUPPORT_COLOR
        if self._device.support_color_tem:
            support_flags |= SUPPORT_COLOR_TEMP
        return support_flags

    @property
    def hs_color(self) -> tuple[float, float]:
        """Return the hs color value."""
        return color.color_RGB_to_hs(
            self._device.color[0],
            self._device.color[1],
            self._device.color[2],
        )

    @property
    def rgb_color(self) -> tuple[int, int, int]:
        """Return the rgb color value."""
        return [
            self._device.color[0],
            self._device.color[1],
            self._device.color[2],
        ]

    @property
    def brightness(self) -> int:
        """Return the brightness value."""
        # govee is reporting 0 to 254 - home assistant uses 1 to 255
        return self._device.brightness + 1

    @property
    def color_temp(self) -> int | None:
        """Return the color_temp of the light."""
        if not self._device.color_temp:
            return None
        return color.color_temperature_kelvin_to_mired(self._device.color_temp)

    @property
    def min_mireds(self) -> int:
        """Return the coldest color_temp that this light supports."""
        return color.color_temperature_kelvin_to_mired(COLOR_TEMP_KELVIN_MAX)

    @property
    def max_mireds(self) -> int:
        """Return the warmest color_temp that this light supports."""
        return color.color_temperature_kelvin_to_mired(COLOR_TEMP_KELVIN_MIN)
