"""Storz & Bickel BLE Python Library.

A Python library for controlling Storz & Bickel vaporizers
(Volcano Hybrid, Venty, Crafty/Crafty+) via Bluetooth Low Energy (BLE).
"""

from storzandbickel_ble.client import StorzBickelClient
from storzandbickel_ble.crafty import CraftyDevice
from storzandbickel_ble.exceptions import (
    ConnectionError,
    DeviceNotFoundError,
    FirmwareUpdateError,
    InvalidDataError,
    StorzBickelError,
    TimeoutError,
)
from storzandbickel_ble.venty import VentyDevice
from storzandbickel_ble.volcano import VolcanoDevice

__version__ = "0.1.1"

__all__ = [
    "StorzBickelClient",
    "VolcanoDevice",
    "VentyDevice",
    "CraftyDevice",
    "StorzBickelError",
    "ConnectionError",
    "DeviceNotFoundError",
    "InvalidDataError",
    "TimeoutError",
    "FirmwareUpdateError",
]
