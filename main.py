# Feature to dos
    # Hardware
        # Power LED from PSU
        # 5v Power from PSU via Power Buck
        # Rear USB port for connecting to Pico
        # Rear holes for Speaker connections
        # Power noise filters
        # Ethernet connection for Pico? to use API?
        # Audio out from each amp to digital signal
        # Line out from master amp
        # Connect Line in from master amp
        # Attach DVD drive cover - Maybe for Antenas
        # RGB LED in VNR light - Increase size of hole
        # Fix LED light in power switch
        # IR mount
        # Network switch mount & power
        # Multiplexer for inbound LineIn, selectable to which amp

    # Software
        # Source RGB LED for currently selected amp "VNR", with PWM to colour fade
        # Read 7 buttons for Source"VNR", Eject"SwitchAmp", Play, Pause, Stop, Forward, Back
        # OLED display to show currently selected Amp
        # IR to receive commands
        # DAC output to control the voltages for the controls using all 3, one per amp.
        # Visual to see if sound playing from each amp
        # Reset amp option
        # LED to show queue temperature

    # Questions?
        # Assume the only task in the main loop would be to display, poll status, read input
        # What output can be seen from the Amp to determine sound actually being played
        # What is PIO and can I use it

    # Answers
        # Primary thread recieves the interupt for the botton press, what happens if in the middle of a UART
        # Thought is for the UART to be on 2nd thread so conversations not interupted by button presses
        # PIO is a very low level ablity to write a custom messaging protocal


### Object for Amp status
# Source for each Amp
# Volune for each Amp
# Song for each Amp
# Artist for each Amp
# Play state for each Amp
# Song position for each Amp
# Audiable output for each Amp

import utime
import machine
import _thread


### Configure Pins
# Pin numbers
Pin_LED_Green = 13          # Need to confirm if PWM capable
Pin_LED_Blue = 15           # Need to confirm if PWM capable
Pin_LED_RED = 14            # Need to confirm if PWM capable
Pin_BUT_Amp_Cycle = 21      #
Pin_BUT_Source_Cycle = 22   #
Pin_LED_Internal = 25       #

# LEDs
LED_Internal = machine.Pin(Pin_LED_Internal, machine.Pin.OUT)
LED_Green = machine.Pin(Pin_LED_Green, machine.Pin.OUT)
LED_Blue = machine.Pin(Pin_LED_Blue, machine.Pin.OUT)

# Buttons
Button_Source_Cycle = machine.Pin(Pin_BUT_Source_Cycle, machine.Pin.IN, machine.Pin.PULL_UP)
Button_Amp_Cycle = machine.Pin(Pin_BUT_Amp_Cycle, machine.Pin.IN, machine.Pin.PULL_UP)

# Limits
Limit_UART_Max_Queue_Length = 5                                                             # Queue size for waiting UART requests
Limit_UART_Multiplexer_Max_Channels = 16                                                    # How many channels does the multiplexer have
Limit_UART_Multiplexer_Max_Minutes_Looking = 10                                             # Max minutes to look for channels in available
Limit_LineIn_Multiplexer_Max_Channels = 16                                                  # Max chanels on the multiplexter for LineIn
Limit_LineOut_Multiplexer_Max_Channels = 0                                                  # Max chanels on the multiplexter for LineOut

# Flags
Flag_UART_Queuing_Enabled = True                                                            # Can the UART queue messages

# Dictonary

# Lists

# Common Functions
def tickNow():
    return utime.ticks_us()

def secondsBetweenTick(firstTimestamp,secondTimestamp):
    return utime.ticks_diff(firstTimestamp,secondTimestamp)

def secondsSinceTick(timestamp):
    #return round(secondsBetweenTick(tickNow(),timestamp)/1000000,4)
    return secondsBetweenTick(tickNow(),timestamp)/1000000

