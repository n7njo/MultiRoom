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


#import utime
from utime import sleep_ms, sleep, ticks_us, ticks_ms, ticks_diff
#import _thread
from _thread import start_new_thread, allocate_lock
from machine import UART,Pin,SPI
#import ure
from ure import match
#import ubinascii
from ubinascii import unhexlify
#import time
import framebuf
#from framebuf import FrameBuffer, framebuf
from math import floor


### Configure Pins
# Pin numbers
Pin_LED_Green = 13          # Need to confirm if PWM capable
Pin_LED_Blue = 15           # Need to confirm if PWM capable
Pin_LED_RED = 14            # Need to confirm if PWM capable
Pin_BUT_Amp_Cycle = 21      #
Pin_BUT_Source_Cycle = 22   #
Pin_LED_Internal = 25       #
Pin_UART_Multi_S0 = 19      # Mutliplexer select Bit 0
Pin_UART_Multi_S1 = 18      # Mutliplexer select Bit 1 
Pin_UART_Multi_E = 20       # Mutliplexer Enable
Pin_UART_Multi_Signal = 18  # Mulliplexer Signal     ---- Not needed for UART
Pin_UART_TX = 16
Pin_UART_RX = 17

Pin_SPI_DC = 5
Pin_SPI_CS = 1              # SPI CS
Pin_SPI_Res = 4
Pin_SPI_MOSI = 3            # SPI TX
Pin_SPI_MISO = 0            # SPI RX
Pin_SPI_SCLK = 2            # SPI Clock

Pico_Channel_UART = 0       # Which Pico coms channel will be used


# LEDs
LED_Internal = Pin(Pin_LED_Internal, Pin.OUT)
LED_Green = Pin(Pin_LED_Green, Pin.OUT)
LED_Blue = Pin(Pin_LED_Blue, Pin.OUT)


