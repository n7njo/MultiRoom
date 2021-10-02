# Display Pico

# Feature to dos

    # Software
        # See the other amps on the display
        # Animation to show progress - Visual to see if sound playing from each amp
        # Brightness control

    # Questions?
        # What output can be seen from the Amp to determine sound actually being played

#import utime
from utime import sleep_ms, sleep, ticks_us, ticks_diff
from machine import UART, Pin, SPI, PWM
from ure import match
import framebuf
from math import floor


### Configure Pins
# Pin numbers
Pin_LED_Source_Red = 15          
Pin_LED_Source_Green = 14            
Pin_LED_Source_Blue = 13 
Pin_LED_Power_Red = 12          
Pin_LED_Power_Green = 11            
Pin_LED_Power_Blue = 10 

Pin_LED_Internal = 25       

Pin_DISPLAY_UART_TX = 8
Pin_DISPLAY_UART_RX = 9

Pin_SPI_DC = 5
Pin_SPI_CS = 1              # SPI CS
Pin_SPI_Res = 4
Pin_SPI_MOSI = 3            # SPI TX
Pin_SPI_MISO = 0            # SPI RX
Pin_SPI_SCLK = 2            # SPI Clock

Pico_DISPLAY_UART = 1       # Which Pico coms channel will be used

# LEDs
LED_Internal = Pin(Pin_LED_Internal, Pin.OUT)

PWM_LED_Frequency = 1000

LED_Power_Change_Rate = 2

# Buttons
# Button_Source_Cycle = Pin(Pin_BUT_Source_Cycle, Pin.IN, Pin.PULL_UP)
# Button_Amp_Cycle = Pin(Pin_BUT_Amp_Cycle, Pin.IN, Pin.PULL_UP)

# Limits
Limit_UART_Max_Queue_Length = 10                                                             # Queue size for waiting UART requests
Limit_UART_Throttling_Queue_Length = 10                                                      # Throttling queue size if Low requests are impacting
Limit_UART_Multiplexer_Max_Channels = 3                                                    # How many channels does the multiplexer have
Limit_UART_Multiplexer_Max_Minutes_Looking = 10                                             # Max minutes to look for channels in available
Limit_LED_PWM_Upper_Limit = 65535
Limit_LED_PWM_Lower_Limit = 0

# Flags                                                        # Can the UART queue messages
Flag_System_RedLine = False
Flag_Display_Probe_Toggle_Blink = True
Flag_Display_Probe_Blink_On = True

# Debugging

Debug_Queue = False
Debug_Display_UART = False
Debug_LED = False
Debug_Amp_UART_Parse = False
Debug_Amp = False

# Common Functions
def tickNow():
    return ticks_us()

def secondsBetweenTick(_firstTimestamp,_secondTimestamp):
    return ticks_diff(_firstTimestamp,_secondTimestamp)

def secondsSinceTick(_timestamp):
    "How many seconds have passed since the timestamp"
    #return round(secondsBetweenTick(tickNow(),timestamp)/1000000,4)
    return secondsBetweenTick(tickNow(),_timestamp)/1000000

def tickSinceSeconds(_seconds):
    "What was the timestamp this number of seconds ago"
    return tickNow() - (_seconds*1000000)

# Timing variables

lastPrune = tickNow()
lastParse = tickNow()
lastProcessed = tickNow()

lastQueuePrint = tickNow()
lastAutoGenerateLow = tickNow()
lastCheckAllStatus = tickNow()
lastUnknownBlink = tickNow()
lastMissingCheck = tickNow()

lastAmpPrint = tickNow()

lastLEDBrightness = tickNow()

