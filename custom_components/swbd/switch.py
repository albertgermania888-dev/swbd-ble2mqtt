"""Switch platform for SWBD."""
from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import SWBDCoordinator

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the switch platform."""
    coordinator: SWBDCoordinator = hass.data[DOMAIN][entry.entry_id]

    async_add_entities([
        SWBDRockingSwitch(coordinator, entry),
        SWBDMotionSensorSwitch(coordinator, entry),
    ])

class SWBDBaseSwitch(CoordinatorEntity, SwitchEntity):
    """Base class for SWBD switches."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: SWBDCoordinator, entry: ConfigEntry) -> None:
        """Initialize."""
        super().__init__(coordinator)
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
            "name": entry.title,
            "manufacturer": "SWBD",
        }

class SWBDRockingSwitch(SWBDBaseSwitch):
    """Switch for starting/stopping the rocking motion."""

    def __init__(self, coordinator: SWBDCoordinator, entry: ConfigEntry) -> None:
        """Initialize."""
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_rocking"
        self._attr_translation_key = "rocking"
        # Optional backward-compat name
        # self._attr_name = "Rocking"

    @property
    def is_on(self) -> bool:
        """Return true if the switch is on."""
        if not self.coordinator.data:
            return False
        return self.coordinator.data.get("enable", False)

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the entity on."""
        await self.coordinator.async_send_command(enable=True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the entity off."""
        await self.coordinator.async_send_command(enable=False)

class SWBDMotionSensorSwitch(SWBDBaseSwitch):
    """Switch for enabling/disabling the motion sensor."""

    def __init__(self, coordinator: SWBDCoordinator, entry: ConfigEntry) -> None:
        """Initialize."""
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_motion_sensor"
        self._attr_translation_key = "motion_sensor"
        self._attr_icon = "mdi:motion-sensor"

    @property
    def is_on(self) -> bool:
        """Return true if the switch is on."""
        if not self.coordinator.data:
            return False
        return self.coordinator.data.get("move_sensor", False)

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the entity on."""
        await self.coordinator.async_send_command(move_sensor=True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the entity off."""
        await self.coordinator.async_send_command(move_sensor=False)
