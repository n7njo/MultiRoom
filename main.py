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
        # Visual to see if sound playing from each amp
        # Reset amp option
        # LED to show queue temperature

    # Questions?
        # Assume the only task in the main loop would be to display, poll status, read input
        # What output can be seen from the Amp to determine sound actually being played

    # Answers
        # Primary thread recieves the interupt for the botton press, what happens if in the middle of a UART
        # Thought is for the UART to be on 2nd thread so conversations not interupted by button presses
        # PIO is a very low level ablity to write a custom messaging protocal


import utime
import machine
import _thread
from machine import UART,Pin
import ure


### Configure Pins
# Pin numbers
Pin_LED_Green = 13          # Need to confirm if PWM capable
Pin_LED_Blue = 15           # Need to confirm if PWM capable
Pin_LED_RED = 14            # Need to confirm if PWM capable
Pin_BUT_Amp_Cycle = 21      #
Pin_BUT_Source_Cycle = 22   #
Pin_LED_Internal = 25       #
Pin_UART_Multi_S0 = 13      # Mutliplexer select Bit 0
Pin_UART_Multi_S1 = 14      # Mutliplexer select Bit 1 
Pin_UART_Multi_E = 16       # Mutliplexer Enable
Pin_UART_Multi_Signal = 18  # Mulliplexer Signal
Pin_UART_TX = 4
Pin_UART_RX = 5


# LEDs
LED_Internal = machine.Pin(Pin_LED_Internal, machine.Pin.OUT)
LED_Green = machine.Pin(Pin_LED_Green, machine.Pin.OUT)
LED_Blue = machine.Pin(Pin_LED_Blue, machine.Pin.OUT)


# Buttons
Button_Source_Cycle = machine.Pin(Pin_BUT_Source_Cycle, machine.Pin.IN, machine.Pin.PULL_UP)
Button_Amp_Cycle = machine.Pin(Pin_BUT_Amp_Cycle, machine.Pin.IN, machine.Pin.PULL_UP)

# Limits
Limit_UART_Max_Queue_Length = 5                                                             # Queue size for waiting UART requests
Limit_UART_Throttling_Queue_Length = 5                                                      # Throttling queue size if Low requests are impacting
Limit_UART_Multiplexer_Max_Channels = 4                                                    # How many channels does the multiplexer have
Limit_UART_Multiplexer_Max_Minutes_Looking = 10                                             # Max minutes to look for channels in available
Limit_LineIn_Multiplexer_Max_Channels = 4                                                  # Max chanels on the multiplexter for LineIn
Limit_LineOut_Multiplexer_Max_Channels = 0                                                  # Max chanels on the multiplexter for LineOut

# Flags
Flag_UART_Threading_Enabled = False                                                            # Can the UART queue messages
Flag_System_RedLine = False


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
        #self.AmpsInstalled = ["Oasis","Pool","Italian"]   
        self.AmpsInstalled = ["Pool"]                                     

    def ampDiscovery(self,cycleAttempts,waitForResponse):
        "Cycle through the multiplexer a specified number of times waiting for a responce"
        # What happens if the amp has changed it's name

        # Loop from begnning to max sending a status message to each Amp
        for cycles in range(cycleAttempts):
            # Loop through all the Amps on the multiplexer
            for ampNumber in range(Limit_UART_Multiplexer_Max_Channels):
                UART_Com.setLiveChannel(ampNumber)
                UART_Com.setMultiplexState("on")
                ## Only needed because pulling from predefined list
                if len(self.AmpsInstalled) > ampNumber:
                    AmpName = self.AmpsInstalled[ampNumber]
                    #print(str(ampNumber) + ":"+ AmpName)

                    if self.Amplifiers.get(ampNumber):
                        print("Skipping: ", end='')
                        print(self.Amplifiers[ampNumber].Name)
                    else:
                        print("Creating Amp: ", end='')
                        NewAmp = Amp()
                        self.Amplifiers[ampNumber] = NewAmp 
                        self.Amplifiers[ampNumber].Name = AmpName
                        self.Amplifiers[ampNumber].AvailableSources = self.List_Sources_Enabled
                        self.Amplifiers[ampNumber].AmpNumber = ampNumber
                        print(self.Amplifiers[ampNumber].Name)
                UART_Com.setMultiplexState("off")
                # No hardcoded Amp name found - REMOVE once dynamic
                #else:
                    #print(ampNumber, end='')

            # Validate if the name matches that in the multiplexer list
                # If the name is different, update the name

    def setAmpSelected(self,ampNumber):
        "Change selected amp"
        self.AmpSelected = ampNumber

    def getAmpSelected(self):
        "Return current selected amp"
        return self.AmpSelected

    def refreshAmpStatus(self,ampNumber,_uart):
        "Gather status information on specific amplifier"
        # print(ampNumber)
        # self.getStatus(ampNumber,_uart)
        # self.getSource(ampNumber,_uart) 
        # self.getVolume(ampNumber,_uart) 
        #print(responseTimestamp)
        self.Amplifiers[ampNumber].requestSystemState(ampNumber,_uart)
        self.Amplifiers[ampNumber].requestPlaybackStatus(_uart)

        #Missing song info
        if int(self.Amplifiers[ampNumber].getPlaybackStatus()) and len(self.Amplifiers[ampNumber].getTitle()) < 1:
            self.Amplifiers[ampNumber].requestTitle(_uart)
            self.Amplifiers[ampNumber].requestArtist(_uart)
            self.Amplifiers[ampNumber].requestAlbum(_uart)
            self.Amplifiers[ampNumber].requestFeed(_uart)
        
        self.Amplifiers[ampNumber].printAmp(ampNumber)

    def refreshAllAmpStatus(self,_uart):
        "Update all amplifier statuses"

        for ampNumber in list(self.Amplifiers.keys()):
            self.refreshAmpStatus(ampNumber,_uart)

