"""Protocol constants and utilities for Storz & Bickel BLE devices."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Sequence

# Device names for discovery
DEVICE_NAME_VOLCANO = "S&B VOLCANO"
DEVICE_NAME_VENTY = "VENTY"
DEVICE_NAME_CRAFTY = "CRAFTY"

# Temperature ranges (in Celsius)
TEMP_MIN_VOLCANO = 40.0
TEMP_MAX_VOLCANO = 230.0
TEMP_MIN_VENTY = 40.0
TEMP_MAX_VENTY = 210.0
TEMP_MIN_CRAFTY = 40.0
TEMP_MAX_CRAFTY = 210.0

# LED brightness ranges
LED_BRIGHTNESS_MIN_VOLCANO = 1
LED_BRIGHTNESS_MAX_VOLCANO = 9
LED_BRIGHTNESS_MIN_CRAFTY = 0
LED_BRIGHTNESS_MAX_CRAFTY = 100

# Volcano Hybrid Service UUIDs
VOLCANO_SERVICE_INFO = "10100000-5354-4f52-5a26-4249434b454c"
VOLCANO_SERVICE_CONTROL = "10110000-5354-4f52-5a26-4249434b454c"

# Volcano Hybrid Characteristic UUIDs
VOLCANO_CHAR_FIRMWARE_VERSION = "10100005-5354-4f52-5a26-4249434b454c"
VOLCANO_CHAR_SERIAL_NUMBER = "10100008-5354-4f52-5a26-4249434b454c"
VOLCANO_CHAR_BLE_VERSION = "10100004-5354-4f52-5a26-4249434b454c"
VOLCANO_CHAR_STATUS_REGISTER_1 = "1010000c-5354-4f52-5a26-4249434b454c"
VOLCANO_CHAR_STATUS_REGISTER_2 = "1010000d-5354-4f52-5a26-4249434b454c"
VOLCANO_CHAR_STATUS_REGISTER_3 = "1010000e-5354-4f52-5a26-4249434b454c"
VOLCANO_CHAR_CURRENT_TEMP = "10110001-5354-4f52-5a26-4249434b454c"
VOLCANO_CHAR_TARGET_TEMP = "10110003-5354-4f52-5a26-4249434b454c"
VOLCANO_CHAR_HEATER_ON = "1011000f-5354-4f52-5a26-4249434b454c"
VOLCANO_CHAR_HEATER_OFF = "10110010-5354-4f52-5a26-4249434b454c"
VOLCANO_CHAR_PUMP_ON = "10110013-5354-4f52-5a26-4249434b454c"
VOLCANO_CHAR_PUMP_OFF = "10110014-5354-4f52-5a26-4249434b454c"
VOLCANO_CHAR_LED_BRIGHTNESS = "10110005-5354-4f52-5a26-4249434b454c"
VOLCANO_CHAR_AUTO_OFF = "1011000c-5354-4f52-5a26-4249434b454c"
VOLCANO_CHAR_HEATING_HOURS = "10110015-5354-4f52-5a26-4249434b454c"
VOLCANO_CHAR_HEATING_MINUTES = "10110016-5354-4f52-5a26-4249434b454c"
VOLCANO_CHAR_CODE_NUMBER = "10100011-5354-4f52-5a26-4249434b454c"  # For bootloader

# Volcano Status Register 1 bits
VOLCANO_STATUS1_HEATER_ON = 0x0020  # Bit 5
VOLCANO_STATUS1_AUTO_SHUTDOWN = 0x0200  # Bit 9
VOLCANO_STATUS1_PUMP_ON = 0x2000  # Bit 13
VOLCANO_STATUS1_ERROR_BITS = 0x4018  # Bits 1, 2, 6, 14, 15

# Volcano Status Register 2 bits
VOLCANO_STATUS2_FAHRENHEIT = 0x0200  # Bit 9
VOLCANO_STATUS2_DISPLAY_COOLING = 0x1000  # Bit 12
VOLCANO_STATUS2_ERROR_BITS = 0x003B  # Bits 0-5, 10-11

# Volcano Status Register 3 bits
VOLCANO_STATUS3_VIBRATION_READY = 0x0400  # Bit 10

# Venty Service UUIDs
VENTY_SERVICE_MAIN = "00000001-5354-4f52-5a26-4249434b454c"
VENTY_SERVICE_GENERIC_ACCESS = "00001800-0000-1000-8000-00805f9b34fb"

# Venty Characteristic UUIDs
VENTY_CHAR_MAIN = "00000001-5354-4f52-5a26-4249434b454c"
VENTY_CHAR_DEVICE_NAME = "00002a00-0000-1000-8000-00805f9b34fb"  # Contains serial

# Venty Command Bytes
VENTY_CMD_STATUS_CONTROL = 0x01
VENTY_CMD_FIRMWARE_VERSION = 0x02
VENTY_CMD_DEVICE_ANALYSIS = 0x03
VENTY_CMD_USAGE_STATS = 0x04
VENTY_CMD_SERIAL_NUMBER = 0x05
VENTY_CMD_SETTINGS = 0x06
VENTY_CMD_FIND_DEVICE = 0x13
VENTY_CMD_BOOTLOADER = 0x30
VENTY_CMD_BOOTLOADER_ALT = 0x48

# Venty Command Masks (for command 0x01, byte 1)
VENTY_MASK_TEMP_WRITE = 0x02  # Bit 1
VENTY_MASK_BOOST_WRITE = 0x04  # Bit 2
VENTY_MASK_SUPERBOOST_WRITE = 0x08  # Bit 3
VENTY_MASK_HEATER_WRITE = 0x20  # Bit 5
VENTY_MASK_SETTINGS_WRITE = 0x80  # Bit 7

# Venty Settings Bits (byte 14 in command 0x01)
VENTY_SETTING_UNIT = 0x01  # Bit 0 (0=Celsius, 1=Fahrenheit)
VENTY_SETTING_SETPOINT_REACHED = 0x02  # Bit 1
VENTY_SETTING_FACTORY_RESET = 0x04  # Bit 2
VENTY_SETTING_ECO_MODE_CHARGE = 0x08  # Bit 3
VENTY_SETTING_BUTTON_CHANGED = 0x10  # Bit 4
VENTY_SETTING_ECO_MODE_VOLTAGE = 0x20  # Bit 5
VENTY_SETTING_BOOST_VISUALIZATION = 0x40  # Bit 6

# Venty Heater Modes
VENTY_HEATER_OFF = 0
VENTY_HEATER_NORMAL = 1
VENTY_HEATER_BOOST = 2
VENTY_HEATER_SUPERBOOST = 3

# Crafty Service UUIDs
CRAFTY_SERVICE_1 = "00000001-4c45-4b43-4942-265a524f5453"
CRAFTY_SERVICE_2 = "00000002-4c45-4b43-4942-265a524f5453"
CRAFTY_SERVICE_3 = "00000003-4c45-4b43-4942-265a524f5453"

# Crafty Service 1 Characteristic UUIDs
CRAFTY_CHAR_TARGET_TEMP = "00000021-4c45-4b43-4942-265a524f5453"
CRAFTY_CHAR_BATTERY = "00000041-4c45-4b43-4942-265a524f5453"

# Crafty Service 2 Characteristic UUIDs
CRAFTY_CHAR_CURRENT_TEMP = "00000011-4c45-4b43-4942-265a524f5453"
CRAFTY_CHAR_HEATER_ON = "00000031-4c45-4b43-4942-265a524f5453"
CRAFTY_CHAR_HEATER_OFF = "00000032-4c45-4b43-4942-265a524f5453"
CRAFTY_CHAR_STATUS_REGISTER = "00000052-4c45-4b43-4942-265a524f5453"
CRAFTY_CHAR_FIRMWARE_VERSION = (
    "00000032-4c45-4b43-4942-265a524f5453"  # Note: duplicate UUID
)
CRAFTY_CHAR_BLE_VERSION = "00000072-4c45-4b43-4942-265a524f5453"

# Crafty Service 3 Characteristic UUIDs
CRAFTY_CHAR_FIND_DEVICE = "00000041-4c45-4b43-4942-265a524f5453"  # Note: duplicate UUID
CRAFTY_CHAR_AKKU_STATUS = "00000073-4c45-4b43-4942-265a524f5453"
CRAFTY_CHAR_USAGE_HOURS = "00000023-4c45-4b43-4942-265a524f5453"
CRAFTY_CHAR_USAGE_MINUTES = "000001e3-4c45-4b43-4942-265a524f5453"
CRAFTY_CHAR_PROJECT_STATUS = "00000093-4c45-4b43-4942-265a524f5453"
CRAFTY_CHAR_PROJECT_STATUS_2 = "000001c3-4c45-4b43-4942-265a524f5453"
CRAFTY_CHAR_LED_BRIGHTNESS = "00000051-4c45-4b43-4942-265a524f5453"
CRAFTY_CHAR_AUTO_OFF = "00000071-4c45-4b43-4942-265a524f5453"
CRAFTY_CHAR_VIBRATION = "00000061-4c45-4b43-4942-265a524f5453"

# Crafty Status Register bits
CRAFTY_STATUS_HEATER_ON = 0x0001  # Bit 0
CRAFTY_STATUS_BOOST_MODE = 0x0002  # Bit 1
CRAFTY_STATUS_VIBRATION_READY = 0x0004  # Bit 2
CRAFTY_STATUS_FAHRENHEIT = 0x0008  # Bit 3

# Crafty Project Status Register bits
CRAFTY_PROJECT_STATUS_ACTIVE = 0x0010  # Bit 4
CRAFTY_PROJECT_STATUS_BOOST_ENABLED = 0x0020  # Bit 5
CRAFTY_PROJECT_STATUS_SUPERBOOST_ENABLED = 0x0040  # Bit 6

# Crafty Project Status Register 2 bits
CRAFTY_PROJECT_STATUS2_VIBRATION_DISABLED = (
    0x0001  # Bit 0 (inverted: 0=enabled, 1=disabled)
)

# Connection settings
CONNECTION_TIMEOUT = 30.0  # seconds
RECONNECT_INTERVAL = 5.0  # seconds
NOTIFICATION_TIMEOUT = 2.0  # seconds


def encode_temperature(temp_celsius: float) -> bytes:
    """Encode temperature as 2-byte little-endian (temp × 10).

    Args:
        temp_celsius: Temperature in Celsius

    Returns:
        2-byte little-endian encoded temperature
    """
    temp_raw = int(temp_celsius * 10)
    return bytes([temp_raw & 0xFF, (temp_raw >> 8) & 0xFF])


def decode_temperature(data: bytes | bytearray | Sequence[int]) -> float:
    """Decode temperature from 2-byte little-endian.

    Args:
        data: 2-byte little-endian encoded temperature

    Returns:
        Temperature in Celsius

    Raises:
        ValueError: If data length is not 2 bytes
    """
    if len(data) < 2:
        msg = f"Temperature data must be 2 bytes, got {len(data)}"
        raise ValueError(msg)
    temp_raw = data[0] | (data[1] << 8)
    return temp_raw / 10.0


def encode_uint16(value: int) -> bytes:
    """Encode 16-bit unsigned integer as little-endian.

    Args:
        value: 16-bit unsigned integer

    Returns:
        2-byte little-endian encoded value
    """
    return bytes([value & 0xFF, (value >> 8) & 0xFF])


def decode_uint16(data: bytes | bytearray | Sequence[int]) -> int:
    """Decode 16-bit unsigned integer from little-endian.

    Args:
        data: 2-byte little-endian encoded value

    Returns:
        16-bit unsigned integer

    Raises:
        ValueError: If data length is less than 2 bytes
    """
    if len(data) < 2:
        msg = f"Uint16 data must be at least 2 bytes, got {len(data)}"
        raise ValueError(msg)
    return data[0] | (data[1] << 8)


def decode_string(data: bytes | bytearray | Sequence[int]) -> str:
    """Decode UTF-8 string, removing null terminators.

    Args:
        data: UTF-8 encoded string data

    Returns:
        Decoded string without null terminators
    """
    if isinstance(data, (bytes, bytearray)):
        return data.decode("utf-8").rstrip("\0")
    return bytes(data).decode("utf-8").rstrip("\0")


def clamp_temperature(temp: float, min_temp: float, max_temp: float) -> float:
    """Clamp temperature to valid range.

    Args:
        temp: Temperature to clamp
        min_temp: Minimum temperature
        max_temp: Maximum temperature

    Returns:
        Clamped temperature
    """
    return max(min_temp, min(max_temp, temp))


def check_bit(value: int, bit: int) -> bool:
    """Check if a specific bit is set in a value.

    Args:
        value: Integer value to check
        bit: Bit position (0-based)

    Returns:
        True if bit is set, False otherwise
    """
    return bool(value & (1 << bit))


def set_bit(value: int, bit: int) -> int:
    """Set a specific bit in a value.

    Args:
        value: Integer value
        bit: Bit position (0-based)

    Returns:
        Value with bit set
    """
    return value | (1 << bit)


def clear_bit(value: int, bit: int) -> int:
    """Clear a specific bit in a value.

    Args:
        value: Integer value
        bit: Bit position (0-based)

    Returns:
        Value with bit cleared
    """
    return value & ~(1 << bit)


def build_venty_command(
    cmd: int,
    mask: int = 0,
    current_temp: int | None = None,
    target_temp: int | None = None,
    boost_offset: int | None = None,
    superboost_offset: int | None = None,
    battery: int | None = None,
    auto_shutoff: int | None = None,
    heater_mode: int | None = None,
    charger_connected: int | None = None,
    settings: int | None = None,
) -> bytearray:
    """Build a Venty command packet (20 bytes).

    Args:
        cmd: Command byte
        mask: Command mask (byte 1)
        current_temp: Current temperature (temp × 10, bytes 2-3)
        target_temp: Target temperature (temp × 10, bytes 4-5)
        boost_offset: Boost temperature offset (byte 6)
        superboost_offset: Superboost temperature offset (byte 7)
        battery: Battery level 0-100 (byte 8)
        auto_shutoff: Auto-shutoff countdown in seconds (bytes 9-10)
        heater_mode: Heater mode 0-3 (byte 11)
        charger_connected: Charger connected 0/1 (byte 13)
        settings: Settings bit flags (byte 14)

    Returns:
        20-byte command packet
    """
    packet = bytearray(20)
    packet[0] = cmd
    packet[1] = mask

    if current_temp is not None:
        packet[2] = current_temp & 0xFF
        packet[3] = (current_temp >> 8) & 0xFF

    if target_temp is not None:
        packet[4] = target_temp & 0xFF
        packet[5] = (target_temp >> 8) & 0xFF

    if boost_offset is not None:
        packet[6] = boost_offset

    if superboost_offset is not None:
        packet[7] = superboost_offset

    if battery is not None:
        packet[8] = battery

    if auto_shutoff is not None:
        packet[9] = auto_shutoff & 0xFF
        packet[10] = (auto_shutoff >> 8) & 0xFF

    if heater_mode is not None:
        packet[11] = heater_mode

    if charger_connected is not None:
        packet[13] = charger_connected

    if settings is not None:
        packet[14] = settings

    return packet