# Structure for MultiAmp
class MultiAmp:
    "Master class conatining all the amps"

    def __init__(self):
        self.Amplifiers = {}                                                                             # Amp Connected
        self.Dict_LED_2_Source = {"Green":"Wifi","Blue":"Bluetooth","Red":"Line In","White":"Optical"}  # LED Source Mapping
        self.List_Sources_Enabled = ["Wifi","Bluetooth","Line In"]                                      # Sources enabled
        self.AmpSelected = 0                                                                            # Which Amp is currently primary
        ### Variable of available Amps - To Be DELETED once Naming is Dynamic
        self.AmpsInstalled = ["Oasis","Pool","Italian"]                                     

    def ampDiscovery(self,cycleAttempts,waitForResponse):
        "Cycle through the multiplexer a specified number of times waiting for a responce"
        # What happens if the amp has changed it's name

        # Loop from begnning to max sending a status message to each channel
        for cycles in range(cycleAttempts):
            # Loop through all the channels on the multiplexer
            for channel in range(Limit_UART_Multiplexer_Max_Channels):
                ## Only needed because pulling from predefined list
                if len(self.AmpsInstalled) > channel:
                    AmpName = self.AmpsInstalled[channel]
                    #print(str(channel) + ":"+ AmpName)

                    if self.Amplifiers.get(channel):
                        print("Skipping: ", end='')
                        print(self.Amplifiers[channel].Name)
                    else:
                        print("Creating Amp: ", end='')
                        NewAmp = Amp()
                        self.Amplifiers[channel] = NewAmp 
                        self.Amplifiers[channel].Name = AmpName
                        self.Amplifiers[channel].AvailableSources = self.List_Sources_Enabled
                        print(self.Amplifiers[channel].Name)

                # No hardcoded Amp name found - REMOVE once dynamic
                #else:
                    #print(channel, end='')

            # Validate if the name matches that in the multiplexer list
                # If the name is different, update the name

    def setAmpSelected(self,channel):
        "Change selected amp"
        self.AmpSelected = channel

    def getAmpSelected(self):
        "Return current selected amp"
        return self.AmpSelected

    def refreshAmpStatus(self,channel):
        "Gather status information on specific amplifier"

    def refreshAllAmpStatus(self,_uart):
        "Update all amplifier statuses"
        for channel in list(self.Amplifiers.keys()):
            #print ("Refresh status: " + self.Amplifiers[channel].Name, end='')
            responseTimestamp = _uart.requestCommand(channel, "STA","Low")

            #print(responseTimestamp)
        

