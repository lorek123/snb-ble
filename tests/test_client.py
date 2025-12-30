"""Tests for BLE client."""

import pytest
from unittest.mock import AsyncMock, patch

from storzandbickel_ble.client import StorzBickelClient
from storzandbickel_ble.exceptions import DeviceNotFoundError
from storzandbickel_ble.models import DeviceType


@pytest.mark.asyncio
async def test_scan(mock_ble_device) -> None:
    """Test device scanning."""
    client = StorzBickelClient()

    discovered_devices = [mock_ble_device]

    def mock_scanner_init(detection_callback=None, **kwargs):
        """Mock scanner initialization."""
        scanner = AsyncMock()
        scanner.start = AsyncMock()
        scanner.stop = AsyncMock()

        # Simulate callback being called
        async def start_side_effect():
            if detection_callback:
                for device in discovered_devices:
                    detection_callback(device, None)

        scanner.start.side_effect = start_side_effect
        return scanner

    with patch("storzandbickel_ble.client.BleakScanner", side_effect=mock_scanner_init):
        devices = await client.scan(timeout=0.1)

        assert len(devices) == 1
        assert devices[0].name == "S&B VOLCANO"
        assert devices[0].device_type == DeviceType.VOLCANO


@pytest.mark.asyncio
async def test_find_device_by_address(mock_ble_device) -> None:
    """Test finding device by address."""
    client = StorzBickelClient()

    discovered_devices = [mock_ble_device]

    def mock_scanner_init(detection_callback=None, **kwargs):
        """Mock scanner initialization."""
        scanner = AsyncMock()
        scanner.start = AsyncMock()
        scanner.stop = AsyncMock()

        # Simulate callback being called
        async def start_side_effect():
            if detection_callback:
                for device in discovered_devices:
                    detection_callback(device, None)

        scanner.start.side_effect = start_side_effect
        return scanner

    with patch("storzandbickel_ble.client.BleakScanner", side_effect=mock_scanner_init):
        device_info = await client.find_device(address="AA:BB:CC:DD:EE:FF", timeout=0.1)

        assert device_info.address == "AA:BB:CC:DD:EE:FF"
        assert device_info.device_type == DeviceType.VOLCANO


@pytest.mark.asyncio
async def test_find_device_not_found() -> None:
    """Test finding device that doesn't exist."""
    client = StorzBickelClient()

    with patch("storzandbickel_ble.client.BleakScanner") as mock_scanner:
        mock_scanner_instance = AsyncMock()
        mock_scanner.return_value = mock_scanner_instance
        mock_scanner_instance.get_discovered_devices.return_value = []
        mock_scanner_instance.start = AsyncMock()
        mock_scanner_instance.stop = AsyncMock()

        with pytest.raises(DeviceNotFoundError):
            await client.find_device(address="AA:BB:CC:DD:EE:FF", timeout=0.1)
