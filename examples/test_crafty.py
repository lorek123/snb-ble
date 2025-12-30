#!/usr/bin/env python3
"""Test script for connecting to and controlling a real Crafty+ device."""

import asyncio
import logging
import sys

from storzandbickel_ble import StorzBickelClient
from storzandbickel_ble.exceptions import ConnectionError, DeviceNotFoundError

# Set up logging to see what's happening
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


async def main() -> None:
    """Main test function."""
    client = StorzBickelClient()

    try:
        # Option 1: Scan for devices
        logger.info("Scanning for Crafty+ devices...")
        logger.info("Make sure your Crafty+ is powered on and Bluetooth is enabled!")

        # Enable debug logging to see all discovered devices
        logging.getLogger("storzandbickel_ble").setLevel(logging.DEBUG)

        devices = await client.scan(timeout=10.0)

        if not devices:
            logger.error("No Storz & Bickel devices found.")
            logger.info("This might mean:")
            logger.info("  1. Device is not powered on")
            logger.info("  2. Device is connected to another app/device")
            logger.info("  3. Device name doesn't match expected pattern")
            logger.info(
                "  4. Bluetooth permissions issue (try running with sudo on Linux)"
            )
            return

        logger.info(f"Found {len(devices)} Storz & Bickel device(s):")
        for device in devices:
            logger.info(f"  - {device.name} ({device.address})")

        # Option 2: Connect by address (if you know it)
        # device = await client.connect_by_address("AA:BB:CC:DD:EE:FF")

        # Connect to first Crafty device found (or any Storz & Bickel device)
        crafty_device = None
        for device_info in devices:
            # Connect to first device found (should be Crafty if detection worked)
            logger.info(f"Connecting to {device_info.name} ({device_info.address})...")
            crafty_device = await client.connect_device(device_info)
            break

        if crafty_device is None:
            logger.error("No device found in scan results")
            return

        logger.info("Connected successfully!")
        logger.info(f"Device: {crafty_device.name}")
        logger.info(f"Address: {crafty_device.address}")
        logger.info(
            "Note: Connection time includes BLE service discovery (typically 20-30s)"
        )
        logger.info(
            "      This is normal for BLE devices and depends on your Bluetooth stack"
        )

        # Update full state to get all values (this may take a moment)
        logger.info("\nUpdating device state (this may take a few seconds)...")
        await crafty_device.update_state()

        state = crafty_device.state
        logger.info("\n=== Current Device State ===")
        logger.info(f"Serial Number: {state.serial_number}")
        logger.info(f"Firmware Version: {state.firmware_version}")
        logger.info(f"Current Temperature: {state.current_temperature}°C")
        logger.info(f"Target Temperature: {state.target_temperature}°C")
        logger.info(f"Battery Level: {state.battery_level}%")
        logger.info(f"Heater On: {state.heater_on}")
        logger.info(f"Boost Mode: {state.boost_mode}")
        logger.info(f"Device Active: {state.device_active}")
        logger.info(f"Charging: {state.charging}")
        logger.info(f"LED Brightness: {state.led_brightness}")
        logger.info(f"Vibration Enabled: {state.vibration_enabled}")

        # Example: Set target temperature
        logger.info("\n=== Testing Controls ===")
        logger.info("Setting target temperature to 185°C...")
        await crafty_device.set_target_temperature(185.0)
        await asyncio.sleep(1)
        await crafty_device.update_state()
        logger.info(
            f"New target temperature: {crafty_device.state.target_temperature}°C"
        )

        # Example: Turn heater on
        logger.info("\nTurning heater on...")
        await crafty_device.turn_heater_on()
        await asyncio.sleep(2)
        await crafty_device.update_state()
        logger.info(f"Heater status: {crafty_device.state.heater_on}")

        # Monitor temperature for a bit
        logger.info("\n=== Monitoring Temperature (10 seconds) ===")
        for i in range(10):
            await asyncio.sleep(1)
            state = crafty_device.state
            logger.info(
                f"  [{i + 1}/10] Current: {state.current_temperature:.1f}°C, "
                f"Target: {state.target_temperature:.1f}°C, "
                f"Battery: {state.battery_level}%",
            )

        # Example: Test find device (vibration/LED alert)
        logger.info("\nTesting 'Find Device' feature (vibration/LED alert)...")
        await crafty_device.find_device()
        logger.info("Find device command sent!")

        # Example: Turn heater off
        logger.info("\nTurning heater off...")
        await crafty_device.turn_heater_off()
        await asyncio.sleep(1)
        await crafty_device.update_state()
        logger.info(f"Heater status: {crafty_device.state.heater_on}")

        logger.info("\n=== Test Complete ===")
        logger.info("Disconnecting...")
        await crafty_device.disconnect()
        logger.info("Disconnected successfully!")

    except DeviceNotFoundError as e:
        logger.error(f"Device not found: {e}")
        logger.info("Make sure your Crafty+ is powered on and in range")
        sys.exit(1)
    except ConnectionError as e:
        logger.error(f"Connection failed: {e}")
        logger.info("Make sure your Crafty+ is not connected to another device")
        sys.exit(1)
    except KeyboardInterrupt:
        logger.info("\nInterrupted by user")
        if crafty_device and crafty_device.is_connected:
            await crafty_device.disconnect()
        sys.exit(0)
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        if crafty_device and crafty_device.is_connected:
            await crafty_device.disconnect()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
