"""Number platform for SWBD."""
from homeassistant.components.number import NumberEntity
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
    """Set up the number platform."""
    coordinator: SWBDCoordinator = hass.data[DOMAIN][entry.entry_id]

    async_add_entities([
        SWBDSpeedNumber(coordinator, entry),
        SWBDSensitivityNumber(coordinator, entry),
        SWBDHoursNumber(coordinator, entry),
        SWBDMinutesNumber(coordinator, entry),
    ])

class SWBDBaseNumber(CoordinatorEntity, NumberEntity):
    """Base class for SWBD numbers."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: SWBDCoordinator, entry: ConfigEntry) -> None:
        """Initialize."""
        super().__init__(coordinator)
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
            "name": entry.title,
            "manufacturer": "SWBD",
        }

class SWBDSpeedNumber(SWBDBaseNumber):
    """Number for setting speed."""

    def __init__(self, coordinator: SWBDCoordinator, entry: ConfigEntry) -> None:
        """Initialize."""
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_speed"
        self._attr_translation_key = "speed"
        self._attr_native_min_value = 1
        self._attr_native_max_value = 6
        self._attr_native_step = 1
        self._attr_icon = "mdi:speedometer"

    @property
    def native_value(self) -> float | None:
        """Return the state of the entity."""
        if not self.coordinator.data:
            return None
        return self.coordinator.data.get("speed")

    async def async_set_native_value(self, value: float) -> None:
        """Set new value."""
        await self.coordinator.async_send_command(speed=int(value))


class SWBDSensitivityNumber(SWBDBaseNumber):
    """Number for setting microphone sensitivity."""

    def __init__(self, coordinator: SWBDCoordinator, entry: ConfigEntry) -> None:
        """Initialize."""
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_sensitivity"
        self._attr_translation_key = "sensitivity"
        self._attr_native_min_value = 0
        self._attr_native_max_value = 5
        self._attr_native_step = 1
        self._attr_icon = "mdi:microphone-settings"

    @property
    def native_value(self) -> float | None:
        """Return the state of the entity."""
        if not self.coordinator.data:
            return None
        return self.coordinator.data.get("sensitivity")

    async def async_set_native_value(self, value: float) -> None:
        """Set new value."""
        await self.coordinator.async_send_command(sensitivity=int(value))


class SWBDHoursNumber(SWBDBaseNumber):
    """Number for setting hours timer."""

    def __init__(self, coordinator: SWBDCoordinator, entry: ConfigEntry) -> None:
        """Initialize."""
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_hours"
        self._attr_translation_key = "hours"
        self._attr_native_min_value = 0
        self._attr_native_max_value = 23
        self._attr_native_step = 1
        self._attr_icon = "mdi:timer-sand"

    @property
    def native_value(self) -> float | None:
        """Return the state of the entity."""
        if not self.coordinator.data:
            return None
        return self.coordinator.data.get("hours")

    async def async_set_native_value(self, value: float) -> None:
        """Set new value."""
        await self.coordinator.async_send_command(hours=int(value))


class SWBDMinutesNumber(SWBDBaseNumber):
    """Number for setting minutes timer."""

    def __init__(self, coordinator: SWBDCoordinator, entry: ConfigEntry) -> None:
        """Initialize."""
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_minutes"
        self._attr_translation_key = "minutes"
        self._attr_native_min_value = 0
        self._attr_native_max_value = 59
        self._attr_native_step = 1
        self._attr_icon = "mdi:timer-sand"

    @property
    def native_value(self) -> float | None:
        """Return the state of the entity."""
        if not self.coordinator.data:
            return None
        return self.coordinator.data.get("minutes")

    async def async_set_native_value(self, value: float) -> None:
        """Set new value."""
        await self.coordinator.async_send_command(minutes=int(value))
