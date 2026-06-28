"""Tests for Crafty device."""

import pytest
from unittest.mock import AsyncMock

from storzandbickel_ble.crafty import CraftyDevice
from storzandbickel_ble.protocol import (
    CRAFTY_CHAR_BOOST_TEMP,
    CRAFTY_CHAR_PROJECT_STATUS_2,
    CRAFTY_CHAR_TARGET_TEMP,
    CRAFTY_PROJECT_STATUS2_AUTO_BLE_SHUTDOWN,
    CRAFTY_PROJECT_STATUS2_CHARGE_LED_DISABLED,
    CRAFTY_PROJECT_STATUS2_TEMP_REACHED,
    CRAFTY_PROJECT_STATUS2_VIBRATION_DISABLED,
    encode_temperature,
    encode_uint16,
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


@pytest.mark.asyncio
async def test_crafty_set_charge_led(mock_bleak_client) -> None:
    """Disabling the charge LED sets bit 1; enabling clears it without touching others."""
    device = CraftyDevice("AA:BB:CC:DD:EE:FF", client=mock_bleak_client)
    device._connected = True
    mock_bleak_client.is_connected = True

    mock_bleak_client.read_gatt_char.return_value = encode_uint16(0x0000)
    await device.set_charge_led(False)
    mock_bleak_client.write_gatt_char.assert_called_with(
        CRAFTY_CHAR_PROJECT_STATUS_2,
        encode_uint16(CRAFTY_PROJECT_STATUS2_CHARGE_LED_DISABLED),
        response=False,
    )
    assert device.state.charge_led_enabled is False

    # Bit set alongside an unrelated bit -> enabling clears only the LED bit.
    mock_bleak_client.read_gatt_char.return_value = encode_uint16(
        CRAFTY_PROJECT_STATUS2_CHARGE_LED_DISABLED | 0x0010
    )
    await device.set_charge_led(True)
    mock_bleak_client.write_gatt_char.assert_called_with(
        CRAFTY_CHAR_PROJECT_STATUS_2, encode_uint16(0x0010), response=False
    )
    assert device.state.charge_led_enabled is True


@pytest.mark.asyncio
async def test_crafty_set_permanent_bluetooth(mock_bleak_client) -> None:
    """Permanent Bluetooth clears the auto-BLE-shutdown bit (bit 12)."""
    device = CraftyDevice("AA:BB:CC:DD:EE:FF", client=mock_bleak_client)
    device._connected = True
    mock_bleak_client.is_connected = True

    mock_bleak_client.read_gatt_char.return_value = encode_uint16(
        CRAFTY_PROJECT_STATUS2_AUTO_BLE_SHUTDOWN
    )
    await device.set_permanent_bluetooth(True)
    mock_bleak_client.write_gatt_char.assert_called_with(
        CRAFTY_CHAR_PROJECT_STATUS_2, encode_uint16(0x0000), response=False
    )
    assert device.state.permanent_bluetooth is True

    mock_bleak_client.read_gatt_char.return_value = encode_uint16(0x0000)
    await device.set_permanent_bluetooth(False)
    mock_bleak_client.write_gatt_char.assert_called_with(
        CRAFTY_CHAR_PROJECT_STATUS_2,
        encode_uint16(CRAFTY_PROJECT_STATUS2_AUTO_BLE_SHUTDOWN),
        response=False,
    )
    assert device.state.permanent_bluetooth is False


@pytest.mark.asyncio
async def test_crafty_set_vibration_preserves_other_bits(mock_bleak_client) -> None:
    """Refactored set_vibration toggles only the vibration bit, keeping others."""
    device = CraftyDevice("AA:BB:CC:DD:EE:FF", client=mock_bleak_client)
    device._connected = True
    mock_bleak_client.is_connected = True

    mock_bleak_client.read_gatt_char.return_value = encode_uint16(
        CRAFTY_PROJECT_STATUS2_CHARGE_LED_DISABLED
    )
    await device.set_vibration(False)
    mock_bleak_client.write_gatt_char.assert_called_with(
        CRAFTY_CHAR_PROJECT_STATUS_2,
        encode_uint16(
            CRAFTY_PROJECT_STATUS2_CHARGE_LED_DISABLED
            | CRAFTY_PROJECT_STATUS2_VIBRATION_DISABLED
        ),
        response=False,
    )
    assert device.state.vibration_enabled is False
    assert device.state.charge_led_enabled is False


def test_crafty_apply_project_status2_decodes_all_bits() -> None:
    """The register-2 decoder maps each bit to the right (possibly inverted) field."""
    device = CraftyDevice("AA:BB:CC:DD:EE:FF", name="CRAFTY")
    state = device.state

    value = (
        CRAFTY_PROJECT_STATUS2_CHARGE_LED_DISABLED
        | CRAFTY_PROJECT_STATUS2_VIBRATION_DISABLED
        | CRAFTY_PROJECT_STATUS2_TEMP_REACHED
    )
    device._apply_project_status2(state, value)
    assert state.vibration_enabled is False
    assert state.charge_led_enabled is False
    assert state.setpoint_reached is True
    assert state.permanent_bluetooth is True  # auto-shutdown bit clear

    device._apply_project_status2(state, CRAFTY_PROJECT_STATUS2_AUTO_BLE_SHUTDOWN)
    assert state.vibration_enabled is True
    assert state.charge_led_enabled is True
    assert state.setpoint_reached is False
    assert state.permanent_bluetooth is False
