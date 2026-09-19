"""Coordinator for SWBD."""
import asyncio
import logging
from datetime import timedelta
from typing import Any

from bleak import BleakClient
from bleak.backends.device import BLEDevice
from bleak_retry_connector import establish_connection
from homeassistant.components.bluetooth import async_ble_device_from_address
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    DOMAIN,
    CONF_CONNECTION_MODE,
    CONF_POLLING_INTERVAL,
    MODE_CONTINUOUS,
    MODE_POLLING,
    DEFAULT_POLLING_INTERVAL,
    SWBD_CHAR_UUID,
)

_LOGGER = logging.getLogger(__name__)

class SWBDCoordinator(DataUpdateCoordinator):
    """Class to manage fetching SWBD data."""

    def __init__(self, hass: HomeAssistant, mac: str, options: dict[str, Any]) -> None:
        """Initialize."""
        self.mac = mac
        self.options = options
        self._client: BleakClient | None = None
        self._ble_device: BLEDevice | None = None
        self.state_array = bytearray([0x01, 0x00, 0x00, 0x00, 0x00, 0x00])

        mode = options.get(CONF_CONNECTION_MODE, MODE_CONTINUOUS)
        interval = options.get(CONF_POLLING_INTERVAL, DEFAULT_POLLING_INTERVAL)

        update_interval = None
        if mode == MODE_POLLING:
            update_interval = timedelta(minutes=interval)

        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=update_interval,
        )

        # Initialize data immediately so entities don't stay unavailable
        self.data = self._parse_state(self.state_array)

    @property
    def mode(self) -> str:
        """Return the connection mode."""
        return self.options.get(CONF_CONNECTION_MODE, MODE_CONTINUOUS)

    def _notification_handler(self, sender: int, data: bytearray) -> None:
        """Handle notifications from the device."""
        if len(data) == 6:
            self.state_array = data
            self.async_set_updated_data(self._parse_state(data))

    def _parse_state(self, data: bytearray) -> dict[str, Any]:
        """Parse the 6-byte state array into a dictionary."""
        time_mins = (data[2] << 8) | data[3]
        return {
            "speed": data[0] & 0x07,
            "enable": (data[0] >> 7) > 0,
            "sensitivity": data[1] & 0x07,
            "move_sensor": (data[1] >> 7) > 0,
            "hours": time_mins // 60,
            "minutes": time_mins % 60,
        }

    def _calc_checksum(self, data: bytearray) -> int:
        """Calculate the checksum."""
        sum_val = 0
        for i in range(5):
            sum_val = (sum_val + data[i] * 211) & 0xFFFF
            sum_val = sum_val ^ (sum_val >> 8)
        return sum_val & 0xFF

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch data from API endpoint."""
        self._ble_device = async_ble_device_from_address(self.hass, self.mac, connectable=True)
        if not self._ble_device:
            raise UpdateFailed(f"Could not find device with MAC {self.mac}")

        if self.mode == MODE_POLLING:
            return await self._poll_device()
        else:
            return await self._ensure_continuous_connection()

    async def _poll_device(self) -> dict[str, Any]:
        """Connect, read, and disconnect."""
        client = None
        try:
            client = await establish_connection(
                BleakClient,
                self._ble_device,
                self.mac,
                disconnected_callback=None
            )
            data = await client.read_gatt_char(SWBD_CHAR_UUID)
            if len(data) == 6:
                self.state_array = bytearray(data)
                return self._parse_state(self.state_array)
            raise UpdateFailed("Invalid data length received")
        except Exception as e:
            raise UpdateFailed(f"Error communicating with device: {e}")
        finally:
            if client and client.is_connected:
                await client.disconnect()

    async def _ensure_continuous_connection(self) -> dict[str, Any]:
        """Ensure connection is maintained and read latest state."""
        if self._client and self._client.is_connected:
            return self.data

        try:
            self._client = await establish_connection(
                BleakClient,
                self._ble_device,
                self.mac,
                disconnected_callback=self._handle_disconnect
            )
            await self._client.start_notify(SWBD_CHAR_UUID, self._notification_handler)
            data = await self._client.read_gatt_char(SWBD_CHAR_UUID)
            if len(data) == 6:
                self.state_array = bytearray(data)
                return self._parse_state(self.state_array)
            raise UpdateFailed("Invalid data length received")
        except Exception as e:
            raise UpdateFailed(f"Error communicating with device: {e}")

    def _handle_disconnect(self, client: BleakClient) -> None:
        """Handle device disconnection."""
        if self.mode == MODE_CONTINUOUS:
            # We must schedule a reconnect without permanently failing the coordinator
            _LOGGER.info("Disconnected from device, scheduling reconnect")
            # Clear current client state
            self._client = None
            self.hass.async_create_task(self._async_reconnect())

    async def _async_reconnect(self):
        """Background task to reconnect if disconnected."""
        try:
            await asyncio.sleep(2)
            await self.async_request_refresh()
        except Exception as e:
             _LOGGER.error(f"Error during reconnect task: {e}")

    async def async_send_command(self, **kwargs) -> None:
        """Update the state array and send to device."""
        new_state = bytearray(self.state_array)

        if "enable" in kwargs:
            val = 1 if kwargs["enable"] else 0
            new_state[0] = (new_state[0] & 0x7F) | (val << 7)
        if "speed" in kwargs:
            new_state[0] = (new_state[0] & 0xF8) | (kwargs["speed"] & 0x07)
        if "move_sensor" in kwargs:
            val = 1 if kwargs["move_sensor"] else 0
            new_state[1] = (new_state[1] & 0x7F) | (val << 7)
        if "sensitivity" in kwargs:
            new_state[1] = (new_state[1] & 0xF8) | (kwargs["sensitivity"] & 0x07)
        if "hours" in kwargs or "minutes" in kwargs:
            hours = kwargs.get("hours", self.data["hours"]) if self.data else 0
            minutes = kwargs.get("minutes", self.data["minutes"]) if self.data else 0
            total_minutes = (int(hours) * 60) + int(minutes)
            new_state[2] = (total_minutes >> 8) & 0xFF
            new_state[3] = total_minutes & 0xFF

        new_state[5] = self._calc_checksum(new_state)

        # Immediately update the internal state to reflect the intent
        self.state_array = new_state
        self.async_set_updated_data(self._parse_state(new_state))

        self._ble_device = async_ble_device_from_address(self.hass, self.mac, connectable=True)
        if not self._ble_device:
            _LOGGER.error(f"Could not find device with MAC {self.mac}")
            return

        if self.mode == MODE_CONTINUOUS:
            if self._client and self._client.is_connected:
                # Send immediately on the active connection without re-establishing
                try:
                    await self._client.write_gatt_char(SWBD_CHAR_UUID, new_state, response=False)
                except Exception as e:
                    _LOGGER.error(f"Failed to send command on active connection: {e}")
            else:
                # The continuous client dropped, establish connection and update the handle
                try:
                    client = await establish_connection(
                        BleakClient,
                        self._ble_device,
                        self.mac,
                        disconnected_callback=self._handle_disconnect
                    )
                    self._client = client
                    await self._client.start_notify(SWBD_CHAR_UUID, self._notification_handler)
                    await self._client.write_gatt_char(SWBD_CHAR_UUID, new_state, response=False)
                except Exception as e:
                    _LOGGER.error(f"Failed to send command: {e}")
        else:
            # Polling mode: always establish, write, and disconnect
            client = None
            try:
                client = await establish_connection(
                    BleakClient,
                    self._ble_device,
                    self.mac,
                    disconnected_callback=None
                )
                await client.write_gatt_char(SWBD_CHAR_UUID, new_state, response=False)
            except Exception as e:
                _LOGGER.error(f"Failed to send command: {e}")
            finally:
                if client and client.is_connected:
                    await client.disconnect()

    async def async_shutdown(self) -> None:
        """Shutdown coordinator and close connection."""
        if self._client and self._client.is_connected:
            await self._client.disconnect()