# LED controller class
class Display_LED:
    "Display LED object"

    def __init__(self) -> None:
        global Limit_LED_PWM_Lower_Limit, Limit_LED_PWM_Upper_Limit, LED_Power_Change_Rate, PWM_LED_Frequency
        global Pin_LED_Power_Red, Pin_LED_Power_Green, Pin_LED_Power_Blue, Pin_LED_Source_Red, Pin_LED_Source_Green, Pin_LED_Source_Blue

        # Initiating LED

        self.lastLEDBrightness = tickNow()
        self.LED_Power_Target = [Limit_LED_PWM_Lower_Limit,Limit_LED_PWM_Lower_Limit,Limit_LED_PWM_Lower_Limit]
        self.LED_Power_Current = [Limit_LED_PWM_Lower_Limit,Limit_LED_PWM_Lower_Limit,Limit_LED_PWM_Lower_Limit]
        self.LED_Source_Target = [Limit_LED_PWM_Lower_Limit,Limit_LED_PWM_Lower_Limit,Limit_LED_PWM_Lower_Limit]
        self.LED_Source_Current = [Limit_LED_PWM_Lower_Limit,Limit_LED_PWM_Lower_Limit,Limit_LED_PWM_Lower_Limit]

        self.LED_Power_Red = Pin(Pin_LED_Power_Red)
        self.PWM_LED_Power_Red = PWM(self.LED_Power_Red)
        self.PWM_LED_Power_Red.freq(PWM_LED_Frequency)

        self.LED_Power_Green = Pin(Pin_LED_Power_Green)
        self.PWM_LED_Power_Green = PWM(self.LED_Power_Green)
        self.PWM_LED_Power_Green.freq(PWM_LED_Frequency)

        self.LED_Power_Blue = Pin(Pin_LED_Power_Blue)
        self.PWM_LED_Power_Blue = PWM(self.LED_Power_Blue)
        self.PWM_LED_Power_Blue.freq(PWM_LED_Frequency)

        self.PWM_LED_Power_Red.duty_u16(self.LED_Power_Current[0])
        self.PWM_LED_Power_Green.duty_u16(self.LED_Power_Current[1])
        self.PWM_LED_Power_Blue.duty_u16(self.LED_Power_Current[2])

        self.LED_Source_Red = Pin(Pin_LED_Source_Red)
        self.PWM_LED_Source_Red = PWM(self.LED_Source_Red)
        self.PWM_LED_Source_Red.freq(PWM_LED_Frequency)

        self.LED_Source_Green = Pin(Pin_LED_Source_Green)
        self.PWM_LED_Source_Green = PWM(self.LED_Source_Green)
        self.PWM_LED_Source_Green.freq(PWM_LED_Frequency)

        self.LED_Source_Blue = Pin(Pin_LED_Source_Blue)
        self.PWM_LED_Source_Blue = PWM(self.LED_Source_Blue)
        self.PWM_LED_Source_Blue.freq(PWM_LED_Frequency)

        self.PWM_LED_Source_Red.duty_u16(self.LED_Source_Current[0])
        self.PWM_LED_Source_Green.duty_u16(self.LED_Source_Current[1])
        self.PWM_LED_Source_Blue.duty_u16(self.LED_Source_Current[2])

        # Red
        #LED_Power_Target = [Limit_LED_PWM_Upper_Limit,Limit_LED_PWM_Lower_Limit,Limit_LED_PWM_Lower_Limit]
        # Green
        #LED_Power_Target = [Limit_LED_PWM_Lower_Limit,Limit_LED_PWM_Upper_Limit,Limit_LED_PWM_Lower_Limit]
        # Blue
        self.LED_Power_Target = [Limit_LED_PWM_Lower_Limit,Limit_LED_PWM_Lower_Limit,Limit_LED_PWM_Upper_Limit]
        self.LED_Source_Target = [Limit_LED_PWM_Lower_Limit,Limit_LED_PWM_Lower_Limit,Limit_LED_PWM_Upper_Limit]

    def LEDBrightness(self,_current,_target,_PWM_LED_Red,_PWM_LED_Green,_PWM_LED_Blue,_which):

        ##if Debug_LED: print("PowerBright")

        if Debug_LED: print(str(_which) + "Current:> " + str(_current))
        if Debug_LED: print(str(_which) + "Target:> " + str(_target))
        for _colour in range(0,3):
            if _colour == 0: _colour_name = "Red"
            elif _colour == 1: _colour_name = "Green"
            elif _colour == 2: _colour_name = "Blue"
            ##if Debug_LED: print(str(_colour_name) + " C:> " + str(_current[_colour]) + " T:> " + str(LED_Power_Target[_colour]))

            # Needs a change
            if (_target[_colour] != _current[_colour]):
                if Debug_LED: print(str(_colour_name) + " difference:> ")

                # Going up
                if (_target[_colour] > _current[_colour]):
                    _difference = _target[_colour] - _current[_colour]
                    _percent_done = 1 - (_difference/Limit_LED_PWM_Upper_Limit)
                    _change_by = int((_percent_done/LED_Power_Change_Rate) * Limit_LED_PWM_Upper_Limit ) + 1
                    if (_change_by > _difference):
                        _current[_colour] = _target[_colour]
                    else:
                        _current[_colour] = _current[_colour] + _change_by
                    
                    if Debug_LED: print(str(_colour_name) + ":> " + str(_current[_colour]) + " -> " + str(_target[_colour]) + "(up by " + str(_change_by) + ")")
                # Going down
                if (_target[_colour] < _current[_colour]):
                    _difference = _current[_colour] - _target[_colour]
                    _percent_done = 1 - (_difference/Limit_LED_PWM_Upper_Limit)
                    _change_by = int((_percent_done/LED_Power_Change_Rate) * Limit_LED_PWM_Upper_Limit ) + 1

                    if (_change_by > _difference):
                        _current[_colour] = _target[_colour]
                    else:
                        _current[_colour] = _current[_colour] - _change_by

                    if Debug_LED: print(str(_colour_name) + ":> " + str(_current[_colour]) + " -> " + str(_target[_colour]) + "(down by " + str(_change_by) + ") ")

        _PWM_LED_Red.duty_u16(_current[0])
        _PWM_LED_Green.duty_u16(_current[1])
        _PWM_LED_Blue.duty_u16(_current[2])

    def SetLEDColour(self,_target,_colour,_mutedby=1):
        if _colour == "Red":
            _target[0]=int(Limit_LED_PWM_Upper_Limit/_mutedby)
            _target[1]=int(Limit_LED_PWM_Lower_Limit/_mutedby)
            _target[2]=int(Limit_LED_PWM_Lower_Limit/_mutedby)

        elif _colour == "Green":
            _target[0]=int(Limit_LED_PWM_Lower_Limit/_mutedby)
            _target[1]=int(Limit_LED_PWM_Upper_Limit/_mutedby)
            _target[2]=int(Limit_LED_PWM_Lower_Limit/_mutedby)

        elif _colour == "Blue":
            _target[0]=int(Limit_LED_PWM_Lower_Limit/_mutedby)
            _target[1]=int(Limit_LED_PWM_Lower_Limit/_mutedby)
            _target[2]=int(Limit_LED_PWM_Upper_Limit/_mutedby)

        elif _colour == "Cyan":
            _target[0]=int(Limit_LED_PWM_Lower_Limit/_mutedby)
            _target[1]=int(Limit_LED_PWM_Upper_Limit/_mutedby)
            _target[2]=int(Limit_LED_PWM_Upper_Limit/_mutedby)

        elif _colour == "Yellow":
            _target[0]=int(Limit_LED_PWM_Upper_Limit/_mutedby)
            _target[1]=int(Limit_LED_PWM_Upper_Limit/_mutedby)
            _target[2]=int(Limit_LED_PWM_Lower_Limit/_mutedby)

        elif _colour == "Purple":
            _target[0]=int(Limit_LED_PWM_Upper_Limit/_mutedby)
            _target[1]=int(Limit_LED_PWM_Lower_Limit/_mutedby)
            _target[2]=int(Limit_LED_PWM_Upper_Limit/_mutedby)

    def LEDColour(self,_target,_which):
        if _which == "Source":
            if Amplifier.readAttribute("SRC") == "NET":
                self.SetLEDColour(_target,"Cyan", 10)
            elif Amplifier.readAttribute("SRC") == "BT":
                self.SetLEDColour(_target,"Blue", 10)
            elif Amplifier.readAttribute("SRC") == "LINE-IN":
                self.SetLEDColour(_target,"Green", 10)
            elif Amplifier.readAttribute("SRC") == "OPT":
                self.SetLEDColour(_target,"Red", 10)
            elif Amplifier.readAttribute("SRC") == "USBPLAY":
                self.SetLEDColour(_target,"Yellow", 10)
            else:
                self.SetLEDColour(_target,"Purple", 10)
                
