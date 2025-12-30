# Storz & Bickel BLE Python Library

A Python library for controlling Storz & Bickel vaporizers (Volcano Hybrid, Venty, and Crafty/Crafty+) via Bluetooth Low Energy (BLE).

## Features

- **Full Device Support**: Control Volcano Hybrid, Venty, and Crafty/Crafty+ devices
- **Async/Await**: Built with modern Python async/await patterns
- **Type Safe**: Full type hints and Pydantic models for data validation
- **Home Assistant Ready**: Follows Home Assistant best practices
- **Comprehensive**: Supports all device features including temperature control, status monitoring, and configuration

## Installation

### Using pip

```bash
pip install storzandbickel-ble
```

### Using uv

```bash
uv pip install storzandbickel-ble
```

## Quick Start

### Basic Usage

```python
import asyncio
from storzandbickel_ble import StorzBickelClient

async def main():
    # Create client
    client = StorzBickelClient()
    
    # Scan for devices
    devices = await client.scan(timeout=10.0)
    print(f"Found {len(devices)} devices")
    
    # Connect to first device
    if devices:
        device = await client.connect_device(devices[0])
        
        # Set target temperature
        await device.set_target_temperature(185.0)
        
        # Turn heater on
        await device.turn_heater_on()
        
        # Read current state
        print(f"Current temperature: {device.state.current_temperature}°C")
        print(f"Target temperature: {device.state.target_temperature}°C")
        
        # Disconnect
        await device.disconnect()

asyncio.run(main())
```

### Testing with Real Device

To test with a real Crafty+ device, use the example script:

```bash
uv run python examples/test_crafty.py
```

This will:
- Scan for your device
- Connect automatically
- Display current state
- Test various controls
- Monitor temperature updates in real-time

See `examples/README.md` for more details.

## Device-Specific Examples

### Crafty/Crafty+

```python
import asyncio
from storzandbickel_ble import StorzBickelClient
from storzandbickel_ble.models import DeviceType

async def main():
    client = StorzBickelClient()
    
    # Scan for Crafty devices
    devices = await client.scan(timeout=10.0, device_type=DeviceType.CRAFTY)
    
    if devices:
        # Connect to first Crafty device
        crafty = await client.connect_device(devices[0])
        
        # Update state to get current values
        await crafty.update_state()
        
        # Check temperatures
        print(f"Current temperature: {crafty.state.current_temperature}°C")
        print(f"Target temperature: {crafty.state.target_temperature}°C")
        
        # Set target temperature
        await crafty.set_target_temperature(185.0)
        print(f"Set target temperature to 185°C")
        
        # Verify the change
        await crafty.update_state()
        print(f"New target temperature: {crafty.state.target_temperature}°C")
        
        await crafty.disconnect()

asyncio.run(main())
```

### Venty

```python
import asyncio
from storzandbickel_ble import StorzBickelClient
from storzandbickel_ble.models import DeviceType

async def main():
    client = StorzBickelClient()
    
    # Scan for Venty devices
    devices = await client.scan(timeout=10.0, device_type=DeviceType.VENTY)
    
    if devices:
        # Connect to first Venty device
        venty = await client.connect_device(devices[0])
        
        # Update state to get current values
        await venty.update_state()
        
        # Check temperatures
        print(f"Current temperature: {venty.state.current_temperature}°C")
        print(f"Target temperature: {venty.state.target_temperature}°C")
        
        # Set target temperature
        await venty.set_target_temperature(190.0)
        print(f"Set target temperature to 190°C")
        
        # Verify the change
        await venty.update_state()
        print(f"New target temperature: {venty.state.target_temperature}°C")
        
        await venty.disconnect()

asyncio.run(main())
```

### Volcano Hybrid

```python
import asyncio
from storzandbickel_ble import StorzBickelClient
from storzandbickel_ble.models import DeviceType

async def main():
    client = StorzBickelClient()
    
    # Scan for Volcano devices
    devices = await client.scan(timeout=10.0, device_type=DeviceType.VOLCANO)
    
    if devices:
        # Connect to first Volcano device
        volcano = await client.connect_device(devices[0])
        
        # Update state to get current values
        await volcano.update_state()
        
        # Check temperatures
        print(f"Current temperature: {volcano.state.current_temperature}°C")
        print(f"Target temperature: {volcano.state.target_temperature}°C")
        
        # Set target temperature
        await volcano.set_target_temperature(200.0)
        print(f"Set target temperature to 200°C")
        
        # Verify the change
        await volcano.update_state()
        print(f"New target temperature: {volcano.state.target_temperature}°C")
        
        await volcano.disconnect()

asyncio.run(main())
```

## Device Support Matrix

| Device | Temperature Control | Heater Control | Battery | Air Pump | Boost Mode | Vibration |
|--------|-------------------|----------------|---------|----------|------------|-----------|
| Volcano Hybrid | ✅ | ✅ | ❌ | ✅ | ❌ | ✅ |
| Venty | ✅ | ✅ | ✅ | ❌ | ✅ | ❌ |
| Crafty/Crafty+ | ✅ | ✅ | ✅ | ❌ | ✅ | ✅ |

## Documentation

Full documentation is available at [Read the Docs](https://storzandbickel-ble.readthedocs.io).

## Requirements

- Python 3.14+
- Bluetooth adapter with BLE support
- Linux, macOS, or Windows

## Dependencies

- `bleak>=0.21.0` - BLE communication
- `pydantic>=2.0.0` - Data validation

## Development

### Setup

```bash
# Clone repository
git clone https://github.com/yourusername/storzandbickel-ble.git
cd storzandbickel-ble

# Install with uv
uv pip install -e ".[dev]"

# Or with pip
pip install -e ".[dev]"
```

### Running Tests

```bash
pytest
```

### Linting

```bash
ruff check .
ruff format .
```

### Type Checking

```bash
mypy src/
```

## Docker

### Build

```bash
docker build -t storzandbickel-ble .
```

### Run

```bash
docker run --rm storzandbickel-ble
```

### Development

```bash
docker-compose up dev
```

## License

MIT License - see LICENSE file for details

## Disclaimer

This library is based on reverse engineering and is not officially supported by Storz & Bickel. Use at your own risk. The authors are not responsible for any damage to devices.

## Contributing

Contributions are welcome! Please open an issue or submit a pull request.

## References

- Protocol documentation: See `s&b_procol.md`
- BLE GATT specification: https://www.bluetooth.com/specifications/specs/core-specification/

