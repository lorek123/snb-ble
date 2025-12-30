"""Main BLE client for Storz & Bickel devices."""

import asyncio
import logging
from typing import TYPE_CHECKING

from bleak import BleakClient, BleakScanner

from storzandbickel_ble.device import BaseDevice
from storzandbickel_ble.exceptions import (
    ConnectionError,
    DeviceNotFoundError,
    TimeoutError,
)
from storzandbickel_ble.models import DeviceInfo, DeviceType
from storzandbickel_ble.protocol import (
    CONNECTION_TIMEOUT,
    DEVICE_NAME_CRAFTY,
    DEVICE_NAME_VENTY,
    DEVICE_NAME_VOLCANO,
)

if TYPE_CHECKING:
    pass

_LOGGER = logging.getLogger(__name__)


class StorzBickelClient:
    """Main client for discovering and connecting to Storz & Bickel devices."""

    def __init__(self) -> None:
        """Initialize the client."""
        self._scanner: BleakScanner | None = None

    @staticmethod
    def _detect_device_type(name: str) -> DeviceType | None:
        """Detect device type from name.

        Args:
            name: Device name

        Returns:
            DeviceType or None if unknown
        """
        name_upper = name.upper()
        # Check for specific device names first
        if DEVICE_NAME_VOLCANO in name_upper:
            return DeviceType.VOLCANO
        if DEVICE_NAME_VENTY in name_upper:
            return DeviceType.VENTY
        if DEVICE_NAME_CRAFTY in name_upper:
            return DeviceType.CRAFTY
        # Generic "STORZ&BICKEL" name - could be Crafty, Venty, or Volcano
        # We can't determine the exact type from the name alone, but we'll try to connect
        # and verify the device type from the actual device characteristics
        if "STORZ" in name_upper and "BICKEL" in name_upper:
            # Default to Crafty for generic names (most common), but this will be
            # verified when we read the device name after connection
            return DeviceType.CRAFTY
        return None

    async def scan(
        self,
        timeout: float = 10.0,
        device_type: DeviceType | None = None,
    ) -> list[DeviceInfo]:
        """Scan for Storz & Bickel devices.

        Args:
            timeout: Scan timeout in seconds
            device_type: Optional device type filter

        Returns:
            List of discovered devices
        """
        _LOGGER.debug("Starting BLE scan (timeout: %s)", timeout)
        devices: list[DeviceInfo] = []

        try:
            discovered_devices: dict[str, tuple] = {}  # address -> (device, name)

            def detection_callback(device: object, advertisement_data: object) -> None:
                """Callback for device detection."""
                # Get device name from advertisement data if available, otherwise from device
                device_name = None
                if advertisement_data and hasattr(advertisement_data, "local_name"):
                    device_name = advertisement_data.local_name
                if not device_name and hasattr(device, "name"):
                    device_name = device.name

                address = getattr(device, "address", "Unknown")
                _LOGGER.debug(
                    "Discovered device: %s (%s)",
                    device_name or "Unknown",
                    address,
                )

                # Store device with its name (use advertisement name if available, fallback to device.name)
                if address not in discovered_devices or device_name:
                    discovered_devices[address] = (device, device_name)

            scanner = BleakScanner(detection_callback=detection_callback)
            await scanner.start()
            await asyncio.sleep(timeout)
            await scanner.stop()

            # Also check discovered_devices from scanner (in case callback missed some)
            if hasattr(scanner, "discovered_devices"):
                for device in scanner.discovered_devices:
                    address = getattr(device, "address", None)
                    if address and address not in discovered_devices:
                        device_name = getattr(device, "name", None)
                        discovered_devices[address] = (device, device_name)

            _LOGGER.debug(
                "Scan complete, processing %d discovered devices",
                len(discovered_devices),
            )

            # Process discovered devices
            seen_addresses: set[str] = set()

            for address, (device, device_name) in discovered_devices.items():
                # Skip duplicates (shouldn't happen, but just in case)
                if address in seen_addresses:
                    continue
                seen_addresses.add(address)

                # Skip if no name at all
                if not device_name:
                    _LOGGER.debug("Skipping device %s (no name)", address)
                    continue

                detected_type = self._detect_device_type(device_name)
                if detected_type is None:
                    _LOGGER.debug(
                        "Skipping device %s (%s) - not a Storz & Bickel device",
                        device_name,
                        address,
                    )
                    continue

                if device_type is not None and detected_type != device_type:
                    continue

                device_info = DeviceInfo(
                    name=device_name,
                    address=address,
                    device_type=detected_type,
                    rssi=device.rssi if hasattr(device, "rssi") else None,
                )
                devices.append(device_info)
                _LOGGER.debug(
                    "Found device: %s (%s, %s)",
                    device_name,
                    address,
                    detected_type.name,
                )

        except Exception as e:
            _LOGGER.error("Error during scan: %s", e, exc_info=True)

        _LOGGER.debug("Scan complete, found %d devices", len(devices))
        return devices

    async def find_device(
        self,
        address: str | None = None,
        name: str | None = None,
        device_type: DeviceType | None = None,
        timeout: float = 10.0,
    ) -> DeviceInfo:
        """Find a specific device by address or name.

        Args:
            address: MAC address (e.g., "XX:XX:XX:XX:XX:XX")
            name: Device name
            device_type: Optional device type filter
            timeout: Scan timeout in seconds

        Returns:
            DeviceInfo for the found device

        Raises:
            DeviceNotFoundError: If device not found
        """
        if address:
            # Try to find by address directly
            try:
                discovered: list = []

                def detection_callback(
                    device: object, advertisement_data: object
                ) -> None:
                    """Callback for device detection."""
                    discovered.append(device)

                scanner = BleakScanner(detection_callback=detection_callback)
                await scanner.start()
                await asyncio.sleep(2.0)  # Brief scan
                await scanner.stop()

                for device in discovered:
                    if device.address.upper() == address.upper():
                        if device.name is None:
                            continue
                        detected_type = self._detect_device_type(device.name)
                        if detected_type is None:
                            continue
                        if device_type is not None and detected_type != device_type:
                            continue

                        return DeviceInfo(
                            name=device.name,
                            address=device.address,
                            device_type=detected_type,
                            rssi=device.rssi if hasattr(device, "rssi") else None,
                        )
            except Exception as e:
                _LOGGER.warning("Error scanning for address %s: %s", address, e)

        # Fall back to full scan
        devices = await self.scan(timeout=timeout, device_type=device_type)

        if address:
            for device in devices:
                if device.address.upper() == address.upper():
                    return device
            msg = f"Device with address {address} not found"
            raise DeviceNotFoundError(msg)

        if name:
            for device in devices:
                if name.upper() in device.name.upper():
                    return device
            msg = f"Device with name containing '{name}' not found"
            raise DeviceNotFoundError(msg)

        if devices:
            return devices[0]

        msg = "No Storz & Bickel devices found"
        raise DeviceNotFoundError(msg)

    async def connect_device(
        self,
        device_info: DeviceInfo,
        timeout: float = CONNECTION_TIMEOUT,
    ) -> BaseDevice:
        """Connect to a device.

        Args:
            device_info: Device information from discovery
            timeout: Connection timeout in seconds

        Returns:
            Connected device instance

        Raises:
            ConnectionError: If connection fails
            DeviceNotFoundError: If device type is unknown or device name doesn't match
        """
        _LOGGER.debug(
            "Connecting to device: %s (%s)",
            device_info.name,
            device_info.address,
        )

        try:
            # Create BleakClient
            client = BleakClient(device_info.address, timeout=timeout)

            # Connect
            await asyncio.wait_for(client.connect(), timeout=timeout)

            # If device name is unknown, read it from the device to verify it's an S&B device
            device_name = device_info.name
            if device_name.startswith("Unknown"):
                try:
                    # Read device name from GAP service (standard BLE characteristic)
                    # UUID 0x2A00 is the Device Name characteristic in GAP service (0x1800)
                    # This works for all BLE devices (Crafty, Volcano, Venty)
                    device_name_char_uuid = "00002a00-0000-1000-8000-00805f9b34fb"

                    try:
                        name_data = await client.read_gatt_char(device_name_char_uuid)
                        device_name = name_data.decode("utf-8", errors="ignore").strip(
                            "\x00"
                        )
                        _LOGGER.debug(
                            "Read device name from GAP service: %s", device_name
                        )
                    except Exception as e:
                        _LOGGER.debug(
                            "Could not read device name from GAP service: %s", e
                        )

                        # Fallback: Try Venty-specific device name characteristic if device type is Venty
                        if device_info.device_type == DeviceType.VENTY:
                            try:
                                from storzandbickel_ble.protocol import (
                                    VENTY_CHAR_DEVICE_NAME,
                                )
                                from storzandbickel_ble.protocol import decode_string

                                name_data = await client.read_gatt_char(
                                    VENTY_CHAR_DEVICE_NAME
                                )
                                device_name = decode_string(name_data)
                                _LOGGER.debug(
                                    "Read device name from Venty characteristic: %s",
                                    device_name,
                                )
                            except Exception as e2:
                                _LOGGER.debug(
                                    "Could not read device name from Venty characteristic: %s",
                                    e2,
                                )

                        # Last resort: Try to get name from client properties if available
                        if (
                            device_name.startswith("Unknown")
                            and hasattr(client, "name")
                            and client.name
                        ):
                            device_name = client.name
                            _LOGGER.debug(
                                "Got device name from client properties: %s",
                                device_name,
                            )

                    # Verify it's a Storz & Bickel device
                    detected_type = self._detect_device_type(device_name)
                    if detected_type is None:
                        await client.disconnect()
                        msg = f"Device at {device_info.address} is not a Storz & Bickel device (name: {device_name or 'unknown'})"
                        raise DeviceNotFoundError(msg)

                    # Update device_info with detected type if it was unknown or mismatched
                    if device_info.device_type != detected_type:
                        _LOGGER.info(
                            "Device type mismatch: expected %s, detected %s. Using detected type.",
                            device_info.device_type,
                            detected_type,
                        )
                        device_info = DeviceInfo(
                            name=device_name,
                            address=device_info.address,
                            device_type=detected_type,
                            rssi=device_info.rssi,
                        )
                    else:
                        # Update name even if type matches
                        device_info = DeviceInfo(
                            name=device_name,
                            address=device_info.address,
                            device_type=device_info.device_type,
                            rssi=device_info.rssi,
                        )
                except DeviceNotFoundError:
                    raise
                except Exception as e:
                    _LOGGER.warning(
                        "Failed to read/verify device name after connection: %s", e
                    )
                    # If we can't read the name but device_type was provided, proceed anyway
                    # (user might know what they're doing)
                    if device_info.device_type is None:
                        await client.disconnect()
                        msg = f"Could not verify device at {device_info.address} is a Storz & Bickel device"
                        raise DeviceNotFoundError(msg) from e

            # Create appropriate device instance
            # Import here to avoid circular imports
            device: BaseDevice
            if device_info.device_type == DeviceType.VOLCANO:
                from storzandbickel_ble.volcano import VolcanoDevice

                device = VolcanoDevice(
                    device_info.address,
                    client=client,
                    name=device_name,
                )
            elif device_info.device_type == DeviceType.VENTY:
                from storzandbickel_ble.venty import VentyDevice

                device = VentyDevice(
                    device_info.address,
                    client=client,
                    name=device_name,
                )
            elif device_info.device_type == DeviceType.CRAFTY:
                from storzandbickel_ble.crafty import CraftyDevice

                device = CraftyDevice(
                    device_info.address,
                    client=client,
                    name=device_name,
                )
            else:
                await client.disconnect()
                msg = f"Unknown device type: {device_info.device_type}"
                raise DeviceNotFoundError(msg)

            # Initialize device connection
            await device.connect()

            _LOGGER.info(
                "Successfully connected to %s (%s)",
                device_name,
                device_info.address,
            )

            return device

        except asyncio.TimeoutError as e:
            msg = f"Connection timeout after {timeout}s"
            raise TimeoutError(msg) from e
        except Exception as e:
            msg = f"Failed to connect: {e}"
            raise ConnectionError(msg) from e

    async def connect_by_address(
        self,
        address: str,
        device_type: DeviceType | None = None,
        timeout: float = CONNECTION_TIMEOUT,
        skip_discovery: bool = False,
    ) -> BaseDevice:
        """Connect to a device by MAC address.

        Args:
            address: MAC address (e.g., "XX:XX:XX:XX:XX:XX")
            device_type: Optional device type (required if skip_discovery=True)
            timeout: Connection timeout in seconds
            skip_discovery: If True, connect directly without scanning (for non-advertising devices)

        Returns:
            Connected device instance

        Raises:
            DeviceNotFoundError: If device not found
            ConnectionError: If connection fails
        """
        if skip_discovery:
            # Connect directly without scanning (for devices that don't advertise)
            if device_type is None:
                msg = "device_type is required when skip_discovery=True"
                raise ValueError(msg)

            # Create DeviceInfo directly without discovery
            device_info = DeviceInfo(
                name=f"Unknown ({address})",
                address=address,
                device_type=device_type,
                rssi=None,
            )
            return await self.connect_device(device_info, timeout=timeout)

        # Try to find device via scanning first
        try:
            device_info = await self.find_device(
                address=address, device_type=device_type, timeout=timeout
            )
            return await self.connect_device(device_info, timeout=timeout)
        except DeviceNotFoundError:
            # If not found via scanning, try direct connection if device_type is provided
            if device_type is not None:
                _LOGGER.info(
                    "Device %s not found via scanning, attempting direct connection",
                    address,
                )
                device_info = DeviceInfo(
                    name=f"Unknown ({address})",
                    address=address,
                    device_type=device_type,
                    rssi=None,
                )
                return await self.connect_device(device_info, timeout=timeout)
            raise

    async def connect_by_name(
        self,
        name: str,
        device_type: DeviceType | None = None,
        timeout: float = CONNECTION_TIMEOUT,
    ) -> BaseDevice:
        """Connect to a device by name.

        Args:
            name: Device name (partial match supported)
            device_type: Optional device type filter
            timeout: Connection timeout in seconds

        Returns:
            Connected device instance

        Raises:
            DeviceNotFoundError: If device not found
            ConnectionError: If connection fails
        """
        device_info = await self.find_device(
            name=name,
            device_type=device_type,
            timeout=timeout,
        )
        return await self.connect_device(device_info, timeout=timeout)
