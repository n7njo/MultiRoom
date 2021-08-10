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
                ## Only needed because pulling from predefined list NOT LOOKING DOWN THE UART
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
        self.Amplifiers[ampNumber].requestAmpState(ampNumber,_uart)
        # Don't trust the general status to show correct play status
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
        self.Attributes = {}                                    # Master Dictionary for all settings

        self.Name = "default"
        self.SelectedSource = "LineIn"
        self.AmpNumber = 0
        self.Volume = 1
        # self.Mute = 0
        # self.Treble = 0
        # self.Bass = 0
        # self.VirtualBass = 0
        self.PlayState = 0
        # self.Audiable = "No"
        # self.OutputEnabled = 1                                # Validation there is output?
        # self.Title = ""
        # self.Artist = ""
        # self.Album = ""
        # self.TrackPosition = 0
        # self.Feed = ""
        # self.LoopMode = ""
        # self.AvailableSources = []
        # self.MultiRoomStatus = ""
        # self.AudioChannel = ""
        # self.MaxVolume = 10
        # self.LED = 0
        # self.Beep = 0
        # self.Network = 0
        # self.Internet = 0
        # self.WWW = 0
        # self.Ethernet = 0
        # self.Upgrading = 0
        # self.SystemState = "_"
        # self.Version = "_"
        # self.Preset = ""
        # self.VoicePrompt = 0
        # self.SystemDelayTime = 0
        # self.AutoSwitch = 0
        # self.PowerOnSource = ""
        

    def pushUART(self,_uart,_key,_value):
        "Push value based on it's key"
        return _uart.requestCommand(self.AmpNumber, _key + ":" + str(_value) + ";","High",0.1)
        
    def requestUART(self,_uart,_key):
        "Request value base on Key"
        return _uart.requestCommand(self.AmpNumber, _key + ";","Low",0.1)
        
    def saveAttribute(self,_key,_value):
        self.Attributes={_key:_value}
    
    def readAttribute(self,_key):
        return self.Attributes[_key]

### STA Methods - AmpState
    # def pushAmpState(self,uart):
    #     "Does nothing"
    #     pass

    def requestAmpState(self,ampNumber,_uart):
        "Confirm status of amp"
        # STA: {source,mute,volume,treble,bass,net,internet,playing,led,upgrading};
        # Returns 
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

    # def getStatus(self):
    #     "Does nothing"
    #     pass

### SYS Methods - SystemState
    def pushSystemState(self,_state,_uart):
        "Push system command to the Amp"
        # SYS: {REBOOT/STANDBY/ON};
        return _uart.requestCommand(self.AmpNumber, "SYS:" + str(_state) + ";","High",0.1)

    def requestSystemState(self,_uart):
        "Request system command from the Amp"
        # SYS: {REBOOT/STANDBY};
        return _uart.requestCommand(self.AmpNumber, "SYS;","Low",0.1)

    def setSystemState(self,state):
        "Set system state"
        # SYS: {ON/STANDBY};
        self.SystemState = state
    
    def getSystemState(self):
        "Set system state"
        # SYS: {ON/STANDBY};
        return self.SystemState

### VER Methods - Version
    # def pushVersion(self,_uart):
    #     "Does nothing"
    #     pass

    def requestVersion(self,_uart):
        "Request software version from Amp"
        # VER: <string>;
        return _uart.requestCommand(self.AmpNumber, "VER;","Low",0.1)

    def setVersion(self,version):
        "Set Amp software version"
        # VER: <string>;
        self.Version = version
    
    def getVersion(self):
        "Set Amp software version"
        # VER: <string>;
        return self.Version

### WWW Methods - Internet
    # def pushInternet(self,_uart):
    #     "Does nothing"
    #     pass

    def requestInternet(self,_uart):
        "Confirm current Internet state"
        # WWW;
        # Returns {0,1}
        return _uart.requestCommand(self.AmpNumber, "WWW;","Low",0.1)

    def setInternet(self,_www):
        "Set Internet state"
        # WWW: {0,1};
        self.WWW = _www

    def getInternet(self):
        "Confirm if connected to the internet"
        # WWW;
        # Returns {0,1}
        return self.WWW

