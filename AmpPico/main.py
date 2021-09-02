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
        # IR to receive commands
        # Visual to see if sound playing from each amp
        # Reset amp option
        # LED to show queue temperature

    # Questions?
        # What output can be seen from the Amp to determine sound actually being played

    # Answers
        # Primary thread recieves the interupt for the botton press, what happens if in the middle of a UART
        # Thought is for the UART to be on 2nd thread so conversations not interupted by button presses


#import utime
from utime import sleep_ms, sleep, ticks_us, ticks_ms, ticks_diff
from _thread import start_new_thread, allocate_lock
from machine import UART,Pin,SPI
from ure import match
from ubinascii import unhexlify
from math import floor
import json


### Configure Pins
# Pin numbers
Pin_LED_Green = 13          # Need to confirm if PWM capable
Pin_LED_Blue = 15           # Need to confirm if PWM capable
Pin_LED_RED = 14            # Need to confirm if PWM capable
Pin_BUT_Amp_Cycle = 16      #
Pin_BUT_Source_Cycle = 22   #
Pin_LED_Internal = 25       #
Pin_UART_Multi_Signal = 5  # Mulliplexer Signal     ---- Not needed for UART ????? Why
Pin_UART_Multi_S1 = 2      # Mutliplexer select Bit 1 
Pin_UART_Multi_S0 = 3     # Mutliplexer select Bit 0
Pin_UART_Multi_E = 4       # Mutliplexer Enable
Pin_AMP_UART_TX = 0
Pin_AMP_UART_RX = 1
Pin_DISPLAY_UART_TX = 8
Pin_DISPLAY_UART_RX = 9

Pico_AMP_UART = 0       # Which Pico coms channel will be used for talking with Amps
Pico_DISPLAY_UART = 1       # Which Pico coms channel will be used for talking with Amps

# LEDs
LED_Internal = Pin(Pin_LED_Internal, Pin.OUT)
LED_Green = Pin(Pin_LED_Green, Pin.OUT)
LED_Blue = Pin(Pin_LED_Blue, Pin.OUT)


# Buttons
# Button_Source_Cycle = Pin(Pin_BUT_Source_Cycle, Pin.IN, Pin.PULL_UP)
Button_Amp_Cycle = Pin(Pin_BUT_Amp_Cycle, Pin.IN, Pin.PULL_DOWN)

# Limits
Limit_UART_Max_Queue_Length = 5                                                             # Queue size for waiting UART requests
Limit_UART_Throttling_Queue_Length = 5                                                      # Throttling queue size if Low requests are impacting
Limit_UART_Multiplexer_Max_Channels = 3                                                    # How many channels does the multiplexer have
Limit_UART_Multiplexer_Max_Minutes_Looking = 10                                             # Max minutes to look for channels in available
Limit_LineIn_Multiplexer_Max_Channels = 4                                                  # Max chanels on the multiplexter for LineIn
Limit_LineOut_Multiplexer_Max_Channels = 0                                                  # Max chanels on the multiplexter for LineOut

# Flags
Flag_UART_Threading_Enabled = False                                                            # Can the UART queue messages
Flag_System_RedLine = False


# Common Functions
def tickNow():
    return ticks_us()