# Amp status object
class Amp:
    "All the current status details about the Amp"

    def __init__(self) -> None:
        self.Name = "default"
        self.SelectedSource = "LineIn"
        self.Volume = 1
        self.PlayState = "Stop"
        self.Audiable = "No"
        self.OutputValue = 1                                # Validation there is output?
        self.Track = ""
        self.Artist = ""
        self.Album = ""
        self.TrackPosition = 0
        self.AvailableSources = []
        self.MaxVolume = 10

    def getSystemState(self):
        "Confirm status of amp"
        # STA: {source,mute,volume,treble,bass,net,internet,playing,led,upgrading};
        # Returns 
        print("STA")
    
    def sendSystemControl(self):
        "Send system command to the Amp"
        # SYS: {REBOOT/STANDBY};
        print("SYS")

    def getInternetState(self):
        "Confirm if connected to the internet"
        # WWW;
        # Returns {0,1}
        print("WWW")

    def getAudioOutputState(self):
        "Confirm current audio output state"
        # AUD;
        # Returns {0,1}
        print("AUD")

    def setAudioOutputState(self):
        "Set audio output state"
        # AUD: {0,1};
        print("AUD")

    def getInputSource(self):
        "Confirm current input source"
        # SRC;
        # Returns {NET/USB/USBDAC/LINE-IN/LINE-IN2/BT/OPT/COAX/I2S/HDMI}
        print("SRC")

    def setInputSource(self):
        "Set current input source"
        # SRC: {NET/USB/USBDAC/LINE-IN/LINE-IN2/BT/OPT/COAX/I2S/HDMI};
        print("SRC")

    def getVolume(self):
        "Confirm current volume"
        # VOL;
        # Returns {0..100}
        print("VOL")
   
    def setVolume(self):
        "Confirm current volume"
        # VOL: {0..100};
        print("VOL")

    def getMute(self):
        "Confirm current mute status"
        # MUT;
        # Returns {0,1}
        print("MUT")
   
    def setMute(self):
        "Set mute status"
        # MUT: {0/1/T};
        print("MUT")    

    def getBass(self):
        "Confirm current Bass level"
        # BAS;
        # Returns {-10..10}
        print("BAS")
   
    def setBass(self):
        "Set Bass level"
        # BAS: {-10..10};
        print("BAS")  

    def getTrebble(self):
        "Confirm current Treble level"
        # TRE;
        # Returns {-10..10}
        print("TRE")
   
    def setTreble(self):
        "Set Treble level"
        # TRE: {-10..10};
        print("TRE")      
   
    def PlayPause(self):
        "Toggle Play Pause"
        # POP;
        print("POP")

    def Stop(self):
        "Stop playing"
        # STP;
        print("STP")
            
    def Next(self):
        "Skip to next track"
        # NXT;
        print("NXT")

    def Previous(self):
        "Jump to previous track"
        # PRE;
        print("PRE")

    def getBluetoothStatus(self):
        "Confirm current bluetooth connection status"
        # BTC;
        # Returns {0,1}
        print("BTC")
    
    def getPlaybackStatus(self):
        "Confirm current wifi playback status"
        # PLA;
        # Returns {0,1}
        print("PLA")
    
    def getChannelStatus(self):
        "Confirm current channel status"
        # CHN;
        # Returns {0,1}
        print("CHN")

    def getMultiRoomStatus(self):
        "Confirm current multiroom status"
        # MRM;
        # Returns {S,M,N}
        # Slave / Master / None
        print("MRM")

    def getLED(self):
        "Confirm current LED status"
        # LED;
        # Returns {0,1}
        print("LED")
   
    def setLED(self):
        "Set LED status"
        # LED: {0/1/T};
        print("LED")    

    def getBeepSound(self):
        "Confirm current BEP status"
        # BEP;
        # Returns {0,1}
        print("BEP")
   
    def setBeepSound(self):
        "Set BEP status"
        # BEP: {0/1};
        print("BEP") 

    def getPreset(self):
        "Confirm current PST status"
        # PST;
        # Returns {0..10}
        print("PST")
   
    def setPreset(self):
        "Set PST status"
        # PST: {0..10};
        print("PST") 

    def getVirtualBass(self):
        "Confirm current Virtual Bass status"
        # VBS;
        # Returns {0,1}
        print("VBS")
   
    def setVirtualBass(self):
        "Set VBS status"
        # VBS: {0/1/T};
        print("VBS")

    def sendWifiReset(self):
        "Send wifi reset to the Amp"
        # WRS;
        print("WRS")

    def getLoopMode(self):
        "Confirm current Loop mode status"
        # LPM;
        # Returns {REPEATALL/REPEATONE/REPEATSHUFFLE/SHUFFLE/SEQUENCE}
        print("LPM")

    def setLoopMode(self):
        "Set current input source"
        # LPM: {REPEATALL/REPEATONE/REPEATSHUFFLE/SHUFFLE/SEQUENCE};
        print("LPM")

    def getName(self):
        "Confirm current Name status"
        # NAM;
        # Returns {Name}
        # hexed string with UTF8 encoding
        print("NAM")
   
    def setName(self):
        "Set Name"
        # NAM: {Name};
        # hexed string with UTF8 encoding
        print("NAM")

    def getEthernet(self):
        "Confirm current Ethernet status"
        # ETH;
        # Returns {0,1}
        print("ETH")

    def getWifi(self):
        "Confirm current Wifi status"
        # WIF;
        # Returns {0,1}
        print("WIF")

    def getVoicePrompt(self):
        "Confirm current Voice prompt status"
        # PMT;
        # Returns {0,1}
        print("NAM")
   
    def setVoicePrompt(self):
        "Set voice prompt status"
        # PMT: {0,1};
        print("PMT")

    def getPreGain(self):
        "Confirm current PreGain status"
        # PRG;
        # Returns {0,1}
        print("PRG")
   
    def setPreGain(self):
        "Set PreGain status"
        # PRG: {0,1};
        print("PRG")

    def getSystemDelayTime(self):
        "Confirm current delay time until system output control"
        # DLY;
        # Returns {1..60}
        # Mute delay
        print("DLY")
   
    def setSystemDelayTime(self):
        "Set system delay time until system output control"
        # DLY: {1..60};
        # Mute delay
        print("DLY")

    def getMaxVolume(self):
        "Confirm current max volume"
        # MXV;
        # Returns {30..100}
        print("VOL")
   
    def setMaxVolume(self):
        "Confirm current volume"
        # MXV: {30..100};
        # remains after factory reset
        print("MXV")

    def getAutoSwitch(self):
        "Confirm current auto switch status"
        # ASW;
        # Returns {0,1}
        print("ASW")
   
    def setAutoSwitch(self):
        "Set voice prompt status"
        # ASW: {0,1};
        # Reverts to previous source after playback stopped
        print("ASW")
   
    def setPowerOnSource(self):
        "Set default source after power on"
        # POM: {NET/USB/USBDAC/LINE-IN/LINE-IN2/BT/OPT/COAX/I2S/HDMI};
        # Reverts to previous source after playback stopped
        # Set NONE for last used
        print("POM")

    def sendZoneMessage(self):
        "Send message to different zone"
        # ZON:[zone]:[msg];
        print("ZON")

