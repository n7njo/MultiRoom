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
        led_green.toggle()
        print(pin)
        amp_pressed=False


def button_handler_blue(pin):
    global amp_pressed
    if not amp_pressed:
        amp_pressed=True
        led_blue.toggle()
        print(pin)
        amp_pressed=False

button_blue_source = machine.Pin(22, machine.Pin.IN, machine.Pin.PULL_UP)
button_grey_amp = machine.Pin(21, machine.Pin.IN, machine.Pin.PULL_UP)

amp_1_source = "Off"
amp_2_source = "Off"

# Turn off all LEDs
led_onboard.value(0)
led_blue.value(0)
led_red.value(0)
led_green.value(0)

button_blue_source.irq(trigger=machine.Pin.IRQ_RISING, handler=button_handler_blue)
button_grey_amp.irq(trigger=machine.Pin.IRQ_RISING, handler=button_handler)

while True:

    print(button_blue_source.value())
    print(button_grey_amp.value())