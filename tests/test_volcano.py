"""Tests for Volcano device."""

import pytest
from unittest.mock import AsyncMock

from storzandbickel_ble.exceptions import ConnectionError
from storzandbickel_ble.models import TemperatureUnit
from storzandbickel_ble.protocol import (
    VOLCANO_CHAR_AUTO_OFF,
    VOLCANO_CHAR_CURRENT_TEMP,
    VOLCANO_CHAR_HEATER_ON,
    VOLCANO_CHAR_LED_BRIGHTNESS,
    VOLCANO_CHAR_STATUS_REGISTER_2,
    VOLCANO_CHAR_STATUS_REGISTER_3,
    VOLCANO_CHAR_TARGET_TEMP,
    VOLCANO_STATUS1_ERROR_BITS,
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
    assert set(VOLCANO_WORKFLOW_PRESETS.keys()) == {
        "balloon",
        "flow1",
        "flow2",
        "flow3",
    }


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
    assert result["findings"] == []
    # Raw registers + history are surfaced as hex for support.
    diag = result["diagnostics"]
    assert diag["status_register_1"].startswith("0x")
    assert "history_1" in diag and "history_2" in diag


@pytest.mark.asyncio
async def test_volcano_run_analysis_detects_error_bits(mock_bleak_client) -> None:
    """Set error bits and confirm they surface as a finding + error, ok=False."""
    device = VolcanoDevice("AA:BB:CC:DD:EE:FF", client=mock_bleak_client)
    device._connected = True
    mock_bleak_client.is_connected = True
    device.state.status_register_1 = VOLCANO_STATUS1_ERROR_BITS
    device.update_state = AsyncMock()

    result = await device.run_analysis()

    assert result["ok"] is False
    assert result["errors"]
    findings = result["findings"]
    assert len(findings) == 1
    assert findings[0]["source"] == "status_register_1"
    assert findings[0]["bits"] == f"0x{VOLCANO_STATUS1_ERROR_BITS:04x}"
    assert findings[0]["meaning"] is None  # per-bit cause is cloud-decoded


@pytest.mark.asyncio
async def test_volcano_availability_transition_count(mock_bleak_client) -> None:
    """Transition count tracks connect/disconnect state changes."""
    device = VolcanoDevice("AA:BB:CC:DD:EE:FF", client=mock_bleak_client)
    mock_bleak_client.is_connected = False

    await device.connect()
    await device.disconnect()

    assert device.availability_transition_count == 2


@pytest.mark.asyncio
async def test_volcano_set_led_brightness(mock_bleak_client) -> None:
    """LED brightness writes encoded value and updates state."""
    device = VolcanoDevice("AA:BB:CC:DD:EE:FF", client=mock_bleak_client)
    device._connected = True
    mock_bleak_client.is_connected = True

    await device.set_led_brightness(7)

    mock_bleak_client.write_gatt_char.assert_called_with(
        VOLCANO_CHAR_LED_BRIGHTNESS,
        encode_uint16(7),
        response=False,
    )
    assert device.state.led_brightness == 7


@pytest.mark.asyncio
async def test_volcano_set_led_brightness_invalid(mock_bleak_client) -> None:
    """Out-of-range brightness is rejected before any write."""
    device = VolcanoDevice("AA:BB:CC:DD:EE:FF", client=mock_bleak_client)
    device._connected = True
    mock_bleak_client.is_connected = True

    with pytest.raises(ValueError, match="between 1 and 9"):
        await device.set_led_brightness(10)


@pytest.mark.asyncio
async def test_volcano_set_auto_off_time(mock_bleak_client) -> None:
    """Auto-off time writes encoded seconds and updates state."""
    device = VolcanoDevice("AA:BB:CC:DD:EE:FF", client=mock_bleak_client)
    device._connected = True
    mock_bleak_client.is_connected = True

    await device.set_auto_off_time(1800)

    mock_bleak_client.write_gatt_char.assert_called_with(
        VOLCANO_CHAR_AUTO_OFF,
        encode_uint16(1800),
        response=False,
    )
    assert device.state.auto_off_time == 1800


@pytest.mark.asyncio
async def test_volcano_set_auto_off_time_negative_raises(mock_bleak_client) -> None:
    """Negative auto-off time is rejected before any write."""
    device = VolcanoDevice("AA:BB:CC:DD:EE:FF", client=mock_bleak_client)
    device._connected = True
    mock_bleak_client.is_connected = True

    with pytest.raises(ValueError, match="Auto-off time must be >= 0"):
        await device.set_auto_off_time(-5)


@pytest.mark.asyncio
async def test_volcano_update_state_surfaces_programming_error(
    mock_bleak_client, monkeypatch
) -> None:
    """A bug inside a poll step propagates with its real type, not as stale state."""
    device = VolcanoDevice("AA:BB:CC:DD:EE:FF", client=mock_bleak_client)
    device._connected = True
    mock_bleak_client.is_connected = True

    def boom(_data) -> int:
        raise AttributeError("renamed decoder")

    monkeypatch.setattr("storzandbickel_ble.volcano.decode_uint16", boom)

    with pytest.raises(AttributeError, match="renamed decoder"):
        await device.update_state()
