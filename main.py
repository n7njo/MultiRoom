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

    # Questions?
        # Can an interupt trigger a new thread
        # Can somekind of object be used for the Amp status
        # How many threads can be used, does it need to be controlled
        # Are global variables across threads
        # Shoud we have a thread for each type of request
        # Assume the only task in the main loop would be to display, poll status, read input
        # What output can be seen from the Amp to determine sound actually being played
        # What is PIO and can I use it

    # Answers
        # Primary thread recieves the interupt for the botton press, what happens if in the middle of a UART
        # Thought is for the UART to be on 2nd thread so conversations not interupted by button presses


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
Limit_UART_Max_Queue_Length = 5                     # Queue size for waiting UART requests
Limit_UART_Multiplexer_Max_Channels = 16            # How many channels does the multiplexer have
Limit_UART_Multiplexer_Max_Minutes_Looking = 16     # Max minutes to look for channels in available
Limit_LineIn_Multiplexer_Max_Channels = 16          # Max chanels on the multiplexter for LineIn
Limit_LineOut_Multiplexer_Max_Channels = 0          # Max chanels on the multiplexter for LineOut

# Flags
Flag_UART_Queuing_Enabled = True            # Can the UART queue messages

# Mappings
Map_LED_2_Source = {"Green":"Wifi","Blue":"Bluetooth","Red":"Line In","White":"Optical"}

# Lists
List_Sources_Enabled = ["Wifi","Bluetooth","Line In"]

# Amp status object
class Amp:
    "All the current status details about the Amp"

    def __init__(self) -> None:
        self.Name = "default"
        self.SelectedSource = "LineIn"
        self.Volume = 1
        self.PlayState = "Stop"
        self.Audiable = "No"
        self.OutputValue = 1
        self.Track = ""
        self.Artist = ""
        self.Album = ""
        self.AvailableSources = "Stream,LineIn"
        self.MaxVolume = 10
        self.MultiplexerChannel = 0

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


#### MERGE THE MULTIPLEXER CONTROLS INTO A SINGLE CODED OBJECT

# Control a Multiplexer
class Multiplexer:
    "Generic multiplexer controls"

    def __init__(self, Max, Live):
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
        self.LiveChannel = channelNumber

    def getChannelList(self):
        "List current channels available"
        return self.ListofChannelNames

    def getAvailbleChannelCount(self):
        "How many channels are now available"
        return len(self.ListofChannelNames)

    def getIsChannelConfigured(self,channelNumber):
        "Is the channel number requested actually configured"
        if self.ListofChannelNames[channelNumber] != '':
            return True
        else:
            return False

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
class UART_Communication:

    def __init__(self) -> None:          
        self.QueuingEnabled = Flag_UART_Queuing_Enabled                             # Toggle to disable queuing
        self.NextRequestPosition = 1                                                # Which queue position to read from next
        self.QueueLength = 0                                                        # Current number of requests in the queue            
        self.MaxQueueLength = Limit_UART_Max_Queue_Length                           # Max number of queued UAT requests
        self.Idle = True                                                            # Currently in use and communitaing
        self.MaxQueueWaitSeconds = 15                                                # How long to wait before request rejected
        self.MaxWaitResponse = 3                                                    # How long to wait for a UART response
        self.QueuedRequests = {}                                                    # -- Not sure how this will be implemented yet
        self.ResponseBuffer = []                                                    # Responses populated in this buffer
        self.LastProcessedRequest = 0                                               # Timestamp of last processed request

    def sendNextCommandFromUARTQueue(self):
        "SECOND THREAD: Check message request queue and send"
        # If queue not empty, check if multiplexer idle
            # Lock mutliplexer idle
                # Read channel and command request from queue, set multiplexer to destination channel
                    # Send message
                    # Push response into buffer
                    # Increment Next Request position and decrement Queue Length
                    # Update last processed request
            # Unlock multiplexer idle
        

    def requestUARTCommand(self,channelNumber,message):
        "Requests an API message to the UART on a particular channel"

        # Check to see if the channel is actaully configured
            # If the queue length at it's max, run prune queue and check length again
                # If queue full return failed
            # If the (request queue has space AND the related response buffer is empty), add command and timestamp to queue and check response buffer

    def pruneUARTQueue(self):
        "Look for requests which are old and prune from quque"
        # Loop through each queue position to look for queue item are older than max queue wait time
            # If old request found, check if last processed request is greater than than max queue time
                # Clear buffer response for item and remove old request from queue  


    def ampDiscovery(self,cycleAttempts,waitForResponse):
        "Cycle through the multiplexer a specified number of times waiting for a responce"

        # Loop from begnniong to max sending a status message to each channel
            # Validate if the name matches that in the multiplexer list
                # If the name is different, update the name


### Variable of available Amps

AmpNumber = 0                               # This could be calculated from talking via each multiplexer and seeing who responds.
AmpsInstalled = ["Oasis","Pool","Italian"]  # Since that can be stored in the Amp after power up, extract from there periodically



### Variable Amp primary
# Which amp is currently selected
AmpSelected = 0

### Function to detect button press
# Interupt if any button depressed (VNR,Eject,Stop,Play/Pause/Forward/Rewind)
def Button_Handler(pin):
    print(pin)

    if pin == Pin_Source_Cycle:
        print("Source")
    elif pin == Pin_Amp_Cycle:
        print("Amp")
    else:
        print("?")



### Function to select UART
# Message to multiplexer to change UART selected
# Validate not inuse first, queues for x time, rejects request if someone waiting
# Is the end point transmitting


### Function to send and recieve UART information
# Provided a selected amp to send the message
# Selects the Amp (handling rejection)
# Provided a message to send and stores the responce


### Function to detect IR request


### Function to convert request to action
# Creates message to be sent to the Amp via UART
# Updates the Amp status


### Function to poll for amp status details
# Round Robin through amp
# Handles rejection,

### Function to push Amp status to the display buffer
# Use framebuf micropython


### Function to read if there's input from the output of each amp


### Function to set LineIn destination Amp


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

