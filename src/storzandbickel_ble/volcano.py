"""Volcano Hybrid device implementation."""

import asyncio
import logging
from typing import TYPE_CHECKING

from bleak import BleakClient

from storzandbickel_ble.device import BaseDevice
from storzandbickel_ble.exceptions import InvalidDataError
from storzandbickel_ble.models import DeviceType, TemperatureUnit, VolcanoState
from storzandbickel_ble.protocol import (
    TEMP_MAX_VOLCANO,
    TEMP_MIN_VOLCANO,
    VOLCANO_CHAR_AUTO_OFF,
    VOLCANO_CHAR_CURRENT_TEMP,
    VOLCANO_CHAR_FIRMWARE_VERSION,
    VOLCANO_CHAR_HEATER_OFF,
    VOLCANO_CHAR_HEATER_ON,
    VOLCANO_CHAR_HISTORY_1,
    VOLCANO_CHAR_HISTORY_2,
    VOLCANO_CHAR_HEATING_HOURS,
    VOLCANO_CHAR_HEATING_MINUTES,
    VOLCANO_CHAR_LED_BRIGHTNESS,
    VOLCANO_CHAR_PUMP_OFF,
    VOLCANO_CHAR_PUMP_ON,
    VOLCANO_CHAR_SERIAL_NUMBER,
    VOLCANO_CHAR_STATUS_REGISTER_1,
    VOLCANO_CHAR_STATUS_REGISTER_2,
    VOLCANO_CHAR_STATUS_REGISTER_3,
    VOLCANO_CHAR_TARGET_TEMP,
    VOLCANO_STATUS1_AUTO_SHUTDOWN,
    VOLCANO_STATUS1_ERROR_BITS,
    VOLCANO_STATUS1_HEATER_ON,
    VOLCANO_STATUS1_PUMP_ON,
    VOLCANO_STATUS2_DISPLAY_COOLING,
    VOLCANO_STATUS2_ERROR_BITS,
    VOLCANO_STATUS2_FAHRENHEIT,
    VOLCANO_STATUS3_VIBRATION_READY,
    clamp_temperature,
    decode_string,
    decode_temperature,
    decode_uint16,
    encode_temperature,
    encode_uint16,
)

if TYPE_CHECKING:
    pass

_LOGGER = logging.getLogger(__name__)

VOLCANO_WORKFLOW_PRESETS: dict[str, list[tuple[float, float, float]]] = {
    # Presets from web app workflow.js.
    "balloon": [(float(t), 0.0, 5.0) for t in range(170, 221, 5)],
    "flow1": [
        (182.0, 10.0, 10.0),
        (192.0, 7.0, 12.0),
        (201.0, 5.0, 10.0),
        (220.0, 3.0, 10.0),
    ],
    "flow2": [
        (175.0, 0.0, 7.0),
        (180.0, 0.0, 7.0),
        (185.0, 0.0, 7.0),
        (190.0, 0.0, 7.0),
        (195.0, 0.0, 10.0),
    ],
    "flow3": [
        (174.0, 20.0, 8.0),
        (199.0, 0.0, 20.0),
        (213.0, 0.0, 10.0),
        (222.0, 0.0, 10.0),
    ],
}


