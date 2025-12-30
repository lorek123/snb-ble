Usage
=====

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
   from storzandbickel_ble.models import HeaterMode

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

