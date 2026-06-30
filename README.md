# Storz & Bickel BLE Python Library

A Python library for controlling Storz & Bickel vaporizers (Volcano Hybrid, Venty/Veazy, and Crafty/Crafty+) via Bluetooth Low Energy (BLE).

## Features

- **Device Support**: Volcano Hybrid, Venty, Veazy (qvap path), and Crafty/Crafty+
- **Async/Await**: Built with modern Python async/await patterns
- **Type Safe**: Full type hints and Pydantic models for data validation
- **Home Assistant Ready**: Follows Home Assistant best practices
- **Controls**: temperature/heater/pump, boost/superboost, and a full settings surface — brightness, auto-off, vibration, ECO charging, display-on-cooling, Venty heater mode, and the Crafty charge-LED & permanent-Bluetooth toggles
- **Diagnostics**: local `run_analysis()` returning a structured report — status, detected error flags, and raw registers (no cloud upload)
- **Workflows**: Volcano presets (`balloon`, `flow1`–`flow3`) **and custom `run_workflow(steps)`** timed heat+pump sequences

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

### Home Assistant-Oriented Quickstart

The library patterns map cleanly to HA coordinator/entity flows:

- discover/connect once
- keep notifications enabled as the primary state path
- call `update_state()` for startup reconciliation or recovery
- use explicit exceptions and `availability_transition_count` for clean availability handling

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

For additional per-device examples (Venty, Veazy, Volcano), see `docs/usage.rst`.

## Workflow and Analysis APIs

```python
import asyncio
from storzandbickel_ble import StorzBickelClient

async def main():
    client = StorzBickelClient()
    volcano = await client.connect_by_name("S&B VOLCANO")

    # Volcano workflow presets: balloon, flow1, flow2, flow3
    await volcano.run_workflow_preset("flow1")

    # ...or a custom workflow: a list of (target_temp, hold_seconds, pump_seconds)
    await volcano.run_workflow([
        (185.0, 10.0, 8.0),
        (200.0, 0.0, 12.0),
    ])

    # Local diagnostics report (no cloud upload)
    report = await volcano.run_analysis()
    print(report["ok"], report["warnings"], report["errors"])
    print(report["findings"])      # which error-mask bits are set, per register
    print(report["diagnostics"])   # raw registers / history, as hex

    await volcano.disconnect()

asyncio.run(main())
```

Per-bit error *meanings* are decoded on Storz & Bickel's servers, not in the client, so
`findings` reports **which** error bits are set; only locally-known cases (e.g. the Crafty
akku charger/cable error) carry a `meaning`. The Venty/Veazy detailed analysis is a cloud-only
blob, so their report returns the decoded settings/state plus a note rather than a full report.

## Device Support Matrix

| Device | Temperature | Heater | Battery | Pump | Boost/Superboost | Vibration | Brightness | Workflow Presets | Local Analysis |
|--------|------------|--------|---------|------|------------------|-----------|------------|------------------|----------------|
| Volcano Hybrid | ✅ | ✅ | ❌ | ✅ | ❌ | ✅ | ✅ | ✅ | ✅ |
| Venty | ✅ | ✅ | ✅ | ❌ | ✅ | ✅ | ✅ | ❌ | ✅ |
| Veazy | ✅ | ✅ | ✅ | ❌ | ✅ | ✅ | ✅ | ❌ | ✅ |
| Crafty/Crafty+ | ✅ | ✅ | ✅ | ❌ | ✅ | ✅ | ✅ | ❌ | ✅ |

## Supported Functions by Family

| Function | Volcano | Venty | Veazy | Crafty |
|----------|---------|-------|-------|--------|
| Discovery and connect | ✅ | ✅ | ✅ | ✅ |
| Real-time notification state | ✅ | ✅ | ✅ | ✅ |
| Temperature target control | ✅ | ✅ | ✅ | ✅ |
| Heater control | ✅ | ✅ | ✅ | ✅ |
| Pump control | ✅ | ❌ | ❌ | ❌ |
| Brightness and vibration settings | ✅ | ✅ | ✅ | ✅ |
| Boost / superboost (offsets / modes) | ❌ | ✅ | ✅ | ✅ |
| Heater mode (normal/boost/superboost) | ❌ | ✅ | ✅ | ❌ |
| ECO charging (optimization / limit) | ❌ | ✅ | ✅ | ❌ |
| Display-on-cooling / vibration-on-ready | ✅ | ❌ | ❌ | ❌ |
| Charge-LED / permanent-Bluetooth | ❌ | ❌ | ❌ | ✅ |
| Find device | ❌ | ✅ | ✅ | ✅ |
| Charging / setpoint-reached state | ❌ | ✅ | ✅ | ✅* |
| Local diagnostics (`run_analysis`) | ✅ | ✅ | ✅ | ✅ |
| Workflow presets | ✅ | ❌ | ❌ | ❌ |
| Custom workflows (`run_workflow`) | ✅ | ❌ | ❌ | ❌ |

<sub>*Crafty exposes `setpoint_reached` but not a charging bit (it signals charging via its LED only).</sub>

## Data Update Model

- Notification-driven updates are enabled on connect for supported characteristics.
- `update_state()` performs explicit reads/commands and is useful for an immediate refresh.
- Home Assistant integrations can treat notifications as the primary state stream and call `update_state()` for recovery or reconciliation.

## Concurrency and Command Semantics

- Device-level BLE I/O is serialized internally to avoid overlapping reads/writes.
- Commands that require responses (for example, qvap command exchange) raise `CommandTimeoutError` when the response does not arrive in time.
- `availability_transition_count` tracks connect/disconnect transitions to help downstream integrations avoid noisy up/down logging.

## Diagnostics Snapshot API

Each device exposes a sanitized diagnostics payload via:

```python
snapshot = device.get_diagnostics_snapshot()
```

Snapshot payloads intentionally omit serial numbers from `state` to reduce sensitive data exposure in logs and diagnostics exports.

## Known Limitations

- Firmware update workflows are not implemented in this library.
- Vendor cloud upload paths are intentionally out of scope.
- Detailed device-error decoding is server-side at Storz & Bickel: `run_analysis()` reports **which** error bits are set plus raw registers, not the per-bit cause. The Venty/Veazy analysis blob is cloud-only.
- The Venty/Veazy boost timeout is a fixed 90 s on/off setting (`set_boost_timeout_disabled`), not a configurable duration.
- BLE behavior can vary by adapter, OS, and stack implementation.

## Troubleshooting

- Ensure your BLE adapter is enabled and supports Bluetooth Low Energy.
- If a device is not discovered, retry scanning and confirm it is advertising.
- For flaky connections, disconnect and reconnect before issuing control commands.
- If command operations timeout, retry with a higher timeout and reduced command burst frequency.
- Use `get_diagnostics_snapshot()` when reporting issues to provide a sanitized runtime context.

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
uv run pytest
```

### Linting

```bash
uv run ruff check .
uv run ruff format .
```

### Type Checking

```bash
uv run mypy src
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

