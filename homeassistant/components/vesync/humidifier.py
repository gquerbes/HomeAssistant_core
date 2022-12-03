"""Support for VeSync humidifiers."""
from __future__ import annotations

import json
import logging

from homeassistant.components.humidifier import (
    HumidifierDeviceClass,
    HumidifierEntity,
    HumidifierEntityFeature,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .common import VeSyncDevice
from .const import DOMAIN, SKU_TO_BASE_DEVICE, VS_DISCOVERY, VS_HUMIDIFIERS

_LOGGER = logging.getLogger(__name__)

DEV_TYPE_TO_HA = {
    "Classic300S": "humidifier",
    "Classic200S": "humidifier",
}


FAN_MODE_AUTO = "auto"
FAN_MODE_SLEEP = "sleep"
FAN_MODE_MANUAL = "manual"

MAX_HUMIDITY = 100
MIN_HUMIDITY = 0

MAX_FAN_SPEED = 9
MIN_FAN_SPEED = 0


PRESET_MODES = {
    "Classic300S": [FAN_MODE_AUTO, FAN_MODE_MANUAL, FAN_MODE_SLEEP],
}


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the VeSync fan platform."""

    @callback
    def discover(devices):
        """Add new devices to platform."""
        _setup_entities(devices, async_add_entities)

    config_entry.async_on_unload(
        async_dispatcher_connect(hass, VS_DISCOVERY.format(VS_HUMIDIFIERS), discover)
    )

    _setup_entities(hass.data[DOMAIN][VS_HUMIDIFIERS], async_add_entities)


@callback
def _setup_entities(devices, async_add_entities):
    """Check if device is online and add entity."""
    entities = []
    for dev in devices:
        if DEV_TYPE_TO_HA.get(SKU_TO_BASE_DEVICE.get(dev.device_type)) == "humidifier":
            entities.append(VeSyncHumidifierHA(dev))
        else:
            _LOGGER.warning(
                "%s - Unknown device type - %s", dev.device_name, dev.device_type
            )
            continue

    async_add_entities(entities, update_before_add=True)


class VeSyncHumidifierHA(VeSyncDevice, HumidifierEntity):
    """Representation of a VeSync humidifer."""

    _attr_device_class = HumidifierDeviceClass.HUMIDIFIER
    _attr_supported_features = HumidifierEntityFeature.MODES
    last_known_fan_speed = 1
    last_known_mode = ""

    def __init__(self, humidifier):
        """Initialize the VeSync humidity device."""
        super().__init__(humidifier)
        self.smarthumidifier = humidifier

    @property
    def unique_info(self):
        """Return the ID of this fan."""
        return self.smarthumidifier.uuid

    @property
    def target_humidity(self) -> int:
        """Return the desired humidity set point."""
        if self.last_known_mode == FAN_MODE_MANUAL:
            return self.last_known_fan_speed
        return int(self.smarthumidifier.auto_humidity)

    @property
    def max_humidity(self) -> int:
        """Return the MAX humidity of this fan."""
        if self.last_known_mode == FAN_MODE_MANUAL:
            return MAX_FAN_SPEED
        return MAX_HUMIDITY

    @property
    def min_humidity(self) -> int:
        """Return the MIN humidity of this fan."""
        if self.last_known_mode == FAN_MODE_MANUAL:
            return MIN_FAN_SPEED
        return MIN_HUMIDITY

    @property
    def mode(self) -> str | None:
        """Return the mode of this fan."""
        if self.smarthumidifier.auto_enabled:
            return FAN_MODE_AUTO

        return self.last_known_mode

    @property
    def available_modes(self) -> list[str] | None:
        """Return the list of available modes."""
        return [FAN_MODE_MANUAL, FAN_MODE_AUTO, FAN_MODE_SLEEP]

    @property
    def device_class(self) -> str | None:
        """Return the device class of this fan."""
        return "DEVICE_CLASS_HUMIDIFIER"

    @property
    def preset_modes(self) -> list[str]:
        """Get the list of available preset modes."""
        return PRESET_MODES[SKU_TO_BASE_DEVICE[self.device.device_type]]

    def set_humidity(self, humidity: int) -> None:
        """Set new target humidity."""
        if not self.smarthumidifier.is_on:
            self.smarthumidifier.turn_on()

        if self.last_known_mode in (FAN_MODE_AUTO, FAN_MODE_SLEEP):
            self.smarthumidifier.set_humidity(humidity)
        else:
            self.smarthumidifier.set_mist_level(humidity)
            self.last_known_fan_speed = humidity

        self.schedule_update_ha_state()

    def set_mode(self, mode: str) -> None:
        """Set the preset mode of device."""
        if mode not in self.preset_modes:
            raise ValueError(
                f"{mode} is not one of the valid preset modes: " f"{self.preset_modes}"
            )

        if not self.smarthumidifier.is_on:
            self.smarthumidifier.turn_on()

        if mode == FAN_MODE_AUTO:
            self.smarthumidifier.set_auto_mode()
        if mode == FAN_MODE_MANUAL:
            self.smarthumidifier.set_manual_mode()
        elif mode == FAN_MODE_SLEEP:
            self.smarthumidifier.set_humidity_mode("sleep")

        # RECORD THE LAST KNOWN MODE
        self.last_known_mode = mode

        self.schedule_update_ha_state()

    def get_latest_info(self) -> None:
        """Get the latest info from the device."""
        display_info = json.loads(self.smarthumidifier.displayJSON())
        self.last_known_mode = display_info.get("Mode")
        self.last_known_fan_speed = int(display_info["Mist Virtual Level"])

    def update(self) -> None:
        """Update information from device."""
        super().update()
        self.get_latest_info()
