### Second Thread Function ###

def UART_Communication ():
    print("...")
    while True:
        LED_Internal.toggle()
        utime.sleep(1)


###### Begin Main ######


### Creating an array of Amp objects
print("Creating Amp objects...", end = '')
AmpStates = [Amp() for AmpNumber in range(len(AmpsInstalled))]

for AmpNumber in range(len(AmpsInstalled)):
    AmpStates[AmpNumber].Name = AmpsInstalled[AmpNumber]

print("done")
print()

###### Spawning Second Thread ######

print("Spawning UART thread", end= '')
_thread.start_new_thread(UART_Communication, ())
print(" done")
print()

### Configure button interupts

print("Configuring button interupts...", end= '')
Button_Source_Cycle.irq(trigger=machine.Pin.IRQ_RISING, handler=Button_Handler)
print("source", end = '')
Button_Amp_Cycle.irq(trigger=machine.Pin.IRQ_RISING, handler=Button_Handler)
print(",amp", end = '')
print(" done")
print()

###### Begin Main Thread ######

while True:
    for AmpNumber in range(len(AmpsInstalled)):
        print(AmpStates[AmpNumber].Name)
        utime.sleep(1)
        print()
