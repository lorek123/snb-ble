# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Install dependencies
uv sync --all-extras

# Lint and format
uv run ruff check src/ tests/
uv run ruff format src/ tests/

# Type check
uv run mypy src/

# Run tests
uv run pytest
uv run pytest tests/test_volcano.py          # Single test module
uv run pytest -k "test_connect"              # Single test by name
uv run pytest --cov=storzandbickel_ble       # With coverage

# Version bumping (updates pyproject.toml + CHANGELOG)
uv run bump2version patch   # or minor / major
```

Tests require 50% minimum coverage. Async tests use `@pytest.mark.asyncio`.

## Architecture

The library is a typed async BLE client for Storz & Bickel vaporizers (Volcano, Venty, Veazy, Crafty). Device classes are instantiated by the client factory and share a common BLE I/O layer.

### Layers

**`client.py`** — Entry point. `StorzBickelClient` scans for devices by name pattern, detects device type, and returns a connected device instance via `connect_device()`.

**`device.py`** — Abstract `BaseDevice`. Owns the bleak client, an `_io_lock` (asyncio.Lock serializing all BLE reads/writes), notification subscriptions, and connection lifecycle. All device reads/writes go through `_read_characteristic()` / `_write_characteristic()`.

**`volcano.py` / `venty.py` / `crafty.py`** — Concrete device classes. Each reads/writes specific GATT characteristics and maintains a `DeviceState` Pydantic model (`VolcanoState`, `VentyState`, `CraftyState`). State is updated both by polling and BLE notifications.

**`protocol.py`** — All UUIDs, service/characteristic constants, and encode/decode utilities (temperature ×10 two-byte LE, uint16 LE, strings). Venty uses a command-byte protocol built here; Volcano and Crafty write directly to characteristics.

**`models.py`** — Pydantic v2 models: `DeviceState`, per-device state subclasses, `DeviceInfo`, `DeviceType` enum, `HeaterMode`, `TemperatureUnit`.

**`exceptions.py`** — Custom exception hierarchy rooted at `StorzBickelError`.

**`firmware/`** — Firmware update helpers for Volcano and Venty (separate from normal operation).

### Key Patterns

- **Protocol differences**: Venty/Veazy use a command-byte write to a single command characteristic; Volcano/Crafty write directly to individual characteristics per feature.
- **Notifications as primary state**: Notification callbacks push state changes asynchronously; polling is secondary. Follows Home Assistant integration conventions.
- **`bleak-retry-connector`**: Used for connection resilience, especially over ESPHome BLE proxies.
- **Temperature encoding**: Always `int(celsius * 10)` packed as 2-byte little-endian. See `protocol.encode_temperature()`.
- **Diagnostics**: `device.diagnostics()` returns a sanitized state dict (serial numbers stripped) safe to share in bug reports.

### Device Support Matrix

| Device | Temp | Pump/Fan | Heater | Battery | Boost |
|---|---|---|---|---|---|
| Volcano Hybrid | ✓ | ✓ (pump) | ✓ | — | — |
| Venty / Veazy | ✓ | — | ✓ | ✓ | ✓ |
| Crafty / Crafty+ | ✓ | — | ✓ | ✓ | ✓ |

### BLE Protocol Reference

`s&b_procol.md` in the repo root documents all known GATT service/characteristic UUIDs and data formats for each device type.