### AUD Methods - OutputEnable
    # def pushOutputEnable(self,_uart):
    #     "Does nothing"
    #     pass

    def requestOutputEnable(self,_uart):
        "Confirm current audio output state"
        # AUD;
        # Returns {0,1}
        return _uart.requestCommand(self.AmpNumber, "AUD;","Low",0.1)

    def setOutputEnable(self,_outputEnable):
        "Set audio output state"
        # AUD: {0,1};
        self.OutputEnabled = _outputEnable

    def getOutputEnable(self):
        "Confirm current audio output state"
        # AUD;
        # Returns {0,1}
        return self.OutputEnabled

### SRC MEthods - InputSource
    def pushInputSource(self,_uart,_source):
        "Push Input Source to the Amp"
        # SRC: {NET/USB/USBDAC/LINE-IN/LINE-IN2/BT/OPT/COAX/I2S/HDMI};
        return _uart.requestCommand(self.AmpNumber, "SRC:" + str(_source) + ";","High",0.1)

    def requestInputSource(self,_uart):
        "Request Input Source from the Amp"
        # SRC;
        # Returns {NET/USB/USBDAC/LINE-IN/LINE-IN2/BT/OPT/COAX/I2S/HDMI}
        return _uart.requestCommand(self.AmpNumber, "SRC;","Low",0.1)

    def setInputSource(self,_source):
        "Set current input source"
        # SRC: {NET/USB/USBDAC/LINE-IN/LINE-IN2/BT/OPT/COAX/I2S/HDMI};
        self.SelectedSource = _source

    def getInputSource(self):
        "Confirm current input source"
        # SRC;
        # Returns {NET/USB/USBDAC/LINE-IN/LINE-IN2/BT/OPT/COAX/I2S/HDMI}
        return self.SelectedSource

### VOL Methods - Volume
    def pushVolume(self,_uart,_volume):
        "Confirm current volume"
        # VOL: {0..100};
        return _uart.requestCommand(self.AmpNumber, "VOL:" + str(_volume) + ";","High",0.1)

    def requestVolume(self,_uart):
        "Confirm current volume"
        # VOL: {0..100};
        return _uart.requestCommand(self.AmpNumber, "VOL;","Low",0.1)

    def setVolume(self,_volume):
        "Set current volume"
        self.Volume = _volume

    def getVolume(self):
        "Confirm current volume"
        # VOL;
        # Returns {0..100}
        return self.Volume

### MUT Methods - Mute
    def pushMute(self,_uart,_mute):
        "Confirm current mute"
        # MUT: {0/1/T};
        return _uart.requestCommand(self.AmpNumber, "MUT:" + str(_mute) + ";","High",0.1)

    def requestMute(self,_uart):
        "Confirm current mute"
        # MUT: {0/1/T};
        return _uart.requestCommand(self.AmpNumber, "MUT;","Low",0.1)
     
    def setMute(self,_mute):
        "Set mute status"
        # MUT: {0/1/T};
        self.Mute = _mute    
   
    def getMute(self):
        "Confirm current mute status"
        # MUT;
        # Returns {0/1/T}
        return self.Mute

# ### BAS Methods - Bass
#     def pushBass(self,_uart,_bass):
#         "Push new Bass"
#         # BAS: {-10..10};
#         return _uart.requestCommand(self.AmpNumber, "BAS:" + str(_bass) + ";","High",0.1)

#     def requestBass(self,_uart):
#         "Request current Bass"
#         # BAS: {-10..10};
#         return _uart.requestCommand(self.AmpNumber, "BAS;","Low",0.1)   
   
#     def setBass(self,_bass):
#         "Set Bass level"
#         # BAS: {-10..10};
#         self.Bass = _bass 

#     def getBass(self):
#         "Confirm current Bass level"
#         # BAS;
#         # Returns {-10..10}
#         return self.Bass

# ### TRE Methods - Treble
#     def pushTreble(self,_uart,_treble):
#         "Push new Treble"
#         # TRE: {-10..10};
#         return _uart.requestCommand(self.AmpNumber, "TRE:" + str(_treble) + ";","High",0.1)

#     def requestTreble(self,_uart):
#         "Request current Treble"
#         # TRE: {-10..10};
#         return _uart.requestCommand(self.AmpNumber, "TRE;","Low",0.1) 

#     def setTreble(self, treble):
#         "Set Treble level"
#         # TRE: {-10..10};
#         self.Treble = treble   

#     def getTrebble(self):
#         "Confirm current Treble level"
#         # TRE;
#         # Returns {-10..10}
#         return self.Treble

