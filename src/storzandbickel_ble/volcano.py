"""Volcano Hybrid device implementation."""

import asyncio
import logging

from bleak import BleakClient

from storzandbickel_ble.device import _PROGRAMMING_ERRORS, BaseDevice
from storzandbickel_ble.exceptions import InvalidDataError
from storzandbickel_ble.models import DeviceType, TemperatureUnit, VolcanoState
from storzandbickel_ble.protocol import (
    TEMP_MAX_VOLCANO,
    TEMP_MIN_VOLCANO,
    VOLCANO_CHAR_AUTO_OFF,
    VOLCANO_CHAR_AUTO_OFF_COUNTDOWN,
    VOLCANO_CHAR_CURRENT_TEMP,
    VOLCANO_CHAR_FIRMWARE_VERSION,
    VOLCANO_CHAR_HEATER_OFF,
    VOLCANO_CHAR_HEATER_ON,
    VOLCANO_CHAR_HEATING_HOURS,
    VOLCANO_CHAR_HEATING_MINUTES,
    VOLCANO_CHAR_HISTORY_1,
    VOLCANO_CHAR_HISTORY_2,
    VOLCANO_CHAR_LED_BRIGHTNESS,
    VOLCANO_CHAR_PUMP_OFF,
    VOLCANO_CHAR_PUMP_ON,
    VOLCANO_CHAR_SERIAL_NUMBER,
    VOLCANO_CHAR_STATUS_REGISTER_1,
    VOLCANO_CHAR_STATUS_REGISTER_2,
    VOLCANO_CHAR_STATUS_REGISTER_3,
    VOLCANO_CHAR_TARGET_TEMP,
    VOLCANO_LED_BRIGHTNESS_MAX,
    VOLCANO_LED_BRIGHTNESS_MIN,
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
    encode_volcano_register_bits,
    error_finding,
)

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
            led_brightness=50,
            auto_off_time=0,
            auto_off_countdown=0,
            heating_hours=0,
            heating_minutes=0,
        )

    @staticmethod
    def _apply_status_register_2(state: VolcanoState, value: int) -> None:
        """Decode status register 2. Display-on-cooling bit is inverted (set = off)."""
        state.status_register_2 = value
        state.fahrenheit_mode = bool(value & VOLCANO_STATUS2_FAHRENHEIT)
        state.display_on_cooling = not bool(value & VOLCANO_STATUS2_DISPLAY_COOLING)

    @staticmethod
    def _apply_status_register_3(state: VolcanoState, value: int) -> None:
        """Decode status register 3. Vibration-on-ready bit is inverted (set = off)."""
        state.status_register_3 = value
        state.vibration_on_ready = not bool(value & VOLCANO_STATUS3_VIBRATION_READY)

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
        await self._start_notifications(
            VOLCANO_CHAR_AUTO_OFF_COUNTDOWN,
            self._handle_auto_off_countdown_notification,
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
            with self._tolerate("read firmware version"):
                data = await self._read_characteristic(VOLCANO_CHAR_FIRMWARE_VERSION)
                state.firmware_version = decode_string(data)

            # Read serial number
            with self._tolerate("read serial number"):
                data = await self._read_characteristic(VOLCANO_CHAR_SERIAL_NUMBER)
                state.serial_number = decode_string(data)

            # Read current temperature
            with self._tolerate("read current temperature"):
                data = await self._read_characteristic(VOLCANO_CHAR_CURRENT_TEMP)
                state.current_temperature = decode_temperature(data)

            # Read target temperature
            with self._tolerate("read target temperature"):
                data = await self._read_characteristic(VOLCANO_CHAR_TARGET_TEMP)
                state.target_temperature = decode_temperature(data)

            # Read status registers
            with self._tolerate("read status register 1"):
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

            with self._tolerate("read status register 2"):
                data = await self._read_characteristic(VOLCANO_CHAR_STATUS_REGISTER_2)
                self._apply_status_register_2(state, decode_uint16(data))

            with self._tolerate("read status register 3"):
                data = await self._read_characteristic(VOLCANO_CHAR_STATUS_REGISTER_3)
                self._apply_status_register_3(state, decode_uint16(data))

            # Read LED brightness
            with self._tolerate("read LED brightness"):
                data = await self._read_characteristic(VOLCANO_CHAR_LED_BRIGHTNESS)
                state.led_brightness = decode_uint16(data)

            # Read auto-off time
            with self._tolerate("read auto-off time"):
                data = await self._read_characteristic(VOLCANO_CHAR_AUTO_OFF)
                state.auto_off_time = decode_uint16(data)

            # Read auto-off countdown
            with self._tolerate("read auto-off countdown"):
                data = await self._read_characteristic(VOLCANO_CHAR_AUTO_OFF_COUNTDOWN)
                state.auto_off_countdown = decode_uint16(data)

            # Read heating hours
            with self._tolerate("read heating hours"):
                data = await self._read_characteristic(VOLCANO_CHAR_HEATING_HOURS)
                state.heating_hours = decode_uint16(data)

            # Read heating minutes
            with self._tolerate("read heating minutes"):
                data = await self._read_characteristic(VOLCANO_CHAR_HEATING_MINUTES)
                state.heating_minutes = decode_uint16(data)

        except _PROGRAMMING_ERRORS:
            # A library bug, not a device problem — surface it with its real type.
            raise
        except Exception as e:
            _LOGGER.exception("Error updating state")
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
            brightness: Brightness in percent (0-100; the vendor app uses steps of 10)
        """
        if not VOLCANO_LED_BRIGHTNESS_MIN <= brightness <= VOLCANO_LED_BRIGHTNESS_MAX:
            msg = (
                f"LED brightness must be between {VOLCANO_LED_BRIGHTNESS_MIN} and "
                f"{VOLCANO_LED_BRIGHTNESS_MAX}, got {brightness}"
            )
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

    async def _change_register_bits(
        self, char_uuid: str, mask: int, set_bits: bool
    ) -> None:
        """Set or clear bits in status register 2/3 via the 4-byte command."""
        await self._write_characteristic(
            char_uuid, encode_volcano_register_bits(mask, set_bits)
        )

    async def _write_register_image(self, char_uuid: str, old: int, new: int) -> None:
        """Move a register from ``old`` to ``new`` using set/clear commands."""
        to_set = new & ~old & 0xFFFF
        to_clear = old & ~new & 0xFFFF
        if to_set:
            await self._change_register_bits(char_uuid, to_set, True)
        if to_clear:
            await self._change_register_bits(char_uuid, to_clear, False)

    async def set_status_register_2(self, value: int) -> None:
        """Set status register 2 (display settings, etc.).

        The firmware takes bit set/clear commands, not a register image, so this
        sends the difference from the last known value.

        Args:
            value: Desired status register 2 value
        """
        state = self._get_state()
        await self._write_register_image(
            VOLCANO_CHAR_STATUS_REGISTER_2, state.status_register_2, value
        )
        self._apply_status_register_2(state, value)

    async def set_status_register_3(self, value: int) -> None:
        """Set status register 3 (vibration settings, etc.).

        Args:
            value: Desired status register 3 value
        """
        state = self._get_state()
        await self._write_register_image(
            VOLCANO_CHAR_STATUS_REGISTER_3, state.status_register_3, value
        )
        self._apply_status_register_3(state, value)

    async def _set_register_bit(
        self, char_uuid: str, mask: int, set_bits: bool
    ) -> None:
        state = self._get_state()
        await self._change_register_bits(char_uuid, mask, set_bits)
        if char_uuid == VOLCANO_CHAR_STATUS_REGISTER_2:
            old = state.status_register_2
            self._apply_status_register_2(
                state, (old | mask) if set_bits else (old & ~mask)
            )
        else:
            old = state.status_register_3
            self._apply_status_register_3(
                state, (old | mask) if set_bits else (old & ~mask)
            )

    async def set_temperature_unit(self, unit: TemperatureUnit) -> None:
        """Set display temperature unit."""
        await self._set_register_bit(
            VOLCANO_CHAR_STATUS_REGISTER_2,
            VOLCANO_STATUS2_FAHRENHEIT,
            unit == TemperatureUnit.FAHRENHEIT,
        )

    async def set_display_on_cooling(self, enabled: bool) -> None:
        """Enable/disable showing temperature during cool-down."""
        # Inverted bit: set = disabled.
        await self._set_register_bit(
            VOLCANO_CHAR_STATUS_REGISTER_2,
            VOLCANO_STATUS2_DISPLAY_COOLING,
            not enabled,
        )

    async def set_vibration_on_ready(self, enabled: bool) -> None:
        """Enable/disable vibration on setpoint reached."""
        # Inverted bit: set = disabled.
        await self._set_register_bit(
            VOLCANO_CHAR_STATUS_REGISTER_3,
            VOLCANO_STATUS3_VIBRATION_READY,
            not enabled,
        )

    async def run_workflow(
        self,
        steps: list[tuple[float, float, float]],
        wait_for_temperature: bool = True,
        temperature_tolerance: float = 1.0,
        poll_interval: float = 1.5,
    ) -> None:
        """Run a custom Volcano workflow.

        A workflow is a sequence of ``(target_temperature, hold_seconds,
        pump_seconds)`` steps: set the temperature, optionally wait for the
        setpoint, hold for ``hold_seconds``, then run the pump for
        ``pump_seconds``. This is the same timed heat+pump orchestration the
        built-in presets use, exposed so callers can run their own balloon/flow
        sequences.

        Args:
            steps: Sequence of (target_temp_celsius, hold_seconds, pump_seconds).
            wait_for_temperature: Wait for the setpoint before the hold/pump phase.
            temperature_tolerance: Acceptable absolute delta from target.
            poll_interval: Poll interval while waiting for the setpoint.
        """
        if not steps:
            msg = "Workflow must have at least one step"
            raise ValueError(msg)

        if not self.state.heater_on:
            await self.turn_heater_on()

        for target_temp, hold_seconds, pump_seconds in steps:
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

    async def run_workflow_preset(
        self,
        preset: str,
        wait_for_temperature: bool = True,
        temperature_tolerance: float = 1.0,
        poll_interval: float = 1.5,
    ) -> None:
        """Run a built-in Volcano workflow preset.

        Args:
            preset: One of `balloon`, `flow1`, `flow2`, `flow3`.
            wait_for_temperature: Wait for setpoint before hold/pump phase.
            temperature_tolerance: Acceptable absolute delta from target.
            poll_interval: Poll interval while waiting for setpoint.
        """
        if preset not in VOLCANO_WORKFLOW_PRESETS:
            msg = f"Unknown workflow preset: {preset}"
            raise ValueError(msg)
        await self.run_workflow(
            VOLCANO_WORKFLOW_PRESETS[preset],
            wait_for_temperature=wait_for_temperature,
            temperature_tolerance=temperature_tolerance,
            poll_interval=poll_interval,
        )

    async def run_analysis(self) -> dict[str, object]:
        """Run a local Volcano diagnostics report (no cloud upload).

        The vendor app only flags *whether* error bits are set and uploads the
        registers for server-side decoding, so this reports the set error bits
        (detection) and the raw registers/history for support — not a
        human-readable per-bit cause, which is not available client-side.
        """
        await self.update_state()
        state = self.state
        warnings: list[str] = []

        if state.led_brightness < 25:
            warnings.append("Display brightness is low.")
        if not state.display_on_cooling:
            warnings.append("Display-on-cooling is disabled.")
        if not state.vibration_on_ready:
            warnings.append("Vibration-on-ready is disabled.")

        findings: list[dict[str, object]] = []
        for source, value, mask in (
            ("status_register_1", state.status_register_1, VOLCANO_STATUS1_ERROR_BITS),
            ("status_register_2", state.status_register_2, VOLCANO_STATUS2_ERROR_BITS),
        ):
            finding = error_finding(source, value, mask)
            if finding is not None:
                findings.append(finding)

        history_1 = ""
        history_2 = ""
        try:
            history_1 = (await self._read_characteristic(VOLCANO_CHAR_HISTORY_1)).hex()
            history_2 = (await self._read_characteristic(VOLCANO_CHAR_HISTORY_2)).hex()
        except Exception as err:
            _LOGGER.debug("History registers unavailable during analysis: %s", err)

        errors = [f"{f['source']} error flags set: {f['bits']}" for f in findings]
        return {
            "ok": not errors,
            "warnings": warnings,
            "errors": errors,
            "findings": findings,
            "diagnostics": {
                "status_register_1": f"0x{state.status_register_1:04x}",
                "status_register_2": f"0x{state.status_register_2:04x}",
                "status_register_3": f"0x{state.status_register_3:04x}",
                "history_1": history_1,
                "history_2": history_2,
            },
        }

    def _handle_temperature_notification(self, data: bytes) -> None:
        """Handle temperature notification."""
        state = self._get_state()
        with self._tolerate("handle temperature notification"):
            state.current_temperature = decode_temperature(bytearray(data))
            _LOGGER.debug("Temperature update: %s°C", state.current_temperature)

    def _handle_status1_notification(self, data: bytes) -> None:
        """Handle status register 1 notification."""
        state = self._get_state()
        with self._tolerate("handle status register 1 notification"):
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

    def _handle_status2_notification(self, data: bytes) -> None:
        """Handle status register 2 notification."""
        state = self._get_state()
        with self._tolerate("handle status register 2 notification"):
            self._apply_status_register_2(state, decode_uint16(bytearray(data)))

    def _handle_status3_notification(self, data: bytes) -> None:
        """Handle status register 3 notification."""
        state = self._get_state()
        with self._tolerate("handle status register 3 notification"):
            self._apply_status_register_3(state, decode_uint16(bytearray(data)))

    def _handle_heating_hours_notification(self, data: bytes) -> None:
        """Handle heating hours notification."""
        state = self._get_state()
        with self._tolerate("handle heating hours notification"):
            state.heating_hours = decode_uint16(bytearray(data))

    def _handle_heating_minutes_notification(self, data: bytes) -> None:
        """Handle heating minutes notification."""
        state = self._get_state()
        with self._tolerate("handle heating minutes notification"):
            state.heating_minutes = decode_uint16(bytearray(data))

    def _handle_auto_off_countdown_notification(self, data: bytes) -> None:
        """Handle auto-off countdown notification."""
        state = self._get_state()
        with self._tolerate("handle auto-off countdown notification"):
            state.auto_off_countdown = decode_uint16(bytearray(data))
