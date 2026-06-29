"""Tests for Venty device."""

import pytest
from unittest.mock import AsyncMock

from storzandbickel_ble.exceptions import CommandTimeoutError
from storzandbickel_ble.models import HeaterMode
from storzandbickel_ble.venty import VentyDevice


@pytest.mark.asyncio
async def test_venty_connect(mock_bleak_client) -> None:
    """Test Venty device connection."""
    device = VentyDevice("AA:BB:CC:DD:EE:FF", client=mock_bleak_client)
    mock_bleak_client.is_connected = False
    device.update_state = AsyncMock()
    device._send_command = AsyncMock(return_value=None)

    await device.connect()

    assert device.is_connected is True
    assert mock_bleak_client.is_connected is True


@pytest.mark.asyncio
async def test_venty_set_heater_mode(mock_bleak_client) -> None:
    """Test setting heater mode."""
    device = VentyDevice("AA:BB:CC:DD:EE:FF", client=mock_bleak_client)
    device._connected = True
    mock_bleak_client.is_connected = True

    await device.set_heater_mode(HeaterMode.BOOST)

    mock_bleak_client.write_gatt_char.assert_called()
    assert device.state.heater_mode == HeaterMode.BOOST


@pytest.mark.asyncio
async def test_venty_set_brightness(mock_bleak_client) -> None:
    """Test setting display brightness."""
    device = VentyDevice("AA:BB:CC:DD:EE:FF", client=mock_bleak_client)
    device._connected = True
    mock_bleak_client.is_connected = True

    await device.set_brightness(7)

    mock_bleak_client.write_gatt_char.assert_called()
    assert device.state.brightness == 7


@pytest.mark.asyncio
async def test_venty_set_brightness_invalid(mock_bleak_client) -> None:
    """Test setting invalid display brightness."""
    device = VentyDevice("AA:BB:CC:DD:EE:FF", client=mock_bleak_client)
    device._connected = True
    mock_bleak_client.is_connected = True

    with pytest.raises(ValueError, match="Brightness must be between 1 and 9"):
        await device.set_brightness(10)


@pytest.mark.asyncio
async def test_venty_set_vibration(mock_bleak_client) -> None:
    """Test toggling vibration."""
    device = VentyDevice("AA:BB:CC:DD:EE:FF", client=mock_bleak_client)
    device._connected = True
    mock_bleak_client.is_connected = True

    await device.set_vibration(False)

    mock_bleak_client.write_gatt_char.assert_called()
    assert device.state.vibration_enabled is False


@pytest.mark.asyncio
async def test_venty_set_boost_timeout_disabled(mock_bleak_client) -> None:
    """Test toggling boost timeout setting."""
    device = VentyDevice("AA:BB:CC:DD:EE:FF", client=mock_bleak_client)
    device._connected = True
    mock_bleak_client.is_connected = True

    await device.set_boost_timeout_disabled(True)

    mock_bleak_client.write_gatt_char.assert_called()
    assert device.state.boost_timeout_disabled is True


def test_venty_parse_settings_notification() -> None:
    """Test parsing cmd 0x06 settings notification."""
    device = VentyDevice("AA:BB:CC:DD:EE:FF")
    data = bytes([0x06, 0x00, 0x05, 0x00, 0x00, 0x01, 0x01])

    device._handle_main_notification(data)

    assert device.state.brightness == 5
    assert device.state.vibration_enabled is True
    assert device.state.boost_timeout_disabled is True


def test_venty_parse_status_sentinel_temperature() -> None:
    """Out-of-range sentinel values (device off/charging) must map to None."""
    device = VentyDevice("AA:BB:CC:DD:EE:FF")
    # 0x7530 = 30000 → 3000.0°C, the sentinel seen when device is off/charging
    raw_lo, raw_hi = 0x30, 0x75
    data = bytearray(15)
    data[0] = 0x01  # VENTY_CMD_STATUS_CONTROL
    data[2], data[3] = raw_lo, raw_hi  # current_temp = 30000 raw
    data[4], data[5] = raw_lo, raw_hi  # target_temp = 30000 raw

    device._handle_main_notification(bytes(data))

    assert device.state.current_temperature is None
    assert device.state.target_temperature is None


def test_venty_parse_status_valid_temperature() -> None:
    """Valid temperatures in range must be stored as-is."""
    device = VentyDevice("AA:BB:CC:DD:EE:FF")
    # 185°C → raw = 1850 = 0x073A → lo=0x3A, hi=0x07
    data = bytearray(15)
    data[0] = 0x01  # VENTY_CMD_STATUS_CONTROL
    data[2], data[3] = 0x3A, 0x07  # current_temp = 185°C
    data[4], data[5] = 0x3A, 0x07  # target_temp = 185°C

    device._handle_main_notification(bytes(data))

    assert device.state.current_temperature == 185.0
    assert device.state.target_temperature == 185.0