# ### PLA Methods - PlaybackStatus
#     def pushPlaybackStatus(self,_uart,_playstate):
#         "Push current wifi playback status"
#         # PLA;
#         # Returns {0,1}
#         return _uart.requestCommand(self.AmpNumber, "PLA:" + str(_playstate) + ";","Low",0.1)

    def requestPlaybackStatus(self,_uart):
        "Request current wifi playback status"
        # PLA;
        # Returns {0,1}
        return _uart.requestCommand(self.AmpNumber, "PLA;","Low",0.1)

#     def setPlaybackStatus(self,playstate):
#         "Set Playback State"
#         # PLA;
#         # Returns {0,1}
#         self.PlayState = playstate

    def getPlaybackStatus(self):
        "Get Playback State"
        # PLA;
        # Returns {0,1}
        return self.PlayState

# ### STP Methods - Stop
#     def requestStop(self,_uart):
#         "Stop playing"
#         # STP;
#         #print("STP")
#         return _uart.requestCommand(self.AmpNumber, "STP;","High",0.1)

# ### NXT Methods - Next
#     def requestNext(self,_uart):
#         "Skip to next track"
#         # NXT;
#         #print("NXT")
#         return _uart.requestCommand(self.AmpNumber, "NXT;","High",0.1)

# ### PRE Methods - Previous
#     def requestPrevious(self,_uart):
#         "Jump to previous track"
#         # PRE;
#         return _uart.requestCommand(self.AmpNumber, "PRE;","High",0.1)

# ### POP Methods - PlayPause
#     def requestPlayPause(self,_uart):
#         "Play or Pause current track"
#         # POP;
#         print("POP")
#         return _uart.requestCommand(self.AmpNumber, "POP;","High",0.1)  

# ### TIT Methods - Title
#     # def pushTitle(self,_uart):
#     #     "Do nothing"
#     #     pass

#     def requestTitle(self,_uart):
#         "Request title infomation"
#         # TIT;
#         return _uart.requestCommand(self.AmpNumber, "TIT;","Low",0.1)

#     def setTitle(self,title):
#         "Set title"
#         self.Title = title

#     def getTitle(self):
#         "Get Title"
#         return self.Title

# ### ART Methods - Artist

#     # def pushArtist(self,_uart):
#     #     "Do nothing"
#     #     pass

#     def requestArtist(self,_uart):
#         "Request Artist infomation"
#         # ART;
#         # Returns <string>
#         return _uart.requestCommand(self.AmpNumber, "ART;","Low",0.1)

#     def setArtist(self,_artist):
#         "Set title"
#         # ART:<string>;
#         self.Title = _artist

#     def getArtist(self):
#         "Get Artist"
#         return self.Artist

# ### ALB Methods - Album
#     # def pushAlbum(self,_uart,_album):
#     #     "Do Nothing"
#     #     pass

#     def requestAlbum(self,_uart):
#         "Request Album infomation"
#         # ALB;
#         # print("ALB")
#         return _uart.requestCommand(self.AmpNumber, "ALB;","Low",0.1)

#     def setAlbum(self,_album):
#         "Set album"
#         self.Album = _album

#     def getAlbum(self):
#         "Get Artist"
#         return self.Album

# ### VND Methods - Feed
#     # def pushFeed(self,_uart,_album):
#     #     "Do Nothing"
#     #     pass

#     def requestFeed(self,_uart):
#         "Request Feed infomation"
#         # VND;
#         return _uart.requestCommand(self.AmpNumber, "VND;","Low",0.1)

#     def setFeed(self,feed):
#         self.Feed = feed

#     def getFeed(self):
#         "Get Feed"
#         return self.Feed

# ### ELP Methods - TrackPosition
#     def pushTrackPosition(self,_trackposition,_uart):
#         "Push new track position"
#         # EPS;
#         return _uart.requestCommand(self.AmpNumber, "ELP:" + str(_trackposition) + ";","High",0.1)

#     def requestTrackPosition(self,_uart):
#         "Request current Track Position"
#         # BAS: {-10..10};
#         return _uart.requestCommand(self.AmpNumber, "ELP;","Low",0.1)   

#     def setTrackPosition(self,_trackposition):
#         "Set Track position"
#         self.TrackPosition = _trackposition

#     def getTrackPosition(self):
#         "Get current Track Position"
#         return self.TrackPosition

# ### BTC Methods - Bluetoothstatus
#     # def pushBluetoothStatus(self,_uart):
#     #     "Do Nothing"
#     #     pass

