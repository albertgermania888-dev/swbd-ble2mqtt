"""Config flow for SWBD integration."""
import logging
from typing import Any, Dict

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.components.bluetooth import (
    BluetoothServiceInfoBleak,
    async_discovered_service_info,
)
from homeassistant.const import CONF_MAC
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult

from .const import (
    DOMAIN,
    CONF_CONNECTION_MODE,
    CONF_POLLING_INTERVAL,
    MODE_CONTINUOUS,
    MODE_POLLING,
    DEFAULT_POLLING_INTERVAL,
    SWBD_SERVICE_UUID,
)

_LOGGER = logging.getLogger(__name__)

class SWBDConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for SWBD."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the config flow."""
        self._discovery_info: BluetoothServiceInfoBleak | None = None
        self._mac = None
        self._name = None

    async def async_step_bluetooth(
        self, discovery_info: BluetoothServiceInfoBleak
    ) -> FlowResult:
        """Handle the bluetooth discovery step."""
        await self.async_set_unique_id(discovery_info.address)
        self._abort_if_unique_id_configured()

        # Check if it has the required service
        if SWBD_SERVICE_UUID not in discovery_info.advertisement.service_uuids:
            return self.async_abort(reason="not_supported")

        self._discovery_info = discovery_info
        self._mac = discovery_info.address
        self._name = discovery_info.name or f"SWBD {discovery_info.address}"

        return await self.async_step_bluetooth_confirm()

    async def async_step_bluetooth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Confirm discovery."""
        if user_input is not None:
            return self.async_create_entry(
                title=self._name,
                data={CONF_MAC: self._mac},
            )

        self._set_confirm_only()
        return self.async_show_form(
            step_id="bluetooth_confirm",
            description_placeholders={"name": self._name},
        )

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle a flow initialized by the user."""
        errors: dict[str, str] = {}

        if user_input is not None:
            mac = user_input[CONF_MAC]
            await self.async_set_unique_id(mac)
            self._abort_if_unique_id_configured()

            return self.async_create_entry(
                title=f"SWBD {mac}",
                data={CONF_MAC: mac},
            )

        # Build list of discovered devices that haven't been added yet
        discovered_devices = []
        for dev in async_discovered_service_info(self.hass):
            if SWBD_SERVICE_UUID in dev.advertisement.service_uuids:
                discovered_devices.append(dev.address)

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_MAC): str,
                }
            ),
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        """Create the options flow."""
        return SWBDOptionsFlowHandler(config_entry)


class SWBDOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle SWBD options."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        options = {
            vol.Required(
                CONF_CONNECTION_MODE,
                default=self.config_entry.options.get(
                    CONF_CONNECTION_MODE, MODE_CONTINUOUS
                ),
            ): vol.In(
                {
                    MODE_CONTINUOUS: "Continuous (Real-time updates)",
                    MODE_POLLING: "Polling (Connect periodically to save resources)",
                }
            ),
            vol.Required(
                CONF_POLLING_INTERVAL,
                default=self.config_entry.options.get(
                    CONF_POLLING_INTERVAL, DEFAULT_POLLING_INTERVAL
                ),
            ): vol.All(vol.Coerce(int), vol.Range(min=1, max=60)),
        }

        return self.async_show_form(step_id="init", data_schema=vol.Schema(options))
