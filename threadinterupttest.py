import machine
import utime
import _thread
import random

internal_led = machine.Pin(25, machine.Pin.OUT)
green_led = machine.Pin(13, machine.Pin.OUT)
blue_led = machine.Pin(15, machine.Pin.OUT)
Blue_Button = machine.Pin(22, machine.Pin.IN, machine.Pin.PULL_UP)


baton = _thread.allocate_lock()

def Button_Handler(pin):
    baton.acquire()
    print("Green")
    green_led.toggle()
    utime.sleep(2.2)
    baton.release()


def Button_Watcher():
    while True:
        blue_led.toggle()
        print("Blue")
        utime.sleep(0.5)

Blue_Button.irq(trigger=machine.Pin.IRQ_RISING, handler=Button_Handler)

_thread.start_new_thread(Button_Watcher, ())

while True:
    internal_led.toggle()
    print("Internal")
    utime.sleep(0.5)