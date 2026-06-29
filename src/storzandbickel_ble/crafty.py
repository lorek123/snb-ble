"""Crafty/Crafty+ device implementation."""

import asyncio
import logging
from typing import TYPE_CHECKING

from bleak import BleakClient

from storzandbickel_ble.device import _PROGRAMMING_ERRORS, BaseDevice
from storzandbickel_ble.exceptions import InvalidDataError
from storzandbickel_ble.models import CraftyState, DeviceType
from storzandbickel_ble.protocol import (
    CRAFTY_AKKU_ERROR,
    CRAFTY_CHAR_AKKU_STATUS,
    CRAFTY_CHAR_AUTO_OFF,
    CRAFTY_CHAR_BATTERY,
    CRAFTY_CHAR_SICHERHEITSCODE,
    CRAFTY_SICHERHEITSCODE,
    CRAFTY_CHAR_BLE_VERSION,
    CRAFTY_CHAR_BOOST_TEMP,
    CRAFTY_CHAR_CURRENT_TEMP,
    CRAFTY_CHAR_HEATER_OFF,
    CRAFTY_CHAR_HEATER_ON,
    CRAFTY_CHAR_LED_BRIGHTNESS,
    CRAFTY_CHAR_PROJECT_STATUS,
    CRAFTY_CHAR_PROJECT_STATUS_2,
    CRAFTY_CHAR_STATUS_REGISTER,
    CRAFTY_CHAR_TARGET_TEMP,
    CRAFTY_CHAR_USAGE_HOURS,
    CRAFTY_CHAR_USAGE_MINUTES,
    CRAFTY_PROJECT_STATUS2_AUTO_BLE_SHUTDOWN,
    CRAFTY_PROJECT_STATUS2_CHARGE_LED_DISABLED,
    CRAFTY_PROJECT_STATUS2_FIND_DEVICE,
    CRAFTY_PROJECT_STATUS2_TEMP_REACHED,
    CRAFTY_PROJECT_STATUS2_VIBRATION_DISABLED,
    CRAFTY_PROJECT_STATUS_ACTIVE,
    CRAFTY_PROJECT_STATUS_BOOST_ENABLED,
    CRAFTY_PROJECT_STATUS_ERROR_BITS,
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
    error_finding,
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
            boost_temperature=None,
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

    @staticmethod
    def _apply_project_status2(state: CraftyState, value: int) -> None:
        """Decode project status register 2 into state fields.

        Shared by the polled read and the notification handler so the two paths
        can't drift. Vibration and charge-LED bits are inverted (set = disabled),
        as is the auto-BLE-shutdown bit (set = device sleeps BLE, so clear means
        permanent Bluetooth).
        """
        state.project_status_register_2 = value
        state.vibration_enabled = not bool(
            value & CRAFTY_PROJECT_STATUS2_VIBRATION_DISABLED
        )
        state.charge_led_enabled = not bool(
            value & CRAFTY_PROJECT_STATUS2_CHARGE_LED_DISABLED
        )
        state.permanent_bluetooth = not bool(
            value & CRAFTY_PROJECT_STATUS2_AUTO_BLE_SHUTDOWN
        )
        state.setpoint_reached = bool(value & CRAFTY_PROJECT_STATUS2_TEMP_REACHED)

    async def connect(self) -> None:
        """Connect to device and initialize."""
        if self._client is None:
            from bleak import BleakClient

            self._client = BleakClient(self.address)

        if not self._client.is_connected:
            await self._client.connect()

        self._set_connection_state(True)

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
        self._set_connection_state(False)

    async def _read_minimal_state(self) -> None:
        """Read minimal state for fast connection (only essential characteristics)."""
        state = self._get_state()
        try:
            # Read status register (contains serial and heater status)
            try:
                data = await self._read_characteristic(CRAFTY_CHAR_STATUS_REGISTER)
                if len(data) >= 10:
                    # Full format: 8-byte serial number + 2-byte status register
                    state.serial_number = decode_string(data[:8])
                    state.status_register = decode_uint16(data[8:10])
                elif len(data) >= 2:
                    # Short format: 2-byte status register only (some firmware versions)
                    state.status_register = decode_uint16(data[:2])
                if len(data) >= 2:
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

            async def read_boost_temp() -> None:
                try:
                    data = await self._read_characteristic(CRAFTY_CHAR_BOOST_TEMP)
                    state.boost_temperature = decode_temperature(data)
                except Exception as e:
                    _LOGGER.warning("Failed to read boost temperature: %s", e)

            async def read_ble_version() -> None:
                try:
                    data = await self._read_characteristic(CRAFTY_CHAR_BLE_VERSION)
                    state.ble_version = decode_string(data)
                except Exception as e:
                    _LOGGER.debug("Failed to read BLE version: %s", e)

            await asyncio.gather(
                read_temp(),
                read_target(),
                read_battery(),
                read_boost_temp(),
                read_ble_version(),
                return_exceptions=True,
            )

        except Exception as e:
            _LOGGER.error("Error reading minimal state: %s", e, exc_info=True)

    async def update_state(self) -> None:
        """Update device state by reading from device."""
        state = self._get_state()
        try:
            # Read status register (contains serial number in first 8 bytes)
            with self._tolerate("read status register"):
                data = await self._read_characteristic(CRAFTY_CHAR_STATUS_REGISTER)
                if len(data) >= 10:
                    # Full format: 8-byte serial number + 2-byte status register
                    state.serial_number = decode_string(data[:8])
                    state.status_register = decode_uint16(data[8:10])
                elif len(data) >= 2:
                    # Short format: 2-byte status register only (some firmware versions)
                    state.status_register = decode_uint16(data[:2])
                if len(data) >= 2:
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

            # Read current temperature
            with self._tolerate("read current temperature"):
                data = await self._read_characteristic(CRAFTY_CHAR_CURRENT_TEMP)
                state.current_temperature = decode_temperature(data)

            # Read target temperature
            with self._tolerate("read target temperature"):
                data = await self._read_characteristic(CRAFTY_CHAR_TARGET_TEMP)
                state.target_temperature = decode_temperature(data)

            # Read battery level
            with self._tolerate("read battery level"):
                data = await self._read_characteristic(CRAFTY_CHAR_BATTERY)
                if len(data) >= 1:
                    state.battery_level = data[0]

            # Read project status register
            with self._tolerate("read project status register"):
                data = await self._read_characteristic(CRAFTY_CHAR_PROJECT_STATUS)
                state.project_status_register = decode_uint16(data)
                state.device_active = bool(
                    state.project_status_register & CRAFTY_PROJECT_STATUS_ACTIVE,
                )
                # heater_on mirrors device_active — the project status ACTIVE bit
                # (char 0x93) is the authoritative heater state source. The status
                # register (char 0x52) may return serial/firmware data, not live status.
                state.heater_on = state.device_active
                state.boost_mode = bool(
                    state.project_status_register & CRAFTY_PROJECT_STATUS_BOOST_ENABLED,
                )
                state.superboost_mode = bool(
                    state.project_status_register
                    & CRAFTY_PROJECT_STATUS_SUPERBOOST_ENABLED,
                )

            # Read project status register 2
            with self._tolerate("read project status register 2"):
                data = await self._read_characteristic(CRAFTY_CHAR_PROJECT_STATUS_2)
                self._apply_project_status2(state, decode_uint16(data))

            # Read boost temperature
            with self._tolerate("read boost temperature"):
                data = await self._read_characteristic(CRAFTY_CHAR_BOOST_TEMP)
                state.boost_temperature = decode_temperature(data)

            # Read LED brightness
            with self._tolerate("read LED brightness"):
                data = await self._read_characteristic(CRAFTY_CHAR_LED_BRIGHTNESS)
                state.led_brightness = decode_uint16(data)

            # Read auto-off time
            with self._tolerate("read auto-off time"):
                data = await self._read_characteristic(CRAFTY_CHAR_AUTO_OFF)
                state.auto_off_time = decode_uint16(data)

            # Read usage hours
            with self._tolerate("read usage hours"):
                data = await self._read_characteristic(CRAFTY_CHAR_USAGE_HOURS)
                state.usage_hours = decode_uint16(data)

            # Read usage minutes
            with self._tolerate("read usage minutes"):
                data = await self._read_characteristic(CRAFTY_CHAR_USAGE_MINUTES)
                state.usage_minutes = decode_uint16(data)

        except _PROGRAMMING_ERRORS:
            # A library bug, not a device problem — surface it with its real type.
            raise
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

    async def set_boost_temperature(self, boost_temperature: float) -> None:
        """Set boost temperature offset (1-99°C)."""
        boost = int(max(1, min(99, round(boost_temperature))))
        data = encode_temperature(float(boost))
        await self._write_characteristic(CRAFTY_CHAR_BOOST_TEMP, data)
        state = self._get_state()
        state.boost_temperature = float(boost)

    async def turn_heater_on(self) -> None:
        """Turn heater on.

        Note: The device may not turn on the heater if:
        - Device is on charger and in certain modes
        - Device is not "active" (powered on)
        - Safety conditions aren't met

        The actual heater status is verified by reading the status register.
        """
        await self._write_characteristic(CRAFTY_CHAR_HEATER_ON, b"\x00\x00")
        await asyncio.sleep(0.5)
        state = self._get_state()
        try:
            data = await self._read_characteristic(CRAFTY_CHAR_STATUS_REGISTER)
            if len(data) >= 10:
                status = decode_uint16(data[8:10])
            elif len(data) >= 2:
                status = decode_uint16(data[:2])
            else:
                raise ValueError(f"Unexpected status register length: {len(data)}")
            state.heater_on = bool(status & CRAFTY_STATUS_HEATER_ON)
            state.status_register = status
            if not state.heater_on:
                _LOGGER.info(
                    "Heater command sent but device reports heater is off; "
                    "device may be on charger or not active."
                )
        except Exception as e:
            _LOGGER.warning("Failed to read heater status after turning on: %s", e)
            state.heater_on = True

    async def turn_heater_off(self) -> None:
        """Turn heater off."""
        await self._write_characteristic(CRAFTY_CHAR_HEATER_OFF, b"\x00\x00")
        await asyncio.sleep(0.5)
        state = self._get_state()
        try:
            data = await self._read_characteristic(CRAFTY_CHAR_STATUS_REGISTER)
            if len(data) >= 10:
                status = decode_uint16(data[8:10])
            elif len(data) >= 2:
                status = decode_uint16(data[:2])
            else:
                raise ValueError(f"Unexpected status register length: {len(data)}")
            state.heater_on = bool(status & CRAFTY_STATUS_HEATER_ON)
            state.status_register = status
        except Exception as e:
            _LOGGER.warning("Failed to read heater status after turning off: %s", e)
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
        """Set auto-off time in seconds (0 = disabled).

        The official S&B app requires the Sicherheitscode (815) to be written
        to char 0x1B3 immediately before writing the auto-off value to char 0x61.
        """
        if seconds < 0:
            msg = f"Auto-off time must be >= 0, got {seconds}"
            raise ValueError(msg)
        await self._write_characteristic(
            CRAFTY_CHAR_SICHERHEITSCODE, encode_uint16(CRAFTY_SICHERHEITSCODE)
        )
        await self._write_characteristic(CRAFTY_CHAR_AUTO_OFF, encode_uint16(seconds))
        state = self._get_state()
        state.auto_off_time = seconds

    async def _write_project_status2_bit(self, mask: int, bit_set: bool) -> None:
        """Read register 2, set or clear `mask`, write it back, and refresh state.

        The read-modify-write keeps the other bits intact; reusing
        _apply_project_status2 to re-derive state means every register-2 setter
        leaves the same consistent view as a poll would.
        """
        try:
            current_value = decode_uint16(
                await self._read_characteristic(CRAFTY_CHAR_PROJECT_STATUS_2)
            )
        except Exception:
            current_value = 0
        new_value = current_value | mask if bit_set else current_value & ~mask
        await self._write_characteristic(
            CRAFTY_CHAR_PROJECT_STATUS_2, encode_uint16(new_value)
        )
        self._apply_project_status2(self._get_state(), new_value)

    async def set_vibration(self, enabled: bool) -> None:
        """Enable/disable readiness vibration (bit inverted: set = disabled)."""
        await self._write_project_status2_bit(
            CRAFTY_PROJECT_STATUS2_VIBRATION_DISABLED, not enabled
        )

    async def set_charge_led(self, enabled: bool) -> None:
        """Enable/disable the charge-indicator LED (bit inverted: set = disabled)."""
        await self._write_project_status2_bit(
            CRAFTY_PROJECT_STATUS2_CHARGE_LED_DISABLED, not enabled
        )

    async def set_permanent_bluetooth(self, enabled: bool) -> None:
        """Keep Bluetooth reachable while the device sleeps.

        The hardware bit enables auto-BLE-shutdown, so permanent Bluetooth is the
        cleared state.
        """
        await self._write_project_status2_bit(
            CRAFTY_PROJECT_STATUS2_AUTO_BLE_SHUTDOWN, not enabled
        )

    async def toggle_boost_mode(self) -> None:
        """Toggle boost mode on/off in the project status register."""
        try:
            data = await self._read_characteristic(CRAFTY_CHAR_PROJECT_STATUS)
            current_value = decode_uint16(data)
        except Exception:
            current_value = self._get_state().project_status_register

        enabled = not bool(current_value & CRAFTY_PROJECT_STATUS_BOOST_ENABLED)
        if enabled:
            new_value = current_value | CRAFTY_PROJECT_STATUS_BOOST_ENABLED
        else:
            new_value = current_value & ~CRAFTY_PROJECT_STATUS_BOOST_ENABLED

        await self._write_characteristic(
            CRAFTY_CHAR_PROJECT_STATUS, encode_uint16(new_value)
        )
        state = self._get_state()
        state.boost_mode = enabled
        state.project_status_register = new_value

    async def set_superboost(self, enabled: bool) -> None:
        """Enable or disable superboost mode.

        Writes the SUPERBOOST_ENABLED bit in the project status register.
        Note: superboost only activates while the heater is on and device is active.
        """
        try:
            data = await self._read_characteristic(CRAFTY_CHAR_PROJECT_STATUS)
            current_value = decode_uint16(data)
        except Exception:
            current_value = 0

        if enabled:
            new_value = current_value | CRAFTY_PROJECT_STATUS_SUPERBOOST_ENABLED
        else:
            new_value = current_value & ~CRAFTY_PROJECT_STATUS_SUPERBOOST_ENABLED

        await self._write_characteristic(
            CRAFTY_CHAR_PROJECT_STATUS, encode_uint16(new_value)
        )
        state = self._get_state()
        state.superboost_mode = enabled
        state.project_status_register = new_value

    async def find_device(self) -> None:
        """Trigger find device (vibration/LED alert, auto-clears after 30 s).

        Sets MASK_PRJSTAT2_SIGNALGEBER_FIND_DEVICE_ENABLE (bit 3) in
        prjStatusReg2, matching the official S&B app behaviour.
        """
        state = self._get_state()
        new_val = state.project_status_register_2 | CRAFTY_PROJECT_STATUS2_FIND_DEVICE
        await self._write_characteristic(
            CRAFTY_CHAR_PROJECT_STATUS_2, encode_uint16(new_val)
        )
        state.project_status_register_2 = new_val

    async def run_analysis(self) -> dict[str, object]:
        """Run a local Crafty diagnostics report (no cloud upload).

        Reports the set error bits (detection) and the raw registers for support.
        Per-bit causes are decoded server-side, except the akku charger/cable
        error flag, which is known locally.
        """
        await self.update_state()
        state = self.state
        warnings: list[str] = []

        if state.led_brightness < 10:
            warnings.append("LED brightness is low.")
        if not state.vibration_enabled:
            warnings.append("Vibration is disabled.")
        if not state.device_active:
            warnings.append("Device is not active.")

        akku = 0
        try:
            akku = decode_uint16(
                await self._read_characteristic(CRAFTY_CHAR_AKKU_STATUS)
            )
        except Exception as err:  # noqa: BLE001
            _LOGGER.debug("Akku status register unavailable during analysis: %s", err)

        findings: list[dict[str, object]] = []
        proj = error_finding(
            "project_status_register",
            state.project_status_register,
            CRAFTY_PROJECT_STATUS_ERROR_BITS,
        )
        if proj is not None:
            findings.append(proj)
        charger = error_finding(
            "akku_status",
            akku,
            CRAFTY_AKKU_ERROR,
            {CRAFTY_AKKU_ERROR: "charger or cable error"},
        )
        if charger is not None:
            findings.append(charger)

        errors = [
            f"{f['source']} error flags set: {f['bits']}"
            + (f" ({f['meaning']})" if f["meaning"] else "")
            for f in findings
        ]
        return {
            "ok": not errors,
            "warnings": warnings,
            "errors": errors,
            "findings": findings,
            "diagnostics": {
                "project_status_register": f"0x{state.project_status_register:04x}",
                "project_status_register_2": f"0x{state.project_status_register_2:04x}",
                "akku_status": f"0x{akku:04x}",
            },
        }

    def _handle_temperature_notification(self, data: bytes) -> None:
        """Handle temperature notification."""
        state = self._get_state()
        with self._tolerate("handle temperature notification"):
            state.current_temperature = decode_temperature(bytearray(data))
            _LOGGER.debug("Temperature update: %s°C", state.current_temperature)

    def _handle_battery_notification(self, data: bytes) -> None:
        """Handle battery notification."""
        state = self._get_state()
        with self._tolerate("handle battery notification"):
            data_array = bytearray(data)
            if len(data_array) >= 1:
                state.battery_level = data_array[0]
                _LOGGER.debug("Battery update: %s%%", state.battery_level)

    def _handle_status_notification(self, data: bytes) -> None:
        """Handle status register notification."""
        state = self._get_state()
        with self._tolerate("handle status register notification"):
            data_array = bytearray(data)
            if len(data_array) >= 10:
                # Full format: 8-byte serial number + 2-byte status register
                state.status_register = decode_uint16(data_array[8:10])
            elif len(data_array) >= 2:
                # Short format: 2-byte status register only (some firmware versions)
                state.status_register = decode_uint16(data_array[:2])
            if len(data_array) >= 2:
                # Do NOT derive heater_on from this register — char 0x52 returns
                # serial/firmware data, not live status. heater_on is set from the
                # project status register (char 0x93) ACTIVE bit instead.
                state.vibration_on_ready = bool(
                    state.status_register & CRAFTY_STATUS_VIBRATION_READY,
                )
                state.fahrenheit_mode = bool(
                    state.status_register & CRAFTY_STATUS_FAHRENHEIT,
                )

    def _handle_project_status_notification(self, data: bytes) -> None:
        """Handle project status register notification."""
        state = self._get_state()
        with self._tolerate("handle project status register notification"):
            state.project_status_register = decode_uint16(bytearray(data))
            state.device_active = bool(
                state.project_status_register & CRAFTY_PROJECT_STATUS_ACTIVE,
            )
            state.heater_on = state.device_active
            state.boost_mode = bool(
                state.project_status_register & CRAFTY_PROJECT_STATUS_BOOST_ENABLED,
            )
            state.superboost_mode = bool(
                state.project_status_register
                & CRAFTY_PROJECT_STATUS_SUPERBOOST_ENABLED,
            )

    def _handle_project_status2_notification(self, data: bytes) -> None:
        """Handle project status register 2 notification."""
        state = self._get_state()
        with self._tolerate("handle project status register 2 notification"):
            self._apply_project_status2(state, decode_uint16(bytearray(data)))

    def _handle_akku_status_notification(self, data: bytes) -> None:
        """Handle Akku status notification (akkuStatusReg2 — error diagnostics only)."""
        with self._tolerate("handle Akku status notification"):
            val = int.from_bytes(data[:2], "little") if len(data) >= 2 else 0
            if val & 0x8000:
                _LOGGER.warning(
                    "Crafty charger/cable error reported (akkuStatusReg2 bit 15)"
                )
