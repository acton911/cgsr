import os
from modules.logger import logger
from queue import Queue
from .micropython import MicroPythonThread

q_in = Queue()
q_out = Queue()

MicroPythonThread(queue_in=q_out, queue_out=q_in)


def set_1v8(pin_id, pin_level):
    """
    set GPIO voltage to 1.8V(Use PWM).
    :param pin_id: pin number
    :param pin_level: True:1.8v；False:0v
    :return: True, success, False: duty_u16 not between 35000 and 36000
    """
    duty_u16 = 36000 if pin_level else 0
    command = f"""
from machine import PWM, Pin
try:
    if not isinstance(p{pin_id}, PWM):
        del p{pin_id}
        p{pin_id} = PWM(Pin({pin_id}))
except NameError:
    p{pin_id} = PWM(Pin({pin_id}))
p{pin_id}.duty_u16({duty_u16})
print(p{pin_id}.duty_u16())"""

    # send command to micropython thread
    logger.info('q_out.put command')
    q_out.put(command)
    # read micropython thread result in block mode
    return_value = q_in.get()
    logger.info(f"q_in.get: {return_value}")
    # return result
    if return_value.isdigit():
        if pin_level:  # 高电平
            if 35000 < int(return_value) < 37000:  # not usually 36000
                return True
            else:
                return False
        else:  # 低电平
            if int(return_value) == 0:
                return True
            else:
                return False
    else:
        return False


def set_gpio(pin_id, pin_level):
    """
    Set micropython GPIO pin level:
        1. set command as micropython REPL variable;
        2. exec saved variable
    :param pin_id: pin number
    :param pin_level:  pin level
    :return: True if set success else False
    """
    command = f"""
from machine import Pin
try:
    if not isinstance(p{pin_id}, Pin):
        del p{pin_id}
        p{pin_id} = Pin({pin_id}, Pin.OUT)
    elif "OUT" not in repr(p{pin_id}):
        del p{pin_id}
        p{pin_id} = Pin({pin_id}, Pin.OUT)
except NameError:
    p{pin_id} = Pin({pin_id}, Pin.OUT)
p{pin_id}.value({pin_level})
print(p{pin_id}.value())"""

    # send command to micropython thread
    logger.info('q_out.put command')
    q_out.put(command)
    # read micropython thread result in block mode
    return_value = q_in.get()
    logger.info(f"q_in.get: {return_value}")
    # return result
    if return_value.isdigit():
        if str(pin_level) in return_value:
            return True
        else:
            return False
    else:
        return False


def get_gpio(pin_id):
    command = f"""
from machine import Pin
try:
    if not isinstance(p{pin_id}, Pin):
        del p{pin_id}
        p{pin_id} = Pin({pin_id}, Pin.IN)
    elif 'IN' not in repr(p{pin_id}):
        del p{pin_id}
        p{pin_id} = Pin({pin_id}, Pin.IN)
except NameError:
    p{pin_id} = Pin({pin_id}, Pin.IN)
pin_level = p{pin_id}.value()
print(pin_level)"""
    # send command to micropython thread
    logger.info('q_out.put command')
    q_out.put(command)
    # read micropython thread result in block mode
    return_value = q_in.get()
    logger.info(f"q_in.get: {return_value}")

    return return_value


def get_pin_out_level(pin_id):
    command = f"""
from machine import Pin
try:
    if not isinstance(p{pin_id}, Pin):
        del p{pin_id}
        p{pin_id} = Pin({pin_id}, Pin.OUT)
    elif 'OUT' not in repr(p{pin_id}):
        del p{pin_id}
        p{pin_id} = Pin({pin_id}, Pin.OUT)
except NameError:
    p{pin_id} = Pin({pin_id}, Pin.OUT)
pin_level = p{pin_id}.value()
print(pin_level)"""
    # send command to micropython thread
    logger.info('q_out.put command')
    q_out.put(command)
    # read micropython thread result in block mode
    return_value = q_in.get()
    logger.info(f"q_in.get: {return_value}")

    return return_value


def led_set_free():
    """
    Set micropython LED free status
    :return: True if set success else False
    """
    command = """
global free, testing, breakdown
breakdown = False
free = True
testing = False
print([free,testing,breakdown])
"""
    # send command to micropython thread
    logger.info('q_out.put command')
    q_out.put(command)
    # read micropython thread result in block mode
    return_value = q_in.get()
    logger.info(f"q_in.get: {return_value}")
    # return result
    if return_value:
        if '[True, False, False]' in return_value:
            return True
        else:
            return False
    else:
        return False


