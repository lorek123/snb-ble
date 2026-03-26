# Home Assistant Library Quality Checklist

This checklist adapts Home Assistant's Integration Quality Scale rules to this
library's scope. It tracks what the library can directly enable for downstream
Home Assistant integrations.

Reference:
<https://developers.home-assistant.io/docs/core/integration-quality-scale/checklist/>

## How to use

- **Current status**: where this repository is today.
- **Target**: desired state for HA-readiness.
- **Owner**: proposed owner for the work item (`lib`, `docs`, or `integration`).
- **Notes**: short implementation guidance and links to relevant modules.

## Checklist

| Rule (HA) | Current status | Target | Owner | Notes |
|---|---|---|---|---|
| `async-dependency` | Implemented (ongoing verification) | Full async-only I/O surface | lib | BLE operations are async; keep runtime paths free from blocking calls in `client.py`, `crafty.py`, `venty.py`, `volcano.py`. |
| `strict-typing` | Partial | Strict typing maintained across public API and internals | lib | `mypy` strict options are enabled in `pyproject.toml`; keep new APIs fully typed. |
| `test-coverage` (integration enabler) | Partial (improved) | Raise and maintain high coverage for core modules | lib | Coverage gate increased to `--cov-fail-under=55`; continue incrementally toward HA-level reliability expectations. |
| `action-exceptions` (integration enabler) | Implemented (baseline) | Stable, explicit exception taxonomy for all command failures | lib | Added explicit BLE operation exceptions (`CharacteristicReadError`, `CharacteristicWriteError`, `NotificationSetupError`, `CommandTimeoutError`). |
| `log-when-unavailable` (integration enabler) | Implemented (baseline) | Clear unavailable/available state transitions exposed | lib | `availability_transition_count` now tracks connect/disconnect transitions for deterministic up/down logging behavior. |
| `diagnostics` (integration enabler) | Implemented (baseline) | Sanitized diagnostics snapshot API available | lib | `get_diagnostics_snapshot()` now returns sanitized payloads and omits serial numbers from exported state. |
| `docs-supported-devices` | Partial | Explicit supported/unsupported matrix kept current | docs | Keep docs aligned with device capability reality (Crafty/Crafty+, Venty, Veazy, Volcano). |
| `docs-supported-functions` | Implemented (baseline) | Per-device capability matrix for major features | docs | README now includes a per-family function matrix for major capability areas. |
| `docs-known-limitations` | Implemented (baseline) | Dedicated limitations section with protocol and scope constraints | docs | README and usage docs now include explicit known limitations and out-of-scope areas. |
| `docs-data-update` (library equivalent) | Implemented (baseline) | Document notification vs polling behavior and timing expectations | docs | README and usage docs now describe notification-driven updates and when to call `update_state()`. |
| `docs-examples` | Implemented (baseline) | Focused examples for common HA-oriented tasks | docs | Usage docs cover discovery, connect, control, analysis, and error handling patterns. |
| `docs-troubleshooting` | Implemented (baseline) | Add troubleshooting section for common BLE/runtime failures | docs | Added troubleshooting guidance for BLE adapter/discovery/timeout/reconnect behavior. |
| `parallel-updates` (integration enabler) | Implemented (baseline) | Concurrency behavior documented and test-backed | lib | Device-level BLE I/O is now serialized in `BaseDevice`; docs describe concurrency contract. |

## Out of scope for this library

These HA rules are primarily owned by the integration layer, not the library:

- `config-flow`
- `unique-config-entry`
- `reauthentication-flow`
- `config-entry-unloading`
- `entity-unique-id`
- `entity-device-class`
- `entity-category`
- `entity-disabled-by-default`
- `repair-issues`
- `stale-devices`

## Suggested milestones

1. **Reliability baseline**
   - Raise test coverage gate in steps.
   - Tighten exception mapping and unavailable-state transitions.
2. **Developer ergonomics**
   - Add diagnostics snapshot and concurrency contract docs.
3. **Documentation completion**
   - Publish supported devices/functions matrix.
   - Add known limitations and troubleshooting sections.
