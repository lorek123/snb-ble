# Example Scripts

## test_crafty.py

Test script for connecting to and controlling a real Crafty+ device.

### Usage

```bash
# From the project root
uv run python examples/test_crafty.py

# Or make it executable and run directly
chmod +x examples/test_crafty.py
./examples/test_crafty.py
```

### What it does

1. Scans for BLE devices (10 second timeout)
2. Finds and connects to a Crafty+ device
3. Reads and displays current device state
4. Tests various controls:
   - Set target temperature
   - Turn heater on/off
   - Monitor temperature updates
   - Test "Find Device" feature
5. Displays real-time updates via notifications

### Requirements

- Crafty+ device powered on
- Bluetooth enabled on your computer
- Device should be in range and not connected to another device

### Troubleshooting

- **Device not found**: Make sure the Crafty+ is powered on and Bluetooth is enabled
- **Connection failed**: The device might be connected to another device (phone app, etc.). Disconnect it first.
- **Permission errors**: On Linux, you may need to run with `sudo` or configure Bluetooth permissions

