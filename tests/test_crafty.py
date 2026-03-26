"""Tests for Crafty device."""

import pytest
from unittest.mock import AsyncMock

from storzandbickel_ble.crafty import CraftyDevice
from storzandbickel_ble.protocol import (
    CRAFTY_CHAR_BOOST_TEMP,
    CRAFTY_CHAR_TARGET_TEMP,
    encode_temperature,
)


@pytest.mark.asyncio
async def test_crafty_connect(mock_bleak_client) -> None:
    """Test Crafty device connection."""
    device = CraftyDevice("AA:BB:CC:DD:EE:FF", client=mock_bleak_client)
    mock_bleak_client.is_connected = False

    await device.connect()

    assert device.is_connected is True
    assert mock_bleak_client.is_connected is True


@pytest.mark.asyncio
async def test_crafty_set_target_temperature(mock_bleak_client) -> None:
    """Test setting target temperature."""
    device = CraftyDevice("AA:BB:CC:DD:EE:FF", client=mock_bleak_client)
    device._connected = True
    mock_bleak_client.is_connected = True

    await device.set_target_temperature(185.0)

    expected_data = encode_temperature(185.0)
    mock_bleak_client.write_gatt_char.assert_called_with(
        CRAFTY_CHAR_TARGET_TEMP,
        expected_data,
        response=False,
    )
    assert device.state.target_temperature == 185.0


@pytest.mark.asyncio
async def test_crafty_set_boost_temperature(mock_bleak_client) -> None:
    """Test setting boost temperature."""
    device = CraftyDevice("AA:BB:CC:DD:EE:FF", client=mock_bleak_client)
    device._connected = True
    mock_bleak_client.is_connected = True

    await device.set_boost_temperature(15)

    expected_data = encode_temperature(15.0)
    mock_bleak_client.write_gatt_char.assert_called_with(
        CRAFTY_CHAR_BOOST_TEMP,
        expected_data,
        response=False,
    )
    assert device.state.boost_temperature == 15.0


@pytest.mark.asyncio
async def test_crafty_run_analysis(mock_bleak_client) -> None:
    """Test local Crafty analysis summary."""
    device = CraftyDevice("AA:BB:CC:DD:EE:FF", client=mock_bleak_client)
    device._connected = True
    mock_bleak_client.is_connected = True
    device.state.led_brightness = 5
    device.state.vibration_enabled = False
    device.state.device_active = False
    device.update_state = AsyncMock()

    result = await device.run_analysis()

    assert result["ok"] is True
    assert "LED brightness is low." in result["warnings"]
    assert "Vibration is disabled." in result["warnings"]


def test_crafty_diagnostics_snapshot_sanitizes_serial() -> None:
    """Diagnostics should omit sensitive serial numbers."""
    device = CraftyDevice("AA:BB:CC:DD:EE:FF", name="CRAFTY")
    device.state.serial_number = "SN-SECRET"
    device._set_connection_state(True)

    snapshot = device.get_diagnostics_snapshot()

    assert snapshot["device_type"] == "CRAFTY"
    assert snapshot["connected"] is False
    assert snapshot["state"]["connected"] is True
    assert snapshot["address_suffix"] == "EE:FF"
    assert snapshot["availability_transition_count"] == 1
    assert "serial_number" not in snapshot["state"]