# Buttons
# Button_Source_Cycle = Pin(Pin_BUT_Source_Cycle, Pin.IN, Pin.PULL_UP)
# Button_Amp_Cycle = Pin(Pin_BUT_Amp_Cycle, Pin.IN, Pin.PULL_UP)

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
        self.AmpSelected = 0                                                                            # Which Amp is currently primary
        ### Variable of available Amps - To Be DELETED once Naming is Dynamic
        #self.AmpsInstalled = ["Oasis","Pool","Italian"]   
        self.AmpsInstalled = ["Pool"]                                     

    def ampDiscovery(self,_cycleAttempts,_waitForResponse,_uart,_oled):
        "Cycle through the multiplexer a specified number of times waiting for a responce"
        # What happens if the amp has changed it's name

        # Loop from begnning to max sending a status message to each Amp
        for cycles in range(_cycleAttempts):
            # Loop through all the Amps on the multiplexer
            for _ampNumber in range(Limit_UART_Multiplexer_Max_Channels):
                _uart.setLiveChannel(_ampNumber)
                _uart.setMultiplexState("on")
                print("PINGING UART: " +str(_ampNumber) + ">",end='')
                # Can we find a version number for current Amp
                if _uart.transmitRequest("VER;",_waitForResponse):
                    print("Found")
                    _oled.ImportantMessage("Found amplifier: " + str(_ampNumber))
                    _uart.transmitRequest("LED:0;",0.1)

                ## Only needed because pulling from predefined list NOT LOOKING DOWN THE UART
                if len(self.AmpsInstalled) > _ampNumber:
                    AmpName = self.AmpsInstalled[_ampNumber]
                    #print(str(ampNumber) + ":"+ AmpName)

                    if self.Amplifiers.get(_ampNumber):
                        print("Skipping: ", end='')
                        print(self.Amplifiers[_ampNumber].Name)
                    else:
                        print("Creating Amp: ", end='')
                        NewAmp = Amp()
                        self.Amplifiers[_ampNumber] = NewAmp 
                        self.Amplifiers[_ampNumber].Name = AmpName
                        self.Amplifiers[_ampNumber].AvailableSources = self.List_Sources_Enabled
                        self.Amplifiers[_ampNumber].AmpNumber = _ampNumber
                        print(self.Amplifiers[_ampNumber].Name)
                        _oled.ImportantMessage("Initialized: " + self.Amplifiers[_ampNumber].Name)
                _uart.setMultiplexState("off")
                # No hardcoded Amp name found - REMOVE once dynamic
                #else:
                    #print(ampNumber, end='')

            # Validate if the name matches that in the multiplexer list
                # If the name is different, update the name

    def setAmpSelected(self,ampNumber):
        "Change selected amp"
        self.AmpSelected = ampNumber

    def getAmpSelected(self) -> int:
        "Return current selected amp"
        return self.AmpSelected

    def refreshAmpStatus(self,ampNumber,_uart):
        "Gather status information on specific amplifier"
        # print(ampNumber)
        # self.getStatus(ampNumber,_uart)
        # self.getSource(ampNumber,_uart) 
        # self.getVolume(ampNumber,_uart) 
        #print(responseTimestamp)
        #####self.Amplifiers[ampNumber].requestAmpState(ampNumber,_uart)
        # self.Amplifiers[ampNumber].requestUART(_uart,"STA")
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
        #### self.Amplifiers[ampNumber].requestPlaybackStatus(_uart)

        # Send blank request - to look for UART in the buffer
        self.Amplifiers[ampNumber].requestUART(_uart,"")


        # Unknown Name
        if self.Amplifiers[ampNumber].readAttribute("NAM") == None:
            self.Amplifiers[ampNumber].requestUART(_uart,"NAM")

        # Missing song info
        if self.Amplifiers[ampNumber].readAttribute("TIT") == None:
             self.Amplifiers[ampNumber].requestUART(_uart,"TIT")
             self.Amplifiers[ampNumber].requestUART(_uart,"ART")
             self.Amplifiers[ampNumber].requestUART(_uart,"ALB")
             self.Amplifiers[ampNumber].requestUART(_uart,"VND")


        # Unknown Volume
        if self.Amplifiers[ampNumber].readAttribute("VOL") == None:
            self.Amplifiers[ampNumber].requestUART(_uart,"VOL")

        # Unknown Play state
        if self.Amplifiers[ampNumber].readAttribute("PLA") == None:
            self.Amplifiers[ampNumber].requestUART(_uart,"PLA")

        # Unknown Source
        if self.Amplifiers[ampNumber].readAttribute("SRC") == None:
            self.Amplifiers[ampNumber].requestUART(_uart,"SRC")

        # Position update if playing
        if self.Amplifiers[ampNumber].readAttribute("PLA") == "1":
            self.Amplifiers[ampNumber].requestUART(_uart,"ELP")

        _one_at_a_time = True
        if _one_at_a_time:
            # Unknown Wifi
            if self.Amplifiers[ampNumber].readAttribute("WIF") == None:
                self.Amplifiers[ampNumber].requestUART(_uart,"WIF")
                _one_at_a_time = False
        if _one_at_a_time:        
            # Unknown Loopmode
            if self.Amplifiers[ampNumber].readAttribute("LPM") == None:
                self.Amplifiers[ampNumber].requestUART(_uart,"LPM")
                _one_at_a_time = False
        if _one_at_a_time:
            # Unknown Audio Channel
            if self.Amplifiers[ampNumber].readAttribute("CHN") == None:
                self.Amplifiers[ampNumber].requestUART(_uart,"CHN")
                _one_at_a_time = False
        if _one_at_a_time:
            # Unknown Bluetooth
            if self.Amplifiers[ampNumber].readAttribute("BTC") == None:
                self.Amplifiers[ampNumber].requestUART(_uart,"BTC")
                _one_at_a_time = False
        if _one_at_a_time:
            # Unknown Mute
            if self.Amplifiers[ampNumber].readAttribute("MUT") == None:
                self.Amplifiers[ampNumber].requestUART(_uart,"MUT")
                _one_at_a_time = False
        if _one_at_a_time:
            # Unknown LED
            if self.Amplifiers[ampNumber].readAttribute("LED") == None:
                self.Amplifiers[ampNumber].requestUART(_uart,"LED")
                _one_at_a_time = False
        if _one_at_a_time:
            # Unknown Treble
            if self.Amplifiers[ampNumber].readAttribute("TRE") == None:
                self.Amplifiers[ampNumber].requestUART(_uart,"TRE")
                _one_at_a_time = False
        if _one_at_a_time:
            # Unknown Bass
            if self.Amplifiers[ampNumber].readAttribute("BAS") == None:
                self.Amplifiers[ampNumber].requestUART(_uart,"BAS")
                _one_at_a_time = False
        if _one_at_a_time:
            # Unknown Vertual Bass
            if self.Amplifiers[ampNumber].readAttribute("VBS") == None:
                self.Amplifiers[ampNumber].requestUART(_uart,"VBS")
                _one_at_a_time = False
        if _one_at_a_time:
            # Unknown Multiroom Audio
            if self.Amplifiers[ampNumber].readAttribute("MRM") == None:
                self.Amplifiers[ampNumber].requestUART(_uart,"MRM")
                _one_at_a_time = False
        if _one_at_a_time:
            # Unknown Audioable
            if self.Amplifiers[ampNumber].readAttribute("AUD") == None:
                self.Amplifiers[ampNumber].requestUART(_uart,"AUD")
                _one_at_a_time = False
        if _one_at_a_time:
            # Unknown Version
            if self.Amplifiers[ampNumber].readAttribute("POM") == None:
                self.Amplifiers[ampNumber].requestUART(_uart,"POM")
                _one_at_a_time = False
        if _one_at_a_time:          
            # Unknown Beep Sound
            if self.Amplifiers[ampNumber].readAttribute("BEP") == None:
                self.Amplifiers[ampNumber].requestUART(_uart,"BEP")
                _one_at_a_time = False
        if _one_at_a_time:
            # Unknown Pregain
            if self.Amplifiers[ampNumber].readAttribute("PRG") == None:
                self.Amplifiers[ampNumber].requestUART(_uart,"PRG")
                _one_at_a_time = False
        if _one_at_a_time:
            # Unknown Max Volume
            if self.Amplifiers[ampNumber].readAttribute("MXV") == None:
                self.Amplifiers[ampNumber].requestUART(_uart,"MXV")
                _one_at_a_time = False
        if _one_at_a_time:
            # Unknown Version
            if self.Amplifiers[ampNumber].readAttribute("VER") == None:
                self.Amplifiers[ampNumber].requestUART(_uart,"VER")
                _one_at_a_time = False
        # if _one_at_a_time:
        #     # Unknown Preset
        #     if self.Amplifiers[ampNumber].readAttribute("PST") == None:
        #         self.Amplifiers[ampNumber].requestUART(_uart,"PST")
        #         _one_at_a_time = False

        
        print(".",end='')
        #self.Amplifiers[ampNumber].printAmp()

    def refreshAllAmpStatus(self,_uart):
        "Update all amplifier statuses"

        for ampNumber in list(self.Amplifiers.keys()):
            self.refreshAmpStatus(ampNumber,_uart)

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

    def pushUART(self,_uart,_key,_value):
        "Push value based on it's key"
        return _uart.requestCommand(self.AmpNumber, _key + ":" + str(_value) + ";","High",0.1)
        
    def requestUART(self,_uart,_key,wait=0.1):
        "Request value base on Key"
        return _uart.requestCommand(self.AmpNumber, _key + ";","Low",wait)
        
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

