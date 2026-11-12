"""Tests for Crafty device."""

from unittest.mock import AsyncMock

import pytest

from storzandbickel_ble.crafty import CraftyDevice
from storzandbickel_ble.protocol import (
    CRAFTY_AKKU_ERROR,
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
    assert result["findings"] == []
    diag = result["diagnostics"]
    assert diag["project_status_register"].startswith("0x")
    assert "akku_status" in diag


@pytest.mark.asyncio
async def test_crafty_run_analysis_detects_charger_error(mock_bleak_client) -> None:
    """The akku charger/cable error bit is decoded into a named finding."""
    device = CraftyDevice("AA:BB:CC:DD:EE:FF", client=mock_bleak_client)
    device._connected = True
    mock_bleak_client.is_connected = True
    device.update_state = AsyncMock()
    # In run_analysis the only live read is the akku status register.
    mock_bleak_client.read_gatt_char.return_value = encode_uint16(CRAFTY_AKKU_ERROR)

    result = await device.run_analysis()

    assert result["ok"] is False
    charger = next(f for f in result["findings"] if f["source"] == "akku_status")
    assert charger["meaning"] == "charger or cable error"
    assert "charger or cable error" in " ".join(result["errors"])


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


def test_tolerate_swallows_expected_but_reraises_bugs() -> None:
    """`_tolerate` continues past device/transport errors but never hides bugs."""
    device = CraftyDevice("AA:BB:CC:DD:EE:FF", name="CRAFTY")

    # Expected/transient failures are swallowed so one bad read can't abort a poll.
    with device._tolerate("read something"):
        raise ValueError("garbled payload")

    # Programming errors propagate so a refactor mistake surfaces.
    with pytest.raises(AttributeError), device._tolerate("read something"):
        raise AttributeError("renamed field")


@pytest.mark.asyncio
async def test_crafty_update_state_surfaces_programming_error(
    mock_bleak_client,
) -> None:
    """A bug inside a poll step propagates with its real type, not as stale state."""
    device = CraftyDevice("AA:BB:CC:DD:EE:FF", client=mock_bleak_client)
    device._connected = True
    mock_bleak_client.is_connected = True

    def boom(_state, _value) -> None:
        raise AttributeError("renamed field")

    device._apply_project_status2 = boom  # type: ignore[method-assign]

    with pytest.raises(AttributeError, match="renamed field"):
        await device.update_state()


def test_crafty_notification_surfaces_programming_error() -> None:
    """A bug in a notification handler propagates instead of being swallowed."""
    device = CraftyDevice("AA:BB:CC:DD:EE:FF", name="CRAFTY")

    def boom(_state, _value) -> None:
        raise AttributeError("renamed field")

    device._apply_project_status2 = boom  # type: ignore[method-assign]

    with pytest.raises(AttributeError, match="renamed field"):
        device._handle_project_status2_notification(bytes([0x00, 0x00]))


# Register values captured from a Crafty+ (FW V04.26) over BLE:
# (power 0x83, akku 0x63, akku2 0x73) -> (charger_connected, charging, full)
_CHARGE_CASES = [
    pytest.param(0x2404, 0x0000, 0x0000, False, False, False, id="unplugged"),
    pytest.param(0x2405, 0x8084, 0x2000, True, True, False, id="charging"),
    pytest.param(0x2405, 0x80D4, 0x2000, True, False, True, id="full-led-solid"),
]


@pytest.mark.parametrize(
    ("power", "akku", "akku2", "connected", "charging", "full"), _CHARGE_CASES
)
def test_crafty_charge_state_from_captured_registers(
    power, akku, akku2, connected, charging, full
) -> None:
    device = CraftyDevice("AA:BB:CC:DD:EE:FF")
    state = device.state
    state.power_status_register = power
    state.akku_status_register = akku
    state.akku_status_register_2 = akku2

    CraftyDevice._apply_charge_state(state)

    assert state.charger_connected is connected
    assert state.charging is charging
    assert state.battery_full is full


@pytest.mark.asyncio
async def test_crafty_update_state_reads_charge_registers(mock_bleak_client) -> None:
    """update_state reads 0x83/0x63/0x73 and derives the charge state."""
    from storzandbickel_ble.protocol import (
        CRAFTY_CHAR_AKKU_STATUS,
        CRAFTY_CHAR_AKKU_STATUS_1,
        CRAFTY_CHAR_POWER_STATUS,
    )

    values = {
        CRAFTY_CHAR_POWER_STATUS: encode_uint16(0x2405),
        CRAFTY_CHAR_AKKU_STATUS_1: encode_uint16(0x8084),
        CRAFTY_CHAR_AKKU_STATUS: encode_uint16(0x2000),
    }

    async def read(uuid, *args, **kwargs):
        return values.get(uuid, bytes([0x3A, 0x07]))

    mock_bleak_client.read_gatt_char = AsyncMock(side_effect=read)
    device = CraftyDevice("AA:BB:CC:DD:EE:FF", client=mock_bleak_client)
    device._connected = True
    mock_bleak_client.is_connected = True

    await device.update_state()

    assert device.state.charger_connected is True
    assert device.state.charging is True
    assert device.state.battery_full is False


def test_crafty_akku_status_1_notification_updates_charge_state() -> None:
    """A 0x63 notification flips charging -> full without a poll."""
    device = CraftyDevice("AA:BB:CC:DD:EE:FF")
    state = device.state
    state.power_status_register = 0x2405
    state.akku_status_register_2 = 0x2000

    device._handle_akku_status_1_notification(encode_uint16(0x8084))
    assert state.charging is True

    device._handle_akku_status_1_notification(encode_uint16(0x80D4))
    assert state.charging is False
    assert state.battery_full is True


@pytest.mark.asyncio
async def test_crafty_target_write_rewrites_boost(mock_bleak_client) -> None:
    """Like the vendor app: target write is followed by a boost-offset write."""
    device = CraftyDevice("AA:BB:CC:DD:EE:FF", client=mock_bleak_client)
    device._connected = True
    mock_bleak_client.is_connected = True
    device.state.boost_temperature = 10.0

    await device.set_target_temperature(185.0)

    calls = mock_bleak_client.write_gatt_char.call_args_list
    assert calls[-2].args[:2] == (CRAFTY_CHAR_TARGET_TEMP, encode_temperature(185.0))
    assert calls[-1].args[:2] == (CRAFTY_CHAR_BOOST_TEMP, encode_temperature(10.0))