def led_set_test():
    """
    Set micropython LED test status
    :return: True if set success else False
    """
    command = """
global free, testing, breakdown
breakdown = False
free = False
testing = True
print([free,testing,breakdown])
"""
    # send command to micropython thread
    logger.info('q_out.put command')
    q_out.put(command)
    # read micropython thread result in block mode
    return_value = q_in.get()
    logger.info(f"q_in.get: {return_value}")
    # return result
    if return_value:
        if '[False, True, False]' in return_value:
            return True
        else:
            return False
    else:
        return False


def led_set_free_with_breakdown():
    """
    Set micropython LED free with breakdown status
    :return: True if set success else False
    """
    command = """
global free, testing, breakdown
breakdown = True
free = True
testing = False
print([free,testing,breakdown])
"""
    # send command to micropython thread
    logger.info('q_out.put command')
    q_out.put(command)
    # read micropython thread result in block mode
    return_value = q_in.get()
    logger.info(f"q_in.get: {return_value}")
    # return result
    if return_value:
        if '[True, False, True]' in return_value:
            return True
        else:
            return False
    else:
        return False


def save_led_status(free, testing, breakdown):
    file_path = os.path.join(os.getcwd(), 'led_status.log')
    led_status = f"{free},{testing},{breakdown}"
    with open(file_path, 'w') as f:
        f.write(led_status)
    logger.info(file_path)


def led_set_status(free, testing, breakdown):
    """
    Set micropython LED status
    :return: True if set success else False
    """
    if testing:
        command = f"""
global free, testing, breakdown
breakdown = False
free = False
testing = True
print([free,testing,breakdown])
"""
    elif free and breakdown:
        command = f"""
global free, testing, breakdown
breakdown = True
free = True
testing = False
print([free,testing,breakdown])
"""
    else:
        command = f"""
global free, testing, breakdown
breakdown = False
free = True
testing = False
print([free,testing,breakdown])
"""
    # send command to micropython thread
    logger.info('q_out.put command')
    q_out.put(command)
    # read micropython thread result in block mode
    return_value = q_in.get()
    logger.info(f"q_in.get: {return_value}")
    save_led_status(free, testing, breakdown)
    # return result
    if return_value:
        if testing and '[False, True, False]' in return_value:
            logger.info("OK")
            return True
        elif free and '[True, False, False]' in return_value:
            logger.info("OK")
            return True
        elif free and breakdown and '[True, False, True]' in return_value:
            logger.info("OK")
            return True
        else:
            return False
    else:
        return False


def get_led_set():
    command = """
global free, testing, breakdown
print(f'{free},{testing},{breakdown}')
"""
    # send command to micropython thread
    logger.info('q_out.put command')
    q_out.put(command)
    # read micropython thread result in block mode
    return_value = q_in.get()
    logger.info(f"q_in.get: {return_value}")
    # return result
    if return_value:
        return return_value
    else:
        return False


def led_set(status_key_value):
    """
    Set micropython LED status
    :return: True if set success else False
    """
    command = f"""
global free, testing, breakdown
"""
    if 'free' in status_key_value.keys():
        command_free = f"""
free = {status_key_value['free']}
"""
        command += command_free
    if 'testing' in status_key_value.keys():
        command_free = f"""
testing = {status_key_value['testing']}
"""
        command += command_free
    if 'breakdown' in status_key_value.keys():
        command_free = f"""
breakdown = {status_key_value['breakdown']}
"""
        command += command_free
    command_print = """
print(f'{free},{testing},{breakdown}')
"""
    command += command_print
    # send command to micropython thread
    logger.info('q_out.put command')
    q_out.put(command)
    # read micropython thread result in block mode
    return_value = q_in.get()
    logger.info(f"q_in.get: {return_value}")
    # return result
    if return_value:
        led_value = return_value.split(',')
        logger.info(f"setting success : {status_key_value}")
        if 'free' in status_key_value.keys():
            if led_value[0] == f"{status_key_value['free']}":
                logger.info(f"set free {status_key_value['free']} success")
            else:
                logger.info(f"set free {status_key_value['free']} fail")
                return False
        if 'testing' in status_key_value.keys():
            if led_value[1] == f"{status_key_value['testing']}":
                logger.info(f"set testing {status_key_value['testing']} success")
            else:
                logger.info(f"set testing {status_key_value['testing']} fail")
                return False
        if 'breakdown' in status_key_value.keys():
            if led_value[2] == f"{status_key_value['breakdown']}":
                logger.info(f"set breakdown {status_key_value['breakdown']} success")
            else:
                logger.info(f"set breakdown {status_key_value['breakdown']} fail")
                return False
        save_led_status(led_value[0], led_value[1], led_value[2])
        return True
    else:
        logger.info(f"setting FAIL : {status_key_value}")
        return False
