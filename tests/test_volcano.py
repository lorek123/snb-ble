"""Tests for Volcano device."""

import pytest

from storzandbickel_ble.exceptions import ConnectionError
from storzandbickel_ble.protocol import (
    VOLCANO_CHAR_CURRENT_TEMP,
    VOLCANO_CHAR_HEATER_ON,
    VOLCANO_CHAR_TARGET_TEMP,
    encode_temperature,
)
from storzandbickel_ble.volcano import VolcanoDevice


@pytest.mark.asyncio
async def test_volcano_connect(mock_bleak_client) -> None:
    """Test Volcano device connection."""
    device = VolcanoDevice("AA:BB:CC:DD:EE:FF", client=mock_bleak_client)
    # Mock client starts as disconnected, connect() will set is_connected = True
    mock_bleak_client.is_connected = False

    await device.connect()

    assert device.is_connected is True
    # connect() may not be called if client is already provided, so just check connection state
    assert mock_bleak_client.is_connected is True


@pytest.mark.asyncio
async def test_volcano_set_target_temperature(mock_bleak_client) -> None:
    """Test setting target temperature."""
    device = VolcanoDevice("AA:BB:CC:DD:EE:FF", client=mock_bleak_client)
    device._connected = True
    mock_bleak_client.is_connected = True

    await device.set_target_temperature(185.0)

    expected_data = encode_temperature(185.0)
    mock_bleak_client.write_gatt_char.assert_called_with(
        VOLCANO_CHAR_TARGET_TEMP,
        expected_data,
        response=False,
    )
    assert device.state.target_temperature == 185.0


@pytest.mark.asyncio
async def test_volcano_turn_heater_on(mock_bleak_client) -> None:
    """Test turning heater on."""
    device = VolcanoDevice("AA:BB:CC:DD:EE:FF", client=mock_bleak_client)
    device._connected = True
    mock_bleak_client.is_connected = True  # Ensure client reports as connected

    await device.turn_heater_on()

    mock_bleak_client.write_gatt_char.assert_called_with(
        VOLCANO_CHAR_HEATER_ON,
        b"\x01",
        response=False,
    )
    assert device.state.heater_on is True


@pytest.mark.asyncio
async def test_volcano_read_characteristic_not_connected() -> None:
    """Test reading characteristic when not connected."""
    device = VolcanoDevice("AA:BB:CC:DD:EE:FF")

    with pytest.raises(ConnectionError, match="not connected"):
        await device._read_characteristic(VOLCANO_CHAR_CURRENT_TEMP)