# Amp status object
class Amp:
    "All the current status details about the Amp"

    def __init__(self) -> None:
        self.Attributes = {}                                    # Master Dictionary for all settings
        self.AmpNumber = -1
        self.AvailableSources = []
        self.CurrentTrackStarted = 0
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
        return _ampuart.requestCommand(_key + ":" + str(_value) + ";","High",0.1)
        
    def requestUART(self,_ampuart,_key,wait=0.1):
        "Request value base on Key"
        return _ampuart.requestCommand(_key + ";","Low",wait)
    
    def missingAttributes(self,_ampuart):

        _requests_in_queue = _ampuart.getQueuedRequestTypes()

        # Already has the request in the queue
        if "NAM" in _requests_in_queue:
            return
        if self.readAttribute("NAM") == None:
            self.requestUART(_ampuart,"NAM")
            # Don't return as we want to continue gathering other details.
        elif self.readAttribute("NAM") == "None":
            self.requestUART(_ampuart,"NAM")
            # Don't return as we want to continue gathering other details.
        elif self.readAttribute("NAM") == "":
            self.requestUART(_ampuart,"NAM")
            # Don't return as we want to continue gathering other details.

        # Already has the request in the queue
        if "PLA" in _requests_in_queue:
            return
        if self.readAttribute("PLA") == None:
            self.requestUART(_ampuart,"PLA")
            return

        # Already has the request in the queue
        if "TIT" in _requests_in_queue:
            return
        if self.readAttribute("TIT") == None and self.readAttribute("PLA") == "1":
            self.requestUART(_ampuart,"TIT")
            return

        # Already has the request in the queue
        if "VND" in _requests_in_queue:
            return
        if self.readAttribute("VND") == None:
            self.requestUART(_ampuart,"VND")
            return

        # Already has the request in the queue
        if "LPM" in _requests_in_queue:
            return
        if self.readAttribute("LPM") == None:
            self.requestUART(_ampuart,"LPM")
            return

        # Already has the request in the queue
        if "CHN" in _requests_in_queue:
            return
        if self.readAttribute("CHN") == None:
            self.requestUART(_ampuart,"CHN")
            return

        if "ELP" in _requests_in_queue:
            return
        if self.readAttribute("ELP") == None:
            self.requestUART(_ampuart,"ELP")
            return
    
        if self.readAttribute("PLA") == "1" and self.readAttribute("TIT") == "":
            self.requestUART(_ampuart,"TIT")   

        # Already has the request in the queue
        if "WIF" in _requests_in_queue:
            return
        if self.readAttribute("WIF") == None:
            self.requestUART(_ampuart,"WIF")
            return

          # Already has the request in the queue
        if "ETH" in _requests_in_queue:
            return
        if self.readAttribute("ETH") == None:
            self.requestUART(_ampuart,"ETH")
            return
    
        # Already has the request in the queue
        if "SRC" in _requests_in_queue:
            return
        if self.readAttribute("SRC") == None:
            self.requestUART(_ampuart,"SRC")
            return

        # print("PLA:> " + str(self.readAttribute("PLA")) + " ELP:> " + str(self.readAttribute("ELP")))
        # if self.readAttribute("PLA") == "None" and self.readAttribute("ELP") != "0":
        #     self.requestUART(_ampuart,"PLA")

    def saveAttribute(self,_key,_value):
        #print("SAVE:" + _key + "='" + _value + "'", end=" ")
        # if _value in self.FlagAttributes:
        #     if _value == 1:
        #         self.Attributes[_key] = True
        #     else:
        #         self.Attributes[_key] = False
        # else:
        if _key == "ELP":
            # convert to ticks
            if _value != "None":
                try:
                    _calc = tickNow() - ((int(str(_value).split("/",1)[0])) * 1000)
                except:
                    # Junk was sent via the UART
                    _calc = None
                if _calc is not None:
                 self.CurrentTrackStarted = _calc
            else:
                _value = 0


        self.Attributes[_key] = _value

        #print("Stored:=" + "'" + self.Attributes[_key] + "'")
    
    def readAttribute(self,_key):
       # print("Attributes: " + str(self.Attributes))
        if _key in self.Attributes.keys():
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

