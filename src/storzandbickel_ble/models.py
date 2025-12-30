"""Data models for Storz & Bickel BLE devices."""

from enum import IntEnum
from typing import TYPE_CHECKING

from pydantic import BaseModel, Field, field_validator

if TYPE_CHECKING:
    pass


class DeviceType(IntEnum):
    """Device type enumeration."""

    VOLCANO = 1
    VENTY = 2
    CRAFTY = 3


class HeaterMode(IntEnum):
    """Heater mode enumeration (for Venty)."""

    OFF = 0
    NORMAL = 1
    BOOST = 2
    SUPERBOOST = 3


class TemperatureUnit(IntEnum):
    """Temperature unit enumeration."""

    CELSIUS = 0
    FAHRENHEIT = 1


class DeviceState(BaseModel):
    """Base device state model."""

    connected: bool = False
    firmware_version: str | None = None
    serial_number: str | None = None
    ble_version: str | None = None


class VolcanoState(DeviceState):
    """Volcano Hybrid device state."""

    current_temperature: float | None = Field(None, ge=40.0, le=230.0)
    target_temperature: float | None = Field(None, ge=40.0, le=230.0)
    heater_on: bool = False
    pump_on: bool = False
    led_brightness: int = Field(5, ge=1, le=9)
    auto_off_time: int = Field(0, ge=0)  # seconds
    heating_hours: int = Field(0, ge=0)
    heating_minutes: int = Field(0, ge=0, le=59)
    fahrenheit_mode: bool = False
    display_on_cooling: bool = False
    vibration_on_ready: bool = False
    auto_shutdown_enabled: bool = False
    status_register_1: int = 0
    status_register_2: int = 0
    status_register_3: int = 0


class VentyState(DeviceState):
    """Venty device state."""

    current_temperature: float | None = Field(None, ge=40.0, le=210.0)
    target_temperature: float | None = Field(None, ge=40.0, le=210.0)
    boost_offset: int = Field(0, ge=0)  # Temperature offset
    superboost_offset: int = Field(0, ge=0)  # Temperature offset
    battery_level: int = Field(0, ge=0, le=100)
    auto_shutoff_countdown: int = Field(0, ge=0)  # seconds
    heater_mode: HeaterMode = HeaterMode.OFF
    charger_connected: bool = False
    unit: TemperatureUnit = TemperatureUnit.CELSIUS
    setpoint_reached: bool = False
    eco_mode_charge: bool = False
    eco_mode_voltage: bool = False
    boost_visualization: bool = False


class CraftyState(DeviceState):
    """Crafty/Crafty+ device state."""

    current_temperature: float | None = Field(None, ge=40.0, le=210.0)
    target_temperature: float | None = Field(None, ge=40.0, le=210.0)
    battery_level: int = Field(0, ge=0, le=100)
    heater_on: bool = False
    boost_mode: bool = False
    superboost_mode: bool = False
    device_active: bool = False
    vibration_enabled: bool = True
    vibration_on_ready: bool = False
    fahrenheit_mode: bool = False
    led_brightness: int = Field(50, ge=0, le=100)
    auto_off_time: int = Field(0, ge=0)  # seconds
    charging: bool = False
    usage_hours: int = Field(0, ge=0)
    usage_minutes: int = Field(0, ge=0, le=59)
    status_register: int = 0
    project_status_register: int = 0
    project_status_register_2: int = 0


class DeviceInfo(BaseModel):
    """Device information from discovery."""

    name: str
    address: str
    device_type: DeviceType
    rssi: int | None = None

    @field_validator("address")
    @classmethod
    def validate_address(cls, v: str) -> str:
        """Validate MAC address format."""
        # Basic validation - should be XX:XX:XX:XX:XX:XX
        parts = v.split(":")
        if len(parts) != 6:
            msg = f"Invalid MAC address format: {v}"
            raise ValueError(msg)
        for part in parts:
            if len(part) != 2:
                msg = f"Invalid MAC address format: {v}"
                raise ValueError(msg)
            try:
                int(part, 16)
            except ValueError as e:
                msg = f"Invalid MAC address format: {v}"
                raise ValueError(msg) from e
        return v.upper()
