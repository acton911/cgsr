from machine import Pin, Timer, PWM
import utime
import _thread


class Light:
    def __init__(self, pin, on_duration, off_duration, freq):
        self.__current_value = 0
        self.__light_pin = Pin(pin, Pin.OUT)
        self.__count = 0
        self.__on_count = int(on_duration/freq)
        self.__off_count = int(off_duration/freq)
        self.__closed = False
        
    def keep_on(self):
        if self.__closed:
            self.__closed = False
        if self.__count <= self.__on_count:
            if self.__current_value != 1:
                self.__light_pin.value(1)
                self.__current_value = 1
        elif self.__on_count < self.__count <= self.__on_count + self.__off_count:
            if self.__current_value != 0:
                self.__light_pin.value(0)
                self.__current_value = 0
        else:
            self.__light_pin.value(1)
            self.__count = 0
        self.__count += 1
    
    def keep_off(self):
        if not self.__closed:
            self.__light_pin.value(0)
            self.__count = 0
            self.__current_value = 0
            self.__closed = True


free = True
testing = False
breakdown = False
RED_LED_PIN = 7
BLUE_LED_PIN = 8
GREEN_LED_PIN = 9
sleep_time = 0.01
red_light = Light(RED_LED_PIN, 0.25, 0.25, sleep_time)
blue_light = Light(BLUE_LED_PIN, 1.5, 0.5, sleep_time)


def run():    
    pwm = PWM(Pin(GREEN_LED_PIN))
    pwm.freq(100)
    duty = 0
    intervel = 164
    while True:
        if free:
            duty += intervel
            if duty > 32768:
                duty = 32768
                intervel = -164
            if duty < 0:
                duty = 0
                intervel = 164
            if duty in [0, 32768]:
                utime.sleep(0.5)
            pwm.duty_u16(duty)
        else:
            pwm.duty_u16(0)
        if testing:
            blue_light.keep_on()
        else:
            blue_light.keep_off()
        if breakdown:
            red_light.keep_on()
        else:
            red_light.keep_off()
        
        
        utime.sleep(sleep_time)

def start():
    _thread.start_new_thread(run, ())


def set_test():
    global free, testing, breakdown
    breakdown = False
    free = False
    testing = True


def set_free():
    global free, testing, breakdown
    breakdown = False
    free = True
    testing = False


def set_free_with_breakdown():
    global free, testing, breakdown
    breakdown = True
    free = True
    testing = False

