"""Tests for Venty device."""

import pytest

from storzandbickel_ble.models import HeaterMode
from storzandbickel_ble.venty import VentyDevice


@pytest.mark.asyncio
async def test_venty_connect(mock_bleak_client) -> None:
    """Test Venty device connection."""
    device = VentyDevice("AA:BB:CC:DD:EE:FF", client=mock_bleak_client)
    mock_bleak_client.is_connected = False

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