#     def requestBluetoothStatus(self,_uart):
#         "Request current Track Position"
#         # BTC: {};
#         return _uart.requestCommand(self.AmpNumber, "BTC;","Low",0.1)   

#     def setBluetoothStatus(self,_bluetoothState):
#         "Set bluetooth connection status"
#         self.BluetoothState = _bluetoothState
        
#     def getBluetoothStatus(self):
#         "Confirm current bluetooth connection status"
#         # BTC;
#         # Returns {}
#         return self.BluetoothState
    
# ### CHN Methods - AudioChannel
    
#     def pushAudioChannel(self,_audiochannel,_uart):
#         "Push new audio channel status"
#         # CHN: {L/R/S};
#         return _uart.requestCommand(self.AmpNumber, "CHN:" + str(_audiochannel) + ";","High",0.1)
    
#     def requestAudioChannel(self,_uart):
#         "Request current audio channel status"
#         # CHN: 
#         # Returns {L/R/S};
#         return _uart.requestCommand(self.AmpNumber, "CHN;","Low",0.1)   

#     def setAudioChannel(self,_audiochannel):
#         "Set audio channel status"
#         # CHN: 
#         # Returns {L/R/S}; 
#         self.AudioChannel = _audiochannel

#     def getAudioChannel(self):
#         "Confirm current audio channel status"
#         # CHN;
#         # Returns {L/R/S}
#         return self.AudioChannel

# ### MRM Methods - MultiRoomStatus
    
#     def pushMultiRoomStatus(self,_multiroomstatus,_uart):
#         "Push new mutliroom status"
#         # MRM: {S,M,N};
#         # Slave / Master / None
#         return _uart.requestCommand(self.AmpNumber, "MRM:" + str(_multiroomstatus) + ";","High",0.1)
    
#     def requestMultiRoomStatus(self,_uart):
#         "Request current mutliroom status"
#         # MRM;
#         # Returns {S,M,N}
#         # Slave / Master / None
#         return _uart.requestCommand(self.AmpNumber, "MRM;","Low",0.1)   

#     def setMultiRoomStatus(self,_multiroomstatus):
#         "Set mutliroom status"
#         # MRM;
#         # Returns {S,M,N}
#         # Slave / Master / None
#         self.MultiRoomStatus = _multiroomstatus

#     def getMultiRoomStatus(self):
#         "Confirm current mutliroom status"
#         # MRM;
#         # Returns {S,M,N}
#         # Slave / Master / None
#         return self.MultiRoomStatus

# ### LED Methods - LED
#     def pushLED(self,_uart):
#         "Do Nothing"
#         pass

#     def requestLED(self,_uart):
#         "Request current LED"
#         # BTC: {};
#         return _uart.requestCommand(self.AmpNumber, "LED;","Low",0.1)  

#     def setLED(self,_led):
#         "Set LED status"
#         # LED: {0/1/T};
#         self.LED = _led   

#     def getLED(self):
#         "Confirm current LED status"
#         # LED;
#         # Returns {0,1}
#         return self.LED

# ### BEP Methods - BeepSound

#     def pushBeepSound(self,_beep,_uart):
#         "Push new Beep status"
#         # BEP: {0/1};
#         return _uart.requestCommand(self.AmpNumber, "BEP:" + str(_beep) + ";","High",0.1)
    
#     def requestBeepSound(self,_uart):
#         "Request current Beep status"
#         # BEP: {0/1};
#         return _uart.requestCommand(self.AmpNumber, "BEP;","Low",0.1)   

#     def setBeepSound(self,_beep):
#         "Set Beep status"
#         # BEP: {0/1};
#         self.Beep = _beep

#     def getBeepSound(self):
#         "Confirm current Beep status"
#         # BEP;
#         # Returns {0,1}
#         return self.Beep

# ### PST Methods - Preset
#     def pushPreset(self,_preset,_uart):
#         "Push new Preset "
#         # PST: {0..10};
#         return _uart.requestCommand(self.AmpNumber, "PST:" + str(_preset) + ";","High",0.1)
    
#     def requestPreset(self,_uart):
#         "Request current Preset"
#         # PST: {0..10};
#         return _uart.requestCommand(self.AmpNumber, "PST;","Low",0.1)   

#     def setPreset(self,_preset):
#         "Set Preset "
#         # PST: {0..10};
#         self.Preset = _preset

