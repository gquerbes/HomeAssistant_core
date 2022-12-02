"""Support for binary sensors for VeSync devices."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
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
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .common import VeSyncBaseEntity
from .const import (
    DEV_TYPE_TO_HA,
    DOMAIN,
    SKU_TO_BASE_DEVICE,
    VS_BINARY_SENSORS,
    VS_DISCOVERY,
)

_LOGGER = logging.getLogger(__name__)


@dataclass
class VeSyncBinarySensorEntityDescriptionMixin:
    """Mixin for required keys."""

    # value_fn: Callable[
    #     [VeSyncAirBypass | VeSyncOutlet | VeSyncSwitch | VeSyncHumid200300S], StateType
    # ]


@dataclass
class VeSyncBinarySensorEntityDescription(
    BinarySensorEntityDescription, VeSyncBinarySensorEntityDescriptionMixin
):
    """Describe VeSync sensor entity."""

    exists_fn: Callable[
        [VeSyncAirBypass | VeSyncOutlet | VeSyncSwitch | VeSyncHumid200300S], bool
    ] = lambda _: True
    update_fn: Callable[
        [VeSyncAirBypass | VeSyncOutlet | VeSyncSwitch | VeSyncHumid200300S], None
    ] = lambda _: None


# @property
# def tank_removed(device) -> bool:
#     """does stuff"""
#     return True


def sku_supported(device, supported):
    """Get the base device of which a device is an instance."""
    return SKU_TO_BASE_DEVICE.get(device.device_type) in supported


def ha_dev_type(device):
    """Get the homeassistant device_type for a given device."""
    return DEV_TYPE_TO_HA.get(device.device_type)


TANK_LIFTED_SUPPORTED = ["Classic300S"]
TANK_EMPTY_SUPPORTED = ["Classic300S"]

SENSORS: tuple[VeSyncBinarySensorEntityDescription, ...] = (
    VeSyncBinarySensorEntityDescription(
        key="water-tank-lifted",
        name="water tank lifted",
        entity_category=EntityCategory.DIAGNOSTIC,
        exists_fn=lambda device: sku_supported(device, TANK_LIFTED_SUPPORTED),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up switches."""

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
        """Initialize the VeSync outlet device."""
        super().__init__(device)
        self.entity_description = description
        self._attr_name = f"{super().name} {description.name}"
        self._attr_unique_id = f"{super().unique_id}-{description.key}"

    # @property
    # def native_value(self) -> StateType:
    #     """Return the state of the sensor."""
    #     return self.entity_description.value_fn(self.device)

    # def update(self) -> None:
    #     """Run the update function defined for the sensor."""
    #     return self.entity_description.update_fn(self.device)

    @property
    def is_on(self) -> bool | None:
        """Get value of if on."""
        return True
