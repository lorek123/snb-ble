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