# Button status
class Button:
    "Status of the buttons"

    def __init__(self) -> None:
        self.PlayPause = False
        self.Stop = False
        self.Forward = False
        self.Reverse = False
        self.Eject = False
        self.Source = False

    def pressedPlayPause(self):
        "Interupt received for Play Pause"
        print("PlayPause")

    def pressedStop(self):
        "Interupt received for Play Pause"
        print("PlayPause")

    def pressedForward(self):
        "Interupt received for Play Pause"
        print("PlayPause")
        
    def pressedReverse(self):
        "Interupt received for Play Pause"
        print("PlayPause")
        
    def pressedEject(self):
        "Interupt received for Play Pause"
        print("PlayPause")
        
    def pressedSource(self):
        "Interupt received for Play Pause"
        print("PlayPause")

# LED control
class LED:
    "Control of LEDs, currently only Source"

    def __init__(self) -> None:
        self.CurrentColour = "Off"
        self.NextColour = ""

    def matchSourcetoColour(self):
        "If needed match the LED colour to the source colour"

# OLED Display
class Display:
    "Control of Display"



# Control a Multiplexer
class Multiplexer:
    "Generic multiplexer controls"

    def __init__(self, Max, Live) -> None:
        self.MaxChannels = Max                                                      # Max number of multiplexer channels
        self.LiveChannel = Live                                                     # Current channel live
        self.ListofChannelNames = []                                                # List of channels available 

    def setChannelName(self,channelNumber,channelName):
        "Add new channel to list"
        self.ListofChannelNames[channelNumber] = channelName

    def getChannelName(self,channelNumber):
        "Get channel selected"
        return self.ListofChannelNames[channelNumber]

    def setLiveChannel(self,channelNumber):
        "Select channel destination"
        #print("Selecting channel: " + str(channelNumber))
        self.LiveChannel = channelNumber

    def getChannelList(self):
        "List current channels available"
        return self.ListofChannelNames

    def getAvailbleChannelCount(self):
        "How many channels are now available"
        return len(self.ListofChannelNames)

    # def getIsChannelConfigured(self,channelNumber):
    #     "Is the channel number requested actually configured"
    #     if self.ListofChannelNames[channelNumber] != '':
    #         return True
    #     else:
    #         return False

# Control of the UART Multiplexer
class UART_Multiplexer(Multiplexer):
    "Control of the multiplexer"

    def __init__(self):
        super.__init__(Limit_UART_Multiplexer_Max_Channels,1)                       # Inherit everything from Multiplexer
        self.idle = False

# Control of the Line In Multiplexer
class LineIn_Multiplexer(Multiplexer):
    "Control of the Line In Multiplexer"

    def __init__(self):
        super.__init__(Limit_LineIn_Multiplexer_Max_Channels,1)                     # Inherit everything from Multiplexer