def secondsBetweenTick(firstTimestamp,secondTimestamp):
    return ticks_diff(firstTimestamp,secondTimestamp)

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
        self.AmpDisplayed = 0                                                                            # Which Amp is currently primary

        self.NextAmpSelectRequested = False                                                             # Button press requesting next amp to be selected

        ### Variable of available Amps - To Be DELETED once Naming is Dynamic
        #self.AmpsInstalled = ["Oasis","Pool","Italian"]   
        self.AmpsInstalled = ["Pool"]                                     

    def ampDiscovery(self,_cycleAttempts,_waitForResponse,_ampuart,):
        "Cycle through the multiplexer a specified number of times waiting for a responce"
        # What happens if the amp has changed it's name

        # Loop from begnning to max sending a status message to each Amp
        for cycles in range(_cycleAttempts):
            # Loop through all the Amps on the multiplexer
            for _ampNumber in range(Limit_UART_Multiplexer_Max_Channels):
                _ampuart.setLiveChannel(_ampNumber)
                _ampuart.setMultiplexState("on")
                # Clear buffer before looking to see if Amp alive
                _ampuart.flushUARTreceive()
                print("PINGING UART: " +str(_ampNumber) + ">",end='')
                # Can we find a version number for current Amp
                if _ampuart.transmitRequest("VER;",_waitForResponse):
                    print("Found amplifier: " + str(_ampNumber))
                    _ampuart.transmitRequest("LED:0;",0.1)

                # ## Only needed because pulling from predefined list NOT LOOKING DOWN THE UART
                # if len(self.AmpsInstalled) > _ampNumber:
                #     AmpName = self.AmpsInstalled[_ampNumber]
                    #print(str(ampNumber) + ":"+ AmpName)

                    if self.Amplifiers.get(_ampNumber):
                        print("Skipping: " + str(_ampNumber))
                    else:
                        print("Creating Amp: ", end='')
                        NewAmp = Amp()
                        self.Amplifiers[_ampNumber] = NewAmp 
                        #self.Amplifiers[_ampNumber].Name = AmpName
                        self.Amplifiers[_ampNumber].AvailableSources = self.List_Sources_Enabled
                        self.Amplifiers[_ampNumber].AmpNumber = _ampNumber
                        #print(self.Amplifiers[_ampNumber].Name)
                        print(_ampNumber)
                else:
                    print("x")

                # ## Only needed because pulling from predefined list NOT LOOKING DOWN THE UART
                # if len(self.AmpsInstalled) > _ampNumber:
                #     AmpName = self.AmpsInstalled[_ampNumber]
                #     #print(str(ampNumber) + ":"+ AmpName)

                #     if self.Amplifiers.get(_ampNumber):
                #         print("Skipping: ", end='')
                #         print(self.Amplifiers[_ampNumber].Name)
                #     else:
                #         print("Creating Amp: ", end='')
                #         NewAmp = Amp()
                #         self.Amplifiers[_ampNumber] = NewAmp 
                #         self.Amplifiers[_ampNumber].Name = AmpName
                #         self.Amplifiers[_ampNumber].AvailableSources = self.List_Sources_Enabled
                #         self.Amplifiers[_ampNumber].AmpNumber = _ampNumber
                #         print(self.Amplifiers[_ampNumber].Name)


                ###_ampuart.setMultiplexState("off")
                # No hardcoded Amp name found - REMOVE once dynamic
                #else:
                    #print(ampNumber, end='')

            # Validate if the name matches that in the multiplexer list
                # If the name is different, update the name
        if (len(self.Amplifiers) == 0):
            return None
        else:
            self.setAmpDisplayed(list(self.Amplifiers.keys())[0])
            return True

    def setAmpDisplayed(self,_ampNumber):
        "Change selected amp"
        self.AmpDisplayed = _ampNumber
        print("Display amp: " + str(_ampNumber))

    def getAmpDisplayed(self) -> int:
        "Return current selected amp"
        return self.AmpDisplayed

    def setNextAmpDisplayed(self):
        "Select next amp"
        # _ampCount = len(list(self.Amplifiers.keys()))
        # if _ampCount == 1:
        #     return
        _lastAmpNumberposition = 0
        _currentAmpDisplayposition = 0
        for _count, _ampNumber in enumerate(list(self.Amplifiers.keys())):
            print("Count: " + str(_count) + "  Amp number: " + str(_ampNumber))
            _lastAmpNumberposition = _count
            if self.getAmpDisplayed() == _ampNumber:
                _currentAmpDisplayposition = _count
        if _lastAmpNumberposition > _currentAmpDisplayposition:
            print(list(self.Amplifiers.keys())[_currentAmpDisplayposition+1])

        # elif self.getAmpDisplayed() < _ampCount:
        #     self.setAmpDisplayed(self.getAmpDisplayed() + 1)
        # else:
        #     self.setAmpDisplayed(0)

    def listAmps(self):
        print(len(self.Amplifiers))

    def refreshAmpStatus(self,ampNumber,_ampuart):
        "Gather status information on specific amplifier"
        # print(ampNumber)
        # self.getStatus(ampNumber,_ampuart)
        # self.getSource(ampNumber,_ampuart) 
        # self.getVolume(ampNumber,_ampuart) 
        #print(responseTimestamp)
        #####self.Amplifiers[ampNumber].requestAmpState(ampNumber,_ampuart)
        # self.Amplifiers[ampNumber].requestUART(_ampuart,"STA")
        # _ampStatusString = self.Amplifiers[ampNumber].readAttribute("STA")
        # # STA: {source,mute,volume,treble,bass,net,internet,playing,led,upgrading};
        # if _ampStatusString:
        #     print("STA attrib :" + _ampStatusString)
        #     self.Amplifiers[ampNumber].saveAttribute("SRC",_ampStatusString.split(",")[0])
        #     self.Amplifiers[ampNumber].saveAttribute("MUT",_ampStatusString.split(",")[1])
        #     self.Amplifiers[ampNumber].saveAttribute("VOL",_ampStatusString.split(",")[2])
        #     self.Amplifiers[ampNumber].saveAttribute("TRE",_ampStatusString.split(",")[3])
        #     self.Amplifiers[ampNumber].saveAttribute("BAS",_ampStatusString.split(",")[4])
        #     self.Amplifiers[ampNumber].saveAttribute("NET",_ampStatusString.split(",")[5])
        # Don't trust the general status to show correct play status
        #### self.Amplifiers[ampNumber].requestPlaybackStatus(_ampuart)

        # Send blank request - to look for UART in the buffer
        self.Amplifiers[ampNumber].requestUART(_ampuart,"")


        # Unknown Name
        if self.Amplifiers[ampNumber].readAttribute("NAM") == None:
            self.Amplifiers[ampNumber].requestUART(_ampuart,"NAM")

        # Missing song info
        if self.Amplifiers[ampNumber].readAttribute("TIT") == None:
             self.Amplifiers[ampNumber].requestUART(_ampuart,"TIT")
             self.Amplifiers[ampNumber].requestUART(_ampuart,"ART")
             self.Amplifiers[ampNumber].requestUART(_ampuart,"ALB")
             self.Amplifiers[ampNumber].requestUART(_ampuart,"VND")


        # Unknown Volume
        if self.Amplifiers[ampNumber].readAttribute("VOL") == None:
            self.Amplifiers[ampNumber].requestUART(_ampuart,"VOL")

        # Unknown Play state
        if self.Amplifiers[ampNumber].readAttribute("PLA") == None:
            self.Amplifiers[ampNumber].requestUART(_ampuart,"PLA")

        # Unknown Source
        if self.Amplifiers[ampNumber].readAttribute("SRC") == None:
            self.Amplifiers[ampNumber].requestUART(_ampuart,"SRC")

        # Position update if playing
        if self.Amplifiers[ampNumber].readAttribute("PLA") == "1":
            self.Amplifiers[ampNumber].requestUART(_ampuart,"ELP")

        # Unknown Feed
        if self.Amplifiers[ampNumber].readAttribute("VND") == None:
            self.Amplifiers[ampNumber].requestUART(_ampuart,"VND")

        # If we have a position but no track info eval("(" + str(_position) + ")")
        try:
            _position = eval("(" + str(self.Amplifiers[ampNumber].readAttribute("ELP")) + ")")
        except:
            _position = None



        _one_at_a_time = True
        if _one_at_a_time:
            # Unknown Wifi
            if self.Amplifiers[ampNumber].readAttribute("WIF") == None:
                self.Amplifiers[ampNumber].requestUART(_ampuart,"WIF")
                _one_at_a_time = False
        if _one_at_a_time:
            # Unknown Wifi
            if self.Amplifiers[ampNumber].readAttribute("ETH") == None:
                self.Amplifiers[ampNumber].requestUART(_ampuart,"ETH")
                _one_at_a_time = False
        if _one_at_a_time:        
            # Unknown Loopmode
            if self.Amplifiers[ampNumber].readAttribute("LPM") == None:
                self.Amplifiers[ampNumber].requestUART(_ampuart,"LPM")
                _one_at_a_time = False
        if _one_at_a_time:
            # Unknown Audio Channel
            if self.Amplifiers[ampNumber].readAttribute("CHN") == None:
                self.Amplifiers[ampNumber].requestUART(_ampuart,"CHN")
                _one_at_a_time = False
        if _one_at_a_time:
            # Unknown Bluetooth
            if self.Amplifiers[ampNumber].readAttribute("BTC") == None:
                self.Amplifiers[ampNumber].requestUART(_ampuart,"BTC")
                _one_at_a_time = False
        if _one_at_a_time:
            # Unknown Mute
            if self.Amplifiers[ampNumber].readAttribute("MUT") == None:
                self.Amplifiers[ampNumber].requestUART(_ampuart,"MUT")
                _one_at_a_time = False
        if _one_at_a_time:
            # Unknown LED
            if self.Amplifiers[ampNumber].readAttribute("LED") == None:
                self.Amplifiers[ampNumber].requestUART(_ampuart,"LED")
                _one_at_a_time = False
        if _one_at_a_time:
            # Unknown Treble
            if self.Amplifiers[ampNumber].readAttribute("TRE") == None:
                self.Amplifiers[ampNumber].requestUART(_ampuart,"TRE")
                _one_at_a_time = False
        if _one_at_a_time:
            # Unknown Bass
            if self.Amplifiers[ampNumber].readAttribute("BAS") == None:
                self.Amplifiers[ampNumber].requestUART(_ampuart,"BAS")
                _one_at_a_time = False
        if _one_at_a_time:
            # Unknown Vertual Bass
            if self.Amplifiers[ampNumber].readAttribute("VBS") == None:
                self.Amplifiers[ampNumber].requestUART(_ampuart,"VBS")
                _one_at_a_time = False
        if _one_at_a_time:
            # Unknown Multiroom Audio
            if self.Amplifiers[ampNumber].readAttribute("MRM") == None:
                self.Amplifiers[ampNumber].requestUART(_ampuart,"MRM")
                _one_at_a_time = False
        if _one_at_a_time:
            # Unknown Audioable
            if self.Amplifiers[ampNumber].readAttribute("AUD") == None:
                self.Amplifiers[ampNumber].requestUART(_ampuart,"AUD")
                _one_at_a_time = False
        if _one_at_a_time:
            # Unknown Version
            if self.Amplifiers[ampNumber].readAttribute("POM") == None:
                self.Amplifiers[ampNumber].requestUART(_ampuart,"POM")
                _one_at_a_time = False
        if _one_at_a_time:          
            # Unknown Beep Sound
            if self.Amplifiers[ampNumber].readAttribute("BEP") == None:
                self.Amplifiers[ampNumber].requestUART(_ampuart,"BEP")
                _one_at_a_time = False
        if _one_at_a_time:
            # Unknown Pregain
            if self.Amplifiers[ampNumber].readAttribute("PRG") == None:
                self.Amplifiers[ampNumber].requestUART(_ampuart,"PRG")
                _one_at_a_time = False
        if _one_at_a_time:
            # Unknown Max Volume
            if self.Amplifiers[ampNumber].readAttribute("MXV") == None:
                self.Amplifiers[ampNumber].requestUART(_ampuart,"MXV")
                _one_at_a_time = False
        if _one_at_a_time:
            # Unknown Version
            if self.Amplifiers[ampNumber].readAttribute("VER") == None:
                self.Amplifiers[ampNumber].requestUART(_ampuart,"VER")
                _one_at_a_time = False
        if _one_at_a_time:
            # Unknown Wifi
            if self.Amplifiers[ampNumber].readAttribute("NAM") == "":
                self.Amplifiers[ampNumber].requestUART(_ampuart,"NAM")
                _one_at_a_time = False
        # if _one_at_a_time:
        #     # Unknown Preset
        #     if self.Amplifiers[ampNumber].readAttribute("PST") == None:
        #         self.Amplifiers[ampNumber].requestUART(_ampuart,"PST")
        #         _one_at_a_time = False

        
        #print(".",end='')
        #self.Amplifiers[ampNumber].printAmp()

    def refreshAllAmpStatus(self,_ampuart):
        "Update all amplifier statuses"

        for ampNumber in list(self.Amplifiers.keys()):
            self.refreshAmpStatus(ampNumber,_ampuart)

