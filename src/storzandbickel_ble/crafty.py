"""Crafty/Crafty+ device implementation."""

import asyncio
import logging
from typing import TYPE_CHECKING

from bleak import BleakClient

from storzandbickel_ble.device import BaseDevice
from storzandbickel_ble.exceptions import InvalidDataError
from storzandbickel_ble.models import CraftyState, DeviceType
from storzandbickel_ble.protocol import (
    CRAFTY_CHAR_AKKU_STATUS,
    CRAFTY_CHAR_AUTO_OFF,
    CRAFTY_CHAR_BATTERY,
    CRAFTY_CHAR_CURRENT_TEMP,
    CRAFTY_CHAR_FIND_DEVICE,
    CRAFTY_CHAR_HEATER_OFF,
    CRAFTY_CHAR_HEATER_ON,
    CRAFTY_CHAR_LED_BRIGHTNESS,
    CRAFTY_CHAR_PROJECT_STATUS,
    CRAFTY_CHAR_PROJECT_STATUS_2,
    CRAFTY_CHAR_STATUS_REGISTER,
    CRAFTY_CHAR_TARGET_TEMP,
    CRAFTY_CHAR_USAGE_HOURS,
    CRAFTY_CHAR_USAGE_MINUTES,
    CRAFTY_PROJECT_STATUS2_VIBRATION_DISABLED,
    CRAFTY_PROJECT_STATUS_ACTIVE,
    CRAFTY_PROJECT_STATUS_BOOST_ENABLED,
    CRAFTY_PROJECT_STATUS_SUPERBOOST_ENABLED,
    CRAFTY_STATUS_BOOST_MODE,
    CRAFTY_STATUS_FAHRENHEIT,
    CRAFTY_STATUS_HEATER_ON,
    CRAFTY_STATUS_VIBRATION_READY,
    TEMP_MAX_CRAFTY,
    TEMP_MIN_CRAFTY,
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


class CraftyDevice(BaseDevice):
    """Crafty/Crafty+ device."""

    def __init__(
        self,
        address: str,
        client: BleakClient | None = None,
        name: str | None = None,
    ) -> None:
        """Initialize Crafty device.

        Args:
            address: BLE MAC address
            client: Optional BleakClient instance
            name: Optional device name
        """
        super().__init__(address, client, name)
        # Initialize with all required fields to satisfy mypy
        self._state = CraftyState(
            current_temperature=None,
            target_temperature=None,
            battery_level=0,
            led_brightness=50,
            auto_off_time=0,
            usage_hours=0,
            usage_minutes=0,
        )

    @property
    def device_type(self) -> DeviceType:
        """Return device type."""
        return DeviceType.CRAFTY

    @property
    def state(self) -> CraftyState:
        """Return current device state."""
        state = self._state
        assert state is not None, "State should never be None"
        assert isinstance(state, CraftyState), "State must be CraftyState"
        return state

    def _get_state(self) -> CraftyState:
        """Get state with type narrowing."""
        state = self._state
        assert state is not None, "State should never be None"
        assert isinstance(state, CraftyState), "State must be CraftyState"
        return state

    async def connect(self) -> None:
        """Connect to device and initialize."""
        if self._client is None:
            from bleak import BleakClient

            self._client = BleakClient(self.address)

        if not self._client.is_connected:
            await self._client.connect()

        self._connected = True

        # Read minimal initial state (fast connection)
        # Service discovery happens automatically on first characteristic access
        # Full state will be updated via notifications and can be read explicitly if needed
        await self._read_minimal_state()

        # Enable notifications (some may not be supported, so we catch errors)
        try:
            await self._start_notifications(
                CRAFTY_CHAR_CURRENT_TEMP,
                self._handle_temperature_notification,
            )
        except Exception as e:
            _LOGGER.warning("Failed to enable notifications for current temp: %s", e)

        try:
            await self._start_notifications(
                CRAFTY_CHAR_BATTERY,
                self._handle_battery_notification,
            )
        except Exception as e:
            _LOGGER.warning("Failed to enable notifications for battery: %s", e)

        try:
            await self._start_notifications(
                CRAFTY_CHAR_STATUS_REGISTER,
                self._handle_status_notification,
            )
        except Exception as e:
            _LOGGER.warning("Failed to enable notifications for status register: %s", e)

        try:
            await self._start_notifications(
                CRAFTY_CHAR_PROJECT_STATUS,
                self._handle_project_status_notification,
            )
        except Exception as e:
            _LOGGER.warning("Failed to enable notifications for project status: %s", e)

        try:
            await self._start_notifications(
                CRAFTY_CHAR_PROJECT_STATUS_2,
                self._handle_project_status2_notification,
            )
        except Exception as e:
            _LOGGER.warning(
                "Failed to enable notifications for project status 2: %s", e
            )

        try:
            await self._start_notifications(
                CRAFTY_CHAR_AKKU_STATUS,
                self._handle_akku_status_notification,
            )
        except Exception as e:
            _LOGGER.warning("Failed to enable notifications for Akku status: %s", e)

    async def disconnect(self) -> None:
        """Disconnect from device."""
        await self._stop_all_notifications()
        if self._client is not None and self._client.is_connected:
            await self._client.disconnect()
        self._connected = False

    async def _read_minimal_state(self) -> None:
        """Read minimal state for fast connection (only essential characteristics)."""
        state = self._get_state()
        try:
            # Read status register (contains serial and heater status)
            try:
                data = await self._read_characteristic(CRAFTY_CHAR_STATUS_REGISTER)
                if len(data) >= 10:
                    state.serial_number = decode_string(data[:8])
                    state.status_register = decode_uint16(data[8:10])
                    state.heater_on = bool(
                        state.status_register & CRAFTY_STATUS_HEATER_ON,
                    )
            except Exception as e:
                _LOGGER.warning("Failed to read status register: %s", e)

            # Read current temperature and target in parallel
            async def read_temp() -> None:
                try:
                    data = await self._read_characteristic(CRAFTY_CHAR_CURRENT_TEMP)
                    state.current_temperature = decode_temperature(data)
                except Exception as e:
                    _LOGGER.warning("Failed to read current temperature: %s", e)

            async def read_target() -> None:
                try:
                    data = await self._read_characteristic(CRAFTY_CHAR_TARGET_TEMP)
                    state.target_temperature = decode_temperature(data)
                except Exception as e:
                    _LOGGER.warning("Failed to read target temperature: %s", e)

            async def read_battery() -> None:
                try:
                    data = await self._read_characteristic(CRAFTY_CHAR_BATTERY)
                    if len(data) >= 1:
                        state.battery_level = data[0]
                except Exception as e:
                    _LOGGER.warning("Failed to read battery level: %s", e)

            # Read in parallel
            await asyncio.gather(
                read_temp(),
                read_target(),
                read_battery(),
                return_exceptions=True,
            )

        except Exception as e:
            _LOGGER.error("Error reading minimal state: %s", e, exc_info=True)

    async def update_state(self) -> None:
        """Update device state by reading from device."""
        state = self._get_state()
        try:
            # Read status register (contains serial number in first 8 bytes)
            try:
                data = await self._read_characteristic(CRAFTY_CHAR_STATUS_REGISTER)
                if len(data) >= 10:
                    # First 8 bytes are serial number
                    state.serial_number = decode_string(data[:8])
                    # Last 2 bytes are status register
                    state.status_register = decode_uint16(data[8:10])
                    state.heater_on = bool(
                        state.status_register & CRAFTY_STATUS_HEATER_ON,
                    )
                    state.boost_mode = bool(
                        state.status_register & CRAFTY_STATUS_BOOST_MODE,
                    )
                    state.vibration_on_ready = bool(
                        state.status_register & CRAFTY_STATUS_VIBRATION_READY,
                    )
                    state.fahrenheit_mode = bool(
                        state.status_register & CRAFTY_STATUS_FAHRENHEIT,
                    )
            except Exception as e:
                _LOGGER.warning("Failed to read status register: %s", e)

            # Read current temperature
            try:
                data = await self._read_characteristic(CRAFTY_CHAR_CURRENT_TEMP)
                state.current_temperature = decode_temperature(data)
            except Exception as e:
                _LOGGER.warning("Failed to read current temperature: %s", e)

            # Read target temperature
            try:
                data = await self._read_characteristic(CRAFTY_CHAR_TARGET_TEMP)
                state.target_temperature = decode_temperature(data)
            except Exception as e:
                _LOGGER.warning("Failed to read target temperature: %s", e)

            # Read battery level
            try:
                data = await self._read_characteristic(CRAFTY_CHAR_BATTERY)
                if len(data) >= 1:
                    state.battery_level = data[0]
            except Exception as e:
                _LOGGER.warning("Failed to read battery level: %s", e)

            # Read project status register
            try:
                data = await self._read_characteristic(CRAFTY_CHAR_PROJECT_STATUS)
                state.project_status_register = decode_uint16(data)
                state.device_active = bool(
                    state.project_status_register & CRAFTY_PROJECT_STATUS_ACTIVE,
                )
                state.boost_mode = bool(
                    state.project_status_register & CRAFTY_PROJECT_STATUS_BOOST_ENABLED,
                )
                state.superboost_mode = bool(
                    state.project_status_register
                    & CRAFTY_PROJECT_STATUS_SUPERBOOST_ENABLED,
                )
            except Exception as e:
                _LOGGER.warning("Failed to read project status register: %s", e)

            # Read project status register 2
            try:
                data = await self._read_characteristic(CRAFTY_CHAR_PROJECT_STATUS_2)
                state.project_status_register_2 = decode_uint16(data)
                # Vibration is inverted: 0 = enabled, 1 = disabled
                state.vibration_enabled = not bool(
                    state.project_status_register_2
                    & CRAFTY_PROJECT_STATUS2_VIBRATION_DISABLED,
                )
            except Exception as e:
                _LOGGER.warning("Failed to read project status register 2: %s", e)

            # Read LED brightness
            try:
                data = await self._read_characteristic(CRAFTY_CHAR_LED_BRIGHTNESS)
                state.led_brightness = decode_uint16(data)
            except Exception as e:
                _LOGGER.warning("Failed to read LED brightness: %s", e)

            # Read auto-off time
            try:
                data = await self._read_characteristic(CRAFTY_CHAR_AUTO_OFF)
                state.auto_off_time = decode_uint16(data)
            except Exception as e:
                _LOGGER.warning("Failed to read auto-off time: %s", e)

            # Read usage hours
            try:
                data = await self._read_characteristic(CRAFTY_CHAR_USAGE_HOURS)
                state.usage_hours = decode_uint16(data)
            except Exception as e:
                _LOGGER.warning("Failed to read usage hours: %s", e)

            # Read usage minutes
            try:
                data = await self._read_characteristic(CRAFTY_CHAR_USAGE_MINUTES)
                state.usage_minutes = decode_uint16(data)
            except Exception as e:
                _LOGGER.warning("Failed to read usage minutes: %s", e)

            # Read Akku status (charging detection)
            try:
                data = await self._read_characteristic(CRAFTY_CHAR_AKKU_STATUS)
                # Parse charging status from data (implementation may vary)
                state.charging = len(data) > 0 and data[0] > 0
            except Exception as e:
                _LOGGER.warning("Failed to read Akku status: %s", e)

        except Exception as e:
            _LOGGER.error("Error updating state: %s", e, exc_info=True)
            raise InvalidDataError(f"Failed to update state: {e}") from e

    async def set_target_temperature(self, temperature: float) -> None:
        """Set target temperature.

        Args:
            temperature: Temperature in Celsius (40-210°C)
        """
        temp = clamp_temperature(temperature, TEMP_MIN_CRAFTY, TEMP_MAX_CRAFTY)
        data = encode_temperature(temp)
        await self._write_characteristic(CRAFTY_CHAR_TARGET_TEMP, data)
        state = self._get_state()
        state.target_temperature = temp

    async def turn_heater_on(self) -> None:
        """Turn heater on.

        Note: The device may not turn on the heater if:
        - Device is on charger and in certain modes
        - Device is not "active" (powered on)
        - Safety conditions aren't met

        The actual heater status is verified by reading the status register.
        """
        await self._write_characteristic(CRAFTY_CHAR_HEATER_ON, b"\x01")
        # Read actual status to verify (device might not turn on if conditions aren't met)
        await asyncio.sleep(0.5)  # Give device time to process
        state = self._get_state()
        try:
            data = await self._read_characteristic(CRAFTY_CHAR_STATUS_REGISTER)
            if len(data) >= 10:
                status = decode_uint16(data[8:10])
                state.heater_on = bool(status & CRAFTY_STATUS_HEATER_ON)
                state.status_register = status
                if not state.heater_on:
                    _LOGGER.info(
                        "Heater command sent but device reports heater is off. "
                        "Device may be on charger or not active."
                    )
        except Exception as e:
            _LOGGER.warning("Failed to read heater status after turning on: %s", e)
            # Fallback to optimistic state
            state.heater_on = True

    async def turn_heater_off(self) -> None:
        """Turn heater off."""
        await self._write_characteristic(CRAFTY_CHAR_HEATER_OFF, b"\x01")
        # Read actual status to verify
        await asyncio.sleep(0.5)  # Give device time to process
        state = self._get_state()
        try:
            data = await self._read_characteristic(CRAFTY_CHAR_STATUS_REGISTER)
            if len(data) >= 10:
                status = decode_uint16(data[8:10])
                state.heater_on = bool(status & CRAFTY_STATUS_HEATER_ON)
                state.status_register = status
        except Exception as e:
            _LOGGER.warning("Failed to read heater status after turning off: %s", e)
            # Fallback to optimistic state
            state.heater_on = False

    async def set_led_brightness(self, brightness: int) -> None:
        """Set LED brightness.

        Args:
            brightness: Brightness level (0-100)
        """
        if brightness < 0 or brightness > 100:
            msg = f"LED brightness must be between 0 and 100, got {brightness}"
            raise ValueError(msg)
        data = encode_uint16(brightness)
        await self._write_characteristic(CRAFTY_CHAR_LED_BRIGHTNESS, data)
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
        await self._write_characteristic(CRAFTY_CHAR_AUTO_OFF, data)
        state = self._get_state()
        state.auto_off_time = seconds

    async def set_vibration(self, enabled: bool) -> None:
        """Set vibration enabled/disabled.

        Args:
            enabled: True to enable vibration, False to disable
        """
        # Read current value first
        try:
            data = await self._read_characteristic(CRAFTY_CHAR_PROJECT_STATUS_2)
            current_value = decode_uint16(data)
        except Exception:
            current_value = 0

        # Vibration is inverted: 0 = enabled, 1 = disabled
        if enabled:
            # Clear bit 0 (enable vibration)
            new_value = current_value & ~CRAFTY_PROJECT_STATUS2_VIBRATION_DISABLED
        else:
            # Set bit 0 (disable vibration)
            new_value = current_value | CRAFTY_PROJECT_STATUS2_VIBRATION_DISABLED

        data_bytes = encode_uint16(new_value)
        await self._write_characteristic(CRAFTY_CHAR_PROJECT_STATUS_2, data_bytes)
        state = self._get_state()
        state.vibration_enabled = enabled
        state.project_status_register_2 = new_value

    async def find_device(self) -> None:
        """Trigger find device (vibration/LED alert)."""
        await self._write_characteristic(CRAFTY_CHAR_FIND_DEVICE, b"\x01")

    def _handle_temperature_notification(self, data: bytes) -> None:
        """Handle temperature notification."""
        state = self._get_state()
        try:
            state.current_temperature = decode_temperature(bytearray(data))
            _LOGGER.debug("Temperature update: %s°C", state.current_temperature)
        except Exception as e:
            _LOGGER.warning("Error handling temperature notification: %s", e)

    def _handle_battery_notification(self, data: bytes) -> None:
        """Handle battery notification."""
        state = self._get_state()
        try:
            data_array = bytearray(data)
            if len(data_array) >= 1:
                state.battery_level = data_array[0]
                _LOGGER.debug("Battery update: %s%%", state.battery_level)
        except Exception as e:
            _LOGGER.warning("Error handling battery notification: %s", e)

    def _handle_status_notification(self, data: bytes) -> None:
        """Handle status register notification."""
        state = self._get_state()
        try:
            data_array = bytearray(data)
            if len(data_array) >= 10:
                # Last 2 bytes are status register
                state.status_register = decode_uint16(data_array[8:10])
                state.heater_on = bool(
                    state.status_register & CRAFTY_STATUS_HEATER_ON,
                )
                state.boost_mode = bool(
                    state.status_register & CRAFTY_STATUS_BOOST_MODE,
                )
                state.vibration_on_ready = bool(
                    state.status_register & CRAFTY_STATUS_VIBRATION_READY,
                )
                state.fahrenheit_mode = bool(
                    state.status_register & CRAFTY_STATUS_FAHRENHEIT,
                )
        except Exception as e:
            _LOGGER.warning("Error handling status register notification: %s", e)

    def _handle_project_status_notification(self, data: bytes) -> None:
        """Handle project status register notification."""
        state = self._get_state()
        try:
            state.project_status_register = decode_uint16(bytearray(data))
            state.device_active = bool(
                state.project_status_register & CRAFTY_PROJECT_STATUS_ACTIVE,
            )
            state.boost_mode = bool(
                state.project_status_register & CRAFTY_PROJECT_STATUS_BOOST_ENABLED,
            )
            state.superboost_mode = bool(
                state.project_status_register
                & CRAFTY_PROJECT_STATUS_SUPERBOOST_ENABLED,
            )
        except Exception as e:
            _LOGGER.warning(
                "Error handling project status register notification: %s", e
            )

    def _handle_project_status2_notification(self, data: bytes) -> None:
        """Handle project status register 2 notification."""
        state = self._get_state()
        try:
            state.project_status_register_2 = decode_uint16(bytearray(data))
            # Vibration is inverted: 0 = enabled, 1 = disabled
            state.vibration_enabled = not bool(
                state.project_status_register_2
                & CRAFTY_PROJECT_STATUS2_VIBRATION_DISABLED,
            )
        except Exception as e:
            _LOGGER.warning(
                "Error handling project status register 2 notification: %s",
                e,
            )

    def _handle_akku_status_notification(self, data: bytes) -> None:
        """Handle Akku status notification."""
        state = self._get_state()
        try:
            # Parse charging status from data
            data_array = bytearray(data)
            state.charging = len(data_array) > 0 and data_array[0] > 0
        except Exception as e:
            _LOGGER.warning("Error handling Akku status notification: %s", e)
