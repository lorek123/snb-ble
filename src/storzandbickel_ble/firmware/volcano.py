"""Experimental firmware update support for Volcano Hybrid.

WARNING: This is experimental and can brick your device if used incorrectly.
Use at your own risk.
"""

import asyncio
import logging
from typing import TYPE_CHECKING

from storzandbickel_ble.exceptions import FirmwareUpdateError, TimeoutError
from storzandbickel_ble.protocol import (
    VOLCANO_CHAR_CODE_NUMBER,
)

if TYPE_CHECKING:
    from storzandbickel_ble.volcano import VolcanoDevice

_LOGGER = logging.getLogger(__name__)


class VolcanoFirmwareUpdater:
    """Experimental firmware updater for Volcano Hybrid.

    WARNING: This is experimental and can brick your device if used incorrectly.
    Use at your own risk.
    """

    # Bootloader service UUIDs
    BOOTLOADER_SERVICE = "00000001-1989-0108-1234-123456789abc"
    BOOTLOADER_CHAR_READ = "00000003-1989-0108-1234-123456789abc"
    BOOTLOADER_CHAR_WRITE = "00000002-1989-0108-1234-123456789abc"

    # Telegram constants
    TELEGRAM_HEADER = bytes([0xFE, 0xFA, 0x7F])
    TELEGRAM_FOOTER = bytes([0x00, 0xFD])

    # Timeouts
    OPERATION_TIMEOUT = 1.5  # seconds
    MAX_RETRIES = 6

    def __init__(self, device: "VolcanoDevice") -> None:
        """Initialize firmware updater.

        Args:
            device: Volcano device instance
        """
        self.device = device
        self._response_data: bytearray | None = None
        self._response_event: asyncio.Event | None = None

    def _calc_checksum(self, data: bytearray) -> int:
        """Calculate XOR checksum for telegram.

        Args:
            data: Telegram data

        Returns:
            Checksum value
        """
        check = 0
        # XOR all bytes from position 4 to length-2
        for i in range(4, len(data) - 2):
            check ^= data[i]
        return check

    def _generate_telegram(self, command: str) -> bytes:
        """Generate telegram with checksum.

        Args:
            command: Command string

        Returns:
            Telegram bytes
        """
        command_bytes = command.encode("utf-8")
        data_len = len(command_bytes)
        buffer = bytearray(6 + data_len)
        buffer[0:3] = self.TELEGRAM_HEADER
        buffer[3] = 6 + data_len
        buffer[4 : 4 + data_len] = command_bytes
        buffer[4 + data_len] = 0x00
        buffer[5 + data_len] = 0xFD

        # Calculate and insert checksum before 0xFD
        checksum = self._calc_checksum(buffer)
        buffer[4 + data_len] = checksum

        return bytes(buffer)

    async def _send_telegram(self, command: str) -> str:
        """Send telegram and wait for response.

        Args:
            command: Command string

        Returns:
            Response string

        Raises:
            FirmwareUpdateError: If operation fails
            TimeoutError: If operation times out
        """
        telegram = self._generate_telegram(command)
        _LOGGER.debug("Sending telegram: %s", command)

        # Wait for response
        self._response_event = asyncio.Event()
        self._response_data = None

        try:
            # Write to bootloader characteristic
            await self.device._write_characteristic(
                self.BOOTLOADER_CHAR_WRITE,
                telegram,
                response=False,
            )

            # Wait for response
            await asyncio.wait_for(
                self._response_event.wait(),
                timeout=self.OPERATION_TIMEOUT,
            )

            if self._response_data is None:
                msg = "No response received"
                raise FirmwareUpdateError(msg)

            # Parse response (remove telegram overhead)
            response = self._response_data.decode("utf-8", errors="ignore").strip()
            _LOGGER.debug("Received response: %s", response)
            return response

        except asyncio.TimeoutError as e:
            msg = f"Operation timeout: {command}"
            raise TimeoutError(msg) from e
        except Exception as e:
            msg = f"Failed to send telegram: {e}"
            raise FirmwareUpdateError(msg) from e

    def _handle_bootloader_notification(self, data: bytes) -> None:
        """Handle bootloader notification."""
        self._response_data = bytearray(data)
        if self._response_event is not None:
            self._response_event.set()

    async def enter_bootloader(self) -> None:
        """Enter bootloader mode.

        Raises:
            FirmwareUpdateError: If bootloader entry fails
        """
        _LOGGER.warning("Entering bootloader mode - this is experimental!")
        try:
            # Write code number 4711 (0x1267) as little-endian
            code_data = bytes([0x67, 0x12])
            await self.device._write_characteristic(
                VOLCANO_CHAR_CODE_NUMBER,
                code_data,
            )

            # Wait for device to enter bootloader
            await asyncio.sleep(1.0)

            # Reconnect to bootloader service
            await self.device.disconnect()
            await asyncio.sleep(0.5)
            await self.device.connect()

            # Enable notifications for bootloader read characteristic
            await self.device._start_notifications(
                self.BOOTLOADER_CHAR_READ,
                self._handle_bootloader_notification,
            )

            # Verify bootloader mode
            response = await self._send_telegram("RV0")
            if "222 BL" not in response:
                msg = "Failed to enter bootloader mode"
                raise FirmwareUpdateError(msg)

            _LOGGER.info("Successfully entered bootloader mode")

        except Exception as e:
            msg = f"Failed to enter bootloader: {e}"
            raise FirmwareUpdateError(msg) from e

    async def update_firmware(self, firmware_data: bytes) -> None:
        """Update firmware (not fully implemented - placeholder).

        Args:
            firmware_data: Firmware binary data

        Raises:
            NotImplementedError: This is a placeholder
        """
        msg = "Firmware update not fully implemented - this is experimental"
        raise NotImplementedError(msg)