# Amp status object
class Amp:
    "All the current status details about the Amp"

    def __init__(self) -> None:
        self.Attributes = {}                                    # Master Dictionary for all settings
        self.AmpNumber = -1
        self.AvailableSources = []
        # self.FlagAttributes = ["WWW","AUD","PLA","BEP","VBS","WRS","ETH","WIF","PMT","PRG","DLY","MVX"]
        # self.TrackStarted = tickNow()
        # BAS: {-10..10};
        # TRE: {-10..10};
        # PLA; {0,1}
        # TIT;
        # ART;
        # ALB;
        # VND;
        # EPS;
        # BTC: {};
        # MRM: {S,M,N};
        # LED: {0/1/T};
        # BEP: {0/1};
        # PST: {0..10};
        # VBS: {0,1};
        # WRS: {0,1};
        # LPM: {REPEATALL/REPEATONE/REPEATSHUFFLE/SHUFFLE/SEQUENCE};
        # ETH: {0,1};
        # WIF: {0,1};
        # PMT: {0,1};
        # PRG: {0,1};
        # DLY: {0,1};
        # MXV: {0,1};
        # POM: {NET/USB/USBDAC/LINE-IN/LINE-IN2/BT/OPT/COAX/I2S/HDMI};
        # ZON:[zone]:[msg];

    def pushUART(self,_ampuart,_key,_value):
        "Push value based on it's key"
        return _ampuart.requestCommand(self.AmpNumber, _key + ":" + str(_value) + ";","High",0.1)
        
    def requestUART(self,_ampuart,_key,wait=0.1):
        "Request value base on Key"
        return _ampuart.requestCommand(self.AmpNumber, _key + ";","Low",wait)
        
    def saveAttribute(self,_key,_value):
        #print("SAVE:" + _key + "='" + _value + "'", end=" ")
        # if _value in self.FlagAttributes:
        #     if _value == 1:
        #         self.Attributes[_key] = True
        #     else:
        #         self.Attributes[_key] = False
        # else:
        self.Attributes[_key] = _value
        # if _key == "EPL":
        #     self.TrackStarted = tickNow()
        #     print("TICK NOW" + str(self.TrackStarted))

        #print("Stored:=" + "'" + self.Attributes[_key] + "'")
    
    def readAttribute(self,_key):
       # print("Attributes: " + str(self.Attributes))
        if _key in self.Attributes.keys():

            if _key == "NAM":
                return unhexlify(self.Attributes[_key]).decode("ASCII")
            # print("Read>" + _key, end=' ')
            # _value = self.Attributes[_key]
            # print("Read:" + "'" + str(_value) + "'")
            return self.Attributes[_key]
        else:  
            return None
   
    def printAmp(self): #remove ampNumber var if not needed now
        print("----- Amp: " + str(self.readAttribute("NAM")) + "  |  Amp#: " + str(self.AmpNumber) + "  |  Ver: " + str(self.readAttribute("VER")) + "  |  Sys: " + str(self.readAttribute("SYS")) + " -------")
        print("Source: " + str(self.readAttribute("SRC")),end='  |  ')
        print("Available: " + str(self.AvailableSources), end='  |  ')
        print("Mute: " + str(self.readAttribute("MUT")),end='  |  ')
        print("Volume: " + str(self.readAttribute("VOL")),end='  |  ')
        print("MaxVolume: " + str(self.readAttribute("MXV")))
        print("Treble: " + str(self.readAttribute("TRE")),end='  |  ')
        print("Bass: " + str(self.readAttribute("BAS")),end='  |  ')
        print("Virtual Bass: " + str(self.readAttribute("VBS")),end='  |  ')
        print("PlayState: " + str(self.readAttribute("PLA")), end='  |  ')
        print("Track Position: " + str(self.readAttribute("ELP")))
        print("Feed: " + str(self.readAttribute("VND")), end='  |  ')
        print("Bluetooth: " + str(self.readAttribute("BTC")), end='  |  ')
        print("LED: " + str(self.readAttribute("LED")), end='  |  ')
        print("Loopmode: " + str(self.readAttribute("LPM")), end='  |  ')
        print("Audiable: " + str(self.readAttribute("AUD")), end='  |  ')
        print("MultiRoom: " + str(self.readAttribute("MRM")), end='  |  ')
        print("AudioChannel: " + str(self.readAttribute("CHN")), end='  |  ')
        print("Pregain: " + str(self.readAttribute("PRG")))
        print("Beep Sound: " + str(self.readAttribute("BEP")), end='  |  ')
        print("Network: " + str(self.readAttribute("NET")), end='  |  ')
        print("Ethernet: " + str(self.readAttribute("ETH")), end='  |  ')
        print("Wifi: " + str(self.readAttribute("WIF")), end='  |  ')
        print("WWW: " + str(self.readAttribute("WWW")))
        print("Voice Prompt: " + str(self.readAttribute("PMT")), end='  |  ')
        print("System Delay Time: " + str(self.readAttribute("DLY")), end='  |  ')
        print("Auto Switch: " + str(self.readAttribute("ASW")), end='  |  ')
        print("Power On Source: " + str(self.readAttribute("POM")), end='  |  ')
        print("Preset: " + str(self.readAttribute("PST")))
        print("Title: " + str(self.readAttribute("TIT")), end='  |  ')
        print("Artist: " + str(self.readAttribute("ALB")), end='  |  ')
        print("Album: " + str(self.readAttribute("ART")))
        # print("Upgrading:" + str(self.Upgrading), end='  |  ')
        print("----------------------------------------------")

