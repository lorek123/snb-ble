Examples
========

Complete Example: Volcano Control
----------------------------------

.. code-block:: python

   import asyncio
   import logging
   from storzandbickel_ble import StorzBickelClient

   logging.basicConfig(level=logging.INFO)

   async def main():
       client = StorzBickelClient()

       # Scan for devices
       print("Scanning for devices...")
       devices = await client.scan(timeout=10.0)

       if not devices:
           print("No devices found")
           return

       # Connect to first device
       device = await client.connect_device(devices[0])
       print(f"Connected to {device.name}")

       try:
           # Set target temperature
           await device.set_target_temperature(185.0)
           print("Set target temperature to 185°C")

           # Turn heater on
           await device.turn_heater_on()
           print("Heater turned on")

           # Monitor temperature for 60 seconds
           for _ in range(60):
               await asyncio.sleep(1)
               state = device.state
               print(
                   f"Current: {state.current_temperature:.1f}°C, "
                   f"Target: {state.target_temperature:.1f}°C"
               )

           # Turn heater off
           await device.turn_heater_off()
           print("Heater turned off")

       finally:
           await device.disconnect()
           print("Disconnected")

   if __name__ == "__main__":
       asyncio.run(main())

Complete Example: Venty with Boost
----------------------------------

.. code-block:: python

   import asyncio
   from storzandbickel_ble import StorzBickelClient
   from storzandbickel_ble.models import HeaterMode

   async def main():
       client = StorzBickelClient()
       device = await client.connect_by_name("VENTY")

       try:
           # Set target temperature
           await device.set_target_temperature(190.0)

           # Set boost offset
           await device.set_boost_offset(15)

           # Enable boost mode
           await device.set_heater_mode(HeaterMode.BOOST)

           # Monitor state
           state = device.state
           print(f"Temperature: {state.current_temperature}°C")
           print(f"Battery: {state.battery_level}%")
           print(f"Heater mode: {state.heater_mode.name}")

       finally:
           await device.disconnect()

   asyncio.run(main())

