# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Added a frontend capability audit document at `docs/app-frontend-capabilities.md` for Home Assistant integration planning.
- Captured and compared STORZ & BICKEL web app device/capability coverage against current library support, including identified feature gaps.
- Added HA library readiness checklist at `docs/ha-library-quality-checklist.md`.
- Added sanitized diagnostics snapshots via `get_diagnostics_snapshot()` with serial number redaction.
- Added explicit BLE operation exception types: `CharacteristicReadError`, `CharacteristicWriteError`, `NotificationSetupError`, and `CommandTimeoutError`.
- Added availability transition tracking via `availability_transition_count` for deterministic up/down transition handling.
- Added tests for diagnostics sanitization, availability transitions, and command timeout behavior.

### Changed
- Serialized per-device BLE I/O operations in `BaseDevice` to reduce read/write overlap races.
- Updated docs with supported-function matrix, data update model, concurrency contract, known limitations, and troubleshooting guidance.
- Increased coverage quality gate from `45` to `55`.

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