#     def getPreset(self):
#         "Confirm Preset"
#         # PST;
#         # Returns {0..10}
#         return self.Preset

# ### VBS Methods - VirtualBass
#     def pushVirtualBass(self,_virtualBass,_uart):
#         "Push new Virtual Bass "
#         # VBS: {0,1};
#         return _uart.requestCommand(self.AmpNumber, "VBS:" + str(_virtualBass) + ";","High",0.1)
    
#     def requestVirtualBass(self,_uart):
#         "Request current Virtual Bass"
#         # VBS;
#         # Returns {0,1}
#         return _uart.requestCommand(self.AmpNumber, "VBS;","Low",0.1)   
   
#     def setVirtualBass(self,_virtualBass):
#         "Set Virtual Bass status"
#         # VBS: {0/1};
#         self.VirtualBass = _virtualBass

#     def getVirtualBass(self):
#         "Confirm current Virtual Bass status"
#         # VBS;
#         # Returns {0,1}
#         return self.VirtualBass

# ### WRS Methods - WifiReset
#     def pushWifiReset(self,_wifireset,_uart):
#         "Push new Virtual Bass "
#         # WRS: {0,1};
#         return _uart.requestCommand(self.AmpNumber, "WRS:" + str(_wifireset) + ";","High",0.1)
    
#     # def requestWifiReset(self,_uart):
#     #     "Do nothing"
#     #     pass   
   
#     # def setWifiReset(self):
#     #     "Do nothing"
#     #     pass

#     # def getWifiReset(self,):
#     #     "Do nothing"
#     #     pass

# ### LPM Methods - LoopMode
#     def pushLoopMode(self,_loopmode,_uart):
#         "Push Loop mode status"
#         # LPM: {REPEATALL/REPEATONE/REPEATSHUFFLE/SHUFFLE/SEQUENCE};
#         return _uart.requestCommand(self.AmpNumber, "LPM:" + str(_loopmode) + ";","High",0.1)
    
#     def requestLoopMode(self,_uart):
#         "Request current Loop mode"
#         # LPM;
#         # Returns {REPEATALL/REPEATONE/REPEATSHUFFLE/SHUFFLE/SEQUENCE}
#         return _uart.requestCommand(self.AmpNumber, "LPM;","Low",0.1)   
   
#     def setLoopMode(self,_loopmode):
#         "Set Loop Mode"
#         # LPM: {REPEATALL/REPEATONE/REPEATSHUFFLE/SHUFFLE/SEQUENCE};
#         self.LoopMode = _loopmode

#     def getLoopMode(self):
#         "Confirm current Loop Mode"
#         # LPM;
#         # Returns {REPEATALL/REPEATONE/REPEATSHUFFLE/SHUFFLE/SEQUENCE}
#         return self.LoopMode

# ### NAM Methods - Name
#     def pushName(self,_name,_uart):
#         "Push Amp Name"
#         # NAM: <HEX string>;
#         # hexed string with UTF8 encoding
#         # print("NAM")
#         # print(ubinascii.unhexlify(name))
#         #self.Name = ubinascii.unhexlify(name)
#         return _uart.requestCommand(self.AmpNumber, "NAM:" + str(_name) + ";","High",0.1)
    
#     def requestName(self,_uart):
#         "Request current Amp Name"
#         # NAM;
#         # Returns <HEX string>
#         return _uart.requestCommand(self.AmpNumber, "NAM;","Low",0.1)   
   
#     def setName(self,_name):
#         "Set Amp Name"
#         # NAM: <string>;
#         self.Name = _name

#     def getName(self):
#         "Confirm Amp Name"
#         # NAM;
#         # Returns <string>
#         return self.Name

# ### ETH Methods - Ethernet
#     # def pushEthernet(self):
#     #     "Do nothing"
#     #     pass

#     def requestEthernet(self,_uart):
#         "Request current Ethernet status"
#         # ETH;
#         # Returns {0,1}
#         return _uart.requestCommand(self.AmpNumber, "ETH;","Low",0.1) 

#     def setEthernet(self,_ethernet):
#         "Set Ethernet status"
#         # ETH: {0,1};
#         self.Ethernet = _ethernet

#     def getEthernet(self):
#         "Get current Ethernet status"
#         # ETH;
#         # Returns {0,1}
#         return self.Ethernet

# ### WIF Methods - Wifi
#     # def pushWifi(self):
#     #     "Do nothing"
#     #     pass

