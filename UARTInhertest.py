
import utime
import machine
from machine import UART

class UART_Com():
    #def __init__(self, id: int, baudrate: int, bits: int, parity: int, stop: int, tx: Pin, rx: Pin):
    def __init__(self):
        #super().__init__(id, baudrate=baudrate, bits=bits, parity=parity, stop=stop, tx=tx, rx=rx)
        #super().__init__(id, baudrate, bits, parity, stop)
    #uart = machine.UART(0)
        self.uart=machine.UART(1)

    def send(self,message: bytes):
        self.uart.write(message)

#indicate program started visually
led_onboard = machine.Pin(25, machine.Pin.OUT)
led_onboard.value(0)     # onboard LED OFF for 0.5 sec
utime.sleep(0.5)
led_onboard.value(1)

#print uart info
#uart = machine.UART(1)
#print(uart)

uartcom = UART_Com()
#uart.write('h')
uartcom.send('hello')
utime.sleep(0.1)

# while uart.any():
#     print(uart.read(1))

print()
print("- bye -")