# Control of the Line Out Multiplexer - Future feature
class LineOut_Multiplexer(Multiplexer):
    "Control of the Line Out Muliplexer - ON HOLD not confirmed"

    def __init__(self):
        super.__init__(Limit_LineOut_Multiplexer_Max_Channels,1)                     # Inherit everything from Multiplexer

# Control of the UART communication
class UART_Communication(UART_Multiplexer):

    def __init__(self) -> None:
        super().__init__                                                            # Import the UART multiplexer         
        self.QueuingEnabled = Flag_UART_Queuing_Enabled                             # Toggle to disable queuing
        self.QueueLength = 0                                                        # Current number of requests in the queue            
        self.MaxQueueLength = Limit_UART_Max_Queue_Length                           # Max number of queued UAT requests
        self.Idle = True                                                            # Currently in use and communitaing
        self.MaxQueueWaitSeconds = 5                                               # Longest a request can wait on the quque
        self.MaxBusyQueueWaitSeconds = 3                                           # Longest a request can wait on a busy queue
        self.MaxWaitResponse = 3                                                    # How long to wait for a UART response
        self.QueuedRequests = {}                                                    # -- Not sure how this will be implemented yet
        self.ResponseBuffer = {}                                                    # Responses populated in this buffer
        self.LastProcessedRequest = 0                                               # Timestamp of last processed request




    # UART Threaded worker
    def sendNextCommandFromQueue(self):
        "SECOND THREAD: Check message request queue and send"
        lastProcessed = tickNow()

        while True:

            ##if secondsSinceTick(lastProcessed) > 1:
            #lastProcessed = tickNow()
            # If queue not empty, check if multiplexer idle
            if len(self.QueuedRequests) > 0 and self.Idle == True:
                # Lock mutliplexer idle
                self.Idle = False
                # Select oldest waiting request
                request = tickNow()
                found = False
                # Find the oldest high priority request
                for lowest in (self.QueuedRequests.keys()):
                    if self.QueuedRequests[lowest][2] == False and self.QueuedRequests[lowest][3] == "High":
                        print("*", end='')
                        if lowest < request:
                            request = lowest
                            found = True

                # If no high priority requests, find the oldest low priorty request
                if not found:
                    for lowest in (self.QueuedRequests.keys()):
                        if self.QueuedRequests[lowest][2] == False and self.QueuedRequests[lowest][3] == "Low":
                            if lowest < request:
                                request = lowest
                                found = True

                if found and request in self.QueuedRequests:
                    ### Process Request ###
                    # Select Multiplexer
                    self.setLiveChannel(self.QueuedRequests[request][0])
                    # Send message
                    self.ResponseBuffer[request]=self.transmitRequest(self.QueuedRequests[request][1])
                    # Push response into buffer
                    baton.acquire()
                    self.QueuedRequests[request][2] = True
                    baton.release()
                    print(".", end='')
                # Unlock multiplexer idle
                self.Idle = True
    
    def transmitRequest(self,message):
        return "ALIVE"+message

    def removeFromQueue(self,request):
        baton.acquire() 
        del self.ResponseBuffer[request]
        del self.QueuedRequests[request]
        baton.release()

    def pushToQueue(self,channel,message,priority):
        addedToQueueTicks = tickNow()

        # Lock Variable
        baton.acquire()
        # Add request to the queue - True/False flag indicates response complete
        self.QueuedRequests[addedToQueueTicks] = [channel,message,False,priority]
        # Add placeholder for response
        self.ResponseBuffer[addedToQueueTicks] = [""]
        baton.release()
        return addedToQueueTicks

    def requestCommand(self,channel,message,priority):
        "Requests an API message to the UART on a particular channel"
        ##print(" -> UART Request: '" + message + "' from " + str(channel))

        # Check to see if the channel is actaully configured
        if MA.Amplifiers.get(channel):
            # If the queue length at it's max, run prune queue and check length again
            if len(self.QueuedRequests) < self.MaxQueueLength:
                # Returns the unique timestamp used as a key
                return (self.pushToQueue(channel,message,priority))
            else:
                    #print("Queue full")
                    return False
        else:
            print("Bad Channel")
            return False
            
            

    def pruneQueue(self):
        "Look for requests which are old and prune from queue"
        # Loop through each queue position to look for queue item are older than max queue wait time
        for request in list(self.QueuedRequests.keys()):
            # Message older than max time and likely stale
            if int(secondsSinceTick(request)) > self.MaxQueueWaitSeconds:
                print("-", end='')
                self.removeFromQueue(request)
            # Queue busy and message older than reasonable
            if (int(secondsSinceTick(request))) > self.MaxBusyQueueWaitSeconds and len(self.QueuedRequests) > self.MaxQueueLength:
                print("+", end='')
                self.removeFromQueue(request)

    def printQueue(self):
        "Return current queue"
        for request in self.QueuedRequests:
            print(str(request) + ":|" + self.QueuedRequests[request][1] + "," + str(self.QueuedRequests[request][2]) + "," + self.QueuedRequests[request][3] + "|  ", end='')
        print()

    def getQueue(self):
        return list(self.QueuedRequests.items())

    def parseResponses(self):
        "Worker processing responses"
        # Look through the queue for any completes
        for request in list(self.QueuedRequests.keys()):
            # Look through the queue for processed high priority responses
            if self.QueuedRequests[request][2] == True and self.QueuedRequests[request][3] == "High":
                # Interpret the request to determine the action needed
                # Push the data

                # Remove the queue
                self.removeFromQueue(request)

        # Look through the queue for processed low priority responses
        for request in list(self.QueuedRequests.keys()):
            if self.QueuedRequests[request][2] == True and self.QueuedRequests[request][3] == "Low":

                # Interpret the request to determine the action needed
                # Push the data

                # Remove the queue
                self.removeFromQueue(request)

            # Call the function required with the variables



