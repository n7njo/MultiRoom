from machine import UART, Pin


Pico_DISPLAY_UART = 0       # Which Pico coms channel will be used
Pin_DISPLAY_UART_TX = 0
Pin_DISPLAY_UART_RX = 1

displayuart = UART(Pico_DISPLAY_UART, baudrate=115200, bits=8, parity=None, stop=1, tx=Pin(Pin_DISPLAY_UART_TX), rx=Pin(Pin_DISPLAY_UART_RX))

displayuart.write(b'VER\n\r')

rxData = bytes()
while True:

    if displayuart.any() > 0:
        rxData = displayuart.read()

        print(rxData)