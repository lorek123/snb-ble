"""Volcano Hybrid device implementation."""

import logging
from typing import TYPE_CHECKING

from bleak import BleakClient

from storzandbickel_ble.device import BaseDevice
from storzandbickel_ble.exceptions import InvalidDataError
from storzandbickel_ble.models import DeviceType, VolcanoState
from storzandbickel_ble.protocol import (
    TEMP_MAX_VOLCANO,
    TEMP_MIN_VOLCANO,
    VOLCANO_CHAR_AUTO_OFF,
    VOLCANO_CHAR_CURRENT_TEMP,
    VOLCANO_CHAR_FIRMWARE_VERSION,
    VOLCANO_CHAR_HEATER_OFF,
    VOLCANO_CHAR_HEATER_ON,
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
    VOLCANO_STATUS1_HEATER_ON,
    VOLCANO_STATUS1_PUMP_ON,
    VOLCANO_STATUS2_DISPLAY_COOLING,
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

        self._connected = True

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
        self._connected = False

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
