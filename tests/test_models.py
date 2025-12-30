"""Tests for data models."""

import pytest

from storzandbickel_ble.models import (
    CraftyState,
    DeviceInfo,
    DeviceType,
    HeaterMode,
    VentyState,
    VolcanoState,
)


def test_device_info() -> None:
    """Test DeviceInfo model."""
    info = DeviceInfo(
        name="S&B VOLCANO",
        address="AA:BB:CC:DD:EE:FF",
        device_type=DeviceType.VOLCANO,
        rssi=-50,
    )
    assert info.name == "S&B VOLCANO"
    assert info.address == "AA:BB:CC:DD:EE:FF"
    assert info.device_type == DeviceType.VOLCANO
    assert info.rssi == -50


def test_device_info_invalid_address() -> None:
    """Test DeviceInfo with invalid MAC address."""
    with pytest.raises(ValueError, match="Invalid MAC address"):
        DeviceInfo(
            name="S&B VOLCANO",
            address="INVALID",
            device_type=DeviceType.VOLCANO,
        )


def test_volcano_state() -> None:
    """Test VolcanoState model."""
    state = VolcanoState(
        current_temperature=185.0,
        target_temperature=190.0,
        heater_on=True,
    )
    assert state.current_temperature == 185.0
    assert state.target_temperature == 190.0
    assert state.heater_on is True


def test_volcano_state_temperature_validation() -> None:
    """Test VolcanoState temperature validation."""
    # Valid temperature
    state = VolcanoState(current_temperature=185.0)
    assert state.current_temperature == 185.0

    # Temperature out of range should be clamped by Pydantic
    with pytest.raises(Exception):  # Pydantic validation error
        VolcanoState(current_temperature=300.0)


def test_venty_state() -> None:
    """Test VentyState model."""
    state = VentyState(
        current_temperature=185.0,
        target_temperature=190.0,
        heater_mode=HeaterMode.NORMAL,
        battery_level=80,
    )
    assert state.current_temperature == 185.0
    assert state.target_temperature == 190.0
    assert state.heater_mode == HeaterMode.NORMAL
    assert state.battery_level == 80


def test_crafty_state() -> None:
    """Test CraftyState model."""
    state = CraftyState(
        current_temperature=185.0,
        target_temperature=190.0,
        heater_on=True,
        battery_level=75,
    )
    assert state.current_temperature == 185.0
    assert state.target_temperature == 190.0
    assert state.heater_on is True
    assert state.battery_level == 75
