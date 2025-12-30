"""Base device class for Storz & Bickel BLE devices."""

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

from bleak import BleakClient, BleakGATTCharacteristic

from storzandbickel_ble.exceptions import ConnectionError, InvalidDataError
from storzandbickel_ble.models import DeviceState, DeviceType

if TYPE_CHECKING:
    from collections.abc import Callable


class BaseDevice(ABC):
    """Abstract base class for all Storz & Bickel devices."""

    def __init__(
        self,
        address: str,
        client: BleakClient | None = None,
        name: str | None = None,
    ) -> None:
        """Initialize base device.

        Args:
            address: BLE MAC address
            client: Optional BleakClient instance
            name: Optional device name
        """
        self.address = address
        self._client = client
        self.name = name
        self._state: DeviceState | None = None
        self._notification_handlers: dict[str, "Callable[[bytes], None]"] = {}
        self._connected = False

    @property
    @abstractmethod
    def device_type(self) -> DeviceType:
        """Return device type."""

    @property
    @abstractmethod
    def state(self) -> DeviceState:
        """Return current device state."""

    @property
    def is_connected(self) -> bool:
        """Check if device is connected."""
        return (
            self._connected and self._client is not None and self._client.is_connected
        )

    @abstractmethod
    async def connect(self) -> None:
        """Connect to device."""

    @abstractmethod
    async def disconnect(self) -> None:
        """Disconnect from device."""

    @abstractmethod
    async def update_state(self) -> None:
        """Update device state by reading from device."""

    async def _read_characteristic(self, uuid: str) -> bytearray:
        """Read a characteristic value.

        Args:
            uuid: Characteristic UUID

        Returns:
            Characteristic value

        Raises:
            ConnectionError: If not connected
            InvalidDataError: If read fails
        """
        if not self.is_connected or self._client is None:
            msg = "Device not connected"
            raise ConnectionError(msg)

        try:
            data = await self._client.read_gatt_char(uuid)
            return bytearray(data)
        except Exception as e:
            msg = f"Failed to read characteristic {uuid}: {e}"
            raise InvalidDataError(msg) from e

    async def _write_characteristic(
        self,
        uuid: str,
        data: bytes | bytearray,
        response: bool = False,
    ) -> None:
        """Write a characteristic value.

        Args:
            uuid: Characteristic UUID
            data: Data to write
            response: Whether to wait for response

        Raises:
            ConnectionError: If not connected
            InvalidDataError: If write fails
        """
        if not self.is_connected or self._client is None:
            msg = "Device not connected"
            raise ConnectionError(msg)

        try:
            await self._client.write_gatt_char(uuid, data, response=response)
        except Exception as e:
            msg = f"Failed to write characteristic {uuid}: {e}"
            raise InvalidDataError(msg) from e

    async def _start_notifications(
        self,
        uuid: str,
        handler: "Callable[[bytes], None]",
    ) -> None:
        """Start notifications for a characteristic.

        Args:
            uuid: Characteristic UUID
            handler: Notification handler callback that takes bytes

        Raises:
            ConnectionError: If not connected
            InvalidDataError: If notification setup fails
        """
        if not self.is_connected or self._client is None:
            msg = "Device not connected"
            raise ConnectionError(msg)

        def bleak_handler(
            characteristic: BleakGATTCharacteristic,
            data: bytearray,
        ) -> None:
            """Adapter to convert Bleak callback to our handler signature."""
            handler(bytes(data))

        try:
            await self._client.start_notify(uuid, bleak_handler)
            self._notification_handlers[uuid] = handler
        except Exception as e:
            msg = f"Failed to start notifications for {uuid}: {e}"
            raise InvalidDataError(msg) from e

    async def _stop_notifications(self, uuid: str) -> None:
        """Stop notifications for a characteristic.

        Args:
            uuid: Characteristic UUID

        Raises:
            ConnectionError: If not connected
        """
        if not self.is_connected or self._client is None:
            msg = "Device not connected"
            raise ConnectionError(msg)

        try:
            await self._client.stop_notify(uuid)
            self._notification_handlers.pop(uuid, None)
        except Exception:
            # Ignore errors when stopping notifications
            self._notification_handlers.pop(uuid, None)

    async def _stop_all_notifications(self) -> None:
        """Stop all active notifications."""
        if not self.is_connected or self._client is None:
            return

        for uuid in list(self._notification_handlers.keys()):
            await self._stop_notifications(uuid)
