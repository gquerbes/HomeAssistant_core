"""Support for binary sensors for VeSync devices."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
import json
import logging

from pyvesync.vesyncfan import VeSyncAirBypass, VeSyncHumid200300S
from pyvesync.vesyncoutlet import VeSyncOutlet
from pyvesync.vesyncswitch import VeSyncSwitch

from homeassistant.components.binary_sensor import (
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .common import VeSyncBaseEntity
from .const import DOMAIN, SKU_TO_BASE_DEVICE, VS_BINARY_SENSORS, VS_DISCOVERY

_LOGGER = logging.getLogger(__name__)


@dataclass
class VeSyncBinarySensorEntityDescription(BinarySensorEntityDescription):
    """Describe VeSync sensor entity."""

    exists_fn: Callable[
        [VeSyncAirBypass | VeSyncOutlet | VeSyncSwitch | VeSyncHumid200300S], bool
    ] = lambda _: True


def sku_supported(device, supported):
    """Get the base device of which a device is an instance."""
    return SKU_TO_BASE_DEVICE.get(device.device_type) in supported


WATER_TANK_REMOVED = "Water Tank Removed"
WATER_TANK_EMPTY = "Water Tank Empty"
TANK_LIFTED_SUPPORTED = ["Classic300S", "Classic200S", "Dual200S"]
TANK_EMPTY_SUPPORTED = ["Classic300S", "Classic200S", "Dual200S"]


SENSORS: tuple[VeSyncBinarySensorEntityDescription, ...] = (
    VeSyncBinarySensorEntityDescription(
        key="water-tank-removed",
        name=WATER_TANK_REMOVED,
        exists_fn=lambda device: sku_supported(device, TANK_LIFTED_SUPPORTED),
    ),
    VeSyncBinarySensorEntityDescription(
        key="water-tank-empty",
        name=WATER_TANK_EMPTY,
        exists_fn=lambda device: sku_supported(device, TANK_EMPTY_SUPPORTED),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up devices."""

    @callback
    def discover(devices):
        """Add new devices to platform."""
        _setup_entities(devices, async_add_entities)

    config_entry.async_on_unload(
        async_dispatcher_connect(hass, VS_DISCOVERY.format(VS_BINARY_SENSORS), discover)
    )

    _setup_entities(hass.data[DOMAIN][VS_BINARY_SENSORS], async_add_entities)


@callback
def _setup_entities(devices, async_add_entities):
    """Check if device is online and add entity."""
    entities = []
    for dev in devices:
        for description in SENSORS:
            if description.exists_fn(dev):
                entities.append(VeSyncSensorEntity(dev, description))
    async_add_entities(entities, update_before_add=True)


class VeSyncSensorEntity(VeSyncBaseEntity, BinarySensorEntity):
    """Representation of a sensor describing a VeSync device."""

    entity_description: VeSyncBinarySensorEntityDescription

    def __init__(
        self,
        device: VeSyncAirBypass | VeSyncOutlet | VeSyncSwitch | VeSyncHumid200300S,
        description: VeSyncBinarySensorEntityDescription,
    ) -> None:
        """Initialize the VeSync device."""
        super().__init__(device)
        self.entity_description = description
        self._attr_name = f"{super().name} {description.name}"
        self._attr_unique_id = f"{super().unique_id}-{description.key}"

    is_tank_removed = True
    is_tank_empty = True

    @property
    def is_on(self) -> bool | None:
        """Get value of if on."""
        item_name = str(self.name)
        if WATER_TANK_REMOVED in item_name:
            return self.is_tank_removed
        if WATER_TANK_EMPTY in item_name:
            return self.is_tank_empty
        return True

    def update(self) -> None:
        """Update values of sensor."""
        info = json.loads(self.device.displayJSON())
        self.is_tank_removed = info.get("Water Tank Lifted")
        self.is_tank_empty = info.get("Water Lacks")
        return super().update()
