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


def test_detect_device_type_veazy_and_venty_short_names() -> None:
    """Test short-name device type detection for qvap devices."""
    assert StorzBickelClient._detect_device_type("S&B VZ 123456") == DeviceType.VEAZY
    assert StorzBickelClient._detect_device_type("S&B VY 654321") == DeviceType.VENTY


def test_is_model_specific_name() -> None:
    """Generic S&B names must not be considered model-specific."""
    assert StorzBickelClient._is_model_specific_name("VENTY") is True
    assert StorzBickelClient._is_model_specific_name("S&B VY 123456") is True
    assert StorzBickelClient._is_model_specific_name("CRAFTY+") is True
    assert StorzBickelClient._is_model_specific_name("S&B VOLCANO") is True
    assert StorzBickelClient._is_model_specific_name("STORZ&BICKEL") is False
    assert StorzBickelClient._is_model_specific_name("S&B DEVICE") is False


@pytest.mark.asyncio
async def test_connect_device_redetects_generic_sb_name(mock_bleak_client) -> None:
    """connect_device re-reads the GAP name when the advertisement is a generic S&B name.

    ESPHome BLE proxies often advertise S&B devices as "STORZ&BICKEL" without the
    model keyword, causing _detect_device_type to default to CRAFTY. The connect path
    must read the GAP Device Name characteristic and correct the type before creating
    the device instance.
    """
    from storzandbickel_ble.models import DeviceInfo
    from storzandbickel_ble.venty import VentyDevice

    # Simulate: advertisement shows generic name, config stored CRAFTY
    device_info = DeviceInfo(
        name="STORZ&BICKEL",
        address="AA:BB:CC:DD:EE:FF",
        device_type=DeviceType.CRAFTY,
        ble_device=None,
    )
    # GAP characteristic returns the real model name
    mock_bleak_client.read_gatt_char = AsyncMock(return_value=b"VENTY\x00")
    mock_bleak_client.is_connected = True

    client = StorzBickelClient()
    with patch("storzandbickel_ble.client.BleakClient", return_value=mock_bleak_client):
        with patch.object(mock_bleak_client, "connect", new_callable=AsyncMock):
            # Patch VentyDevice.connect so we don't actually do BLE I/O
            with patch.object(VentyDevice, "connect", new_callable=AsyncMock):
                device = await client.connect_device(device_info)

    assert isinstance(device, VentyDevice)
