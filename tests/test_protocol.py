"""Tests for protocol utilities."""

import pytest

from storzandbickel_ble.protocol import (
    decode_string,
    decode_temperature,
    decode_uint16,
    encode_temperature,
    encode_uint16,
)


def test_encode_temperature() -> None:
    """Test temperature encoding."""
    # Test 185.0°C
    data = encode_temperature(185.0)
    assert data == bytes([0x3A, 0x07])

    # Test 40.0°C (minimum)
    data = encode_temperature(40.0)
    assert data == bytes([0x90, 0x01])

    # Test 230.0°C (maximum for Volcano)
    data = encode_temperature(230.0)
    assert data == bytes([0xFC, 0x08])


def test_decode_temperature() -> None:
    """Test temperature decoding."""
    # Test 185.0°C
    data = bytes([0x3A, 0x07])
    temp = decode_temperature(data)
    assert temp == 185.0

    # Test 40.0°C
    data = bytes([0x90, 0x01])
    temp = decode_temperature(data)
    assert temp == 40.0

    # Test 230.0°C
    data = bytes([0xFC, 0x08])
    temp = decode_temperature(data)
    assert temp == 230.0


def test_decode_temperature_invalid() -> None:
    """Test temperature decoding with invalid data."""
    with pytest.raises(ValueError, match="must be 2 bytes"):
        decode_temperature(bytes([0x3A]))


def test_encode_uint16() -> None:
    """Test uint16 encoding."""
    data = encode_uint16(0x1234)
    assert data == bytes([0x34, 0x12])


def test_decode_uint16() -> None:
    """Test uint16 decoding."""
    data = bytes([0x34, 0x12])
    value = decode_uint16(data)
    assert value == 0x1234


def test_decode_uint16_invalid() -> None:
    """Test uint16 decoding with invalid data."""
    with pytest.raises(ValueError, match="must be at least 2 bytes"):
        decode_uint16(bytes([0x34]))


def test_decode_string() -> None:
    """Test string decoding."""
    # Test with null terminator
    data = bytes([0x56, 0x31, 0x2E, 0x30, 0x2E, 0x30, 0x00])
    result = decode_string(data)
    assert result == "V1.0.0"

    # Test without null terminator
    data = bytes([0x56, 0x31, 0x2E, 0x30, 0x2E, 0x30])
    result = decode_string(data)
    assert result == "V1.0.0"