# Amp status object
class Amp:
    "All the current status details about the Amp"

    def __init__(self) -> None:
        self.Name = "default"
        self.SelectedSource = "LineIn"
        self.AmpNumber = 0
        self.Volume = 1
        self.Mute = 0
        self.Treble = 0
        self.Bass = 0
        self.PlayState = 0
        self.Audiable = "No"
        self.OutputValue = 1                                # Validation there is output?
        self.Title = ""
        self.Artist = ""
        self.Album = ""
        self.TrackPosition = 0
        self.Feed = ""
        self.AvailableSources = []
        self.MaxVolume = 10
        self.LED = 0
        self.Network = 0
        self.Internet = 0
        self.WWW = 0
        self.Ethernet = 0
        self.Upgrading = 0

    def requestSystemState(self,ampNumber,_uart):
        "Confirm status of amp"
        # STA: {source,mute,volume,treble,bass,net,internet,playing,led,upgrading};
        # Returns 
        # print("STA")
        return _uart.requestCommand(ampNumber, "STA;","Low",0.1)
       
    def setStatus(self,status):
        _ampStatus = status.split(",")
        _statusElements = len(_ampStatus)
        ##print(_ampStatus)
        if _statusElements < 10:
            return False
        self.setInputSource(_ampStatus[0])
        self.setMute(_ampStatus[1])
        self.setVolume(_ampStatus[2])
        self.setTreble(_ampStatus[3])
        self.setBass(_ampStatus[4])
        self.setNetwork(_ampStatus[5])
        self.setInternet(_ampStatus[6])
        #self.setPlaybackStatus(_ampStatus[7])  # This doesn't appear to be what I think it is....
        self.setLED(_ampStatus[8])
        self.setUpgrading(_ampStatus[9])

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

    def getInputSource(self,ampNumber,_uart):
        "Confirm current input source"
        # SRC;
        # Returns {NET/USB/USBDAC/LINE-IN/LINE-IN2/BT/OPT/COAX/I2S/HDMI}
        # print("SRC")
        return _uart.requestCommand(ampNumber, "SRC;","Low",0.1)

    def setInputSource(self,source):
        "Set current input source"
        # SRC: {NET/USB/USBDAC/LINE-IN/LINE-IN2/BT/OPT/COAX/I2S/HDMI};
        # print("SRC")
        self.SelectedSource = source

    def getVolume(self,ampNumber,_uart):
        "Confirm current volume"
        # VOL;
        # Returns {0..100}
        # print("VOL")
        return _uart.requestCommand(ampNumber, "VOL;","Low",0.1)
   
    def requestVolume(self,ampNumber,_uart,volume):
        "Confirm current volume"
        # VOL: {0..100};
        # print("VOL")
        return _uart.requestCommand(ampNumber, "VOL:" + str(volume) + ";","High",0.1)

    def setVolume(self,volume):
        self.Volume = volume

    def getMute(self):
        "Confirm current mute status"
        # MUT;
        # Returns {0,1}
        print("MUT")
   
    def setMute(self,mute):
        "Set mute status"
        # MUT: {0/1/T};
        # print("MUT")
        self.Mute = mute    

    def getBass(self):
        "Confirm current Bass level"
        # BAS;
        # Returns {-10..10}
        print("BAS")
   
    def setBass(self,bass):
        "Set Bass level"
        # BAS: {-10..10};
        # print("BAS") 
        self.Bass = bass 

    def getTrebble(self):
        "Confirm current Treble level"
        # TRE;
        # Returns {-10..10}
        print("TRE")
   
    def setTreble(self, treble):
        "Set Treble level"
        # TRE: {-10..10};
        #print("TRE")   
        self.Treble = treble    
   
    def setPlaybackStatus(self,playstate):
        "Set Playback State"
        self.PlayState = playstate

    def requestStop(self,ampNumber,_uart):
        "Stop playing"
        # STP;
        #print("STP")
        return _uart.requestCommand(ampNumber, "STP;","High",0.1)
            
    def requestNext(self,ampNumber,_uart):
        "Skip to next track"
        # NXT;
        #print("NXT")
        return _uart.requestCommand(ampNumber, "NXT;","High",0.1)

    def requestPrevious(self,ampNumber,_uart):
        "Jump to previous track"
        # PRE;
        #print("PRE")
        return _uart.requestCommand(ampNumber, "PRE;","High",0.1)

    def requestPlayPause(self,ampNumber,_uart):
        "Play or Pause current track"
        # POP;
        print("POP")
        return _uart.requestCommand(ampNumber, "POP;","High",0.1)  

    def requestTitle(self,_uart):
        "Request title infomation"
        # TIT;
        # print("TIT")
        return _uart.requestCommand(self.AmpNumber, "TIT;","Low",0.1)

    def requestArtist(self,_uart):
        "Request Artist infomation"
        # ART;
        # print("ART")
        return _uart.requestCommand(self.AmpNumber, "ART;","Low",0.1)

    def requestAlbum(self,_uart):
        "Request Album infomation"
        # ALB;
        # print("ALB")
        return _uart.requestCommand(self.AmpNumber, "ALB;","Low",0.1)

    def requestFeed(self,_uart):
        "Request Feed infomation"
        # TIT;
        # print("VND")
        return _uart.requestCommand(self.AmpNumber, "VND;","Low",0.1)

    def setTitle(self,title):
        self.Title = title

    def getTitle(self):
        return self.Title

    def setAlbum(self,album):
        self.Album = album

    def setArtist(self,artist):
        self.Artist = artist

    def setTrackPosition(self,trackposition):
        self.TrackPosition = trackposition

    def setFeed(self,feed):
        self.Feed = feed

    def getBluetoothStatus(self):
        "Confirm current bluetooth connection status"
        # BTC;
        # Returns {0,1}
        print("BTC")
    
    def requestPlaybackStatus(self,_uart):
        "Confirm current wifi playback status"
        # PLA;
        # Returns {0,1}
        #print("PLA")
        return _uart.requestCommand(self.AmpNumber, "PLA;","Low",0.1)

    def getPlaybackStatus(self):
        return self.PlayState
    
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
   
    def setLED(self,led):
        "Set LED status"
        # LED: {0/1/T};
        # print("LED") 
        self.LED = led   

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

    def getName(self,ampNumber,_uart,):
        "Confirm current Name status"
        # NAM;
        # Returns {Name}
        # hexed string with UTF8 encoding
        # print("NAM")
        return _uart.requestCommand(ampNumber, "NAM;","Low",0)
   
    def setName(self,name):
        "Set Name"
        pass
        # NAM: {Name};
        # hexed string with UTF8 encoding
        # print("NAM")
        # print(ubinascii.unhexlify(name))
        #self.Name = ubinascii.unhexlify(name)

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

    def setNetwork(self,network):
        self.Network = network
    
    def setInternet(self,internet):
        self.Internet = internet

    def setUpgrading(self,upgrading):
        self.Upgrading = upgrading

    def printAmp(self,ampNumber):
        print("----- Amp: " + self.Name + "  |  Ch: " + str(ampNumber) + " --------------------")
        print("Source: " + self.SelectedSource, end='  |  ')
        print("Available: " + str(self.AvailableSources), end='  |  ')
        print("Mute: " + str(self.Mute),end='  |  ')
        print("Volume: " + str(self.Volume),end='  |  ')
        print("MaxVolume: " + str(self.MaxVolume), end='  |  ')
        print("Treble: " + str(self.Treble),end='  |  ')
        print("Bass: " + str(self.Bass))
        print("PlayState: " + str(self.PlayState), end='  |  ')
        print("TrackPosition: " + str(self.TrackPosition), end='  |  ')
        print("LED: " + str(self.LED), end='  |  ')
        print("Audiable:" + self.Audiable, end='  |  ')
        print("Output value:" + str(self.OutputValue), end='  |  ')
        print("Network:" + str(self.Network), end='  |  ')      # Maybe same as Ethernet
        print("Ethernet:" + str(self.Ethernet), end='  |  ')
        print("Internet:" + str(self.Internet), end='  |  ')    # Maybe same as WWW
        print("WWW:" + str(self.WWW))
        print("Feed: " + self.Feed, end='  |  ')
        print("Title: " + self.Title, end='  |  ')
        print("Artist: " + self.Artist, end='  |  ')
        print("Album: " + self.Album)
        print("----------------------------------------------")


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

    def __init__(self, S0, S1, E, Max, signal):
        self.S0 = machine.Pin(S0, machine.Pin.OUT)
        self.S1 = machine.Pin(S1, machine.Pin.OUT)
        self.E = machine.Pin(E, machine.Pin.OUT)
        self.signal = machine.Pin(signal)
        self._reset()
        self.current_bits = "00"
        self.state = False
        self.MaxChannels = Max                                                      # Max number of multiplexer channels
        self.LiveChannel = 0

    def _reset(self):
        self.S0.off()
        self.S1.off()  
        self.E.off()

    def _switch_pins_with_bits(self, bits):  
        s0, s1 = [int(x) for x in tuple(bits)]  
        self.S0.value(s0)  
        self.S1.value(s1) 
    
    def _bits_to_channel(self, bits):
        return int("00" + "".join([str(x) for x in "".join(reversed(bits))]), 2)

    def _channel_to_bits(self, channel_id):
        return ''.join(reversed("{:0>{w}}".format(bin(channel_id)[2:], w=2)))

    def setLiveChannel(self, channel_id):
        if channel_id == self.MaxChannels: return False
        bits = self._channel_to_bits(channel_id)  
        self._switch_pins_with_bits(bits)  
        self.current_bits = bits
        self.LiveChannel = channel_id
        #print(self.LiveChannel)

    def setMultiplexState(self,newstate):
        if newstate == "off":
            self.E.value(0)                       # toggle off
            self.state = False
        elif newstate == "on":
            self.E.value(1)                       # toggle on
            self.state = True