class VolcanoDevice(BaseDevice):
    """Volcano Hybrid device."""

    def __init__(
        self,
        address: str,
        client: BleakClient | None = None,
        name: str | None = None,
    ) -> None:
        """Initialize Volcano device.

        Args:
            address: BLE MAC address
            client: Optional BleakClient instance
            name: Optional device name
        """
        super().__init__(address, client, name)
        # Initialize with all required fields to satisfy mypy
        self._state = VolcanoState(
            current_temperature=None,
            target_temperature=None,
            led_brightness=5,
            auto_off_time=0,
            heating_hours=0,
            heating_minutes=0,
        )

    @property
    def device_type(self) -> DeviceType:
        """Return device type."""
        return DeviceType.VOLCANO

    @property
    def state(self) -> VolcanoState:
        """Return current device state."""
        state = self._get_state()
        assert isinstance(state, VolcanoState), "State must be VolcanoState"
        return state

    def _get_state(self) -> VolcanoState:
        """Get state with type narrowing."""
        state = self._state
        assert state is not None, "State should never be None"
        assert isinstance(state, VolcanoState), "State must be VolcanoState"
        return state

    async def connect(self) -> None:
        """Connect to device and initialize."""
        if self._client is None:
            from bleak import BleakClient

            self._client = BleakClient(self.address)

        if not self._client.is_connected:
            await self._client.connect()

        self._set_connection_state(True)

        # Service discovery happens automatically when we access characteristics
        # Read initial state
        await self.update_state()

        # Enable notifications
        await self._start_notifications(
            VOLCANO_CHAR_CURRENT_TEMP,
            self._handle_temperature_notification,
        )
        await self._start_notifications(
            VOLCANO_CHAR_STATUS_REGISTER_1,
            self._handle_status1_notification,
        )
        await self._start_notifications(
            VOLCANO_CHAR_STATUS_REGISTER_2,
            self._handle_status2_notification,
        )
        await self._start_notifications(
            VOLCANO_CHAR_STATUS_REGISTER_3,
            self._handle_status3_notification,
        )
        await self._start_notifications(
            VOLCANO_CHAR_HEATING_HOURS,
            self._handle_heating_hours_notification,
        )
        await self._start_notifications(
            VOLCANO_CHAR_HEATING_MINUTES,
            self._handle_heating_minutes_notification,
        )

    async def disconnect(self) -> None:
        """Disconnect from device."""
        await self._stop_all_notifications()
        if self._client is not None and self._client.is_connected:
            await self._client.disconnect()
        self._set_connection_state(False)

    async def update_state(self) -> None:
        """Update device state by reading from device."""
        state = self._get_state()
        try:
            # Read firmware version
            try:
                data = await self._read_characteristic(VOLCANO_CHAR_FIRMWARE_VERSION)
                state.firmware_version = decode_string(data)
            except Exception as e:
                _LOGGER.warning("Failed to read firmware version: %s", e)

            # Read serial number
            try:
                data = await self._read_characteristic(VOLCANO_CHAR_SERIAL_NUMBER)
                state.serial_number = decode_string(data)
            except Exception as e:
                _LOGGER.warning("Failed to read serial number: %s", e)

            # Read current temperature
            try:
                data = await self._read_characteristic(VOLCANO_CHAR_CURRENT_TEMP)
                state.current_temperature = decode_temperature(data)
            except Exception as e:
                _LOGGER.warning("Failed to read current temperature: %s", e)

            # Read target temperature
            try:
                data = await self._read_characteristic(VOLCANO_CHAR_TARGET_TEMP)
                state.target_temperature = decode_temperature(data)
            except Exception as e:
                _LOGGER.warning("Failed to read target temperature: %s", e)

            # Read status registers
            try:
                data = await self._read_characteristic(VOLCANO_CHAR_STATUS_REGISTER_1)
                state.status_register_1 = decode_uint16(data)
                state.heater_on = bool(
                    state.status_register_1 & VOLCANO_STATUS1_HEATER_ON,
                )
                state.auto_shutdown_enabled = bool(
                    state.status_register_1 & VOLCANO_STATUS1_AUTO_SHUTDOWN,
                )
                state.pump_on = bool(
                    state.status_register_1 & VOLCANO_STATUS1_PUMP_ON,
                )
            except Exception as e:
                _LOGGER.warning("Failed to read status register 1: %s", e)

            try:
                data = await self._read_characteristic(VOLCANO_CHAR_STATUS_REGISTER_2)
                state.status_register_2 = decode_uint16(data)
                state.fahrenheit_mode = bool(
                    state.status_register_2 & VOLCANO_STATUS2_FAHRENHEIT,
                )
                state.display_on_cooling = bool(
                    state.status_register_2 & VOLCANO_STATUS2_DISPLAY_COOLING,
                )
            except Exception as e:
                _LOGGER.warning("Failed to read status register 2: %s", e)

            try:
                data = await self._read_characteristic(VOLCANO_CHAR_STATUS_REGISTER_3)
                state.status_register_3 = decode_uint16(data)
                state.vibration_on_ready = bool(
                    state.status_register_3 & VOLCANO_STATUS3_VIBRATION_READY,
                )
            except Exception as e:
                _LOGGER.warning("Failed to read status register 3: %s", e)

            # Read LED brightness
            try:
                data = await self._read_characteristic(VOLCANO_CHAR_LED_BRIGHTNESS)
                state.led_brightness = decode_uint16(data)
            except Exception as e:
                _LOGGER.warning("Failed to read LED brightness: %s", e)

            # Read auto-off time
            try:
                data = await self._read_characteristic(VOLCANO_CHAR_AUTO_OFF)
                state.auto_off_time = decode_uint16(data)
            except Exception as e:
                _LOGGER.warning("Failed to read auto-off time: %s", e)

            # Read heating hours
            try:
                data = await self._read_characteristic(VOLCANO_CHAR_HEATING_HOURS)
                state.heating_hours = decode_uint16(data)
            except Exception as e:
                _LOGGER.warning("Failed to read heating hours: %s", e)

            # Read heating minutes
            try:
                data = await self._read_characteristic(VOLCANO_CHAR_HEATING_MINUTES)
                state.heating_minutes = decode_uint16(data)
            except Exception as e:
                _LOGGER.warning("Failed to read heating minutes: %s", e)

        except Exception as e:
            _LOGGER.error("Error updating state: %s", e, exc_info=True)
            raise InvalidDataError(f"Failed to update state: {e}") from e

    async def set_target_temperature(self, temperature: float) -> None:
        """Set target temperature.

        Args:
            temperature: Temperature in Celsius (40-230°C)
        """
        temp = clamp_temperature(temperature, TEMP_MIN_VOLCANO, TEMP_MAX_VOLCANO)
        data = encode_temperature(temp)
        await self._write_characteristic(VOLCANO_CHAR_TARGET_TEMP, data)
        state = self._get_state()
        state.target_temperature = temp

    async def turn_heater_on(self) -> None:
        """Turn heater on."""
        await self._write_characteristic(VOLCANO_CHAR_HEATER_ON, b"\x01")
        state = self._get_state()
        state.heater_on = True

    async def turn_heater_off(self) -> None:
        """Turn heater off."""
        await self._write_characteristic(VOLCANO_CHAR_HEATER_OFF, b"\x01")
        state = self._get_state()
        state.heater_on = False

    async def turn_pump_on(self) -> None:
        """Turn air pump on."""
        await self._write_characteristic(VOLCANO_CHAR_PUMP_ON, b"\x01")
        state = self._get_state()
        state.pump_on = True

    async def turn_pump_off(self) -> None:
        """Turn air pump off."""
        await self._write_characteristic(VOLCANO_CHAR_PUMP_OFF, b"\x01")
        state = self._get_state()
        state.pump_on = False

    async def set_led_brightness(self, brightness: int) -> None:
        """Set LED brightness.

        Args:
            brightness: Brightness level (1-9)
        """
        if brightness < 1 or brightness > 9:
            msg = f"LED brightness must be between 1 and 9, got {brightness}"
            raise ValueError(msg)
        data = encode_uint16(brightness)
        await self._write_characteristic(VOLCANO_CHAR_LED_BRIGHTNESS, data)
        state = self._get_state()
        state.led_brightness = brightness

    async def set_auto_off_time(self, seconds: int) -> None:
        """Set auto-off time.

        Args:
            seconds: Auto-off time in seconds
        """
        if seconds < 0:
            msg = f"Auto-off time must be >= 0, got {seconds}"
            raise ValueError(msg)
        data = encode_uint16(seconds)
        await self._write_characteristic(VOLCANO_CHAR_AUTO_OFF, data)
        state = self._get_state()
        state.auto_off_time = seconds

    async def set_status_register_2(self, value: int) -> None:
        """Set status register 2 (display settings, etc.).

        Args:
            value: Status register 2 value
        """
        data = encode_uint16(value)
        await self._write_characteristic(VOLCANO_CHAR_STATUS_REGISTER_2, data)
        state = self._get_state()
        state.status_register_2 = value
        state.fahrenheit_mode = bool(value & VOLCANO_STATUS2_FAHRENHEIT)
        state.display_on_cooling = bool(value & VOLCANO_STATUS2_DISPLAY_COOLING)

    async def set_status_register_3(self, value: int) -> None:
        """Set status register 3 (vibration settings, etc.).

        Args:
            value: Status register 3 value
        """
        data = encode_uint16(value)
        await self._write_characteristic(VOLCANO_CHAR_STATUS_REGISTER_3, data)
        state = self._get_state()
        state.status_register_3 = value
        state.vibration_on_ready = bool(value & VOLCANO_STATUS3_VIBRATION_READY)

    async def set_temperature_unit(self, unit: TemperatureUnit) -> None:
        """Set display temperature unit."""
        state = self._get_state()
        value = state.status_register_2
        if unit == TemperatureUnit.FAHRENHEIT:
            value |= VOLCANO_STATUS2_FAHRENHEIT
        else:
            value &= ~VOLCANO_STATUS2_FAHRENHEIT
        await self.set_status_register_2(value)

    async def set_display_on_cooling(self, enabled: bool) -> None:
        """Enable/disable showing temperature during cool-down."""
        state = self._get_state()
        value = state.status_register_2
        if enabled:
            value |= VOLCANO_STATUS2_DISPLAY_COOLING
        else:
            value &= ~VOLCANO_STATUS2_DISPLAY_COOLING
        await self.set_status_register_2(value)

    async def set_vibration_on_ready(self, enabled: bool) -> None:
        """Enable/disable vibration on setpoint reached."""
        state = self._get_state()
        value = state.status_register_3
        if enabled:
            value |= VOLCANO_STATUS3_VIBRATION_READY
        else:
            value &= ~VOLCANO_STATUS3_VIBRATION_READY
        await self.set_status_register_3(value)

    async def run_workflow_preset(
        self,
        preset: str,
        wait_for_temperature: bool = True,
        temperature_tolerance: float = 1.0,
        poll_interval: float = 1.5,
    ) -> None:
        """Run a Volcano workflow preset.

        Args:
            preset: One of `balloon`, `flow1`, `flow2`, `flow3`.
            wait_for_temperature: Wait for setpoint before hold/pump phase.
            temperature_tolerance: Acceptable absolute delta from target.
            poll_interval: Poll interval while waiting for setpoint.
        """
        if preset not in VOLCANO_WORKFLOW_PRESETS:
            msg = f"Unknown workflow preset: {preset}"
            raise ValueError(msg)

        if not self.state.heater_on:
            await self.turn_heater_on()

        for target_temp, hold_seconds, pump_seconds in VOLCANO_WORKFLOW_PRESETS[preset]:
            await self.set_target_temperature(target_temp)
            if wait_for_temperature:
                while True:
                    await self.update_state()
                    current = self.state.current_temperature
                    if (
                        current is not None
                        and abs(current - target_temp) <= temperature_tolerance
                    ):
                        break
                    await asyncio.sleep(poll_interval)
            if hold_seconds > 0:
                await asyncio.sleep(hold_seconds)
            await self.turn_pump_on()
            await asyncio.sleep(max(0.5, pump_seconds))
            await self.turn_pump_off()

    async def run_analysis(self) -> dict[str, object]:
        """Run local Volcano diagnostics summary (no cloud upload)."""
        await self.update_state()
        state = self.state
        warnings: list[str] = []
        errors: list[str] = []

        if state.led_brightness < 3:
            warnings.append("Display brightness is low.")
        if not state.display_on_cooling:
            warnings.append("Display-on-cooling is disabled.")
        if not state.vibration_on_ready:
            warnings.append("Vibration-on-ready is disabled.")
        if state.status_register_1 & VOLCANO_STATUS1_ERROR_BITS:
            errors.append("Status register 1 indicates device error flags.")
        if state.status_register_2 & VOLCANO_STATUS2_ERROR_BITS:
            errors.append("Status register 2 indicates device error flags.")

        history_1 = ""
        history_2 = ""
        try:
            history_1 = (await self._read_characteristic(VOLCANO_CHAR_HISTORY_1)).hex()
            history_2 = (await self._read_characteristic(VOLCANO_CHAR_HISTORY_2)).hex()
        except Exception as err:  # noqa: BLE001
            _LOGGER.debug("History registers unavailable during analysis: %s", err)

        return {
            "ok": not errors,
            "warnings": warnings,
            "errors": errors,
            "history_1": history_1,
            "history_2": history_2,
            "status_register_1": state.status_register_1,
            "status_register_2": state.status_register_2,
            "status_register_3": state.status_register_3,
        }

    def _handle_temperature_notification(self, data: bytes) -> None:
        """Handle temperature notification."""
        state = self._get_state()
        try:
            state.current_temperature = decode_temperature(bytearray(data))
            _LOGGER.debug("Temperature update: %s°C", state.current_temperature)
        except Exception as e:
            _LOGGER.warning("Error handling temperature notification: %s", e)

    def _handle_status1_notification(self, data: bytes) -> None:
        """Handle status register 1 notification."""
        state = self._get_state()
        try:
            state.status_register_1 = decode_uint16(bytearray(data))
            state.heater_on = bool(
                state.status_register_1 & VOLCANO_STATUS1_HEATER_ON,
            )
            state.auto_shutdown_enabled = bool(
                state.status_register_1 & VOLCANO_STATUS1_AUTO_SHUTDOWN,
            )
            state.pump_on = bool(
                state.status_register_1 & VOLCANO_STATUS1_PUMP_ON,
            )
        except Exception as e:
            _LOGGER.warning("Error handling status register 1 notification: %s", e)

    def _handle_status2_notification(self, data: bytes) -> None:
        """Handle status register 2 notification."""
        state = self._get_state()
        try:
            state.status_register_2 = decode_uint16(bytearray(data))
            state.fahrenheit_mode = bool(
                state.status_register_2 & VOLCANO_STATUS2_FAHRENHEIT,
            )
            state.display_on_cooling = bool(
                state.status_register_2 & VOLCANO_STATUS2_DISPLAY_COOLING,
            )
        except Exception as e:
            _LOGGER.warning("Error handling status register 2 notification: %s", e)

    def _handle_status3_notification(self, data: bytes) -> None:
        """Handle status register 3 notification."""
        state = self._get_state()
        try:
            state.status_register_3 = decode_uint16(bytearray(data))
            state.vibration_on_ready = bool(
                state.status_register_3 & VOLCANO_STATUS3_VIBRATION_READY,
            )
        except Exception as e:
            _LOGGER.warning("Error handling status register 3 notification: %s", e)

    def _handle_heating_hours_notification(self, data: bytes) -> None:
        """Handle heating hours notification."""
        state = self._get_state()
        try:
            state.heating_hours = decode_uint16(bytearray(data))
        except Exception as e:
            _LOGGER.warning("Error handling heating hours notification: %s", e)

    def _handle_heating_minutes_notification(self, data: bytes) -> None:
        """Handle heating minutes notification."""
        state = self._get_state()
        try:
            state.heating_minutes = decode_uint16(bytearray(data))
        except Exception as e:
            _LOGGER.warning("Error handling heating minutes notification: %s", e)
