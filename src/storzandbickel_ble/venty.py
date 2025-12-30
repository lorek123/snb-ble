"""Venty device implementation."""

import asyncio
import logging
from typing import TYPE_CHECKING

from bleak import BleakClient

from storzandbickel_ble.device import BaseDevice
from storzandbickel_ble.exceptions import InvalidDataError
from storzandbickel_ble.models import (
    HeaterMode,
    TemperatureUnit,
    VentyState,
    DeviceType,
)
from storzandbickel_ble.protocol import (
    TEMP_MAX_VENTY,
    TEMP_MIN_VENTY,
    VENTY_CHAR_DEVICE_NAME,
    VENTY_CHAR_MAIN,
    VENTY_CMD_FIND_DEVICE,
    VENTY_CMD_FIRMWARE_VERSION,
    VENTY_CMD_SERIAL_NUMBER,
    VENTY_CMD_SETTINGS,
    VENTY_CMD_STATUS_CONTROL,
    VENTY_CMD_USAGE_STATS,
    VENTY_MASK_BOOST_WRITE,
    VENTY_MASK_HEATER_WRITE,
    VENTY_MASK_SETTINGS_WRITE,
    VENTY_MASK_SUPERBOOST_WRITE,
    VENTY_MASK_TEMP_WRITE,
    VENTY_SETTING_BOOST_VISUALIZATION,
    VENTY_SETTING_ECO_MODE_CHARGE,
    VENTY_SETTING_ECO_MODE_VOLTAGE,
    VENTY_SETTING_UNIT,
    build_venty_command,
    clamp_temperature,
    decode_string,
)

if TYPE_CHECKING:
    pass

_LOGGER = logging.getLogger(__name__)


