"""Tests for Volcano device."""

import pytest
from unittest.mock import AsyncMock

from storzandbickel_ble.exceptions import ConnectionError
from storzandbickel_ble.models import TemperatureUnit
from storzandbickel_ble.protocol import (
    VOLCANO_CHAR_CURRENT_TEMP,
    VOLCANO_CHAR_HEATER_ON,
    VOLCANO_CHAR_STATUS_REGISTER_2,
    VOLCANO_CHAR_STATUS_REGISTER_3,
    VOLCANO_CHAR_TARGET_TEMP,
    VOLCANO_STATUS2_DISPLAY_COOLING,
    VOLCANO_STATUS2_FAHRENHEIT,
    VOLCANO_STATUS3_VIBRATION_READY,
    encode_temperature,
    encode_uint16,
)
from storzandbickel_ble.volcano import VOLCANO_WORKFLOW_PRESETS, VolcanoDevice


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


@pytest.mark.asyncio
async def test_volcano_set_temperature_unit(mock_bleak_client) -> None:
    """Test setting Volcano temperature unit helper."""
    device = VolcanoDevice("AA:BB:CC:DD:EE:FF", client=mock_bleak_client)
    device._connected = True
    mock_bleak_client.is_connected = True

    await device.set_temperature_unit(TemperatureUnit.FAHRENHEIT)

    mock_bleak_client.write_gatt_char.assert_called_with(
        VOLCANO_CHAR_STATUS_REGISTER_2,
        encode_uint16(VOLCANO_STATUS2_FAHRENHEIT),
        response=False,
    )


@pytest.mark.asyncio
async def test_volcano_set_display_on_cooling(mock_bleak_client) -> None:
    """Test setting display-on-cooling helper."""
    device = VolcanoDevice("AA:BB:CC:DD:EE:FF", client=mock_bleak_client)
    device._connected = True
    mock_bleak_client.is_connected = True

    await device.set_display_on_cooling(True)

    mock_bleak_client.write_gatt_char.assert_called_with(
        VOLCANO_CHAR_STATUS_REGISTER_2,
        encode_uint16(VOLCANO_STATUS2_DISPLAY_COOLING),
        response=False,
    )


@pytest.mark.asyncio
async def test_volcano_set_vibration_on_ready(mock_bleak_client) -> None:
    """Test setting vibration-on-ready helper."""
    device = VolcanoDevice("AA:BB:CC:DD:EE:FF", client=mock_bleak_client)
    device._connected = True
    mock_bleak_client.is_connected = True

    await device.set_vibration_on_ready(True)

    mock_bleak_client.write_gatt_char.assert_called_with(
        VOLCANO_CHAR_STATUS_REGISTER_3,
        encode_uint16(VOLCANO_STATUS3_VIBRATION_READY),
        response=False,
    )


def test_volcano_workflow_presets_exist() -> None:
    """Test known workflow presets are available."""
    assert set(VOLCANO_WORKFLOW_PRESETS.keys()) == {"balloon", "flow1", "flow2", "flow3"}


@pytest.mark.asyncio
async def test_volcano_run_analysis(mock_bleak_client) -> None:
    """Test Volcano local diagnostics summary."""
    device = VolcanoDevice("AA:BB:CC:DD:EE:FF", client=mock_bleak_client)
    device._connected = True
    mock_bleak_client.is_connected = True
    device.state.led_brightness = 2
    device.state.display_on_cooling = False
    device.state.vibration_on_ready = False
    device.update_state = AsyncMock()

    result = await device.run_analysis()

    assert result["ok"] is True
    assert "Display brightness is low." in result["warnings"]
    assert "Display-on-cooling is disabled." in result["warnings"]


@pytest.mark.asyncio
async def test_volcano_availability_transition_count(mock_bleak_client) -> None:
    """Transition count tracks connect/disconnect state changes."""
    device = VolcanoDevice("AA:BB:CC:DD:EE:FF", client=mock_bleak_client)
    mock_bleak_client.is_connected = False

    await device.connect()
    await device.disconnect()

    assert device.availability_transition_count == 2