#     def requestWifi(self,_uart):
#         "Request current Wifi status"
#         # WIF;
#         # Returns {0,1}
#         return _uart.requestCommand(self.AmpNumber, "WIF;","Low",0.1) 

#     def setWifi(self,_wifi):
#         "Set current Wifi status"
#         # WIF: {0,1};
#         self.Wifi = _wifi

#     def getWifi(self):
#         "Get current Wifi status"
#         # WIF;
#         # Returns {0,1}
#         return self.Wifi

# ### PMT Methods - VoicePrompt
#     def pushVoicePrompt(self,_voicePrompt,_uart):
#         "Push Voice Prompt status"
#         # PMT: {0,1};
#         return _uart.requestCommand(self.AmpNumber, "PMT:" + str(_voicePrompt) + ";","High",0.1)
    
#     def requestVoicePrompt(self,_uart):
#         "Confirm current Voice prompt status"
#         # PMT;
#         # Returns {0,1}
#         return _uart.requestCommand(self.AmpNumber, "PMT;","Low",0.1)   
   
#     def setVoicePrompt(self,_voicePrompt):
#         "Set Voice prompt status"
#         # PMT: {0,1};
#         self.VoicePrompt = _voicePrompt

#     def getVoicePrompt(self):
#         "Confirm current Voice prompt status"
#         # PMT;
#         # Returns {0,1}
#         return self.VoicePrompt

# ### PRG Methods - PreGain
#     def pushPreGain(self,_pregain,_uart):
#         "Push PreGain status"
#         # PRG: {0,1};
#         return _uart.requestCommand(self.AmpNumber, "PRG:" + str(_pregain) + ";","High",0.1)
    
#     def requestPreGain(self,_uart):
#         "Confirm current PreGain status"
#         # PRG;
#         # Returns {0,1}
#         return _uart.requestCommand(self.AmpNumber, "PRG;","Low",0.1)   
   
#     def setPreGain(self,_pregain):
#         "Set PreGain status"
#         # PRG: {0,1};
#         self.PreGain = _pregain

#     def getPreGain(self):
#         "Confirm current PreGain status"
#         # PRG;
#         # Returns {0,1}
#         return self.PreGain

# ### DLY Methods - SystemDelayTime
#     def pushSystemDelayTime(self,_systemdelaytime,_uart):
#         "Push System Delay Time status"
#         # DLY: {0,1};
#         return _uart.requestCommand(self.AmpNumber, "DLY:" + str(_systemdelaytime) + ";","High",0.1)
    
#     def requestSystemDelayTime(self,_uart):
#         "Confirm current System Delay Time status"
#         # DLY;
#         # Returns {0,1}
#         return _uart.requestCommand(self.AmpNumber, "DLY;","Low",0.1)   
   
#     def setSystemDelayTime(self,_systemdelaytime):
#         "Set System Delay Time status"
#         # DLY: {0,1};
#         self.SystemDelayTime = _systemdelaytime

#     def getSystemDelayTime(self):
#         "Confirm current System Delay Time status"
#         # DLY;
#         # Returns {0,1}
#         return self.SystemDelayTime

# ### MXV Methods - MaxVolume
#     def pushMaxVolume(self,_maxVolume,_uart):
#         "Push Max Volume"
#         # MXV: {0,1};
#         return _uart.requestCommand(self.AmpNumber, "MXV:" + str(_maxVolume) + ";","High",0.1)
    
#     def requestMaxVolume(self,_uart):
#         "Confirm current Max Volume"
#         # MXV;
#         # Returns {0,1}
#         return _uart.requestCommand(self.AmpNumber, "MXV;","Low",0.1)   
   
#     def setMaxVolume(self,_maxVolume):
#         "Set Max Volume"
#         # MXV: {0,1};
#         self.MaxVolume = _maxVolume

#     def getMaxVolume(self):
#         "Confirm current Max Volume"
#         # MXV;
#         # Returns {0,1}
#         return self.MaxVolume

# ### ASW Methods - AutoSwitch
#     def pushAutoSwitch(self,_autoswitch,_uart):
#         "Push AutoSwitch"
#         # ASW: {0,1};
#         # Reverts to previous source after playback stopped
#         return _uart.requestCommand(self.AmpNumber, "ASW:" + str(_autoswitch) + ";","High",0.1)
    