# OLED Display

class SSD1322:
    def __init__(self, width=256, height=64):
        self.width = width
        self.height = height
        self.buffer = bytearray(self.width * self.height //2)
        self.framebuf = framebuf.FrameBuffer(self.buffer, self.width, self.height, framebuf.GS4_HMSB)

        # self.poweron()
        sleep_ms(5)
        self.init_display()

    def init_display(self):
        self.write_cmd(0xFD)  # Set Command Lock (MCU protection status)
        self.write_data(0x12)  # 0x12 = Unlock Basic Commands; 0x16 = lock

        self.write_cmd(0xA4)  # Set Display Mode = OFF

        self.write_cmd(0xB3)  # Set Front Clock Divider / Oscillator Frequency
        self.write_data(0x91)  # 0x91 = 80FPS; 0xD0 = default / 1100b 

        self.write_cmd(0xCA)  # Set MUX Ratio
        self.write_data(0x3F)  # 0x3F = 63d = 64MUX (1/64 duty cycle)

        self.write_cmd(0xA2)  # Set Display Offset
        self.write_data(0x00)  # 0x00 = (default)

        self.write_cmd(0xA1)  # Set Display Start Line
        self.write_data(0x00)  # 0x00 = register 00h

        self.write_cmd(0xA0)  # Set Re-map and Dual COM Line mode
        self.write_data(0x14)  # 0x14 = Default except Enable Nibble Re-map, Scan from COM[N-1] to COM0, where N is the Multiplex ratio
        self.write_data(0x11)  # 0x11 = Enable Dual COM mode (MUX <= 63)

        self.write_cmd(0xB5)  # Set GPIO
        self.write_data(0x00)  # 0x00 = {GPIO0, GPIO1 = HiZ (Input Disabled)}

        self.write_cmd(0xAB)  # Function Selection
        self.write_data(0x01)  # 0x01 = Enable internal VDD regulator (default)

        self.write_cmd(0xB4)  # Display Enhancement A
        self.write_data(0xA0)  # 0xA0 = Enable external VSL; 0xA2 = internal VSL
        self.write_data(0xB5)  # 0xB5 = Normal (default); 0xFD = 11111101b = Enhanced low GS display quality

        self.write_cmd(0xC1)  # Set Contrast Current
        self.write_data(0x7F)  # 0x7F = (default)

        self.write_cmd(0xC7)  # Master Contrast Current Control
        self.write_data(0x0F)  # 0x0F = (default)

        self.write_cmd(0xB8)  # Select Custom Gray Scale table (GS0 = 0)
        self.write_data(0x00)  # GS1
        self.write_data(0x02)  # GS2
        self.write_data(0x08)  # GS3
        self.write_data(0x0d)  # GS4
        self.write_data(0x14)  # GS5
        self.write_data(0x1a)  # GS6
        self.write_data(0x20)  # GS7
        self.write_data(0x28)  # GS8
        self.write_data(0x30)  # GS9
        self.write_data(0x38)  # GS10
        self.write_data(0x40)  # GS11
        self.write_data(0x48)  # GS12
        self.write_data(0x50)  # GS13
        self.write_data(0x60)  # GS14
        self.write_data(0x70)  # GS15
        self.write_data(0x00)  # Enable Custom Gray Scale table

        self.write_cmd(0xB1)  # Set Phase Length
        self.write_data(0xE2)  # 0xE2 = Phase 1 period (reset phase length) = 5 DCLKs,
                               # Phase 2 period (first pre-charge phase length) = 14 DCLKs
        self.write_cmd(0xD1)  # Display Enhancement B
        self.write_data(0xA2)  # 0xA2 = Normal (default); 0x82 = reserved
        self.write_data(0x20)  # 0x20 = as-is

        self.write_cmd(0xBB)  # Set Pre-charge voltage
        self.write_data(0x1F)  # 0x17 = default; 0x1F = 0.60*Vcc (spec example)

        self.write_cmd(0xB6)  # Set Second Precharge Period
        self.write_data(0x08)  # 0x08 = 8 dclks (default)

        self.write_cmd(0xBE)  # Set VCOMH
        self.write_data(0x07)  # 0x04 = 0.80*Vcc (default); 0x07 = 0.86*Vcc (spec example)

        self.write_cmd(0xA6)  # Set Display Mode = Normal Display
        self.write_cmd(0xA9)  # Exit Partial Display
        self.write_cmd(0xAF)  # Set Sleep mode OFF (Display ON)
        
        self.fill(0)
        self.write_data(self.buffer)

    def poweroff(self):
        self.write_cmd(0xAB)
        self.write_data(0x00) # Disable internal VDD regulator, to save power
        self.write_cmd(0xAE)

    def poweron(self):
        self.write_cmd(0xAB)
        self.write_data(0x01) # Enable internal VDD regulator
        self.write_cmd(0xAF)

    def contrast(self, contrast):
        self.write_cmd(0x81)
        self.write_data(0x81) # 0-255

    def rotate(self, rotate):
        self.write_cmd(0xA0)
        self.write_data(0x06 if rotate else 0x14)
        self.write_data(0x11)

    def invert(self, invert):
        self.write_cmd(0xA4 | (invert & 1) << 1 | (invert & 1)) # 0xA4=Normal, 0xA7=Inverted

    def show(self):
        offset=(480-self.width)//2
        col_start=offset//4
        col_end=col_start+self.width//4-1
        self.write_cmd(0x15)
        self.write_data(col_start)
        self.write_data(col_end)
        self.write_cmd(0x75)
        self.write_data(0)
        self.write_data(self.height-1)
        self.write_cmd(0x5c)
        self.write_data(self.buffer)

    def fill(self, col):
        self.framebuf.fill(col)

    def pixel(self, x, y, col):
        self.framebuf.pixel(x, y, col)

    def pp(self,x,y,col):
        self.buffer[self.width//2*y+x//2]=0xff if col else 0

    def line(self, x1, y1, x2, y2, col):
        self.framebuf.line(x1, y1, x2, y2, col)

    def scroll(self, dx, dy):
        self.framebuf.scroll(dx, dy)
        # software scroll

    def text(self, string, x, y, col=15):
        self.framebuf.text(string, x, y, col)

    def write_cmd(self):
        raise NotImplementedError

    def write_data(self):
        raise NotImplementedError

class SSD1322_SPI(SSD1322):
    def __init__(self, width, height, spi, dc,cs,res):
        self.spi = spi
        self.dc=dc
        self.cs=cs
        self.res=res

        self.res(1)
        sleep_ms(1)
        self.res(0)
        sleep_ms(10)
        self.res(1)

        super().__init__(width, height)
        sleep_ms(5)

    def write_cmd( self, aCommand ) :
        '''Write given command to the device.'''
        self.dc(0)
        self.cs(0)
        self.spi.write(bytearray([aCommand]))
        self.cs(1)

    #@micropython.native
    def write_data( self, aData ) :
        '''Write given data to the device.  This may be
           either a single int or a bytearray of values.'''
        self.dc(1)
        self.cs(0)
        if type(aData)==bytes or type(aData)==bytearray:
            self.spi.write(aData)
        else:
            self.spi.write(bytearray([aData]))
        self.cs(1)

class Display(SSD1322_SPI):
    "Control of Display"

    def __init__(self):
        spi = SPI(0, baudrate=16000000,polarity=0, phase=0, sck=Pin(Pin_SPI_SCLK), mosi=Pin(Pin_SPI_MOSI), miso=Pin(Pin_SPI_MISO))
        dc=Pin(Pin_SPI_DC,Pin.OUT)
        cs=Pin(Pin_SPI_CS,Pin.OUT)
        res=Pin(Pin_SPI_Res,Pin.OUT)
        super().__init__(256,64,spi,dc,cs,res)

    def ImportantMessage(self, _message):
        self.fill(0)
        self.text(_message,20,30,0xff)
        self.show()

    def ProgressBar(self,_x_start,_y_start,_x_width,_y_height,_orientation,_direction,_current_percent,_box_bright,_line_bright):
        "Draw progress bar with percent completed"
        # Position box
        self.DrawBox(_x_start,_y_start,_x_width,_y_height,_box_bright)

        if _orientation == "Horizontal":
            # Calculate horizontal position
            if _direction == "Right":
                _current_x_position = _x_start + int(_x_width *_current_percent)            
            else:
                _current_x_position = (_x_start + _x_width) - int(_x_width * _current_percent)

            # Position Line
            self.line(_current_x_position,_y_start-1,_current_x_position,_y_start+_y_height+1,_line_bright)

        elif _orientation == "Vertical":
            # Calculate vertical position
            if _direction == "Up":
                _current_y_position = _y_start+ _y_height - int(_y_height * _current_percent)
            else:
                _current_y_position = _y_start + int(_y_height * _current_percent)

            # Position Line
            self.line(_x_start-1,_current_y_position,_x_start+_x_width+1,_current_y_position,_line_bright)

    def DrawPlay(self,_x_start,_y_start,_x_width,_y_height,_symbol_bright):
        "Draw a hollow equalatral triangle"
        # Top Left
        self.line(_x_start,_y_start,_x_start+_x_width,_y_start+int(_y_height/2),_symbol_bright)
        self.line(_x_start+_x_width,_y_start+int(_y_height/2),_x_start,_y_start+_y_height,_symbol_bright)
        self.line(_x_start,_y_start+_y_height,_x_start,_y_start,_symbol_bright)

    def DrawBox(self,_x_start,_y_start,_x_width,_y_height,_brightness):
        "Draw hollow box"
        # Top Line
        self.line(_x_start,_y_start,_x_start+_x_width,_y_start,_brightness)
        # Bottom Line
        self.line(_x_start,_y_start+_y_height,_x_start+_x_width,_y_start+_y_height,_brightness)
        # Left Line
        self.line(_x_start,_y_start,_x_start,_y_start+_y_height,_brightness)
        # Right Line
        self.line(_x_start+_x_width,_y_start,_x_start+_x_width,_y_start+_y_height,_brightness)

    def DrawPause(self,_x_start,_y_start,_x_width,_y_height,_symbol_bright):
        "Draw a hollow pause button"
        # Left box
        self.DrawBox(_x_start,_y_start,int(_x_width/3),_y_height,_symbol_bright)
        self.DrawBox(_x_start+int(_x_width/3)*2,_y_start,int(_x_width/3),_y_height,_symbol_bright)

    def DrawSpotify(self,_x_start,_y_start,_symbol_bright) -> None:
        "Spotify logo"
        # Row 1
        self.line(_x_start+1,_y_start+1,_x_start+7,_y_start+1,_symbol_bright)
        # Row 2
        self.line(_x_start+0,_y_start+2,_x_start+1,_y_start+2,_symbol_bright)
        self.line(_x_start+7,_y_start+2,_x_start+8,_y_start+2,_symbol_bright)
        # Row 3
        self.line(_x_start+0,_y_start+3,_x_start+6,_y_start+3,_symbol_bright)
        self.line(_x_start+8,_y_start+3,_x_start+8,_y_start+3,_symbol_bright)
        # Row 4
        self.line(_x_start+0,_y_start+4,_x_start+1,_y_start+4,_symbol_bright)
        self.line(_x_start+6,_y_start+4,_x_start+8,_y_start+4,_symbol_bright)
        # Row 5
        self.line(_x_start+0,_y_start+5,_x_start+5,_y_start+5,_symbol_bright)
        self.line(_x_start+7,_y_start+5,_x_start+8,_y_start+5,_symbol_bright)
        # Row 6
        self.line(_x_start+0,_y_start+6,_x_start+1,_y_start+6,_symbol_bright)
        self.line(_x_start+5,_y_start+6,_x_start+8,_y_start+6,_symbol_bright)
        # Row 7
        self.line(_x_start+1,_y_start+7,_x_start+7,_y_start+7,_symbol_bright)

    def DrawNet(self,_x_start,_y_start,_symbol_bright) -> None:
        "Network logo"
        # Draw network device
        self.DrawBox(_x_start+1,_y_start,5,4,_symbol_bright)
        # Draw connection
        self.line(_x_start+3,_y_start+5,_x_start+3,_y_start+7,_symbol_bright)
        # Dtaw network
        self.line(_x_start,_y_start+7,_x_start+7,_y_start+7,_symbol_bright)

    def DrawWifi(self,_x_start,_y_start,_symbol_bright) -> None:
        "Wifi logo"
        # Draw base
        self.line(_x_start+1,_y_start+7,_x_start+5,_y_start+7,_symbol_bright)
        # Draw antena
        self.line(_x_start+3,_y_start+1,_x_start+3,_y_start+6,_symbol_bright)
        # Draw transmission
        self.line(_x_start+1,_y_start+0,_x_start+1,_y_start+3,_symbol_bright)
        self.line(_x_start+5,_y_start+0,_x_start+5,_y_start+3,_symbol_bright)

    def DrawRepeat(self,_x_start,_y_start,_symbol_bright) -> None:
        "Repeat logo"
        # Draw Right Arrow
        self.line(_x_start+5,_y_start+0,_x_start+5,_y_start+4,_symbol_bright)
        self.line(_x_start+6,_y_start+1,_x_start+6,_y_start+3,_symbol_bright)
        # Draw Left Arrow
        self.line(_x_start+1,_y_start+5,_x_start+1,_y_start+7,_symbol_bright)
        self.line(_x_start+2,_y_start+4,_x_start+2,_y_start+8,_symbol_bright)
        # Draw top arrow stick
        self.line(_x_start+1,_y_start+2,_x_start+7,_y_start+2,_symbol_bright)
        # Draw bottom arrow stick
        self.line(_x_start+0,_y_start+6,_x_start+6,_y_start+6,_symbol_bright)

    def DrawRepeatOne(self,_x_start,_y_start,_symbol_bright) -> None:
        "Repeat one logo"
        # Draw Right Arrow
        self.line(_x_start+5,_y_start+0,_x_start+5,_y_start+4,_symbol_bright)
        self.line(_x_start+6,_y_start+1,_x_start+6,_y_start+3,_symbol_bright)
        # Draw Left Arrow
        self.line(_x_start+1,_y_start+5,_x_start+1,_y_start+7,_symbol_bright)
        self.line(_x_start+2,_y_start+4,_x_start+2,_y_start+8,_symbol_bright)
        # Draw top arrow stick
        self.line(_x_start+1,_y_start+2,_x_start+7,_y_start+2,_symbol_bright)
        # Draw bottom arrow stick
        self.line(_x_start+0,_y_start+6,_x_start+4,_y_start+6,_symbol_bright)
        # Draw number 1
        self.line(_x_start+6,_y_start+6,_x_start+6,_y_start+8,_symbol_bright)

    def DrawShuffle(self,_x_start,_y_start,_symbol_bright) -> None:
        "Shuffle logo"
        # Draw Down Right Arrow
        self.line(_x_start+7,_y_start+5,_x_start+7,_y_start+6,_symbol_bright)
        self.line(_x_start+5,_y_start+7,_x_start+6,_y_start+7,_symbol_bright)
        # Draw Down Right stick
        self.line(_x_start+0,_y_start+0,_x_start+7,_y_start+7,_symbol_bright)
        # Draw Up Left Arrow
        self.line(_x_start+7,_y_start+1,_x_start+7,_y_start+2,_symbol_bright)
        self.line(_x_start+5,_y_start+0,_x_start+6,_y_start+0,_symbol_bright)
        # Draw Up Left stick
        self.line(_x_start+0,_y_start+7,_x_start+7,_y_start+0,_symbol_bright)

    def DrawRepeatShuffle(self,_x_start,_y_start,_symbol_bright) -> None:
        "Shuffle repeat logo"
        # Draw Bottom Right Arrow
        self.line(_x_start+7,_y_start+5,_x_start+7,_y_start+6,_symbol_bright)
        self.line(_x_start+5,_y_start+7,_x_start+6,_y_start+7,_symbol_bright)
        # Draw Down Right stick
        self.line(_x_start+0,_y_start+0,_x_start+7,_y_start+7,_symbol_bright)
        # Draw Bottom Left Arrow
        self.line(_x_start+0,_y_start+5,_x_start+0,_y_start+6,_symbol_bright)
        self.line(_x_start+1,_y_start+7,_x_start+2,_y_start+7,_symbol_bright)
        # Draw Top Right Arrow
        self.line(_x_start+7,_y_start+1,_x_start+7,_y_start+2,_symbol_bright)
        self.line(_x_start+5,_y_start+0,_x_start+6,_y_start+0,_symbol_bright)
        # Draw Up Left stick
        self.line(_x_start+0,_y_start+7,_x_start+7,_y_start+0,_symbol_bright)
        # Draw Top Left Arrow
        self.line(_x_start+0,_y_start+1,_x_start+0,_y_start+2,_symbol_bright)
        self.line(_x_start+2,_y_start+0,_x_start+1,_y_start+0,_symbol_bright)

    def DrawSequence(self,_x_start,_y_start,_symbol_bright) -> None:
        "Sequence logo"
        # Draw 1st Right Arrow
        self.line(_x_start+1,_y_start+1,_x_start+1,_y_start+5,_symbol_bright)
        self.line(_x_start+2,_y_start+2,_x_start+2,_y_start+4,_symbol_bright)
        # Draw 2nd Right Arrow
        self.line(_x_start+5,_y_start+1,_x_start+5,_y_start+5,_symbol_bright)
        self.line(_x_start+6,_y_start+2,_x_start+6,_y_start+4,_symbol_bright)
        # Draw centre stick
        self.line(_x_start+0,_y_start+3,_x_start+7,_y_start+3,_symbol_bright)

    def DrawLeftChannel(self,_x_start,_y_start,_symbol_bright) -> None:
        "Left channel logo"
        # Draw 1st Right Arrow
        self.line(_x_start+0,_y_start+1,_x_start+0,_y_start+6,_symbol_bright)
        self.line(_x_start+2,_y_start+2,_x_start+2,_y_start+5,_symbol_bright)
        self.line(_x_start+4,_y_start+3,_x_start+4,_y_start+4,_symbol_bright)
        self.line(_x_start+6,_y_start+3,_x_start+6,_y_start+4,_symbol_bright)
        self.line(_x_start+7,_y_start+3,_x_start+7,_y_start+4,_symbol_bright)
    
    def DrawRightChannel(self,_x_start,_y_start,_symbol_bright) -> None:
        "Right channel logo"
        # Draw 1st Right Arrow
        self.line(_x_start+0,_y_start+3,_x_start+0,_y_start+4,_symbol_bright)
        self.line(_x_start+1,_y_start+3,_x_start+1,_y_start+4,_symbol_bright)
        self.line(_x_start+3,_y_start+3,_x_start+3,_y_start+4,_symbol_bright)
        self.line(_x_start+5,_y_start+2,_x_start+5,_y_start+5,_symbol_bright)
        self.line(_x_start+7,_y_start+1,_x_start+7,_y_start+6,_symbol_bright)
 
    def DrawStereoChannel(self,_x_start,_y_start,_symbol_bright) -> None:
        "Stereo logo"
        # Draw 1st Right Arrow
        self.pixel(_x_start+1,_y_start+0,_symbol_bright)
        self.pixel(_x_start+1,_y_start+7,_symbol_bright)
        self.line(_x_start+0,_y_start+1,_x_start+0,_y_start+6,_symbol_bright)
        self.line(_x_start+2,_y_start+2,_x_start+2,_y_start+5,_symbol_bright)
        self.line(_x_start+3,_y_start+3,_x_start+3,_y_start+4,_symbol_bright)
        self.line(_x_start+4,_y_start+3,_x_start+4,_y_start+4,_symbol_bright)
        self.line(_x_start+5,_y_start+2,_x_start+5,_y_start+5,_symbol_bright)
        self.line(_x_start+7,_y_start+1,_x_start+7,_y_start+6,_symbol_bright)
        self.pixel(_x_start+6,_y_start+0,_symbol_bright)
        self.pixel(_x_start+6,_y_start+7,_symbol_bright)

    def Main(self,_amp):
        "Display selected amplifier details - Max 32 long"

        self.fill(0)
        _normal_brightness = 0xff
        _dim_brightness = 0x06
        _unknown_brightness = 0x01
        _min_brightness = 0x01

        _name = _amp.readAttribute("NAM")
        if not _name:
            _name = ".searching"
            self.text(_name,0,0,_unknown_brightness)
        else:
            self.text(_name,0,0,_dim_brightness)

        _source = _amp.readAttribute("SRC")
        if not _amp.readAttribute("SRC"):
            _source = ""
        
        _feed = _amp.readAttribute("VND")
        if not _amp.readAttribute("VND"):
            _feed = ""

        _title = _amp.readAttribute("TIT")
        if not _amp.readAttribute("TIT"):
            _title = ""

        _artist = _amp.readAttribute("ART")
        if not _amp.readAttribute("ART"):
            _artist = ""

        _album = _amp.readAttribute("ALB")
        if not _amp.readAttribute("ALB"):
            _album = ""

        _play = _amp.readAttribute("PLA")
        if not _amp.readAttribute("PLA"):
            _play = ""
        
        _loop = _amp.readAttribute("LPM")
        # LPM: {REPEATALL/REPEATONE/REPEATSHUFFLE/SHUFFLE/SEQUENCE};
        if not _amp.readAttribute("LPM"):
            _loop = ""

        _volume = _amp.readAttribute("VOL")
        if not _amp.readAttribute("VOL"):
            _volume = 0

        _ethernet = _amp.readAttribute("ETH")
        if not _amp.readAttribute("ETH"):
            _ethernet = 0

        _wifi = _amp.readAttribute("WIF")
        if not _amp.readAttribute("WIF"):
            _wifi = 0

        _channels = _amp.readAttribute("CHN")
        if not _amp.readAttribute("CHN"):
            _channels = 0

        _position = _amp.readAttribute("ELP")
        if not _position:
            _position = 0
        if _amp.readAttribute("PLA"):
            if _position == "0/0":
                _position = "0"
        try:
            _position_percent = eval("(" + str(_position) + ")")
        except:
            _position_percent = 0
        _time = int(str(_position).split("/",1)[0])/1000
        _minutes = floor(_time/60)
        _seconds = floor(_time-(_minutes*60))
        # else:
        #     _minutes = floor (secondsSinceTick(_amp.TrackStarted)/60)
        #     _seconds = floor(secondsSinceTick(_amp.TrackStarted)-(_minutes*60))

        _first_icon_start=80
        _icon_gap=12


        if _ethernet == "1":
            self.DrawNet(_first_icon_start+(_icon_gap*1),0,_dim_brightness)
        else:
            self.DrawNet(_first_icon_start+(_icon_gap*1),0,_min_brightness)

        if _wifi == "1":
            self.DrawWifi(_first_icon_start+(_icon_gap*2),0,_dim_brightness)
        else:
            self.DrawWifi(_first_icon_start+(_icon_gap*2),0,_min_brightness)

        if _feed == "Spotify":
            self.DrawSpotify(_first_icon_start+(_icon_gap*3),0,_dim_brightness)
        if _feed == "Spotify":
            self.DrawSpotify(_first_icon_start+(_icon_gap*3),0,_dim_brightness)
        else:
            self.DrawSpotify(_first_icon_start+(_icon_gap*3),0,_min_brightness)

        # Loop symbol  {REPEATALL/REPEATONE/REPEATSHUFFLE/SHUFFLE/SEQUENCE};
        if _loop == "REPEATALL":
            self.DrawRepeat(_first_icon_start+(_icon_gap*4),0,_dim_brightness)
        elif _loop == "REPEATONE":
            self.DrawRepeatOne(_first_icon_start+(_icon_gap*4),0,_dim_brightness)
        elif _loop == "SHUFFLE":
            self.DrawShuffle(_first_icon_start+(_icon_gap*4),0,_dim_brightness)
        elif _loop == "REPEATSHUFFLE":
            self.DrawRepeatShuffle(_first_icon_start+(_icon_gap*4),0,_dim_brightness)
        elif _loop == "SEQUENCE":
            self.DrawSequence(_first_icon_start+(_icon_gap*4),0,_dim_brightness)
        else:
            self.DrawSequence(_first_icon_start+(_icon_gap*4),0,_min_brightness)


        if _channels == "L":
            self.DrawLeftChannel(_first_icon_start+(_icon_gap*5),0,_dim_brightness)
        elif _channels == "R":
            self.DrawRightChannel(_first_icon_start+(_icon_gap*5),0,_dim_brightness)
        elif _channels == "S":
            self.DrawStereoChannel(_first_icon_start+(_icon_gap*5),0,_dim_brightness)
        else:
            self.DrawStereoChannel(_first_icon_start+(_icon_gap*5),0,_min_brightness)

        # Play / Pause symbol
        if _play == "1":
            self.DrawPlay(_first_icon_start+(_icon_gap*6),0,6,7,_dim_brightness)
        else:
            self.DrawPause(_first_icon_start+(_icon_gap*6),0,6,7,_dim_brightness)


        self.text(str(_minutes)+":"+str(_seconds), 180,0,_dim_brightness)
        self.ProgressBar(220,1,35,2,"Horizontal","Right",_position_percent,_min_brightness,_dim_brightness)
        self.ProgressBar(250,10,2,45,"Vertical","Up",int(_volume)/100,_min_brightness,_dim_brightness)
        
        self.text(_title,0,20,_normal_brightness)
        self.text(_artist,0,30,_dim_brightness)
        self.text(_album,0,40,_dim_brightness)

        #self.text("123456789-123456789-123456789-123456789-",0,55,_dim_brightness)
        self.show()


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
        self.QueuedRequests = {}                                                    # Queries requests
        self.ResponseBuffer = {}                                                    # Responses populated in this buffer
        self.BackPresure = False                                                    # Are High priority requests not making it onto the queue
        self.LastBackPresure = 0                                                    # When was back pressure last applied
        self.BackPresureRelease = 3                                                 # After how long to take of back presure
        self.BackPresureCount = 0                                                   # How many times has backpresure been applied
        self.BackPresureThreshold = 2                                               # Adjust soft limit
        self.LastBackPresureThreshold = 0                                           # When was the limit last adjusted
        
        self.uart = UART(Pico_Channel_UART, baudrate=115200, bits=8, parity=None, stop=1, tx=Pin(Pin_UART_TX), rx=Pin(Pin_UART_RX))

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
        # print("{" + str(self.uart.read()),end='}')
        self.uart.write(message)
        sleep(wait)
        # read line into buffer
        response = self.uart.read()
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

            #print(" <" + str(self.ResponseBuffer[request]) + "> ")
            #print("RECEIVED:" + requestType + "#(" + response + ") ",end='')
            MA.Amplifiers[ampNumber].saveAttribute(requestType,response)


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
# Button_Source_Cycle.irq(trigger=Pin.IRQ_RISING, handler=Button_Handler)
# print("source", end = '')
# Button_Amp_Cycle.irq(trigger=Pin.IRQ_RISING, handler=Button_Handler)
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

# print("Initializing SPI Display")
# spi = SPI(0, baudrate=16000000,polarity=0, phase=0, sck=Pin(2), mosi=Pin(3), miso=Pin(0))
# dc=Pin(5,Pin.OUT)
# cs=Pin(1,Pin.OUT)
# res=Pin(4,Pin.OUT)
# oled=SSD1322_SPI(256,64,spi,dc,cs,res)
# oled.fill(0)

# Initiate Primary Object
MA = MultiAmp()

# Initiate UART
UART_Com = UART_Communication()

# Find Amps and create the objects
OLED = Display()
OLED.text("Searching for Amplifiers",20,30,0xff)
OLED.show()

MA.ampDiscovery(1,1,UART_Com,OLED)

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

lastAmpPrint = tickNow()


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

    if secondsSinceTick(lastAmpPrint) > 1:
        lastAmpPrint = tickNow()
        print("Number of Amps: " + str(len(MA.Amplifiers)))
        for ampNumber in range(len(MA.Amplifiers)):
            MA.Amplifiers[ampNumber].printAmp()
            OLED.Main(MA.Amplifiers[MA.getAmpSelected()])