class VentyDevice(BaseDevice):
    """Venty device."""

    def __init__(
        self,
        address: str,
        client: BleakClient | None = None,
        name: str | None = None,
    ) -> None:
        """Initialize Venty device.

        Args:
            address: BLE MAC address
            client: Optional BleakClient instance
            name: Optional device name
        """
        super().__init__(address, client, name)
        # Initialize with all required fields to satisfy mypy
        self._state = VentyState(
            current_temperature=None,
            target_temperature=None,
            boost_offset=0,
            superboost_offset=0,
            battery_level=0,
            auto_shutoff_countdown=0,
        )
        self._response_event: asyncio.Event | None = None
        self._response_data: bytearray | None = None

    @property
    def device_type(self) -> DeviceType:
        """Return device type."""
        return DeviceType.VENTY

    @property
    def state(self) -> VentyState:
        """Return current device state."""
        state = self._state
        assert state is not None, "State should never be None"
        assert isinstance(state, VentyState), "State must be VentyState"
        return state

    def _get_state(self) -> VentyState:
        """Get state with type narrowing."""
        state = self._state
        assert state is not None, "State should never be None"
        assert isinstance(state, VentyState), "State must be VentyState"
        return state

    async def connect(self) -> None:
        """Connect to device and initialize."""
        if self._client is None:
            from bleak import BleakClient

            self._client = BleakClient(self.address)

        if not self._client.is_connected:
            await self._client.connect()

        self._connected = True

        # Enable notifications for main characteristic
        # Service discovery happens automatically when we access characteristics
        await self._start_notifications(
            VENTY_CHAR_MAIN,
            self._handle_main_notification,
        )

        # Read initial state
        await self.update_state()

        # Start periodic updates (command 0x01 with byte 1 = 0x06)
        await self._send_command(
            VENTY_CMD_STATUS_CONTROL,
            mask=0x06,  # Start periodic updates
        )

    async def disconnect(self) -> None:
        """Disconnect from device."""
        await self._stop_all_notifications()
        if self._client is not None and self._client.is_connected:
            await self._client.disconnect()
        self._connected = False

    async def update_state(self) -> None:
        """Update device state by reading from device."""
        try:
            # Request firmware version
            await self._send_command(VENTY_CMD_FIRMWARE_VERSION)
            await asyncio.sleep(0.1)

            # Request serial number
            await self._send_command(VENTY_CMD_SERIAL_NUMBER)
            await asyncio.sleep(0.1)

            # Request usage statistics
            await self._send_command(VENTY_CMD_USAGE_STATS)
            await asyncio.sleep(0.1)

            # Request settings
            await self._send_command(VENTY_CMD_SETTINGS)
            await asyncio.sleep(0.1)

            # Request status
            await self._send_command(VENTY_CMD_STATUS_CONTROL)
            await asyncio.sleep(0.1)

            # Also try reading device name (contains serial number)
            try:
                data = await self._read_characteristic(VENTY_CHAR_DEVICE_NAME)
                # Device name may contain serial number
                name_str = decode_string(data)
                if name_str:
                    state = self._get_state()
                    if not state.serial_number:
                        state.serial_number = name_str
            except Exception as e:
                _LOGGER.warning("Failed to read device name: %s", e)

        except Exception as e:
            _LOGGER.error("Error updating state: %s", e, exc_info=True)
            raise InvalidDataError(f"Failed to update state: {e}") from e

    async def _send_command(
        self,
        cmd: int,
        mask: int = 0,
        wait_response: bool = True,
        timeout: float = 2.0,
    ) -> bytearray | None:
        """Send a command and optionally wait for response.

        Args:
            cmd: Command byte
            mask: Command mask (for command 0x01)
            wait_response: Whether to wait for response
            timeout: Response timeout in seconds

        Returns:
            Response data or None if not waiting
        """
        packet = build_venty_command(cmd, mask=mask)
        await self._write_characteristic(VENTY_CHAR_MAIN, packet, response=False)

        if not wait_response:
            return None

        # Wait for response
        self._response_event = asyncio.Event()
        self._response_data = None

        try:
            await asyncio.wait_for(self._response_event.wait(), timeout=timeout)
            return self._response_data
        except asyncio.TimeoutError:
            _LOGGER.warning("Command response timeout for command 0x%02X", cmd)
            return None

    async def set_target_temperature(self, temperature: float) -> None:
        """Set target temperature.

        Args:
            temperature: Temperature in Celsius (40-210°C)
        """
        temp = clamp_temperature(temperature, TEMP_MIN_VENTY, TEMP_MAX_VENTY)
        temp_raw = int(temp * 10)

        packet = build_venty_command(
            VENTY_CMD_STATUS_CONTROL,
            mask=VENTY_MASK_TEMP_WRITE,
            target_temp=temp_raw,
        )
        await self._write_characteristic(VENTY_CHAR_MAIN, packet, response=False)
        state = self._get_state()
        state.target_temperature = temp

    async def set_heater_mode(self, mode: HeaterMode) -> None:
        """Set heater mode.

        Args:
            mode: Heater mode (OFF, NORMAL, BOOST, SUPERBOOST)
        """
        mask = VENTY_MASK_HEATER_WRITE
        if mode == HeaterMode.BOOST:
            mask |= VENTY_MASK_BOOST_WRITE
        elif mode == HeaterMode.SUPERBOOST:
            mask |= VENTY_MASK_SUPERBOOST_WRITE

        packet = build_venty_command(
            VENTY_CMD_STATUS_CONTROL,
            mask=mask,
            heater_mode=mode.value,
        )
        await self._write_characteristic(VENTY_CHAR_MAIN, packet, response=False)
        state = self._get_state()
        state.heater_mode = mode

    async def turn_heater_on(self) -> None:
        """Turn heater on (normal mode)."""
        await self.set_heater_mode(HeaterMode.NORMAL)

    async def turn_heater_off(self) -> None:
        """Turn heater off."""
        await self.set_heater_mode(HeaterMode.OFF)

    async def set_boost_offset(self, offset: int) -> None:
        """Set boost temperature offset.

        Args:
            offset: Temperature offset in degrees
        """
        if offset < 0:
            msg = f"Boost offset must be >= 0, got {offset}"
            raise ValueError(msg)

        packet = build_venty_command(
            VENTY_CMD_STATUS_CONTROL,
            mask=VENTY_MASK_BOOST_WRITE,
            boost_offset=offset,
        )
        await self._write_characteristic(VENTY_CHAR_MAIN, packet, response=False)
        state = self._get_state()
        state.boost_offset = offset

    async def set_superboost_offset(self, offset: int) -> None:
        """Set superboost temperature offset.

        Args:
            offset: Temperature offset in degrees
        """
        if offset < 0:
            msg = f"Superboost offset must be >= 0, got {offset}"
            raise ValueError(msg)

        packet = build_venty_command(
            VENTY_CMD_STATUS_CONTROL,
            mask=VENTY_MASK_SUPERBOOST_WRITE,
            superboost_offset=offset,
        )
        await self._write_characteristic(VENTY_CHAR_MAIN, packet, response=False)
        state = self._get_state()
        state.superboost_offset = offset

    async def set_temperature_unit(self, unit: TemperatureUnit) -> None:
        """Set temperature unit.

        Args:
            unit: Temperature unit (CELSIUS or FAHRENHEIT)
        """
        # Read current settings first
        state = self._get_state()
        current_settings = 0
        if state.unit == TemperatureUnit.FAHRENHEIT:
            current_settings |= VENTY_SETTING_UNIT

        # Update unit bit
        if unit == TemperatureUnit.FAHRENHEIT:
            current_settings |= VENTY_SETTING_UNIT
        else:
            current_settings &= ~VENTY_SETTING_UNIT

        packet = build_venty_command(
            VENTY_CMD_STATUS_CONTROL,
            mask=VENTY_MASK_SETTINGS_WRITE,
            settings=current_settings,
        )
        await self._write_characteristic(VENTY_CHAR_MAIN, packet, response=False)
        state.unit = unit

    async def set_eco_mode_charge(self, enabled: bool) -> None:
        """Set eco mode charge.

        Args:
            enabled: True to enable eco mode charge
        """
        # Read current settings first
        state = self._get_state()
        current_settings = 0
        if state.eco_mode_charge:
            current_settings |= VENTY_SETTING_ECO_MODE_CHARGE

        # Update eco mode charge bit
        if enabled:
            current_settings |= VENTY_SETTING_ECO_MODE_CHARGE
        else:
            current_settings &= ~VENTY_SETTING_ECO_MODE_CHARGE

        packet = build_venty_command(
            VENTY_CMD_STATUS_CONTROL,
            mask=VENTY_MASK_SETTINGS_WRITE,
            settings=current_settings,
        )
        await self._write_characteristic(VENTY_CHAR_MAIN, packet, response=False)
        state.eco_mode_charge = enabled

    async def set_eco_mode_voltage(self, enabled: bool) -> None:
        """Set eco mode voltage.

        Args:
            enabled: True to enable eco mode voltage
        """
        # Read current settings first
        state = self._get_state()
        current_settings = 0
        if state.eco_mode_voltage:
            current_settings |= VENTY_SETTING_ECO_MODE_VOLTAGE

        # Update eco mode voltage bit
        if enabled:
            current_settings |= VENTY_SETTING_ECO_MODE_VOLTAGE
        else:
            current_settings &= ~VENTY_SETTING_ECO_MODE_VOLTAGE

        packet = build_venty_command(
            VENTY_CMD_STATUS_CONTROL,
            mask=VENTY_MASK_SETTINGS_WRITE,
            settings=current_settings,
        )
        await self._write_characteristic(VENTY_CHAR_MAIN, packet, response=False)
        state.eco_mode_voltage = enabled

    async def set_boost_visualization(self, enabled: bool) -> None:
        """Set boost visualization.

        Args:
            enabled: True to enable boost visualization
        """
        # Read current settings first
        state = self._get_state()
        current_settings = 0
        if state.boost_visualization:
            current_settings |= VENTY_SETTING_BOOST_VISUALIZATION

        # Update boost visualization bit
        if enabled:
            current_settings |= VENTY_SETTING_BOOST_VISUALIZATION
        else:
            current_settings &= ~VENTY_SETTING_BOOST_VISUALIZATION

        packet = build_venty_command(
            VENTY_CMD_STATUS_CONTROL,
            mask=VENTY_MASK_SETTINGS_WRITE,
            settings=current_settings,
        )
        await self._write_characteristic(VENTY_CHAR_MAIN, packet, response=False)
        state.boost_visualization = enabled

    async def find_device(self) -> None:
        """Trigger find device (vibration/LED alert)."""
        packet = build_venty_command(VENTY_CMD_FIND_DEVICE)
        await self._write_characteristic(VENTY_CHAR_MAIN, packet, response=False)

    def _handle_main_notification(self, data: bytes) -> None:
        """Handle main characteristic notification."""
        state = self._get_state()
        try:
            if len(data) < 15:
                _LOGGER.warning(
                    "Received notification with insufficient data: %d bytes", len(data)
                )
                return

            data_array = bytearray(data)
            cmd = data_array[0]

            if cmd == VENTY_CMD_STATUS_CONTROL:
                # Parse status/control response
                current_temp_raw = data_array[2] | (data_array[3] << 8)
                target_temp_raw = data_array[4] | (data_array[5] << 8)
                boost_offset = data_array[6]
                superboost_offset = data_array[7]
                battery = data_array[8]
                auto_shutoff = data_array[9] | (data_array[10] << 8)
                heater_mode = data_array[11]
                charger_connected = data_array[13] if len(data_array) > 13 else 0
                settings = data_array[14] if len(data_array) > 14 else 0

                state.current_temperature = current_temp_raw / 10.0
                state.target_temperature = target_temp_raw / 10.0
                state.boost_offset = boost_offset
                state.superboost_offset = superboost_offset
                state.battery_level = battery
                state.auto_shutoff_countdown = auto_shutoff
                state.heater_mode = HeaterMode(heater_mode)
                state.charger_connected = bool(charger_connected)
                state.unit = TemperatureUnit(settings & VENTY_SETTING_UNIT)
                state.setpoint_reached = bool(settings & 0x02)
                state.eco_mode_charge = bool(settings & VENTY_SETTING_ECO_MODE_CHARGE)
                state.eco_mode_voltage = bool(settings & VENTY_SETTING_ECO_MODE_VOLTAGE)
                state.boost_visualization = bool(
                    settings & VENTY_SETTING_BOOST_VISUALIZATION
                )

                _LOGGER.debug(
                    "Status update: temp=%s°C, target=%s°C, battery=%s%%, heater=%s",
                    state.current_temperature,
                    state.target_temperature,
                    state.battery_level,
                    state.heater_mode.name,
                )

            elif cmd == VENTY_CMD_FIRMWARE_VERSION:
                # Parse firmware version
                if len(data_array) > 1:
                    state.firmware_version = decode_string(data_array[1:])

            elif cmd == VENTY_CMD_SERIAL_NUMBER:
                # Parse serial number
                if len(data_array) > 1:
                    state.serial_number = decode_string(data_array[1:])

            # Signal response received
            if self._response_event is not None:
                self._response_data = data_array
                self._response_event.set()

        except Exception as e:
            _LOGGER.warning("Error handling main notification: %s", e)
            if self._response_event is not None:
                self._response_event.set()