#     def requestAutoSwitch(self,_uart):
#         "Confirm current AutoSwitch"
#         # ASW;
#         # Returns {0,1}
#         return _uart.requestCommand(self.AmpNumber, "ASW;","Low",0.1)   
   
#     def setAutoSwitch(self,_autoswitch):
#         "Set AutoSwitch"
#         # ASW: {0,1};
#         self.AutoSwitch = _autoswitch

#     def getAutoSwitch(self):
#         "Confirm current AutoSwitch"
#         # ASW;
#         # Returns {0,1}
#         return self.AutoSwitch
   
# ### POM Methods - PowerOnSource
#     def pushPowerOnSource(self,_poweronsource,_uart):
#         "Push Set default source after power on"
#         # POM: {NET/USB/USBDAC/LINE-IN/LINE-IN2/BT/OPT/COAX/I2S/HDMI};
#         # Reverts to previous source after playback stopped
#         # Set NONE for last used
#         return _uart.requestCommand(self.AmpNumber, "POM:" + str(_poweronsource) + ";","High",0.1)
    
#     def requestPowerOnSource(self,_uart):
#         "Confirm current Power on Source"
#         # POM;
#         # Returns {NET/USB/USBDAC/LINE-IN/LINE-IN2/BT/OPT/COAX/I2S/HDMI}
#         return _uart.requestCommand(self.AmpNumber, "POM;","Low",0.1)   
   
#     def setPowerOnSource(self,_poweronsource):
#         "Set Power on Source"
#         # POM: {NET/USB/USBDAC/LINE-IN/LINE-IN2/BT/OPT/COAX/I2S/HDMI};
#         self.PowerOnSource = _poweronsource

#     def getPowerOnSource(self):
#         "Confirm current Power on Source"
#         # POM;
#         # Returns {NET/USB/USBDAC/LINE-IN/LINE-IN2/BT/OPT/COAX/I2S/HDMI}
#         return self.PowerOnSource

# ### ZON Methods - ZoneMessage

#     def pushZoneMessage(self,_zonemessage,_uart):
#         "Send message to different zone"
#         # ZON:[zone]:[msg];
#         return _uart.requestCommand(self.AmpNumber, "ZON:" + str(_zonemessage) + ";","High",0.1)
    
#     # def requestZoneMessage(self,_uart):
#     #     "Do nothing"
#     #     pass  
   
#     # def setZoneMessage(self,_poweronsource):
#     #     "Do nothing"
#     #     pass  

#     # def getZoneMessage(self):
#     #     "Do nothing"
#     #     pass  

# ### NET Methods - Network
#     # def pushNetwork(self,_uart):
#     #     "Do nothing"
#     #     pass  
    
#     # def requestNetwork(self,_uart):
#     #     "Do nothing"
#     #     pass  

#     def setNetwork(self,_network):
#         "Set network"
#         self.Network = _network

#     def getNetwork(self,):
#         "Return network"
#         return self.Network
    
# ### Upgrade Methods
#     # def pushUpgrading(self,_uart):
#     #     "Do nothing"
#     #     pass  
    
#     # def requestUpgrading(self,_uart):
#     #     "Do nothing"
#     #     pass  

#     def setUpgrading(self,_upgrading):
#         "Set upgrading status"
#         self.Upgrading = _upgrading

#     def getUpgrading(self,):
#         "Return upgrading status"
#         return self.Upgrading