# Display chip
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

# Communication with the display chip over SPI
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

# Display functions
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
        DLED.SetLEDColour(DLED.LED_Power_Target,"Red", 1)

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
        
        ## Normal mode
        DLED.SetLEDColour(DLED.LED_Power_Target,"Cyan", 10)

        self.fill(0)
        _normal_brightness = 0xff
        _dim_brightness = 0x06
        _blink_brightness = 0x02
        _unknown_brightness = 0x01
        _toggle_blink_brightness = _unknown_brightness
        _min_brightness = 0x01
        _off_brightness = 0x00

        if Flag_Display_Probe_Toggle_Blink:
            if Flag_Display_Probe_Blink_On:
                _toggle_blink_brightness = _blink_brightness
            else:
                _toggle_blink_brightness = _off_brightness


        _name = _amp.readAttribute("NAM")
        if not _name:
            _name = "........"
            self.text(_name,0,0,_toggle_blink_brightness)
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

        # Read track position string
        _position = _amp.readAttribute("ELP")

        # If not set, assume beginning
        if not _position:
            _position = 0

        # Evaluated position percentage, if it's doesn't evaluate assue beginning
        try:
            _position_percent = eval("(" + str(_position) + ")")
        except:
            _position_percent = 0
            _position = "0"

        if _play == '1':
            _time = round(secondsSinceTick(_amp.CurrentTrackStarted),0)
            _minutes = int(floor(_time/60))
            _seconds = int(floor(_time-(_minutes*60)))
        else:
            _time = int(str(_position).split("/",1)[0])/1000
            _minutes = int(floor(_time/60))
            _seconds = int(floor(_time-(_minutes*60)))
        if len(str(_seconds)) == 1:
            _seconds = "0" + str(_seconds)

        _first_icon_start=80
        _icon_gap=12


        if _ethernet == "1":
            self.DrawNet(_first_icon_start+(_icon_gap*1),0,_dim_brightness)
        elif _ethernet == "0":
            self.DrawNet(_first_icon_start+(_icon_gap*1),0,_min_brightness)
        else:
            self.DrawNet(_first_icon_start+(_icon_gap*1),0,_toggle_blink_brightness)

        if _wifi == "1":
            self.DrawWifi(_first_icon_start+(_icon_gap*2),0,_dim_brightness)
        elif _wifi == "0":
            self.DrawWifi(_first_icon_start+(_icon_gap*2),0,_min_brightness)
        else:
            self.DrawWifi(_first_icon_start+(_icon_gap*2),0,_toggle_blink_brightness)

        if _feed == "spotify":
            self.DrawSpotify(_first_icon_start+(_icon_gap*3),0,_dim_brightness)
        elif _feed == "tunein":
            self.text("T",_first_icon_start+(_icon_gap*3),0,_dim_brightness)
        if _feed == "amazon":
            self.text("A",_first_icon_start+(_icon_gap*3),0,_dim_brightness)
        # else:
        #     self.text("?",_first_icon_start+(_icon_gap*3),0,_toggle_blink_brightness)

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
            self.DrawSequence(_first_icon_start+(_icon_gap*4),0,_toggle_blink_brightness)


        if _channels == "L":
            self.DrawLeftChannel(_first_icon_start+(_icon_gap*5),0,_dim_brightness)
        elif _channels == "R":
            self.DrawRightChannel(_first_icon_start+(_icon_gap*5),0,_dim_brightness)
        elif _channels == "S":
            self.DrawStereoChannel(_first_icon_start+(_icon_gap*5),0,_dim_brightness)
        else:
            self.DrawStereoChannel(_first_icon_start+(_icon_gap*5),0,_toggle_blink_brightness)

        # Play / Pause symbol
        if _play == "1":
            self.DrawPlay(_first_icon_start+(_icon_gap*6),0,6,7,_dim_brightness)
        elif _play == "0":
            self.DrawPause(_first_icon_start+(_icon_gap*6),0,6,7,_dim_brightness)
        else:
            self.DrawPause(_first_icon_start+(_icon_gap*6),0,6,7,_toggle_blink_brightness)


        self.text(str(_minutes)+":"+str(_seconds), 180,0,_dim_brightness)
        self.ProgressBar(220,1,35,2,"Horizontal","Right",_position_percent,_min_brightness,_dim_brightness)
        self.ProgressBar(250,10,2,45,"Vertical","Up",int(_volume)/100,_min_brightness,_dim_brightness)
        
        self.text(_title,0,20,_normal_brightness)
        self.text(_artist,0,30,_dim_brightness)
        self.text(_album,0,40,_dim_brightness)

        #self.text("123456789-123456789-123456789-123456789-",0,55,_dim_brightness)
        self.show()

