# govee-h6002
Simple automation for a Govee H6002 bulb

I could not find any programs for automating the Govee H6002 bulb over Bluetooth Low Energy. I did not want to use a 3rd party library that could not be installed via apt-get on Rasberry PI OS. Since this is just a white dimmable bulb, no color support needed.
Hopefully this is helpful to others.

References I used:

https://github.com/Obi2000/Govee-H6199-Reverse-Engineering
https://github.com/philhzss/Govee-H6127-Reverse-Engineering
https://github.com/ddxtanx/GoveeAPI/blob/master/controller.py
https://github.com/chvolkmann/govee_btled/blob/master/govee_btled/bluetooth_led.py
https://github.com/oscaracena/pygattlib
https://github.com/peplin/pygatt/blob/master/pygatt/backends/gatttool/gatttool.py
https://github.com/mqttblebulb/mqttblebulb/blob/main/mqttblebulb.py

# char-write-cmd 0x0011 3301000000000000000000000000000000000032 # off
# char-write-cmd 0x0011 3301010000000000000000000000000000000033 # on