def test_venty_parse_firmware_binary_payload() -> None:
    """Binary notification payloads containing 0xff must not raise."""
    device = VentyDevice("AA:BB:CC:DD:EE:FF")
    # cmd=VENTY_CMD_FIRMWARE_VERSION with a binary byte at position 17
    data = bytes([0x02]) + b"V1.0" + bytes([0xFF] * 13)

    device._handle_main_notification(data)  # must not raise


@pytest.mark.asyncio
async def test_venty_run_analysis(mock_bleak_client) -> None:
    """Test local analysis summary generation."""
    device = VentyDevice("AA:BB:CC:DD:EE:FF", client=mock_bleak_client)
    device._connected = True
    mock_bleak_client.is_connected = True
    device.update_state = AsyncMock()
    device._send_command = AsyncMock(return_value=None)
    device.state.brightness = 5
    device.state.vibration_enabled = False

    result = await device.run_analysis()

    assert result["ok"] is True
    assert "Display brightness reduced from default." in result["warnings"]
    assert "Vibration is disabled." in result["warnings"]


@pytest.mark.asyncio
async def test_venty_send_command_timeout_raises(mock_bleak_client) -> None:
    """Command timeouts should raise explicit timeout error."""
    device = VentyDevice("AA:BB:CC:DD:EE:FF", client=mock_bleak_client)
    device._set_connection_state(True)
    mock_bleak_client.is_connected = True

    with pytest.raises(CommandTimeoutError):
        await device._send_command(0xFF, timeout=0.01)


def _connected_venty(mock_bleak_client) -> VentyDevice:
    device = VentyDevice("AA:BB:CC:DD:EE:FF", client=mock_bleak_client)
    device._connected = True
    mock_bleak_client.is_connected = True
    return device


@pytest.mark.asyncio
async def test_venty_set_boost_offset(mock_bleak_client) -> None:
    """Boost offset is written and reflected in state."""
    device = _connected_venty(mock_bleak_client)
    await device.set_boost_offset(15)
    mock_bleak_client.write_gatt_char.assert_called()
    assert device.state.boost_offset == 15


@pytest.mark.asyncio
async def test_venty_set_boost_offset_negative_raises(mock_bleak_client) -> None:
    """Negative offsets are rejected before any write."""
    device = _connected_venty(mock_bleak_client)
    with pytest.raises(ValueError, match="Boost offset must be >= 0"):
        await device.set_boost_offset(-1)


@pytest.mark.asyncio
async def test_venty_set_superboost_offset(mock_bleak_client) -> None:
    """Superboost offset is written and reflected in state."""
    device = _connected_venty(mock_bleak_client)
    await device.set_superboost_offset(30)
    mock_bleak_client.write_gatt_char.assert_called()
    assert device.state.superboost_offset == 30


@pytest.mark.asyncio
async def test_venty_set_eco_mode_charge(mock_bleak_client) -> None:
    """ECO charge-optimization toggles the state flag."""
    device = _connected_venty(mock_bleak_client)
    await device.set_eco_mode_charge(True)
    mock_bleak_client.write_gatt_char.assert_called()
    assert device.state.eco_mode_charge is True


@pytest.mark.asyncio
async def test_venty_set_eco_mode_voltage(mock_bleak_client) -> None:
    """ECO charge-limit toggles the state flag."""
    device = _connected_venty(mock_bleak_client)
    await device.set_eco_mode_voltage(True)
    mock_bleak_client.write_gatt_char.assert_called()
    assert device.state.eco_mode_voltage is True


@pytest.mark.asyncio
async def test_venty_set_boost_visualization(mock_bleak_client) -> None:
    """Boost visualization toggles the state flag."""
    device = _connected_venty(mock_bleak_client)
    await device.set_boost_visualization(True)
    mock_bleak_client.write_gatt_char.assert_called()
    assert device.state.boost_visualization is True


def test_venty_main_notification_surfaces_bug_and_releases_waiter(monkeypatch) -> None:
    """A bug in the main handler propagates, but the command waiter is still released."""
    import asyncio

    device = VentyDevice("AA:BB:CC:DD:EE:FF")
    event = asyncio.Event()
    device._response_event = event

    def boom(_value):
        raise AttributeError("renamed enum")

    monkeypatch.setattr("storzandbickel_ble.venty.HeaterMode", boom)

    data = bytearray(15)
    data[0] = 0x01  # VENTY_CMD_STATUS_CONTROL

    with pytest.raises(AttributeError, match="renamed enum"):
        device._handle_main_notification(bytes(data))
    assert event.is_set()  # waiter released despite the bug