### Print Methods
    def printAmp(self,ampNumber): #remove ampNumber var if not needed now
        print("----- Amp: " + self.Name + "  |  Amp#: " + str(self.AmpNumber) + "  |  Ver: " + str(self.Version) + "  |  Sys: " + str(self.SystemState) + " -------")
        print("Source: " + self.SelectedSource, end='  |  ')
        print("Available: " + str(self.AvailableSources), end='  |  ')
        print("Mute: " + str(self.Mute),end='  |  ')
        print("Volume: " + str(self.Volume),end='  |  ')
        print("MaxVolume: " + str(self.MaxVolume), end='  |  ')
        print("Treble: " + str(self.Treble),end='  |  ')
        print("Bass: " + str(self.Bass),end='  |  ')
        print("Virtual Bass: " + str(self.VirtualBass))
        print("PlayState: " + str(self.PlayState), end='  |  ')
        print("LED: " + str(self.LED), end='  |  ')
        print("Loopmode: " + str(self.LoopMode), end='  |  ')
        print("LED: " + str(self.LED), end='  |  ')
        print("Audiable:" + self.Audiable, end='  |  ')
        print("AudioChannel:" + self.AudioChannel, end='  |  ')
        print("Output Enabled:" + str(self.OutputEnabled))
        print("Beep:" + str(self.Beep))
        print("Upgrading:" + str(self.Upgrading), end='  |  ')
        print("Network:" + str(self.Network), end='  |  ')      # Maybe same as Ethernet
        print("Ethernet:" + str(self.Ethernet), end='  |  ')
        print("Internet:" + str(self.Internet), end='  |  ')    # Maybe same as WWW
        print("WWW:" + str(self.WWW), end='  |  ')
        print("MultiRoom Status:" + str(self.MultiRoomStatus))
        print("Voice Prompt:" + str(self.VoicePrompt), end='  |  ')
        print("System Delay Time:" + str(self.SystemDelayTime), end='  |  ')
        print("Auto Switch:" + str(self.AutoSwitch), end='  |  ')
        print("Power On Source:" + str(self.PowerOnSource), end='  |  ')
        print("Preset:" + str(self.Preset))
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
            print("Bad amp number")
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
            print(requestType + "#{" + response + "} ",end='')

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
            ###### System status 
            elif requestType == "SYS":
                MA.Amplifiers[ampNumber].setSystemState(response)
            ###### Amp Version 
            elif requestType == "VER":
                MA.Amplifiers[ampNumber].setVersion(response)
            ###### Amp Version 
            elif requestType == "WWW":
                MA.Amplifiers[ampNumber].setWWW(response)
            ###### Amp Version 
            elif requestType == "AUD":
                MA.Amplifiers[ampNumber].setOutputEnable(response)
            ###### Amp Version 
            elif requestType == "BAS":
                MA.Amplifiers[ampNumber].setBass(response)
            ###### Amp Version 
            elif requestType == "TRE":
                MA.Amplifiers[ampNumber].setTreble(response)
            ###### Amp Version 
            elif requestType == "BTC":
                MA.Amplifiers[ampNumber].setBluetoothStatus(response)
            ###### Amp Version 
            elif requestType == "CHN":
                MA.Amplifiers[ampNumber].setAudioChannel(response)
            ###### Amp Version 
            elif requestType == "MRM":
                MA.Amplifiers[ampNumber].setMultiRoomStatus(response)
            ###### Amp Version 
            elif requestType == "LED":
                MA.Amplifiers[ampNumber].setLED(response)
            ###### Amp Version 
            elif requestType == "BEP":
                MA.Amplifiers[ampNumber].setBeepSound(response)
            ###### Amp Version 
            elif requestType == "PST":
                MA.Amplifiers[ampNumber].setPreset(response)
            ###### Amp Version 
            elif requestType == "VBS":
                MA.Amplifiers[ampNumber].setVirtualBass(response)
            ###### Amp Version 
            elif requestType == "WRS":
                MA.Amplifiers[ampNumber].setWifiReset(response)
            ###### Amp Version 
            elif requestType == "LPM":
                MA.Amplifiers[ampNumber].setLoopMode(response)
            ###### Amp Version 
            elif requestType == "ETH":
                MA.Amplifiers[ampNumber].setEthernet(response)
            ###### Amp Version 
            elif requestType == "WIF":
                MA.Amplifiers[ampNumber].setWifi(response)
            ###### Amp Version 
            elif requestType == "PMT":
                MA.Amplifiers[ampNumber].setVoicePrompt(response)
            ###### Amp Version 
            elif requestType == "PRG":
                MA.Amplifiers[ampNumber].setPreGain(response)
            ###### Amp Version 
            elif requestType == "DLY":
                MA.Amplifiers[ampNumber].setSystemDelayTime(response)
            ###### Amp Version 
            elif requestType == "MXV":
                MA.Amplifiers[ampNumber].setMaxVolume(response)
            ###### Amp Version 
            elif requestType == "ASW":
                MA.Amplifiers[ampNumber].setAutoSwitch(response)
            ###### Amp Version 
            elif requestType == "POM":
                MA.Amplifiers[ampNumber].setPowerOnMode(response)
            ###### Amp Version 
            elif requestType == "ZON":
                MA.Amplifiers[ampNumber].setZoneMessage(response)
            ###### Amp Version 
            elif requestType == "NET":
                MA.Amplifiers[ampNumber].setNetwork(response)

        print()

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


