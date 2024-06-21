import configparser

config = configparser.ConfigParser()
config.read("gpio_config.ini")
pin = config['PIN']
print(pin['VBAT'])
pin.update({"VBAT": '233'})
with open("gpio_config.ini", 'w') as f:
    config.write(f)
