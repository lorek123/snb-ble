Usage
=====

Home Assistant Quickstart
-------------------------

Recommended integration pattern:

1. Connect once and keep notifications enabled.
2. Treat notifications as the primary state stream.
3. Call ``update_state()`` for startup reconciliation and recovery.
4. Use explicit exceptions (for example ``CommandTimeoutError``) for clean service-action error handling.
5. Use ``availability_transition_count`` to emit one-shot down/up availability logs.

Basic Usage
-----------

Device Discovery
~~~~~~~~~~~~~~~~

.. code-block:: python

   import asyncio
   from storzandbickel_ble import StorzBickelClient

   async def main():
       client = StorzBickelClient()
       devices = await client.scan(timeout=10.0)
       for device in devices:
           print(f"Found: {device.name} ({device.address})")

   asyncio.run(main())

Connecting to a Device
~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   # Connect by address
   device = await client.connect_by_address("AA:BB:CC:DD:EE:FF")

   # Connect by name
   device = await client.connect_by_name("S&B VOLCANO")

   # Connect using device info
   device_info = await client.find_device(address="AA:BB:CC:DD:EE:FF")
   device = await client.connect_device(device_info)

Volcano Hybrid
--------------

.. code-block:: python

   from storzandbickel_ble import StorzBickelClient

   async def control_volcano():
       client = StorzBickelClient()
       device = await client.connect_by_name("S&B VOLCANO")

       # Set target temperature
       await device.set_target_temperature(185.0)

       # Turn heater on
       await device.turn_heater_on()

       # Control air pump
       await device.turn_pump_on()
       await device.turn_pump_off()

       # Set LED brightness (1-9)
       await device.set_led_brightness(5)

       # Set auto-off time (seconds)
       await device.set_auto_off_time(300)

       # Read state
       print(f"Temperature: {device.state.current_temperature}°C")
       print(f"Heater: {'On' if device.state.heater_on else 'Off'}")

       await device.disconnect()

Venty
-----

.. code-block:: python

   from storzandbickel_ble import StorzBickelClient
   from storzandbickel_ble.models import HeaterMode, TemperatureUnit

   async def control_venty():
       client = StorzBickelClient()
       device = await client.connect_by_name("VENTY")

       # Set target temperature
       await device.set_target_temperature(185.0)

       # Set heater mode
       await device.set_heater_mode(HeaterMode.BOOST)

       # Set boost offset
       await device.set_boost_offset(10)

       # Set temperature unit
       await device.set_temperature_unit(TemperatureUnit.FAHRENHEIT)

       # Qvap settings (also used by Veazy)
       await device.set_brightness(7)
       await device.set_vibration(True)
       await device.set_boost_timeout_disabled(False)

       # Read state
       print(f"Temperature: {device.state.current_temperature}°C")
       print(f"Battery: {device.state.battery_level}%")

       await device.disconnect()

Crafty/Crafty+
--------------

.. code-block:: python

   from storzandbickel_ble import StorzBickelClient

   async def control_crafty():
       client = StorzBickelClient()
       device = await client.connect_by_name("CRAFTY")

       # Set target temperature
       await device.set_target_temperature(185.0)

       # Set boost temperature offset (1-99°C)
       await device.set_boost_temperature(15)

       # Turn heater on
       await device.turn_heater_on()

       # Set LED brightness (0-100)
       await device.set_led_brightness(50)

       # Enable/disable vibration
       await device.set_vibration(True)

       # Find device (vibration/LED alert)
       await device.find_device()

       # Read state
       print(f"Temperature: {device.state.current_temperature}°C")
       print(f"Battery: {device.state.battery_level}%")
       print(f"Charging: {device.state.charging}")

       await device.disconnect()

Veazy
-----

.. code-block:: python

   from storzandbickel_ble import StorzBickelClient
   from storzandbickel_ble.models import DeviceType

   async def control_veazy():
       client = StorzBickelClient()

       # Veazy uses the same qvap protocol path as Venty
       devices = await client.scan(timeout=10.0, device_type=DeviceType.VEAZY)
       if not devices:
           return

       device = await client.connect_device(devices[0])
       await device.set_target_temperature(185.0)
       await device.set_brightness(8)
       await device.set_vibration(True)
       await device.disconnect()

Workflow Presets (Volcano)
--------------------------

.. code-block:: python

   from storzandbickel_ble import StorzBickelClient

   async def volcano_workflow():
       client = StorzBickelClient()
       device = await client.connect_by_name("S&B VOLCANO")

       # Presets: balloon, flow1, flow2, flow3
       await device.run_workflow_preset("flow1")

       await device.disconnect()

Local Device Analysis
---------------------

.. code-block:: python

   from storzandbickel_ble import StorzBickelClient

   async def analyze_device():
       client = StorzBickelClient()
       device = await client.connect_by_name("VENTY")

       report = await device.run_analysis()
       print("OK:", report["ok"])
       print("Warnings:", report["warnings"])
       print("Errors:", report["errors"])

       await device.disconnect()

Notifications
-------------

The library automatically enables notifications for real-time updates. State is updated automatically when notifications are received.

Error Handling
--------------

.. code-block:: python

   from storzandbickel_ble import StorzBickelClient
   from storzandbickel_ble.exceptions import (
       ConnectionError,
       DeviceNotFoundError,
   )

   try:
       client = StorzBickelClient()
       device = await client.connect_by_address("AA:BB:CC:DD:EE:FF")
   except DeviceNotFoundError:
       print("Device not found")
   except ConnectionError:
       print("Failed to connect")

Data Update Behavior
--------------------

- Notification updates are enabled automatically after ``connect()``.
- ``update_state()`` can be used for on-demand reconciliation reads.
- For Home Assistant integrations, use notifications as the primary state path and reserve ``update_state()`` for recovery or startup sync.

Diagnostics Snapshot
--------------------

Each device exposes a sanitized diagnostics payload suitable for troubleshooting:

.. code-block:: python

   snapshot = device.get_diagnostics_snapshot()
   print(snapshot["device_type"], snapshot["connected"])

Serial numbers are intentionally removed from the snapshot ``state`` payload.

Concurrency Contract
--------------------

- Device-level BLE I/O is serialized internally, so overlapping reads/writes are not sent concurrently.
- For qvap command flows that expect responses, timeout conditions raise ``CommandTimeoutError``.
- ``availability_transition_count`` tracks connect/disconnect transitions and can help integrations implement "log once on down/up change" behavior.

Known Limitations
-----------------

- Firmware update and vendor cloud workflows are out of scope.
- Some advanced vendor frontend maintenance flows are not yet exposed as first-class library APIs.
- BLE reliability can vary between operating systems, adapters, and host stack implementations.

Troubleshooting
---------------

- Verify BLE hardware is present and enabled.
- Retry discovery with a longer timeout when devices are not advertising.
- If commands time out, reduce burst rate and retry with a larger timeout budget.
- Reconnect devices when state appears stale.