# Control of the UART Multiplexer
class UART_Multiplexer(Multiplexer):
    "Control of the multiplexer"

    def __init__(self):
        #super.__init__(Limit_UART_Multiplexer_Max_Channels,1)                       # Inherit everything from Multiplexer
        super().__init__(Pin_UART_Multi_S0, Pin_UART_Multi_S1, Pin_UART_Multi_E,Limit_UART_Multiplexer_Max_Channels,Pin_UART_Multi_Signal)       # Which pins to use
        self.idle = False

# Control of the Line In Multiplexer
class LineIn_Multiplexer(Multiplexer):
    "Control of the Line In Multiplexer"

    def __init__(self):
        super().__init__(1,1,1,Limit_LineIn_Multiplexer_Max_Channels,1)                     # Inherit everything from Multiplexer

# Control of the Line Out Multiplexer - Future feature
class LineOut_Multiplexer(Multiplexer):
    "Control of the Line Out Muliplexer - ON HOLD not confirmed"

    def __init__(self):
        super().__init__(1,1,1,Limit_LineOut_Multiplexer_Max_Channels,1)                     # Inherit everything from Multiplexer

# Control of the UART communication

#class UART_Communication(UART_Multiplexer,UART):

class UART_Communication(UART_Multiplexer):

    def __init__(self) -> None:
        super().__init__()       
        self.QueuingEnabled = Flag_UART_Threading_Enabled                             # Toggle to disable queuing
        self.QueueLength = 0                                                        # Current number of requests in the queue            
        self.MaxQueueLength = Limit_UART_Max_Queue_Length                           # Max number of queued UAT requests
        self.ThrottleingQueueLength = Limit_UART_Throttling_Queue_Length                # Throttling queue length for low
        self.Idle = True                                                            # Currently in use and communitaing
        self.MaxQueueWaitSeconds = 5                                               # Longest a request can wait on the quque
        self.MaxBusyQueueWaitSeconds = 3                                           # Longest a request can wait on a busy queue
        self.MaxWaitResponse = 3                                                    # How long to wait for a UART response
        self.QueuedRequests = {}                                                    # -- Not sure how this will be implemented yet
        self.ResponseBuffer = {}                                                    # Responses populated in this buffer
        self.LastProcessedRequest = 0                                               # Timestamp of last processed request
        self.BackPresure = False                                                    # Are High priority requests not making it onto the queue
        self.LastBackPresure = 0                                                    # When was back pressure last applied
        self.BackPresureRelease = 3                                                 # After how long to take of back presure
        self.BackPresureCount = 0                                                   # How many times has backpresure been applied
        self.BackPresureThreshold = 2                                               # Adjust soft limit
        self.LastBackPresureThreshold = 0                                           # When was the limit last adjusted
        
        self.uart = UART(1, baudrate=115200, bits=8, parity=None, stop=1, tx=Pin(Pin_UART_TX), rx=Pin(Pin_UART_RX))


    # UART NON-Threaded worker
    def sendNextCommandFromQueue(self):
        "Check message request queue and send"

        # If queue not empty, check if multiplexer idle
        if self.getRequestQueueLength() > 0 and self.Idle == True:
            #print(UART_Com.getRequestQueueLength(), end='')
            #print(list(self.getQueueRequests()))
            #self.printQueue()
            # Lock mutliplexer idle
            self.Idle = False
            # Select oldest waiting request
            request = tickNow()
            found = False
            # Find the oldest high priority request
            for lowest in (self.getQueueRequests()):
                if self.getRequestComplete(lowest) == False and self.getRequestPriority(lowest) == "High":
                    #print("*", end='')
                    if lowest < request:
                        request = lowest
                        found = True

            # If no high priority requests, find the oldest low priorty request
            if found == False:
                for lowest in (self.getQueueRequests()):
                        if self.getRequestComplete(lowest) == False and self.getRequestPriority(lowest) == "Low":
                            if lowest < request:
                                request = lowest
                                found = True

            if found == True and request in self.getQueueRequests():
                ### Process Request ###
                # Select Multiplexer
                self.setMultiplexState("on")
                self.setLiveChannel(self.getRequestAmp(request))
                # Send message
                self.ResponseBuffer[request]=self.transmitRequest(self.getRequestMessage(request),self.getResponseWait(request))
                self.setMultiplexState("off")
                # Push response into buffer
                self.setRequestComplete(request,True)
                # if self.getRequestPriority(request) == "High":
                #     print("H",end='')
                # else:
                #     print("L",end='')
            # Unlock multiplexer idle
            self.Idle = True

    # UART Threaded worker
    def THREADsendNextCommandFromQueue(self):
        "SECOND THREAD: Check message request queue and send"
        lastProcessed = utime.ticks_ms()

        while True:
            try:
                #UART_Com.printQueue()    
                ##if secondsSinceTick(lastProcessed) > 1:
                lastProcessed = tickNow()
                # If queue not empty, check if multiplexer idle
                if self.getRequestQueueLength() > 0 and self.Idle == True:
                    # Lock mutliplexer idle
                    self.Idle = False
                    # Select oldest waiting request
                    request = tickNow()
                    found = False
                    # Find the oldest high priority request
                    for lowest in (self.QueuedRequests.keys()):
                        if self.getRequestComplete(lowest) == False and self.getRequestPriority(lowest) == "High":
                            print("*", end='')
                            if lowest < request:
                                request = lowest
                                found = True

                    # If no high priority requests, find the oldest low priorty request
                    if not found:
                        for lowest in (self.QueuedRequests.keys()):
                            if self.getRequestComplete(lowest) == False and self.getRequestPriority(lowest) == "Low":
                                if lowest < request:
                                    request = lowest
                                    found = True

                    if found and request in self.QueuedRequests:
                        ### Process Request ###
                        # Select Multiplexer
                        self.setLiveChannel(self.getRequestAmp(request))
                        # Send message
                        self.ResponseBuffer[request]=self.transmitRequest(self.getRequestMessage(request))
                        # Push response into buffer
                        self.setRequestComplete(request,True)
                        print(".")
                    # Unlock multiplexer idle
                    self.Idle = True
            except Exception:
                print("EXECPTION")
    
    def transmitRequest(self,message,wait):
        "Actually send the message down the UART"
        # Anything in the buffer 
        # print("{" + str(self.uart.read()),end='}')
        self.uart.write(message)
        utime.sleep(wait)
        # read line into buffer
        response = self.uart.read()
        # print(str(response)[2:])
        # if response == None:
        #     utime.sleep(0.5)
        #     response = self.uart.read()

        # print("[" + str(self.uart.read()),end=']')
        
        return str(response)[2:][:-6]

    def removeFromQueue(self,request):
        if Flag_UART_Threading_Enabled == True:
            baton.acquire() 

        del self.ResponseBuffer[request]
        del self.QueuedRequests[request]

        if Flag_UART_Threading_Enabled == True:
            baton.release()

    def pushToQueue(self,ampNumber,message,priority,wait):
        addedToQueueTicks = tickNow()

        # Lock Variable
        if Flag_UART_Threading_Enabled == True:
            baton.acquire()
        # Add request to the queue - True/False flag indicates response complete
        self.QueuedRequests[addedToQueueTicks] = [ampNumber,message,False,priority,wait]
        # Add placeholder for response
        self.ResponseBuffer[addedToQueueTicks] = [""]
        if Flag_UART_Threading_Enabled == True:
            baton.release()
        return addedToQueueTicks
  
    def getRequestQueueLength(self):
        #baton.acquire()
        length = len(self.QueuedRequests)
        #baton.release()
        return length

    def getRequestAmp(self,request):
        #baton.acquire()
        ampNumber = self.QueuedRequests[request][0]
        #baton.release()
        return ampNumber

    def getRequestMessage(self,request):
        #baton.acquire()
        message = self.QueuedRequests[request][1]
        #baton.release()
        return message

    def getRequestComplete(self,request):
        #baton.acquire()
        complete = self.QueuedRequests[request][2]
        #baton.release()
        return complete

    def getRequestPriority(self,request):
        #baton.acquire()
        priority = self.QueuedRequests[request][3]
        #baton.release()
        return priority

    def getResponseWait(self,request):
        #baton.acquire()
        priority = self.QueuedRequests[request][4]
        #baton.release()
        return priority

    def setRequestComplete(self,request,complete):
        if Flag_UART_Threading_Enabled == True:
            baton.acquire()
        self.QueuedRequests[request][2]=complete
        if Flag_UART_Threading_Enabled == True:
            baton.release()

    def requestCommand(self,ampNumber:int,message="",priority="low",wait=1):
        "Requests an API message to the UART to a particular Amp"
        
        global Flag_System_RedLine

        # How many times has back presure been applied, if too high lower soft limit
        if self.BackPresureCount == self.BackPresureThreshold:
            if self.ThrottleingQueueLength > 0:
                self.ThrottleingQueueLength = self.ThrottleingQueueLength - 1
                self.BackPresureCount = 0
                self.LastBackPresureThreshold = tickNow()
                print("<",end='')
            else:
                print("Danger",end='')
                print("<",end='')
                self.MaxQueueLength = self.MaxQueueLength + 1
                self.BackPresureCount = 0
                self.LastBackPresureThreshold = tickNow()
                self.ThrottleingQueueLength = 1
                Flag_System_RedLine = True

        # When was threshold last adjusted, can it be lifted
        if secondsSinceTick(self.LastBackPresureThreshold) > 10:
            if self.MaxQueueLength > Limit_UART_Max_Queue_Length:
                self.MaxQueueLength = self.MaxQueueLength - 1
                self.LastBackPresureThreshold = tickNow()
                print(">",end='')
                if self.MaxQueueLength == Limit_UART_Max_Queue_Length:
                    Flag_System_RedLine = False
                    print("Cooling",end='')
            elif self.ThrottleingQueueLength < self.MaxQueueLength:
                    self.ThrottleingQueueLength = self.ThrottleingQueueLength + 1
                    self.LastBackPresureThreshold = tickNow()
                    print(">",end='')
            else:
                # Things have returned to normal
                #print("N",end='')
                pass

            
        # Check if Back pressure is enabled, but can be removed
        if self.BackPresure and secondsSinceTick(self.LastBackPresure) > self.BackPresureRelease:
            self.BackPresure = False

        # Check to see if the Amp is actaully configured
        if MA.Amplifiers.get(ampNumber):
            # If the queue length at it's max, run prune queue and check length again
            if self.getRequestQueueLength() < self.MaxQueueLength:
                if priority == "Low" and self.BackPresure == True:
                    # High Priority requests aren't making it onto the queue
                    ##print("b", end='')
                    return False
                else:
                    # Check for soft limit on Low
                    if priority == "Low" and self.getRequestQueueLength() > self.ThrottleingQueueLength:
                        ##print("s",end='')
                        return False
                    # Returns the unique timestamp used as a key
                    if priority == "High":
                        ##print("h",end='')
                        pass
                    else:
                        ##print("l",end='')
                        pass
                    return (self.pushToQueue(ampNumber,message,priority,wait))

            else:
                if priority == "High":
                    ##print("[h]",end='')
                    self.BackPresure = True
                    self.LastBackPresure = tickNow()
                    self.BackPresureCount = self.BackPresureCount + 1
                    #print(self.BackPresureCount,end='')
                else:
                    ##print("[l]",end='')
                    pass
                return False
        else:
            print("Bad ampNumber")
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
            if (int(secondsSinceTick(request))) > self.MaxBusyQueueWaitSeconds and self.getRequestQueueLength() > self.MaxQueueLength:
                print("+", end='')
                self.removeFromQueue(request)

    def printQueue(self):
        "Return current queue"
        for request in self.QueuedRequests:
            print(str(request) + ":|" + self.QueuedRequests[request][1] + "," + str(self.QueuedRequests[request][2]) + "," + self.QueuedRequests[request][3] + "|  ", end='')
        print()

    def getQueue(self):
        return list(self.QueuedRequests.items())
    
    def getQueueRequests(self):
        return list(self.QueuedRequests.keys())

    def parseResponses(self):
        "Worker processing responses"
        # Look through the queue for any completes
        for request in list(self.QueuedRequests.keys()):
            # Look through the queue for processed high priority responses
            if self.QueuedRequests[request][2] == True and self.QueuedRequests[request][3] == "High":

                # Interpret the request to determine the action needed
                self.actionParsedResponse(request)

                # Remove the queue
                self.removeFromQueue(request)

        # Look through the queue for processed low priority responses
        for request in list(self.QueuedRequests.keys()):
            if self.QueuedRequests[request][2] == True and self.QueuedRequests[request][3] == "Low":
                
                # Interpret the request to determine the action needed
                self.actionParsedResponse(request)
                
                # Remove the queue
                self.removeFromQueue(request)

    def actionParsedResponse(self,request):

        #print("{" + self.ResponseBuffer[request] + "}")

        # Count if more that one Response type in the buffer, look for the ':'
        ##bufferRequests = ure.sub("r|n\g","",self.ResponseBuffer[request])

        self.ResponseBuffer[request]
        _firstFound = -1
        # Check if starts with control chars, and remove
        for i in range(len(self.ResponseBuffer[request])):
            m = ure.match('[A-Z]',self.ResponseBuffer[request][i])
            if m and _firstFound < 0:
                _firstFound = i
        # print(str(_firstFound) + "@", end='')
        # print("-" + str(self.ResponseBuffer[request]) + "-")
        self.ResponseBuffer[request] = self.ResponseBuffer[request][_firstFound:]

        #command = ure.compile('[A-Z][A-Z][A-Z]')
        #print(command.search(buffer), end='')
        #print(ure.match('S',buffer))
        bufferRequests = str(self.ResponseBuffer[request]).split(";")
        responseCount = len(bufferRequests)
        if responseCount < 1:
            bufferRequests = self.ResponseBuffer[request]
        #bufferRequests
        #print("\n+" + str(bufferRequests) + "+\n")

    ##### Need to handle when not receiving an unexpected brain dump
    ##### NEED TO HANDLE WHEN RECIEVING DUMP, BUT CHOP OFF 3 CHARS BY MISTAKE

        for i in range(len(bufferRequests)):
            if i > 0 and len(bufferRequests) > 1:
                bufferRequests[i] = bufferRequests[i][4:]
            else:
                pass
                #print("+",end='')
            
            # Loop through each
            #print(bufferRequests[i])
            ampNumber = self.getRequestAmp(request)
            requestType = bufferRequests[i][:3]
            response = bufferRequests[i][4:]
            ##self.ResponseBuffer[request] = self.ResponseBuffer[request][4:]

            #print(" <" + str(self.ResponseBuffer[request]) + "> ")
            #print(requestType + "#{" + response + "} ",end='')

            ###### Status change
            if requestType == "STA":
                MA.Amplifiers[ampNumber].setStatus(response)
            ###### Volume change
            elif requestType == "VOL":
                MA.Amplifiers[ampNumber].setVolume(response)
            ###### Source change
            elif requestType == "SRC":
                MA.Amplifiers[ampNumber].setInputSource(response)
            ###### Mute change
            elif requestType == "MUT":
                MA.Amplifiers[ampNumber].setVolume(response)
            ###### Play Pause toggle
            elif requestType == "POP":
                MA.Amplifiers[ampNumber].setPlayPause(response)
            ###### Stop 
            elif requestType == "STP":
                MA.Amplifiers[ampNumber].Stop(response)
            ###### Next track 
            elif requestType == "NXT":
                MA.Amplifiers[ampNumber].Next(response)
            ###### Previous track 
            elif requestType == "PRE":
                MA.Amplifiers[ampNumber].Previous(response)
            ###### Title 
            elif requestType == "TIT":
                MA.Amplifiers[ampNumber].setTitle(response)
            ###### Album 
            elif requestType == "ALB":
                MA.Amplifiers[ampNumber].setAlbum(response)
            ###### Artist 
            elif requestType == "ART":
                MA.Amplifiers[ampNumber].setArtist(response)
            ###### Track position 
            elif requestType == "ELP":
                MA.Amplifiers[ampNumber].setTrackPosition(response)
            ###### VND???? Don't know 
            elif requestType == "VND":
                MA.Amplifiers[ampNumber].setFeed(response)
            ###### Playing information 
            elif requestType == "PLA":
                MA.Amplifiers[ampNumber].setPlaybackStatus(response)
            ###### Amp Name 
            elif requestType == "NAM":
                MA.Amplifiers[ampNumber].setName(response)

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
UART_Com = UART_Communication()

