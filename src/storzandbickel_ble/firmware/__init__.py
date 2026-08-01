"""Experimental firmware update support for Storz & Bickel devices.

WARNING: Firmware updates are experimental and can brick devices if performed incorrectly.
Use at your own risk. The authors are not responsible for any damage to devices.
"""

from storzandbickel_ble.firmware.venty import VentyFirmwareUpdater
from storzandbickel_ble.firmware.volcano import VolcanoFirmwareUpdater

__all__ = ["VentyFirmwareUpdater", "VolcanoFirmwareUpdater"]