# Communications with the Amplifier Pico
class UART_Communication():

    def __init__(self) -> None:
        super().__init__()       
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
                        # print(">" + str(lowest) + "<--->" + str(request) + "<")
                        if lowest < request:
                            ##print("lowest",end='')
                            request = lowest
                            found = True
                            if Debug_Queue: print("Found-Q:>" + str(request) + " (" + str(self.getRequestMessage(request)) + ")")
                        ##else:
                            ##print("request",end='')
                    ##print("****")

            if found == True and request in self.getQueueRequests():
                ### Process Request ###

                ###self.printQueue()
                if Debug_Queue: print("Length-Q:> " + str(self.getRequestQueueLength()))
                # Send message
                if Debug_Queue: print("PopOff-Q:> " + str(request) + " (" + self.getRequestMessage(request) + ")")
                _response = self.transmitRequest(self.getRequestMessage(request),self.getResponseWait(request))
                if Debug_Amp: print("Response-M:> " + str(request) + " (" + str(self.getRequestMessage(request)) + ") > " + "[" + str(_response) + "]")
                if _response is not None:
                    # Push response into buffer
                    self.ResponseBuffer[request] = _response
                    self.setRequestComplete(request,True)
                    if Debug_Queue: print("Length-Q:> " + str(self.getRequestQueueLength()))
                else:
                    if Debug_Queue: print("Removed-Q:> " + str(request) + " (" + str(self.getRequestMessage(request)) + ") > " + "[" + str(_response) + "]")
                    self.removeFromQueue(request)

                if Debug_Queue: print("Length-Q:> " + str(self.getRequestQueueLength()))
                

                # print("Queue check:" + str(self.ResponseBuffer[request]))
                # if self.getRequestPriority(request) == "High":
                #     print("H",end='')
                # else:
                #     print("L",end='')
            # Unlock multiplexer idle
            self.Idle = True

    def transmitRequest(self,message,wait):
        "Actually send the message down the UART"
        # Anything in the buffer 
        # print("{" + str(self.displayuart.read()),end='}')
        LED_Internal.high()
        self.displayuart.write(message)
        LED_Internal.low()
        if Debug_Amp: print("Transmit-M:> " + "(" + str(message) + ")")
        sleep(wait)
        # read line into buffer
        
        # response = self.displayuart.read()
        # print("RESPONSE" + str(response))
        # return str(response)[2:][:-6]

    def removeFromQueue(self,_request):
        if Debug_Queue: print("Delete-Q:> " + str(_request))
        del self.ResponseBuffer[_request]
        del self.QueuedRequests[_request]

    def pushToQueue(self,_message,_priority,_wait):
        addedToQueueTicks = tickNow()
        # Lock Variable
        # Add request to the queue - True/False flag indicates response complete
        self.QueuedRequests[addedToQueueTicks] = [_message,False,_priority,_wait]
        if Debug_Queue: print("Added_1-Q:> (" + _message + ")")
        # Add placeholder for response
        self.ResponseBuffer[addedToQueueTicks] = [""]
        return addedToQueueTicks

    def pushToBothQueues(self,_message,_priority,_wait,_response):
        addedToQueueTicks = tickNow()
        # Lock Variable
        # Add request to the queue - True/False flag indicates response complete
        if Debug_Queue: print("Added_2-Q:>" + " (" + str(_message) + ") > " + "(" + str(_response) + ")")
        self.QueuedRequests[addedToQueueTicks] = [_message,True,_priority,_wait]
        # Add placeholder for response
        self.ResponseBuffer[addedToQueueTicks] = [_response]
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
        message = self.QueuedRequests[request][0]
        #baton.release()
        return message

    def getRequestComplete(self,request):
        #baton.acquire()
        #print(self.QueuedRequests[request])
        complete = self.QueuedRequests[request][1]
        #baton.release()
        return complete

    def getRequestPriority(self,request):
        #baton.acquire()
        priority = self.QueuedRequests[request][2]
        #baton.release()
        return priority

    def getResponseWait(self,request):
        #baton.acquire()
        priority = self.QueuedRequests[request][3]
        #baton.release()
        return priority

    def setRequestComplete(self,request,complete):
        self.QueuedRequests[request][1]=complete

    def requestCommand(self,message="",priority="low",wait=1):
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

                return (self.pushToQueue(message,priority,wait))

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
        _count = 0
        for request in self.QueuedRequests:
            if Debug_Queue: print("Contents-Q:>" + str(request) + ":|" + str(self.QueuedRequests[request][0]) + "," + str(self.QueuedRequests[request][1]) + "," + str(self.QueuedRequests[request][2]) + "| > [" + str(self.ResponseBuffer[request]) + "] ", end='')
            _count =+ 1
        if _count > 0:
            if Debug_Queue: print()

    def getQueue(self):
        "Return the queue"
        return list(self.QueuedRequests.items())
    
    def getQueueRequests(self):
        return list(self.QueuedRequests.keys())

    def getQueuedRequestTypes(self):
        "Return a list of all the request types in the queue"
        _request_types = []
        for request in self.QueuedRequests:
            _request_types.append(str(self.QueuedRequests[request][0][:3]))
        return _request_types

    def parseResponses(self):
        "Worker processing responses"
        # Look through the queue for any completes
        for request in list(self.QueuedRequests.keys()):
            # Look through the queue for processed high priority responses
            if self.QueuedRequests[request][1] == True and self.QueuedRequests[request][2] == "High":

                # Interpret the request to determine the action needed
                self.actionParsedResponse(request)

                # Remove the queue
                self.removeFromQueue(request)

        # Look through the queue for processed low priority responses
        for request in list(self.QueuedRequests.keys()):
            if self.QueuedRequests[request][1] == True and self.QueuedRequests[request][2] == "Low":
                
                # Interpret the request to determine the action needed
                self.actionParsedResponse(request)
                
                # Remove the queue
                self.removeFromQueue(request)

    def actionParsedResponse(self,request):

        #print("{" + self.ResponseBuffer[request] + "}")

        # Count if more that one Response type in the buffer, look for the ':'
        ##bufferRequests = ure.sub("r|n\g","",self.ResponseBuffer[request])

        #self.ResponseBuffer[request]
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
        bufferRequests = str(self.ResponseBuffer[request])[2:][:-3].split(";")
        responseCount = len(bufferRequests)
        if responseCount < 1:
            bufferRequests = self.ResponseBuffer[request]
        #bufferRequests
        #print("\n+" + str(bufferRequests) + "+\n")

        for i in range(len(bufferRequests)):
            # if i > 0 and len(bufferRequests) > 1:
            #     print(">" + bufferRequests[i])
            #     bufferRequests[i] = bufferRequests[i][4:]
            # else:
            #     pass
                #print("+",end='')
            
            # Loop through each
            #print(bufferRequests[i])
            requestType = bufferRequests[i][:3]
            response = bufferRequests[i][4:]
            if Debug_Amp_UART_Parse: print("SaveAttrib:> " + requestType + " (" + response + ") ")
            Amplifier.saveAttribute(requestType,response)

    def checkUARTForAmpUpdates(self):
        "Read UART to see if there's more info from the Amp Pico"
        if self.displayuart.any() > 0:
            response = self.displayuart.read()
            #print(">" + str(response) + "<")
            if str(response)[2:][:-1] != ":;":
                # Possibly recived a long line of junk
                #if len(str(response)[2:][:-1]) < 40:
                if Debug_Amp: print("Received-M:> [" + str(response)[2:][:-1] + "]")
                if bool(match('^[A-Z][A-Z][A-Z]',str(response)[2:][:-1])):
                    self.pushToBothQueues("","Low",0.1,str(response)[2:][:-1])

            #return str(response)[2:][:-6]