# Button status
# class Button:
#     "Status of the buttons"

#     def __init__(self) -> None:
#         self.PlayPause = False
#         self.Stop = False
#         self.Forward = False
#         self.Reverse = False
#         self.Eject = False
#         self.Source = False

#     def pressedPlayPause(self):
#         "Interupt received for Play Pause"
#         print("PlayPause")

#     def pressedStop(self):
#         "Interupt received for Play Pause"
#         print("PlayPause")

#     def pressedForward(self):
#         "Interupt received for Play Pause"
#         print("PlayPause")
        
#     def pressedReverse(self):
#         "Interupt received for Play Pause"
#         print("PlayPause")
        
#     def pressedEject(self):
#         "Interupt received for Play Pause"
#         print("PlayPause")
        
#     def pressedSource(self):
#         "Interupt received for Play Pause"
#         print("PlayPause")

# LED control
# class LED:
#     "Control of LEDs, currently only Source"

#     def __init__(self) -> None:
#         self.CurrentColour = "Off"
#         self.NextColour = ""

#     def matchSourcetoColour(self):
#         "If needed match the LED colour to the source colour"


# Control a Multiplexer
class Multiplexer:
    "Generic multiplexer controls"

    def __init__(self, S0, S1, E, Max, signal):
        self.S0 = Pin(S0, Pin.OUT)
        self.S1 = Pin(S1, Pin.OUT)
        self.E = Pin(E, Pin.OUT)
        #self.signal = Pin(signal)          ## Not needed for UART
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
        "Redirect the multiplexer"

        if channel_id == self.MaxChannels: return False
        bits = self._channel_to_bits(channel_id)  
        self._switch_pins_with_bits(bits)  
        self.current_bits = bits
        self.LiveChannel = channel_id
        #print(self.LiveChannel)

    def getLiveChannel(self) -> int:
        " Return where the multiplexer is currently pointing"
        return self.LiveChannel

    def setMultiplexState(self,newstate):
        if newstate == "off":
            self.E.value(1)                       # toggle off
            self.state = False
        elif newstate == "on":
            self.E.value(0)                       # toggle on
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
        self.QueuedRequests = {}                                                    # Queries requests
        self.DisplayQueuedRequests = {}                                             # Queries requests
        self.ResponseBuffer = {}                                                    # Responses populated in this buffer
        self.BackPresure = False                                                    # Are High priority requests not making it onto the queue
        self.LastBackPresure = 0                                                    # When was back pressure last applied
        self.BackPresureRelease = 3                                                 # After how long to take of back presure
        self.BackPresureCount = 0                                                   # How many times has backpresure been applied
        self.BackPresureThreshold = 2                                               # Adjust soft limit
        self.LastBackPresureThreshold = 0                                           # When was the limit last adjusted

        
        self.ampuart = UART(Pico_AMP_UART, baudrate=115200, bits=8, parity=None, stop=1, tx=Pin(Pin_AMP_UART_TX), rx=Pin(Pin_AMP_UART_RX))
        self.displayuart = UART(Pico_DISPLAY_UART, baudrate=115200, bits=8, parity=None, stop=1, tx=Pin(Pin_DISPLAY_UART_TX), rx=Pin(Pin_DISPLAY_UART_RX))

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
                self.setMultiplexState("off")
                self.setLiveChannel(self.getRequestAmp(request))
                self.setMultiplexState("on")
                # Send message
                self.ResponseBuffer[request]=self.transmitRequest(self.getRequestMessage(request),self.getResponseWait(request))
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
        lastProcessed = ticks_ms()

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
                        self.ResponseBuffer[request]=self.transmitRequest(self.getRequestMessage(request),1)
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
        # print("{" + str(self.ampuart.read()),end='}')
        self.ampuart.write(message)
        sleep(wait)
        # read line into buffer
        _response = self.ampuart.read()
        #print("Receive-A:" + str(_response))
        return str(_response)[2:][:-6]

    def flushUARTreceive(self):
        self.ampuart.read()

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
                    
                    #Actually push the request to the queue
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
            m = match('[A-Z]',self.ResponseBuffer[request][i])
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

            #screen out if the amp sends junk
            if bool(match('^[A-Z][A-Z][A-Z]',requestType)):
                
                if requestType == "NAM":
                    _display_ampname = unhexlify(response).decode("ASCII")
                    print("Received-A:> " + requestType + ":" + _display_ampname + "; ",end='')
                    _displaypush = requestType + ":" + _display_ampname + ";"
                else:
                    print("Received-A:> " + requestType + ":" + response + "; ",end='')
                    _displaypush = requestType + ":" + response + ";"


                if str(MA.Amplifiers[ampNumber].readAttribute(requestType)) != response:
                    self.pushToUARTDisplay(_displaypush)
                    #print("DISPLAY>" + _displaypush)
                    MA.Amplifiers[ampNumber].saveAttribute(requestType,response)
                else:
                    print()
                    #print("Already have:> " + str(requestType) + ":" + str(MA.Amplifiers[ampNumber].readAttribute(requestType)))

    def pushToUARTDisplay(self,message):
        "Push attribute to display"
        print("Write-D:> " + str(message))
        LED_Internal.high()
        self.displayuart.write(message)
        LED_Internal.low()

    def pullFromUARTDisplay(self):
        "Push attribute to display"
        _request = self.displayuart.read()
        #print("Receive-D<" + str(_request)[:2][:-1])
        if _request is None:
            return None
        else:
            return str(_request)[2:][:-2]

    def answerUARTDisplayRequest(self):
        _request = self.pullFromUARTDisplay()
        #print("Receive-D<" + str(_request))
        if not None and len(str(_request)) == 3:
            LED_Internal.high()
            try:
                _response = MA.Amplifiers[MA.getAmpDisplayed()].readAttribute(_request)
            except:
                print("Exception: getAmpDisplayed / readAttribute")
                _response = None

            LED_Internal.low()
        
            # When the amp first starts up, it doesn't have a title, and returns None, this is passed as a string.
            if _request == "TIT" and _response is None:
                _displaypush = str(_request) + ":;"
            else:
                _displaypush = str(_request) + ":" + str(_response) + ";"

            # When the amp first starts up, it doesn't have a title, and returns None, this is passed as a string.
            if _request == "NAM" and _response is None:
                _displaypush = str(_request) + ":;"
            else:
                _displaypush = str(_request) + ":" + str(_response) + ";"

            print("Read-D:> " + _displaypush)
            self.pushToUARTDisplay(_displaypush)
        #else:
            #print("x",end='')
            #print(str(_request)[:2][:-1])

