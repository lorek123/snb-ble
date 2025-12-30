"""Tests for Crafty device."""

import pytest

from storzandbickel_ble.crafty import CraftyDevice
from storzandbickel_ble.protocol import CRAFTY_CHAR_TARGET_TEMP, encode_temperature


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
