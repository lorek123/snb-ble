# Storz & Bickel Device Control Protocol Documentation

This document provides comprehensive technical documentation for controlling Storz & Bickel vaporizers (Volcano Hybrid, Venty, and Crafty/Crafty+) via Bluetooth Low Energy (BLE). This documentation is based on the implementation in this repository and is intended for developers creating their own control applications.

## Table of Contents

1. [Overview](#overview)
2. [Device Discovery](#device-discovery)
3. [BLE Connection](#ble-connection)
4. [Service and Characteristic UUIDs](#service-and-characteristic-uuids)
5. [Data Formats](#data-formats)
6. [Status Registers](#status-registers)
7. [Commands and Operations](#commands-and-operations)
8. [Notifications](#notifications)
9. [Firmware Updates](#firmware-updates)
10. [Implementation Examples](#implementation-examples)
11. [Device-Specific Details](#device-specific-details)

## Overview

Storz & Bickel vaporizers communicate via BLE using custom service and characteristic UUIDs. The protocol supports:

- **Temperature Control**: Set and read target/current temperatures
- **Power Management**: Turn device on/off, control heater
- **Status Monitoring**: Battery level, charging status, runtime statistics
- **Device Configuration**: LED brightness, auto-off timer, vibration settings
- **Device-Specific Features**: Air pump (Volcano), boost mode (Crafty/Venty)

### Supported Devices

- **Volcano Hybrid**: Desktop vaporizer with air pump control
- **Venty**: Portable vaporizer with boost mode
- **Crafty/Crafty+**: Portable vaporizer with boost mode and vibration

## Device Discovery

### Device Names

Devices advertise with the following names:
- `S&B VOLCANO` - Volcano Hybrid
- `VENTY` - Venty
- `CRAFTY` - Crafty/Crafty+

### MAC Address

Each device has a unique MAC address that should be used for connection. The MAC address format is `XX:XX:XX:XX:XX:XX` (6 bytes, colon-separated hexadecimal).

## BLE Connection

### Connection Process

1. **Scan for Device**: Use BLE scanning to find devices by name or MAC address
2. **Connect**: Establish BLE connection to the device
3. **Service Discovery**: Discover available GATT services
4. **Characteristic Discovery**: Discover characteristics within each service
5. **Store Handles**: Store characteristic handles for later use (services may be released after discovery)
6. **Enable Notifications**: Enable notifications for characteristics that support them
7. **Initial Read**: Read initial values from important characteristics

### Connection State Management

- Devices may disconnect automatically after inactivity
- Implement reconnection logic with exponential backoff
- Recommended reconnect interval: 5 seconds
- Connection timeout: 30 seconds

## Service and Characteristic UUIDs

### Volcano Hybrid

#### Service UUIDs

```
Device Info Service:     10100000-5354-4f52-5a26-4249434b454c
Device Control Service:  10110000-5354-4f52-5a26-4249434b454c
```

#### Characteristic UUIDs

**Device Info Service:**
- `10100005-5354-4f52-5a26-4249434b454c` - Firmware Version (read, UTF-8 string)
- `10100008-5354-4f52-5a26-4249434b454c` - Serial Number (read, UTF-8 string)
- `10100004-5354-4f52-5a26-4249434b454c` - BLE Version (read)
- `1010000c-5354-4f52-5a26-4249434b454c` - Status Register 1 (read/notify, 2 bytes)
- `1010000d-5354-4f52-5a26-4249434b454c` - Status Register 2 (read/notify, 2 bytes)
- `1010000e-5354-4f52-5a26-4249434b454c` - Status Register 3 (read/notify, 2 bytes)

**Device Control Service:**
- `10110001-5354-4f52-5a26-4249434b454c` - Current Temperature (read/notify, 2 bytes)
- `10110003-5354-4f52-5a26-4249434b454c` - Target Temperature (read/write, 2 bytes)
- `1011000f-5354-4f52-5a26-4249434b454c` - Heater On (write, 1 byte)
- `10110010-5354-4f52-5a26-4249434b454c` - Heater Off (write, 1 byte)
- `10110013-5354-4f52-5a26-4249434b454c` - Air Pump On (write, 1 byte)
- `10110014-5354-4f52-5a26-4249434b454c` - Air Pump Off (write, 1 byte)
- `10110005-5354-4f52-5a26-4249434b454c` - LED Brightness (read/write, 2 bytes)
- `1011000c-5354-4f52-5a26-4249434b454c` - Auto-off Time (read/write, 2 bytes)
- `10110015-5354-4f52-5a26-4249434b454c` - Heating Hours (read/notify, 2 bytes)
- `10110016-5354-4f52-5a26-4249434b454c` - Heating Minutes (read/notify, 2 bytes)

### Venty



#### Service UUIDs

```
Main Service: 00000001-5354-4f52-5a26-4249434b454c
Generic Access Service: 00001800-0000-1000-8000-00805f9b34fb (for serial number)
```

#### Characteristic UUIDs

- `00000001-5354-4f52-5a26-4249434b454c` - Main Characteristic (read/notify/write, command-based protocol)
- `00002a00-0000-1000-8000-00805f9b34fb` - Device Name (read, contains serial number)

#### Command-Based Protocol

The Venty uses a command-based protocol where the first byte of the data packet indicates the command type:

**Command Bytes:**
- `0x01` - Status/Control command (main command for reading status and controlling device)
- `0x02` - Firmware version request
- `0x03` - Device analysis/error reporting
- `0x04` - Usage statistics request
- `0x05` - Serial number request
- `0x06` - Settings read/write (brightness, vibration, etc.)
- `0x13` - Find device (trigger vibration/LED alert)
- `0x30` (0x48) - Bootloader mode commands (firmware updates)

**Command Masks (for command 0x01):**
- Bit 1 (0x02) - Set Temperature Write
- Bit 2 (0x04) - Set Boost Write
- Bit 3 (0x08) - Set Superboost Write
- Bit 5 (0x20) - Heater Write
- Bit 7 (0x80) - Settings Write

**Settings Bits (byte 14 in command 0x01):**
- Bit 0 (0x01) - Unit (0 = Celsius, 1 = Fahrenheit)
- Bit 1 (0x02) - Setpoint Reached
- Bit 2 (0x04) - Factory Reset
- Bit 3 (0x08) - Eco Mode Charge
- Bit 4 (0x10) - Button Changed Filling Chamber
- Bit 5 (0x20) - Eco Mode Voltage
- Bit 6 (0x40) - Boost Visualization

**Response Format (Command 0x01):**
- Byte 0: Command (0x01)
- Byte 1: Mask/Status
- Byte 2-3: Current Temperature (little-endian, temp × 10)
- Byte 4-5: Target Temperature (little-endian, temp × 10)
- Byte 6: Boost Temperature Offset
- Byte 7: Superboost Temperature Offset
- Byte 8: Battery Level (0-100)
- Byte 9-10: Auto-shutoff Countdown (little-endian, seconds)
- Byte 11: Heater Mode (0 = off, 1 = normal, 2 = boost, 3 = superboost)
- Byte 13: Charger Connected (0/1)
- Byte 14: Settings (bit flags)

### Crafty/Crafty+

#### Service UUIDs

```
Service 1: 00000001-4c45-4b43-4942-265a524f5453
Service 2: 00000002-4c45-4b43-4942-265a524f5453
Service 3: 00000003-4c45-4b43-4942-265a524f5453
```

#### Characteristic UUIDs

**Service 1:**
- `00000021-4c45-4b43-4942-265a524f5453` - Target Temperature (read/write, 2 bytes)
- `00000041-4c45-4b43-4942-265a524f5453` - Battery Level (read/notify, 1 byte)

**Service 2:**
- `00000011-4c45-4b43-4942-265a524f5453` - Current Temperature (read/notify, 2 bytes)
- `00000031-4c45-4b43-4942-265a524f5453` - Heater On (write, 1 byte)
- `00000032-4c45-4b43-4942-265a524f5453` - Heater Off (write, 1 byte)
- `00000052-4c45-4b43-4942-265a524f5453` - Status Register (read/notify, variable length)
- `00000032-4c45-4b43-4942-265a524f5453` - Firmware Version (read, UTF-8 string)
- `00000072-4c45-4b43-4942-265a524f5453` - BLE Version (read, 3 bytes)

**Service 3:**
- `00000041-4c45-4b43-4942-265a524f5453` - Find Device (write, 1 byte)
- `00000073-4c45-4b43-4942-265a524f5453` - Akku Status (read/notify, charging detection)
- `00000023-4c45-4b43-4942-265a524f5453` - Usage Hours (read, 2 bytes)
- `000001e3-4c45-4b43-4942-265a524f5453` - Usage Minutes (read, 2 bytes)
- `00000093-4c45-4b43-4942-265a524f5453` - Project Status Register (read/notify, 2 bytes)
- `000001c3-4c45-4b43-4942-265a524f5453` - Project Status Register 2 (read/notify, 2 bytes)
- `00000051-4c45-4b43-4942-265a524f5453` - LED Brightness (read/write, 2 bytes)
- `00000071-4c45-4b43-4942-265a524f5453` - Auto-off Time (read/write, 2 bytes)
- `00000061-4c45-4b43-4942-265a524f5453` - Vibration (read/write, 2 bytes)

## Data Formats

### Temperature Encoding

Temperatures are encoded as 16-bit little-endian integers representing temperature × 10.

**Encoding:**
```python
# Convert Celsius to device format
temp_celsius = 185.0
temp_raw = int(temp_celsius * 10)  # 1850
data = [
    temp_raw & 0xFF,        # Low byte:  0x3A
    (temp_raw >> 8) & 0xFF  # High byte: 0x07
]
# Result: [0x3A, 0x07]
```

**Decoding:**
```python
# Convert device format to Celsius
data = [0x3A, 0x07]
temp_raw = data[0] | (data[1] << 8)  # 1850
temp_celsius = temp_raw / 10.0       # 185.0
```

**Temperature Ranges:**
- Volcano Hybrid: 40°C - 230°C
- Venty: 40°C - 210°C
- Crafty: 40°C - 210°C

### Battery Level

**Crafty:**
- Format: 1 byte, 0-100 (percentage)
- Read from: `00000041-4c45-4b43-4942-265a524f5453` (Service 1)

**Volcano Hybrid:**
- Battery level may not be available (desktop device)

### Status Registers

Status registers are 16-bit little-endian values with bit flags indicating device state.

**Format:**
```python
# Read 2 bytes
data = [0x20, 0x00]  # Example
status = data[0] | (data[1] << 8)  # 0x0020
```

See [Status Registers](#status-registers) section for bit definitions.

### LED Brightness

**Format:** 2 bytes, little-endian, range 1-9 (Volcano) or 0-100 (Crafty)

**Volcano:**
```python
brightness = 5
data = [brightness & 0xFF, (brightness >> 8) & 0xFF]
```

**Crafty:**
```python
brightness = 50  # 0-100
data = [brightness & 0xFF, (brightness >> 8) & 0xFF]
```

### Auto-off Time

**Format:** 2 bytes, little-endian, time in seconds

```python
seconds = 300  # 5 minutes
data = [seconds & 0xFF, (seconds >> 8) & 0xFF]
```

### String Data

Firmware version and serial number are UTF-8 strings. Remove null terminators when parsing.

```python
# Example: Firmware version
data = [0x56, 0x31, 0x2E, 0x30, 0x2E, 0x30, 0x00]  # "V1.0.0\0"
firmware = bytes(data).decode('utf-8').rstrip('\0')  # "V1.0.0"
```

## Status Registers

### Volcano Hybrid

#### Status Register 1 (0x1010000c)

| Bit | Mask | Description |
|-----|------|-------------|
| 5   | 0x0020 | Heater On |
| 9   | 0x0200 | Auto Shutdown Enabled |
| 13  | 0x2000 | Air Pump On |
| 1,2,6,14,15 | 0x4018 | Error bits |

#### Status Register 2 (0x1010000d)

| Bit | Mask | Description |
|-----|------|-------------|
| 9   | 0x0200 | Fahrenheit Mode |
| 12  | 0x1000 | Display On Cooling |
| 0-5,10-11 | 0x003B | Error bits |

#### Status Register 3 (0x1010000e)

| Bit | Mask | Description |
|-----|------|-------------|
| 10  | 0x0400 | Vibration On Ready |

### Crafty/Crafty+

#### Status Register (0x00000052)

This characteristic contains:
- First 8 bytes: Serial number (UTF-8 string)
- Last 2 bytes: Status register (little-endian)

**Status Register Bits:**
| Bit | Mask | Description |
|-----|------|-------------|
| 0   | 0x0001 | Heater On |
| 1   | 0x0002 | Boost Mode |
| 2   | 0x0004 | Vibration On Ready |
| 3   | 0x0008 | Fahrenheit Mode |

#### Project Status Register (0x00000093)

| Bit | Mask | Description |
|-----|------|-------------|
| 4   | 0x0010 | Crafty Active (Power On) |
| 5   | 0x0020 | Boost Mode Enabled |
| 6   | 0x0040 | Superboost Mode Enabled |

#### Project Status Register 2 (0x000001c3)

| Bit | Mask | Description |
|-----|------|-------------|
| 0   | 0x0001 | Vibration Disabled (inverted: 0 = enabled, 1 = disabled) |
| Other bits | - | LED brightness, auto-shutdown settings |

**Note:** For vibration, bit 0 = 0 means vibration is ENABLED, bit 0 = 1 means vibration is DISABLED (inverted logic).

## Commands and Operations

### Temperature Control

#### Set Target Temperature

**Volcano Hybrid:**
```
Characteristic: 10110003-5354-4f52-5a26-4249434b454c
Operation: Write
Data: [temp_low, temp_high]  (2 bytes, little-endian, temp × 10)
```

**Crafty:**
```
Characteristic: 00000021-4c45-4b43-4942-265a524f5453
Operation: Write
Data: [temp_low, temp_high]  (2 bytes, little-endian, temp × 10)
```

**Example (185°C):**
```python
temp = 185.0
temp_raw = int(temp * 10)  # 1850
data = [temp_raw & 0xFF, (temp_raw >> 8) & 0xFF]  # [0x3A, 0x07]
write_characteristic(char_uuid, data)
```

#### Read Current Temperature

**Volcano Hybrid:**
```
Characteristic: 10110001-5354-4f52-5a26-4249434b454c
Operation: Read or Notify
Data: [temp_low, temp_high]  (2 bytes, little-endian, temp × 10)
```

**Crafty:**
```
Characteristic: 00000011-4c45-4b43-4942-265a524f5453
Operation: Read or Notify
Data: [temp_low, temp_high]  (2 bytes, little-endian, temp × 10)
```

### Power Control

#### Turn Heater On

**Volcano Hybrid:**
```
Characteristic: 1011000f-5354-4f52-5a26-4249434b454c
Operation: Write
Data: [0x01]  (1 byte)
```

**Crafty:**
```
Characteristic: 00000031-4c45-4b43-4942-265a524f5453
Operation: Write
Data: [0x01]  (1 byte)
```

#### Turn Heater Off

**Volcano Hybrid:**
```
Characteristic: 10110010-5354-4f52-5a26-4249434b454c
Operation: Write
Data: [0x01]  (1 byte)
```

**Crafty:**
```
Characteristic: 00000032-4c45-4b43-4942-265a524f5453
Operation: Write
Data: [0x01]  (1 byte)
```

### Air Pump Control (Volcano Hybrid Only)

#### Turn Pump On
```
Characteristic: 10110013-5354-4f52-5a26-4249434b454c
Operation: Write
Data: [0x01]  (1 byte)
```

#### Turn Pump Off
```
Characteristic: 10110014-5354-4f52-5a26-4249434b454c
Operation: Write
Data: [0x01]  (1 byte)
```

### LED Brightness

#### Set LED Brightness

**Volcano Hybrid:**
```
Characteristic: 10110005-5354-4f52-5a26-4249434b454c
Operation: Write
Data: [brightness_low, brightness_high]  (2 bytes, little-endian, range 1-9)
```

**Crafty:**
```
Characteristic: 00000051-4c45-4b43-4942-265a524f5453
Operation: Write
Data: [brightness_low, brightness_high]  (2 bytes, little-endian, range 0-100)
```

### Auto-off Timer

#### Set Auto-off Time

**Volcano Hybrid:**
```
Characteristic: 1011000c-5354-4f52-5a26-4249434b454c
Operation: Write
Data: [seconds_low, seconds_high]  (2 bytes, little-endian, time in seconds)
```

**Crafty:**
```
Characteristic: 00000071-4c45-4b43-4942-265a524f5453
Operation: Write
Data: [seconds_low, seconds_high]  (2 bytes, little-endian, time in seconds)
```

### Status Register Control (Volcano Hybrid)

#### Set Status Register 2 (Display on Cooling, etc.)
```
Characteristic: 1010000d-5354-4f52-5a26-4249434b454c
Operation: Write
Data: [value_low, value_high]  (2 bytes, little-endian, bit flags)
```

**Example (Enable Display on Cooling):**
```python
# Set bit 12 (0x1000)
value = 0x1000
data = [value & 0xFF, (value >> 8) & 0xFF]  # [0x00, 0x10]
write_characteristic(char_uuid, data)
```

#### Set Status Register 3 (Vibration on Ready)
```
Characteristic: 1010000e-5354-4f52-5a26-4249434b454c
Operation: Write
Data: [value_low, value_high]  (2 bytes, little-endian, bit flags)
```

**Example (Enable Vibration on Ready):**
```python
# Set bit 10 (0x0400)
value = 0x0400
data = [value & 0xFF, (value >> 8) & 0xFF]  # [0x00, 0x04]
write_characteristic(char_uuid, data)
```

### Project Status Register Control (Crafty)

#### Set Project Status Register 2 (Vibration, LED, Auto-shutdown)
```
Characteristic: 000001c3-4c45-4b43-4942-265a524f5453
Operation: Write
Data: [value_low, value_high]  (2 bytes, little-endian, bit flags)
```

**Example (Disable Vibration):**
```python
# Set bit 0 (vibration disabled = 1)
# Read current value first, then set bit 0
current_value = read_characteristic(char_uuid)
value = current_value | 0x0001  # Set bit 0
data = [value & 0xFF, (value >> 8) & 0xFF]
write_characteristic(char_uuid, data)
```

### Find Device (Crafty)

#### Trigger Find Device (Vibration/LED Alert)
```
Characteristic: 00000041-4c45-4b43-4942-265a524f5453
Operation: Write
Data: [0x01]  (1 byte)
```

## Notifications

Many characteristics support notifications (indications) for real-time updates. Enable notifications by:

1. **Register for Notifications**: Call `esp_ble_gattc_register_for_notify()`
2. **Write to CCCD**: Write `[0x01, 0x00]` to the Client Characteristic Configuration Descriptor (CCCD)

## Firmware Updates

**Warning:** Firmware updates are complex operations that can brick devices if performed incorrectly. This documentation is for reference only. Use at your own risk.

### Overview

Firmware updates are device-specific and use different protocols:
- **Volcano Hybrid**: Uses bootloader mode with telegram-based protocol
- **Venty**: Uses command-based protocol with encryption
- **Crafty**: Firmware updates are not documented in the reference code

### Volcano Hybrid Firmware Update

The Volcano Hybrid uses a bootloader mode with a telegram-based communication protocol.

#### Bootloader Entry

1. **Switch to Bootloader Mode**:
   - Write value `4711` (0x1267) as 16-bit little-endian to Code Number characteristic:
     - UUID: `10100011-5354-4f52-5a26-4249434b454c`
     - Data: `[0x67, 0x12]`
   - Wait 1 second for device to enter bootloader mode

2. **Bootloader Service**:
   - Service UUID: `00000001-1989-0108-1234-123456789abc`
   - Read Characteristic: `00000003-1989-0108-1234-123456789abc` (notifications enabled)
   - Write Characteristic: `00000002-1989-0108-1234-123456789abc`

#### Telegram Protocol

All bootloader commands use a telegram format:

**Telegram Structure:**
```
[0xFE, 0xFA, 0x7F, length, ...data..., 0x00, 0xFD, checksum]
```

- **Header**: `0xFE 0xFA 0x7F`
- **Length**: Total telegram length (byte 3)
- **Data**: UTF-8 encoded command string
- **Footer**: `0x00 0xFD`
- **Checksum**: XOR of all data bytes (byte before 0xFD)

**Checksum Calculation:**
```python
def calc_checksum(data):
    """Calculate XOR checksum for telegram"""
    check = 0
    # XOR all bytes from position 4 to length-2
    for i in range(4, len(data) - 2):
        check ^= data[i]
    return check
```

#### Bootloader Commands

**Get Boot Status:**
```
Command: "RV0"
Response: "RV0 222 BL" (indicates bootloader active)
```

**Get Page Number:**
```
Command: "Ra1"
Response: "Ra1 <number>" (number of pages)
```

**Get Page Size:**
```
Command: "Ra2"
Response: "Ra2 <size>" (page size, typically 2048)
```

**Chip Erase:**
```
Command: "We "
Response: "W> " (ACK) or "W?" (NACK)
```

**Write Page Address:**
```
Command: "Wp  <page_number>" (4-digit zero-padded)
Example: "Wp  0000"
Response: "W> " (ACK)
```

**Flash Page:**
```
Command: "Wfp"
Response: "W> " (ACK)
```

**Get CRC Checksum:**
```
Command: "Rc "
Response: "Rc <checksum>" (e.g., "Rc 0xEF920C37")
```

**Send CRC Checksum:**
```
Command: "Wc  <checksum>"
Example: "Wc  0xEF920C37"
Response: "W> " (ACK)
```

**Exit Boot Mode:**
```
Command: "Wl "
Response: "W> " (ACK)
```

#### Update Process (State Machine)

1. **Idle** → **Get Boot Status** → Wait for "RV0 222 BL"
2. **Get Page Number** → Wait for "Ra1 <number>"
3. **Get Page Size** → Wait for "Ra2 <size>"
4. **Erase** → Send "We ", wait for "W> "
5. **Write Page Address** → For each page (0 to N-1):
   - Send "Wp  <page>", wait for "W> "
   - **Write Page Data** → Send 16 chunks of 128 bytes each
   - **Flash Page** → Send "Wfp", wait for "W> "
6. **Get CRC Checksum** → Send "Rc ", wait for "Rc <checksum>"
7. **Send CRC Checksum** → Send "Wc  <expected_checksum>", wait for "W> "
8. **Quit Boot Mode** → Send "Wl ", wait for "W> "

#### Page Data Format

**Page Size**: 2048 bytes
**Chunk Size**: 128 bytes per packet
**Chunks per Page**: 16 chunks

**Send Page Data Command:**
```
Command: "Wd<position> <hex_data>"
Example: "Wd0 <128 bytes hex>"
```

The data is sent in 13 packets of 20 bytes each (total 260 bytes including telegram overhead).

**Telegram Generation:**
```python
def generate_telegram(command_bytes, data_len):
    """Generate telegram with checksum"""
    buffer = bytearray(6 + len(command_bytes))
    buffer[0:3] = [0xFE, 0xFA, 0x7F]
    buffer[3] = 6 + data_len
    buffer[4:4+len(command_bytes)] = command_bytes
    buffer[4+len(command_bytes)] = 0x00
    buffer[5+len(command_bytes)] = 0xFD
    buffer[4+len(command_bytes)] = calc_checksum(buffer)  # Checksum before 0xFD
    return bytes(buffer)
```

#### Error Handling

- **Timeout**: 1500ms per operation, retry up to 6 times
- **NACK**: If "W?" received, retry the operation
- **Checksum Mismatch**: Verify telegram checksum before processing
- **Connection Interval**: BLE connection interval must be >= 25ms for reliable updates

### Venty Firmware Update

The Venty uses a command-based protocol with encryption support.

#### Update Types

- **Application Firmware**: Command byte `0x01`
- **Bootloader Firmware**: Command byte `0x30` (0x48)

#### Firmware Retrieval

Firmware is retrieved from server:
```
POST /firmware
Body: device=Venty&action=firmwareBootloader&serial=<serial>
      or device=Venty&action=firmwareApplication&serial=<serial>
Response: JSON with firmware (hex) and IV (hex)
```

#### Update Process

1. **Initialize Update**:
   - Command: `[0x01 or 0x30, 0x05, chunk_size]`
   - Chunk size: 128 bytes
   - Response: Status in command `0x01` or `0x30`

2. **Write Page Data**:
   - For each page (0 to N-1):
     - For each chunk (0 to 15):
       - Command: `[0x01 or 0x30, 0x01, page_idx, chunk_idx, ...128 bytes data...]`
       - Wait for response (status byte 1 = 1)
     - **Write Page Start**:
       - Command: `[0x01 or 0x30, 0x08, page_idx, 0x00, ...32 bytes IV...]`
       - Wait for response (status byte 1 = 8)
     - **Decrypt and Flash**:
       - Command: `[0x01 or 0x30, 0x02, page_idx]`
       - Wait for response (status byte 1 = 2)

3. **Confirm Update**:
   - Command: `[0x01 or 0x30, 0x03]`
   - Response: Status byte 1 = 3 indicates success
   - Send confirmation to server: `POST /firmware` with `action=firmwareConfirm`

#### Page Data Format

**Page Size**: 2048 bytes
**Chunk Size**: 128 bytes per packet
**Chunks per Page**: 16 chunks (2048 / 128)

**Data Packet Structure:**
```
Byte 0: Command (0x01 for app, 0x30/0x48 for bootloader)
Byte 1: Sub-command (0x01 = data, 0x08 = page start, 0x02 = flash, 0x03 = confirm)
Byte 2: Page index
Byte 3: Chunk index (for data) or 0x00 (for page start)
Bytes 4-131: Data (128 bytes) or IV (32 bytes for page start)
```

#### Response Status Codes

**Command 0x01/0x30 Response:**
- Status byte 1 = 1: Data chunk received, continue
- Status byte 1 = 2: Page flash complete, continue to next page
- Status byte 1 = 3: Confirmation received
- Status byte 1 = 8: Decrypt complete, ready for flash
- Status byte 1 = 19: Validation failed (retry once)
- Status byte 1 = 34: Erase failed
- Status byte 1 = 35: Validation failed
- Status byte 1 = 51: Validation failed (mode)
- Status byte 1 = 82: Version major failed
- Status byte 1 = 98: Version minor failed

#### Error Handling

- **Timeout**: 750ms per operation, retry up to 14 times
- **Connection Interval**: Must be >= 25ms for reliable updates
- **Validation Errors**: Some errors allow one retry (status 19)

#### Encryption

- Firmware data is encrypted
- IV (Initialization Vector) is provided by server
- IV is sent with page start command (byte 1 = 0x08)
- Device handles decryption internally

### Important Notes

1. **Browser Support**: Firmware updates require `writeValueWithoutResponse` support (not available in all browsers)
2. **Connection Stability**: Maintain stable BLE connection throughout update
3. **Power**: Device must remain powered during entire update process
4. **Serial Number**: Required for firmware retrieval from server
5. **Checksums**: Always verify firmware checksums before and after update
6. **Reconnection**: Device may disconnect after update; reconnect to verify new firmware version

### Implementation Notes

The firmware update process uses state machines and requires careful error handling:
- **Volcano Hybrid**: Uses telegram-based protocol with checksums and state machine (idle → erase → write → flash → verify → exit)
- **Venty**: Uses command-based protocol with encryption, page-by-page updates with IV handling

### Characteristics with Notifications

**Volcano Hybrid:**
- Current Temperature (`10110001-...`)
- Status Register 1 (`1010000c-...`)
- Status Register 2 (`1010000d-...`)
- Status Register 3 (`1010000e-...`)
- Heating Hours (`10110015-...`)
- Heating Minutes (`10110016-...`)

**Crafty:**
- Current Temperature (`00000011-...`)
- Battery Level (`00000041-...` in Service 1)
- Status Register (`00000052-...`)
- Project Status Register (`00000093-...`)
- Project Status Register 2 (`000001c3-...`)
- Akku Status (`00000073-...`)

### Notification Handling

When a notification is received:
1. Parse the data according to the characteristic's format
2. Update internal state
3. Trigger callbacks/events for UI updates

## Implementation Examples

### Python Example (using bleak)

```python
import asyncio
from bleak import BleakClient, BleakScanner

# UUIDs
VOLCANO_SERVICE_CONTROL = "10110000-5354-4f52-5a26-4249434b454c"
CHAR_TARGET_TEMP = "10110003-5354-4f52-5a26-4249434b454c"
CHAR_CURRENT_TEMP = "10110001-5354-4f52-5a26-4249434b454c"
CHAR_HEATER_ON = "1011000f-5354-4f52-5a26-4249434b454c"

def encode_temperature(temp_celsius):
    """Encode temperature as 2-byte little-endian (temp × 10)"""
    temp_raw = int(temp_celsius * 10)
    return bytes([temp_raw & 0xFF, (temp_raw >> 8) & 0xFF])

def decode_temperature(data):
    """Decode temperature from 2-byte little-endian"""
    temp_raw = data[0] | (data[1] << 8)
    return temp_raw / 10.0

async def control_volcano():
    # Scan for device
    device = await BleakScanner.find_device_by_name("S&B VOLCANO")
    if not device:
        print("Device not found")
        return

    async with BleakClient(device) as client:
        # Set target temperature to 185°C
        temp_data = encode_temperature(185.0)
        await client.write_gatt_char(CHAR_TARGET_TEMP, temp_data)
        print("Set target temperature to 185°C")

        # Turn heater on
        await client.write_gatt_char(CHAR_HEATER_ON, b"\x01")
        print("Heater turned on")

        # Read current temperature
        data = await client.read_gatt_char(CHAR_CURRENT_TEMP)
        temp = decode_temperature(data)
        print(f"Current temperature: {temp}°C")

        # Enable notifications for current temperature
        await client.start_notify(CHAR_CURRENT_TEMP, notification_handler)

        # Keep connection alive
        await asyncio.sleep(60)

def notification_handler(sender, data):
    """Handle notification data"""
    temp = decode_temperature(data)
    print(f"Temperature update: {temp}°C")

asyncio.run(control_volcano())
```

### JavaScript Example (using noble)

```javascript
const noble = require('@abandonware/noble');

const CHAR_TARGET_TEMP = '10110003-5354-4f52-5a26-4249434b454c';
const CHAR_CURRENT_TEMP = '10110001-5354-4f52-5a26-4249434b454c';
const CHAR_HEATER_ON = '1011000f-5354-4f52-5a26-4249434b454c';

function encodeTemperature(tempCelsius) {
    const tempRaw = Math.round(tempCelsius * 10);
    return Buffer.from([tempRaw & 0xFF, (tempRaw >> 8) & 0xFF]);
}

function decodeTemperature(data) {
    const tempRaw = data[0] | (data[1] << 8);
    return tempRaw / 10.0;
}

noble.on('stateChange', async (state) => {
    if (state === 'poweredOn') {
        await noble.startScanning(['10110000-5354-4f52-5a26-4249434b454c'], false);
    }
});

noble.on('discover', async (peripheral) => {
    if (peripheral.advertisement.localName === 'S&B VOLCANO') {
        await noble.stopScanning();

        await peripheral.connect();
        const { characteristics } = await peripheral.discoverAllServicesAndCharacteristics();

        // Find characteristics
        const targetTempChar = characteristics.find(c => c.uuid === CHAR_TARGET_TEMP);
        const currentTempChar = characteristics.find(c => c.uuid === CHAR_CURRENT_TEMP);
        const heaterOnChar = characteristics.find(c => c.uuid === CHAR_HEATER_ON);

        // Set target temperature
        const tempData = encodeTemperature(185.0);
        await targetTempChar.write(tempData, false);
        console.log('Set target temperature to 185°C');

        // Turn heater on
        await heaterOnChar.write(Buffer.from([0x01]), false);
        console.log('Heater turned on');

        // Read current temperature
        const tempData = await currentTempChar.read();
        const temp = decodeTemperature(tempData);
        console.log(`Current temperature: ${temp}°C`);

        // Enable notifications
        await currentTempChar.subscribe();
        currentTempChar.on('data', (data) => {
            const temp = decodeTemperature(data);
            console.log(`Temperature update: ${temp}°C`);
        });
    }
});
```

## Device-Specific Details

### Volcano Hybrid

**Special Features:**
- Air pump control (on/off)
- Status register 2 for display settings
- Status register 3 for vibration settings
- Heating hours/minutes tracking

**Connection Notes:**
- Requires both Device Info and Device Control services
- Status registers should be read after connection
- Enable notifications for real-time updates

### Venty

**Special Features:**
- Command-based protocol (single characteristic with command bytes)
- Boost mode and Superboost mode
- Temperature unit selection (Celsius/Fahrenheit)
- Eco mode settings (charge optimization, voltage limit)
- Boost visualization toggle
- Factory reset capability
- Device analysis/error reporting

**Connection Notes:**
- Uses single main service with command-based protocol
- Main characteristic (`00000001-5354-4f52-5a26-4249434b454c`) handles all operations via command bytes
- Serial number can be read from Generic Access Service characteristic `00002a00-0000-1000-8000-00805f9b34fb`
- After connection, send initialization sequence:
  1. Command `0x02` - Request firmware version
  2. Command `0x01` - Request status
  3. Command `0x04` - Request usage statistics
  4. Command `0x05` - Request serial number
  5. Command `0x06` - Request settings
  6. Command `0x01` with byte 1 = 0x06 - Start periodic updates (every 500ms)

**Protocol Details:**
- All commands use 20-byte buffers (except some specific commands)
- Command byte is first byte of packet
- Use masks in byte 1 to indicate which fields to write
- Settings are written using bit flags in bytes 14-15
- Temperature values are encoded as little-endian 16-bit (temp × 10)
- Heater mode: 0 = off, 1 = normal, 2 = boost, 3 = superboost

### Crafty/Crafty+

**Special Features:**
- Boost mode
- Vibration control
- Find device feature
- Battery level monitoring
- Charging status detection

**Connection Notes:**
- Three services with different purposes:
  - Service 1: Basic control (target temp, battery)
  - Service 2: Status and heater control
  - Service 3: Advanced features (find device, usage stats, project registers)
- Serial number is embedded in status register characteristic
- Project status registers provide detailed state information
- Akku status characteristic provides charging detection

**Battery Monitoring:**
- Read from Service 1, characteristic `00000041-...`
- Format: 1 byte, 0-100 (percentage)
- Supports notifications for real-time updates

**Charging Detection:**
- Read from Service 3, characteristic `00000073-...` (Akku Status)
- Parse data to determine charging state

## Best Practices

1. **Handle Disconnections**: Implement robust reconnection logic
2. **Store Handles**: Services may be released after discovery; store characteristic handles
3. **Enable Notifications**: Use notifications instead of polling when possible
4. **Validate Data**: Always validate data length and range before parsing
5. **Error Handling**: Handle BLE errors gracefully (timeouts, disconnections)
6. **Temperature Clamping**: Clamp temperatures to device-specific ranges
7. **State Synchronization**: Read initial state after connection before sending commands
8. **Bit Manipulation**: Use proper bit masks when reading/writing status registers

## Troubleshooting

### Connection Issues

- **Device not found**: Ensure device is powered on and Bluetooth is enabled
- **Connection timeout**: Check device is in range and not connected to another device
- **Service discovery fails**: Wait for connection to fully establish before discovering services

### Data Issues

- **Invalid temperature**: Check data length (should be 2 bytes) and range
- **Status register wrong**: Verify byte order (little-endian)
- **String parsing fails**: Remove null terminators and handle UTF-8 encoding

### Notification Issues

- **Notifications not received**: Ensure CCCD is written correctly (`[0x01, 0x00]`)
- **Notifications stop**: Device may have disconnected; implement reconnection

## License and Disclaimer

This documentation is based on reverse engineering and is not officially supported by Storz & Bickel. Use at your own risk. The authors are not responsible for any damage to devices.

## References

- This documentation is based on the implementation in the Vulcano ESPHome component
- BLE GATT specification: https://www.bluetooth.com/specifications/specs/core-specification/
- ESP-IDF BLE documentation: https://docs.espressif.com/projects/esp-idf/en/latest/esp32/api-reference/bluetooth/esp_gattc.html
