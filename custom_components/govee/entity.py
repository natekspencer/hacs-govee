"""Govee entity."""
from __future__ import annotations

from datetime import datetime, timedelta
import logging
from typing import Any

from govee_api_laggat import Govee, GoveeDevice, GoveeError, GoveeSource

from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    ATTR_COLOR_TEMP,
    ATTR_HS_COLOR,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_DELAY
from homeassistant.helpers.entity import DeviceInfo, Entity
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.helpers.update_coordinator import UpdateFailed
from homeassistant.util import color

from .const import (
    COLOR_TEMP_KELVIN_MAX,
    COLOR_TEMP_KELVIN_MIN,
    CONF_USE_ASSUMED_STATE,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)

DEFAULT_DELAY = 10
DEFAULT_USE_ASSUMED_STATE = True


class GoveeEntity(Entity):
    """Representation of a stateful entity."""

    _attr_should_poll = False

    def __init__(
        self, hub: Govee, title: str, device: GoveeDevice, entry: ConfigEntry
    ) -> None:
        """Init a Govee entity."""
        self._hub = hub
        self._title = title
        self._device = device
        self._use_assumed_state = entry.options.get(
            CONF_USE_ASSUMED_STATE, DEFAULT_USE_ASSUMED_STATE
        )
        self._delay = timedelta(
            seconds=entry.options.get(
                CONF_DELAY, entry.data.get(CONF_DELAY, DEFAULT_DELAY)
            )
        )

    async def async_update(self, _: datetime | None = None) -> None:
        """Fetch data."""
        _LOGGER.debug("async_update")
        hub: Govee = self.hass.data[DOMAIN]["hub"]
        try:
            await hub._api._get_device_state(self._device)
            if _ is not None:
                self.async_write_ha_state()
            if self._device.error:
                _LOGGER.warning(
                    "Update failed for %s: %s", self._device.device, self._device.error
                )
        except GoveeError as ex:
            raise UpdateFailed(f"Exception on getting states: {ex}") from ex

    async def async_added_to_hass(self) -> None:
        """Run when entity about to be added to hass."""
        self.async_on_remove(
            async_track_time_interval(self.hass, self.async_update, self._delay)
        )

    async def async_turn_off(self, **kwargs: dict[str, Any]) -> None:
        """Turn device off."""
        _LOGGER.debug("async_turn_off for Govee device %s", self._device.device)
        await self._hub.turn_off(self._device)
        self.async_write_ha_state()

    async def async_turn_on(self, **kwargs: dict[str, Any]) -> None:
        """Turn device on."""
        _LOGGER.debug(
            "async_turn_on for Govee device %s, kwargs: %s", self._device.device, kwargs
        )
        err = None

        just_turn_on = True
        if ATTR_HS_COLOR in kwargs:
            hs_color = kwargs.pop(ATTR_HS_COLOR)
            just_turn_on = False
            col = color.color_hs_to_RGB(hs_color[0], hs_color[1])
            _, err = await self._hub.set_color(self._device, col)
        if ATTR_BRIGHTNESS in kwargs:
            brightness = kwargs.pop(ATTR_BRIGHTNESS)
            just_turn_on = False
            bright_set = brightness - 1
            _, err = await self._hub.set_brightness(self._device, bright_set)
        if ATTR_COLOR_TEMP in kwargs:
            color_temp = kwargs.pop(ATTR_COLOR_TEMP)
            just_turn_on = False
            color_temp_kelvin = color.color_temperature_mired_to_kelvin(color_temp)
            if color_temp_kelvin > COLOR_TEMP_KELVIN_MAX:
                color_temp_kelvin = COLOR_TEMP_KELVIN_MAX
            elif color_temp_kelvin < COLOR_TEMP_KELVIN_MIN:
                color_temp_kelvin = COLOR_TEMP_KELVIN_MIN
            _, err = await self._hub.set_color_temp(self._device, color_temp_kelvin)

        # if there is no known specific command - turn on
        if just_turn_on:
            _, err = await self._hub.turn_on(self._device)
        self.async_write_ha_state()
        # debug log unknown commands
        if kwargs:
            _LOGGER.debug(
                "async_turn_on doesnt know how to handle kwargs: %s", repr(kwargs)
            )
        # warn on any error
        if err:
            _LOGGER.warning(
                "Govee async_turn_on failed with '%s' for %s, kwargs: %s",
                err,
                self._device.device,
                kwargs,
            )

    @property
    def unique_id(self) -> str:
        """Return the unique ID."""
        return f"govee_{self._title}_{self._device.device}"

    @property
    def device_id(self) -> str:
        """Return the ID."""
        return self.unique_id

    @property
    def name(self) -> str:
        """Return the name."""
        return self._device.device_name

    @property
    def device_info(self) -> DeviceInfo:
        """Return the device info."""
        return DeviceInfo(
            identifiers={(DOMAIN, self.device_id)},
            name=self.name,
            manufacturer="Govee",
            model=self._device.model,
            via_device=(DOMAIN, "Govee API (cloud)"),
        )

    @property
    def is_on(self) -> bool:
        """Return true if device is on."""
        return self._device.power_state

    @property
    def assumed_state(self) -> bool:
        """
        Return true if the state is assumed.

        This can be disabled in options.
        """
        return self._use_assumed_state and self._device.source == GoveeSource.HISTORY

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return self._device.online

    ## These don't work right now
    # @property
    # def extra_state_attributes(self) -> dict[str, Any]:
    #     """Return the device state attributes."""
    #     return {
    #         # rate limiting information on Govee API
    #         "rate_limit_total": self._hub.rate_limit_total,
    #         "rate_limit_remaining": self._hub.rate_limit_remaining,
    #         "rate_limit_reset_seconds": round(self._hub.rate_limit_reset_seconds, 2),
    #         "rate_limit_reset": datetime.fromtimestamp(
    #             self._hub.rate_limit_reset
    #         ).isoformat(),
    #         "rate_limit_on": self._hub.rate_limit_on,
    #     }
