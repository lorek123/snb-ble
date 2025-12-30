"""Pytest configuration and fixtures."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from bleak import BleakClient


@pytest.fixture
def mock_bleak_client():
    """Create a mock BleakClient."""
    client = AsyncMock(spec=BleakClient)
    client.is_connected = False  # Start as disconnected
    client.address = "AA:BB:CC:DD:EE:FF"
    client.get_services = AsyncMock()
    client.read_gatt_char = AsyncMock(
        return_value=bytes([0x3A, 0x07])
    )  # Default: 185.0°C
    client.write_gatt_char = AsyncMock()
    client.start_notify = AsyncMock()
    client.stop_notify = AsyncMock()
    client.connect = AsyncMock()
    client.disconnect = AsyncMock()

    # Make is_connected True after connect is called
    async def connect_side_effect():
        client.is_connected = True

    client.connect.side_effect = connect_side_effect
    return client


@pytest.fixture
def mock_ble_device():
    """Create a mock BLE device."""
    device = MagicMock()
    device.name = "S&B VOLCANO"
    device.address = "AA:BB:CC:DD:EE:FF"
    device.rssi = -50
    return device