### Function to detect button press
# Interupt if any button depressed (VNR,Eject,Stop,Play/Pause/Forward/Rewind)
def Button_Handler(pin):
    print(pin)
    MA.NextAmpSelectRequested = True
    # if pin == Pin_Source_Cycle:
    #     print("Source")
    # elif pin == Pin_Amp_Cycle:
    #     print("Amp")
    # else:
    #     print("?")


### Configure button interupts

# print("Configuring button interupts...", end= '')
# Button_Source_Cycle.irq(trigger=Pin.IRQ_RISING, handler=Button_Handler)
# print("source", end = '')
Button_Amp_Cycle.irq(trigger=Pin.IRQ_RISING, handler=Button_Handler)
# print(",amp", end = '')
# print(" done")
# print()

### Function to detect IR request


### Function to read if there's input from the output of each amp

### Function to set LineIn destination Amp


###### Begin Main ######

print("STARTING")

# Initiate Primary Object
MA = MultiAmp()

# Initiate UART
UART_Com = UART_Communication()

# Loop until at least 1 amp is found
Found_Any = None

while Found_Any == None:
    Found_Any = MA.ampDiscovery(1,1,UART_Com)


###### Spawning Second Thread (or not) ######

if Flag_UART_Threading_Enabled == True:
    print("SPAWN")
    start_new_thread(UART_Com.THREADsendNextCommandFromQueue, ())
    baton = allocate_lock()

