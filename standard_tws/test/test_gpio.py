from utils.functions.gpio import GPIO


if __name__ == '__main__':
    gpio = GPIO()
    gpio.set_vbat_high_level()
    gpio.set_vbat_low_level()
