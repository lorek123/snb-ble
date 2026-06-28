---
name: analyze-sb-app
description: >-
  Reverse-engineer the official Storz & Bickel app (the Web Bluetooth PWA at
  app.storz-bickel.com, snapshotted under research/storz-bickel-app/, and
  optionally the Android APK via the jadx MCP) to extract or verify BLE protocol
  details — GATT service/characteristic UUIDs, command byte sequences,
  notification/status-register formats, and per-device behavior — and feed them
  into this library (protocol.py, the device classes, models.py) and the
  protocol docs. Use this whenever the task involves figuring out HOW a
  vaporizer feature works over BLE, finding the UUID or command for a feature,
  closing a gap between the app and the library, auditing what the frontend can
  do that we don't, or updating s&b_procol.md / app-frontend-capabilities.md.
  Trigger even if the user just says "how does the app set boost temp", "what
  characteristic does X use", "diff the app against our library", or names a
  file like qvap.js / crafty.js / volcano.js.
---

# Analyze the Storz & Bickel app

The official app is the ground truth for this library. Storz & Bickel publish no
protocol spec, so every UUID and command we implement was read out of their app.
This skill is how you go from "the app can do X" to "the library does X, and it's
documented and tested."

## Where the app lives

The app is a **Web Bluetooth PWA**. A local snapshot is checked out under:

```
research/storz-bickel-app/
  index.html
  js/main.js       # device detection, app shell, dispatch
  js/volcano.js    # Volcano Hybrid handlers
  js/crafty.js     # Crafty / Crafty+ handlers
  js/qvap.js       # Venty + Veazy ("qvap" = the command-byte device family)
  js/workflow.js   # Volcano balloon/flow timed sequences
```

`research/` is **gitignored on purpose** — it holds vendor assets and must never
be committed. Read it freely, quote byte sequences and UUIDs into our own docs,
but don't copy vendor JS into tracked files.

To refresh the snapshot from the live app (`https://app.storz-bickel.com/`, check
the version string in the app shell against the date in
`docs/app-frontend-capabilities.md`), fetch the page and its `js/*` assets into
`research/storz-bickel-app/`. The web bundle is the fastest source.

**Android APK (deeper / harder):** the `jadx` MCP server gives decompiled Java if
the web app is minified past usefulness or a feature only exists on mobile. It is
disabled by default in `.claude/settings.local.json` (`disabledMcpjsonServers`).
Mention to the user that it needs enabling + a decompiled APK loaded before its
tools work; prefer the web bundle unless it can't answer the question.

## The S&B UUID convention (your fastest grep)

S&B's proprietary characteristics all share one base. The 16-bit-looking prefix
varies per characteristic; the suffix is constant and spells `STORZ&BICKEL` in
ASCII:

```
xxxxxxxx-5354-4f52-5a26-4249434b454c   <- S&B proprietary (53='S' 54='T' ... 4c='L')
0000xxxx-0000-1000-8000-00805f9b34fb   <- standard BLE SIG (e.g. 2a00 = device name)
```

So to enumerate everything the app touches:

```bash
grep -rnoE '[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}' research/storz-bickel-app/js/
```

Then map each UUID to its meaning by reading the surrounding handler.

## How the app talks BLE — what to look for

The PWA uses the Web Bluetooth API. The call shapes that reveal the protocol:

- `getPrimaryService(<service-uuid>)` / `getCharacteristic(<char-uuid>)` — wiring a
  feature to a characteristic.
- `characteristic.writeValue(dataView)` — a command/setter. **Read backwards from
  here** to see how `dataView` was built.
- `startNotifications()` + an `oncharacteristicvaluechanged` handler — live state;
  the handler shows the decode layout (which byte is temp, which bit is a flag).
- `DataView` / `ArrayBuffer` + `setUint8(offset, value)` / `setUint16(offset, value,
  littleEndian)` — the byte layout of a command. Note offsets and endianness.

### Two protocol families — know which one you're in

This split is the single most important thing to get right:

- **Volcano Hybrid & Crafty/Crafty+** write **directly to a dedicated characteristic
  per feature** (separate UUIDs for heater-on, heater-off, pump-on, target-temp,
  LED brightness, …). Finding the feature = finding its characteristic UUID.