### Function to detect button press
# Interupt if any button depressed (VNR,Eject,Stop,Play/Pause/Forward/Rewind)
# def Button_Handler(pin):
#     print(pin)

#     if pin == Pin_Source_Cycle:
#         print("Source")
#     elif pin == Pin_Amp_Cycle:
#         print("Amp")
#     else:
#         print("?")


### Configure button interupts

# print("Configuring button interupts...", end= '')
# Button_Source_Cycle.irq(trigger=machine.Pin.IRQ_RISING, handler=Button_Handler)
# print("source", end = '')
# Button_Amp_Cycle.irq(trigger=machine.Pin.IRQ_RISING, handler=Button_Handler)
# print(",amp", end = '')
# print(" done")
# print()

### Function to detect IR request


### Function to push Amp status to the display buffer
# Use framebuf micropython

### Function to read if there's input from the output of each amp

### Function to set LineIn destination Amp


###### Begin Main ######

print("STARTING")

# Initiate Primary Object
MA = MultiAmp()

# Initiate UART
UART = UART_Communication()

# Find Amps and create the objects
MA.ampDiscovery(1,1)

###### Spawning Second Thread ######

print("SPAWN")
_thread.start_new_thread(UART.sendNextCommandFromQueue, ())
baton = _thread.allocate_lock()
utime.sleep(0.5)

MA.refreshAllAmpStatus(UART)

UART.requestCommand(1, "PLA","High")
UART.requestCommand(1, "OLD","Pause")

lastPrune = tickNow()
lastParse = tickNow()
lastAutoGenerate = tickNow()
lastQueuePrint = tickNow()

while True:

    if secondsSinceTick(lastParse) > 0.5:
        lastParse = tickNow()
        UART.parseResponses()

    if secondsSinceTick(lastPrune) > 10:  
        lastPrune = tickNow()
        UART.pruneQueue()

    if secondsSinceTick(lastQueuePrint) > 1:
        lastQueuePrint = tickNow()
        UART.printQueue()
        #print(len(UART.getQueue()))

    if secondsSinceTick(lastAutoGenerate) > 2:
        lastAutoGenerate = tickNow()  
        #MA.refreshAllAmpStatus(UART) 
        queueRequest = UART.requestCommand(1, "OLD","HIGH")
        if queueRequest == False:
            print("!", end='')
        else:
            print("^", end='')




