class AnalogSensor(object):
    def __init__(self):
        print('analogsensor __init__')

class SleepMixin(object):
    def __init__(self):
        print('sleepmixin __init__')
        super(SleepMixin, self).__init__()  # Calls object.__init__ on MicroPython, but AnalogSensor.__init__ on CPython

class Waterpump(SleepMixin, AnalogSensor):
    def __init__(self):
        print('waterpump __init__')
        super().__init__()

w = Waterpump()