- **Venty & Veazy (`qvap.js`)** use a **command-byte protocol**: a single command
  characteristic receives a packet whose first byte is the opcode. Settings (LED
  brightness, vibration, boost/superboost timeout, factory reset) are multiplexed
  under **command `0x06`**, differentiated by a sub-selector/bitfield. Finding the
  feature = finding its opcode and the byte/bit it sets, not a new UUID.

Mirror this in code: `protocol.py` defines `*_CHAR_*` UUID constants for the direct
devices and command/encode helpers for the qvap family; `venty.py` builds command
packets, `volcano.py`/`crafty.py` write characteristics.

### Encodings you'll see repeatedly

- **Temperature:** `int(celsius * 10)` packed **2-byte little-endian**. e.g. 186.0 °C
  → 1860 → `0x44 0x07`. Use `protocol.encode_temperature()` / `decode_temperature()`;
  don't re-derive it inline.
- **Status / project-status registers** (Volcano, Crafty): a uint16 bitfield where
  individual bits are flags (vibration, display-on-cooling, permanent-Bluetooth,
  charge-lamp, …). The app reads the register, flips one bit, writes it back. Capture
  *which bit* — that's the whole finding. See the "Status Registers" section of
  `s&b_procol.md`.
- **Battery:** uint8 percent. **Strings** (serial, firmware): UTF-8 char reads.

## Cross-reference against the library

A finding isn't done until you've checked it against what we already have. The
targets, in order:

1. `src/storzandbickel_ble/protocol.py` — UUID constants, encode/decode, name/temp
   ranges. Is the UUID already named here? Under the right device?
2. `src/storzandbickel_ble/{volcano,crafty,venty}.py` — is there a method that
   writes it? For qvap, is the opcode/bit already handled?
3. `src/storzandbickel_ble/models.py` — is the state field modeled
   (`VolcanoState` / `CraftyState` / `VentyState`, `DeviceType`, enums)?
4. `s&b_procol.md` — is it documented? This file is the human-readable protocol
   reference (UUID tables, data formats, status-register bit maps, command lists).
5. `docs/app-frontend-capabilities.md` — the app-vs-library capability matrix and
   the gap list. Keep its status column honest (Implemented / Partial / Missing /
   Out of scope).

## Output: a findings report

When you analyze a feature or do a gap audit, produce this structure so the user
can act on it directly:

```
## Feature: <name> (<device(s)>)
- App source: research/storz-bickel-app/js/<file>.js:<lines>
- Protocol family: direct-characteristic | qvap command-byte
- UUID / opcode: <uuid>  OR  cmd 0x06, byte <n> / bit <n>
- Encoding: <e.g. temp ×10 LE 2 bytes; uint16 bitfield bit 12>
- Notification/decode: <if it reports state, the byte layout>
- Library status: Implemented | Partial | Missing  (protocol.py / <device>.py / models.py)
- Proposed change: <new const, new method, new state field, doc update>
- Verification: <what to confirm on real hardware — see guardrails>
```

For a full audit, emit one block per feature plus a prioritized summary (highest
HA value + lowest risk first, the way `app-frontend-capabilities.md` orders it).

## Guardrails — why these matter

- **Never commit vendor assets.** `research/` is gitignored to keep S&B's code off
  GitHub while staying reproducible locally. Quote findings into our own docs; don't
  paste their JS into tracked files.
- **Firmware update and cloud/analysis-upload flows are out of scope.** The app does
  them via vendor web endpoints and a bootloader transport with real bricking risk.
  Document them if asked, but don't implement them as normal-operation features
  without the user explicitly scoping a separate, guarded module.
- **The app is a strong hypothesis, not proof.** The library swallows most GATT
  errors, so a wrong UUID or bit can look like it "worked." Flag anything that hasn't
  been confirmed against a real device as unverified, and prefer
  `device.diagnostics()` (serials stripped) when comparing live state to your decode.
- **Route device-type logic through the existing helpers**, and keep the
  Volcano/Crafty-direct vs Venty/Veazy-command split intact — conflating them is the
  most common way these changes break.

## Handing off to implementation

Once a finding is confirmed, implement it the normal way: add the constant/encoder to
`protocol.py`, the method to the device class, the field to the state model, update
`s&b_procol.md` + the capability matrix, and add a test (coverage gate is enforced).
If the feature should also appear in Home Assistant, the `ha-snb` repo has its own
`analyze-sb-app` skill that maps a confirmed library capability to an HA entity.