###### Begin Main Program ######

print("Starting Multiroom Amplifier Pico - Display Pico")
print("************************************************")
print()

print("Intantiating LED object ...", end= '')
DLED = Display_LED()
DLED.SetLEDColour(DLED.LED_Power_Target,"Blue", 12)
DLED.SetLEDColour(DLED.LED_Source_Target,"Red", 12)
print("[DONE]")

print("Creating Amplifier object...", end= '')
Amplifier = Amp()
print("[DONE]")

# Initiate UART
print("Initializing UART...", end= '')
UART_Com = UART_Communication()
print("[DONE]")

# Find Amps and create the objects
print("Initializing Display...", end= '')
OLED = Display()
OLED.show()
Amplifier.saveAttribute("AMP","0")
Amplifier.saveAttribute("MSG","Initializing...")
print("[DONE]")

# Main program
print()
print("Configuration complete, staring main program...[GO]")
print()

while True:

    # LED update
    if secondsSinceTick(lastLEDBrightness) > 0.01:
        lastLEDBrightness = tickNow()

        # Change Colour if needed
        DLED.LEDColour(DLED.LED_Power_Target,"Power")
        DLED.LEDColour(DLED.LED_Source_Target,"Source")

        # Change Brightness
        DLED.LEDBrightness(DLED.LED_Power_Current,DLED.LED_Power_Target,DLED.PWM_LED_Power_Red,DLED.PWM_LED_Power_Green,DLED.PWM_LED_Power_Blue,"Power")
        DLED.LEDBrightness(DLED.LED_Source_Current,DLED.LED_Source_Target,DLED.PWM_LED_Source_Red,DLED.PWM_LED_Source_Green,DLED.PWM_LED_Source_Blue,"Source")

    # Is the system very busy
    if Flag_System_RedLine:
        # System running hot
        #print("HOT")
        pass

    # Parse response Queue
    if secondsSinceTick(lastParse) > 0.1:
        lastParse = tickNow()
        UART_Com.parseResponses()

    # Prune old requests
    if secondsSinceTick(lastPrune) > 10:  
        lastPrune = tickNow()
        UART_Com.pruneQueue()

    # Print message queue
    if secondsSinceTick(lastQueuePrint) > 1:
        lastQueuePrint = tickNow()
        UART_Com.printQueue()

    # Are any attributes missing that would be expectec
    if secondsSinceTick(lastMissingCheck) > 0.3:
        lastMissingCheck = tickNow()

        if Amplifier.readAttribute("AMP") == "1":
            Amplifier.missingAttributes(UART_Com)
        else:
            Amplifier.requestUART(UART_Com,"AMP")

    # Check all amp status
    if secondsSinceTick(lastCheckAllStatus) > 5:
        lastCheckAllStatus = tickNow()
        Amplifier.requestUART(UART_Com,"WHT")

    # Check UART for updates
    if secondsSinceTick(lastProcessed) > 0.01:
        lastProcessed = tickNow()
        UART_Com.checkUARTForAmpUpdates()
        UART_Com.sendNextCommandFromQueue()

    # Print amp
    if secondsSinceTick(lastAmpPrint) > 0.1:
        lastAmpPrint = tickNow()
        #if Amplifier.readAttribute("NAM") != None:
        if Amplifier.readAttribute("AMP") == "1" and Amplifier.readAttribute("NAM") is not None and Amplifier.readAttribute("NAM") != "":
            #Amplifier.printAmp()

            ##Amplifier.requestUART(UART_Com,"")
            OLED.Main(Amplifier)
        else:
            OLED.ImportantMessage(str(Amplifier.readAttribute("MSG")))

    # Toggle unknown
    if secondsSinceTick(lastUnknownBlink) > 1:
        lastUnknownBlink = tickNow()
        if Flag_Display_Probe_Blink_On:
            Flag_Display_Probe_Blink_On = False
        else:
            Flag_Display_Probe_Blink_On = True

