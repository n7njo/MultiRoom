import machine
import utime
import _thread
import random

internal_led = machine.Pin(25, machine.Pin.OUT)

class UART_Conversation:
    "Conversation with devices over UART"

    def __init__(self) -> None:
        self.DestinationAmp = 0
        self.OutboundRequest = ""
        self.InboundResponse = ""
        self.TimeOfRequest = 0
        self.TimeOfResponse = 0

FrontOfQueue = 0
QueueLength = 0
MaxQueueLength = 5

# We create a semaphore (A.K.A lock)
baton = _thread.allocate_lock()
# Function that will block the thread with a while loop

def UART_Communication():
    global FrontOfQueue, QueueLength, MaxQueueLength
    while True:

        if baton.locked == True and QueueLength < MaxQueueLength:
            print ("-UNLOCKED-")
            baton.release()
        if baton.locked == False and QueueLength == MaxQueueLength-1:
            baton.acquire()
            print ("+LOCKED+")

        if QueueLength > 0:
            print ("Worker")
            if baton.locked == False:
                baton.acquire()
                print ("+LOCKED+")
            taskdivide = random.randrange(1,10,1)
            taskduration = 1 / taskdivide
            #print(taskduration)
            utime.sleep(taskduration)
            QueueLength = QueueLength - 1
            if baton.locked == True and QueueLength < MaxQueueLength:
                print ("-UNLOCKED-")
                baton.release()


        
# Function that initializes execution in the second core
# The second argument is a list or dictionary with the arguments
# that will be passed to the function.

_thread.start_new_thread(UART_Communication, ())
# Second loop that will block the main thread, and what it will do
# that the internal led blinks every half second

while True:
    status = baton.acquire(1,0)
    if QueueLength < 5:
        print ("Primary: " + str(QueueLength))
        QueueLength = QueueLength + 1
        utime.sleep(0.1)
        print ("Added> " + str(QueueLength))
    baton.release()
    if status == False:
        print("------ TIMEOUT")
    else:
        internal_led.toggle()