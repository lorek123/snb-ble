# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Fixed
Found by cross-checking the vendor web app and other open-source S&B clients (orth4x0r/venty-android, andrzejdus/glow, SavageNL/home-assistant-volcano-hybrid, firsttris/reactive-volcano-app, Chuffnugget/volcano_integration):
- Venty/Veazy: find device is cmd `0x0D` (was `0x13`, which did nothing).
- Venty/Veazy: settings writes (unit, eco charge, eco voltage, boost visualization) now set the byte-15 change mask; without it the device ignored them.
- Venty/Veazy: switching to boost/superboost no longer also writes the boost/superboost offset as 0.
- Venty/Veazy: leaving boost/superboost turns the heater off before writing mode 1 (mode 1 alone does not end boost).
- Venty/Veazy: serial number is bytes 15-16 + 9-14 of the `0x05` response; auto-shutoff adds bytes 9 + 10 like the vendor app; `VENTY_SERVICE_MAIN` is `00000000-…`.
- Volcano: target temperature is written as uint32, like the vendor app.
- Crafty: the boost offset is rewritten after every target write, like the vendor app.
- Crafty: `setpoint_reached` now follows project status bit 8, which holds while at temperature (verified on a Crafty+, FW V04.26). Project status 2 bit 2 only pulses for ~2 s, so the Ready state was almost never seen (ha-snb#34).

### Changed
- Venty/Veazy: the current-temperature bytes of the `0x01` status packet are `0x8000` ("not reported") on real devices, idle and heating (FW V01.11), and the vendor app hides the current temperature for these models. This is now handled explicitly as `None` instead of relying on the range check (the old "~3276 °C" reading in ha-snb#8).

## [0.1.24] - 2026-11-10

### Added
- Crafty/Crafty+: charge state. `CraftyState.charger_connected` (char `0x83` bit 0, or akkuStatusReg2 `0x73` bit 13), `battery_full` (akkuStatusReg `0x63` bits 4+6, the point the device LED goes solid) and `charging` (connected and not full). The raw `power_status_register`, `akku_status_register` and `akku_status_register_2` are exposed too. `0x63` is subscribed for notifications so charging -> full updates without a poll. Bits were determined on a Crafty+ (FW V04.26) by unplugging/replugging the charger and charging to 100 %; the web app does not decode them.

## [0.1.23] - 2026-11-10

### Fixed
- Venty/Veazy: the connect sequence sent cmd `0x01` with byte 1 = `0x06` as "start periodic updates". Byte 1 of a `0x01` packet is the write mask (`0x02` target temperature, `0x04` boost offset), so every connect wrote zeroed target/boost values. Connect now mirrors the vendor app: `0x02`, `0x1D`, then (on application firmware) `0x30` with byte 1 = `0x06` (ha-snb#8).
- Venty/Veazy: byte 1 of the `0x02` firmware response is the application-firmware flag, not part of the version string; exposed as `VentyDevice.application_firmware`.

### Added
- Venty/Veazy: raw notification payloads are logged (hex) at debug level, to diagnose device reports.

## [0.1.22] - 2026-11-10

### Fixed
- Volcano: status registers 2/3 are now changed with the firmware's 4-byte bit set/clear command (low 16 bits = mask, bit 16 = set) instead of writing a uint16 register image. The old write could disable Bluetooth when toggling vibration-on-ready.
- Volcano: `display_on_cooling` and `vibration_on_ready` were decoded inverted — the register bits are disable flags.
- Volcano: LED brightness is 0-100 (vendor app slider, step 10), not 1-9.
- Volcano: the auto-off *setting* is read/written on `1011000d`; `1011000c` is the live countdown, now exposed as `VolcanoState.auto_off_countdown`.

### Deprecated
- `CraftyDevice.toggle_boost_mode()` and `set_superboost()`: boost/superboost are status bits set by the device button; the firmware ignores BLE writes to them.

## [0.1.20] - 2026-06-29

### Added
- Added `VolcanoDevice.run_workflow(steps)` to run a custom timed heat+pump sequence — a list of `(target_temperature, hold_seconds, pump_seconds)` steps. This is the engine the built-in presets already used, now exposed for user-defined balloon/flow workflows; `run_workflow_preset` is a thin wrapper over it.

## [0.1.19] - 2026-06-29

### Changed
- Enriched `run_analysis` on all device classes with a consistent schema: `ok`, `warnings`, `errors`, a structured `findings` list (which error-mask bits are set per register), and a `diagnostics` map of raw register/history values (as hex). Per-bit error *meanings* are decoded on Storz & Bickel's servers, not in the client, so only the locally-known cases (e.g. the Crafty akku charger/cable error) carry a `meaning`; Venty/Veazy note that the detailed report is cloud-only.

## [0.1.18] - 2026-06-29

### Changed
- Extended the `BaseDevice._tolerate` hardening to the Crafty, Venty, and Volcano notification handlers, so a programming error in a notification callback surfaces (and fails tests) instead of being swallowed. The Venty main-notification path still releases any waiting command on a bug so it can't hang.

## [0.1.17] - 2026-06-29

### Added
- Added `CraftyDevice.set_charge_led()` and `set_permanent_bluetooth()`, toggling the project-status-register-2 charge-LED and auto-BLE-shutdown bits.
- Added `CraftyState.charge_led_enabled`, `permanent_bluetooth`, and `setpoint_reached`, decoded from project status register 2.
- Added a frontend capability audit document at `docs/app-frontend-capabilities.md` for Home Assistant integration planning.
- Captured and compared STORZ & BICKEL web app device/capability coverage against current library support, including identified feature gaps.
- Added HA library readiness checklist at `docs/ha-library-quality-checklist.md`.
- Added sanitized diagnostics snapshots via `get_diagnostics_snapshot()` with serial number redaction.
- Added explicit BLE operation exception types: `CharacteristicReadError`, `CharacteristicWriteError`, `NotificationSetupError`, and `CommandTimeoutError`.
- Added availability transition tracking via `availability_transition_count` for deterministic up/down transition handling.
- Added tests for diagnostics sanitization, availability transitions, and command timeout behavior.
- Added tests covering the Venty (boost/superboost offset, ECO charge/voltage, boost visualization) and Volcano (LED brightness, auto-off) setters that the Home Assistant integration depends on.

### Changed
- Hardened the Crafty, Venty, and Volcano poll loops (`update_state`) via `BaseDevice._tolerate`: per-characteristic device/transport errors are still tolerated, but programming errors (missing import, renamed attribute) now surface with their real type instead of being silently swallowed as stale state.
- Decoded and wrote Crafty project status register 2 through shared helpers (`_apply_project_status2`, `_write_project_status2_bit`) so polling, notifications, and setters can't drift.
- Serialized per-device BLE I/O operations in `BaseDevice` to reduce read/write overlap races.
- Updated docs with supported-function matrix, data update model, concurrency contract, known limitations, and troubleshooting guidance.
- Increased coverage quality gate to `58` (config previously lagged at `50`).

## [0.1.2] - 2025-12-30

### Changed
- Re-release after repository history cleanup

## [0.1.1] - 2025-12-30

### Changed
- Re-release after repository history cleanup

## [0.1.0] - 2025-12-28

### Added
- Initial release
- Support for Volcano Hybrid device
- Support for Venty device
- Support for Crafty/Crafty+ device
- Device discovery and scanning
- Temperature control
- Heater control
- Status monitoring via notifications
- LED brightness control
- Auto-off timer configuration
- Air pump control (Volcano)
- Boost mode support (Venty, Crafty)
- Vibration control (Crafty)
- Battery monitoring (Venty, Crafty)
- Comprehensive test suite
- Full type hints
- Pydantic models for data validation
- Docker support
- CI/CD pipeline
- Documentation

### Experimental
- Firmware update support (Volcano, Venty) - Use at your own risk

