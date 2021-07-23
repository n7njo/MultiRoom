import utime
import machine

amp_pressed = False

led_blue = machine.Pin(15, machine.Pin.OUT)
led_red = machine.Pin(14, machine.Pin.OUT)
led_green = machine.Pin(13, machine.Pin.OUT)
led_onboard = machine.Pin(25, machine.Pin.OUT)


def button_handler(pin):
    global amp_pressed
    if not amp_pressed:
        amp_pressed=True
        print(pin)

button_blue_source = machine.Pin(22, machine.Pin.IN, machine.Pin.PULL_UP)
button_grey_amp = machine.Pin(21, machine.Pin.IN, machine.Pin.PULL_UP)

amp_1_source = "Off"
amp_2_source = "Off"

# Turn off all LEDs
led_onboard.value(0)
led_blue.value(0)
led_red.value(0)
led_green.value(0)

button_grey_amp.irq(trigger=machine.Pin.IRQ_RISING, handler=button_handler)

while True:
    led_onboard.toggle()
    print("Onboard")
    utime.sleep(0.1)
    led_green.toggle()
    print("Green")
    utime.sleep(0.1)
    led_red.toggle()
    print("Red")
    utime.sleep(0.1)
    print("Blue")
    led_blue.toggle()
    utime.sleep(1)
    print(button_blue_source.value())
    print(button_grey_amp.value())