MA.refreshAllAmpStatus(UART_Com)


lastPrune = tickNow()
lastParse = tickNow()
lastProcessed = tickNow()

lastQueuePrint = tickNow()
lastAutoGenerateLow = tickNow()
lastCheckAllStatus = tickNow()
lastAmpScan = tickNow()
lastButtonFlagChecks = tickNow()

lastAmpPrint = tickNow()

lastDisplayUARTCheck = tickNow()


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

    if secondsSinceTick(lastCheckAllStatus) > 1:
        lastCheckAllStatus = tickNow()  
        MA.refreshAllAmpStatus(UART_Com) 

    if secondsSinceTick(lastProcessed) > 0.01 and Flag_UART_Threading_Enabled == False:
        lastProcessed = tickNow()
        UART_Com.sendNextCommandFromQueue()

#Print details about all amps
    if secondsSinceTick(lastAmpPrint) > 10:
        lastAmpPrint = tickNow()
        print(str(len(MA.Amplifiers)) + " amplifier monitored and " + str(MA.getAmpDisplayed()) + " currently selected")
        for ampNumber in list(MA.Amplifiers.keys()):
            MA.Amplifiers[ampNumber].printAmp()


    if secondsSinceTick(lastDisplayUARTCheck) > 0.25:
        lastDisplayUARTCheck = tickNow()
        UART_Com.answerUARTDisplayRequest()

    if secondsSinceTick(lastAmpScan) > 30:
        lastAmpScan = tickNow()
        MA.ampDiscovery(1,1,UART_Com)

    if secondsSinceTick(lastButtonFlagChecks) > 1:
        lastButtonFlagChecks = tickNow()
        if MA.NextAmpSelectRequested == True:
            MA.setNextAmpDisplayed()
            MA.NextAmpSelectRequested = False
            print("IPNG") 