# Find Amps and create the objects
MA.ampDiscovery(1,1)

###### Spawning Second Thread ######

if Flag_UART_Threading_Enabled == True:
    print("SPAWN")
    _thread.start_new_thread(UART_Com.THREADsendNextCommandFromQueue, ())
    baton = _thread.allocate_lock()

MA.refreshAllAmpStatus(UART_Com)

#UART_Com.requestCommand(1, "PLA","High")
#UART_Com.requestCommand(1, "OLD","Pause")

lastPrune = tickNow()
lastParse = tickNow()
lastProcessed = tickNow()

lastQueuePrint = tickNow()
lastAutoGenerateLow = tickNow()
lastCheckAllStatus = tickNow()


while True:

    if Flag_System_RedLine:
        # System running hot
        #print("HOT")
        pass

    if secondsSinceTick(lastParse) > 0.1:
        lastParse = tickNow()
        UART_Com.parseResponses()

    if secondsSinceTick(lastPrune) > 10:  
        lastPrune = tickNow()
        UART_Com.pruneQueue()

    if secondsSinceTick(lastQueuePrint) < 0:
        lastQueuePrint = tickNow()
        #UART_Com.printQueue()

    if secondsSinceTick(lastCheckAllStatus) > 2:
        lastCheckAllStatus = tickNow()  
        MA.refreshAllAmpStatus(UART_Com) 

    if secondsSinceTick(lastProcessed) > 0.01 and Flag_UART_Threading_Enabled == False:
        lastProcessed = tickNow()
        UART_Com.sendNextCommandFromQueue()


