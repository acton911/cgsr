from modules.logger import logger
import configparser
import sys
import getpass
import os
from collections import deque
from threading import Thread
from queue import Queue
import time
import serial.tools.list_ports
import traceback
import subprocess


class MicroPythonThread(Thread):

    """
    MicropythonThread Thread connect to local serial port, and listening to queue to accept message:
        1. if queue_in dont have message, readline of port and print message
        2. if queue_in received message:
            a. Micro Thread save to message as variable in MicroPython REPL
            b. MicroPython Thread exec saved variable to execute command
            c. MicroPython Thread get execute result and put result into queue_out to tell executor result.
    """

    def __init__(self, queue_in, queue_out):
        super().__init__()
        self.dq = deque()
        self.port = self._get_pico_port()
        self.queue_in = queue_in
        self.queue_out = queue_out
        self.daemon = True
        self.start()
        self.cnt = 3  # 初始化计数器，self.init函数初始化了几个引脚就是几，用于取走队列中的消息，防止错误
        self.file_path = os.path.join(os.getcwd(), 'led_status.log')

    def init(self):
        self._set_gpio_default_high_level("W_DISABLE")
        self._get_gpio_default_high_level("SIM1_DET")
        self._get_gpio_default_high_level("SIM2_DET")

    def read_led_status(self):
        if not os.path.exists(self.file_path):
            logger.info('use default value')
            return True, False, False
        with open(self.file_path, 'r') as f:
            led_status = f.read()
            logger.info(led_status)
            s1, s2, s3 = led_status.split(',')
            if s1 == 'True':
                s1 = True
            else:
                s1 = False
            if s2 == 'True':
                s2 = True
            else:
                s2 = False
            if s3 == 'True':
                s3 = True
            else:
                s3 = False
        return s1, s2, s3

    @staticmethod
    def _get_pico_port():
        for s in serial.tools.list_ports.comports():
            logger.info(f"{s.name}-{s.vid}-{s.pid}")
            if s.vid == 11914 and s.pid == 5:  # 树莓派pico的pid vid，10进制
                if os.name == 'nt':
                    return s.name
                else:
                    return '/dev/' + s.name
        else:
            logger.info("未检测到树莓派Pico，请确认是否接入：\n"
                        "1. 如果使用的是其他开发板(如ESP32/MicroPython)，请手动填写端口号，例如COM3或/dev/ttyUSB1，然后按Enter；\n"
                        "2. 如果使用的是树莓派Pico但是还是提示输入端口号，请联系脚本开发人员修改脚本。")
            return ''

    @staticmethod
    def _get_config_path():
        if os.name == 'nt':
            config_path = os.path.join("C:\\Users", getpass.getuser(), 'gpio_config.ini')
        else:
            config_path = os.path.join('/root', 'gpio_config.ini')
        return config_path

    def _get_gpio_default_high_level(self, gpio_name):
        # get config
        config = configparser.ConfigParser()
        config_path = self._get_config_path()
        config.read(config_path, encoding='gb2312' if os.name == 'nt' else 'utf-8')

        # get pin mapping
        pin = config['PIN']
        id_pin = pin[gpio_name]
        command = f"""from machine import Pin
p{id_pin} = Pin({id_pin}, Pin.IN)
print(p{id_pin}.value())"""

        data = exec_micropython(self.port, command)
        logger.info(f"_get_gpio_default_high_level ret: {data}")

    def _start_led(self):
        free, testing, breakdown = self.read_led_status()
        command = f"""
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
reset_flag = False
free = {free}
testing = {testing}
breakdown = {breakdown}
RED_LED_PIN = 7
BLUE_LED_PIN = 9
GREEN_LED_PIN = 8
sleep_time = 0.01
red_light = Light(RED_LED_PIN, 0.25, 0.25, sleep_time)
blue_light = Light(BLUE_LED_PIN, 1.5, 0.5, sleep_time)
def run():
    global reset_flag
    pwm = PWM(Pin(GREEN_LED_PIN))
    pwm.freq(100)
    duty = 0
    intervel = 164
    start_time = utime.time()
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
        if utime.time()-start_time > 61:
            if reset_flag:
                machine.reset()
            else:
                reset_flag = True
            start_time = utime.time()
        utime.sleep(sleep_time)
def start():
    _thread.start_new_thread(run, ())
start()
print([free,testing,breakdown])
"""
        data = exec_micropython(self.port, command)
        logger.info(f"_start_led: {data}")

    def _get_led_status(self):
        command = """
global free, testing, breakdown
print([free,testing,breakdown])
        """
        data = exec_micropython(self.port, command)
        logger.info(f"_get_led_status: {data}")
        self.led_free = data[0]
        self.led_testing = data[1]
        self.led_breakdown = data[2]

    def _set_gpio_default_high_level(self, gpio_name):
        # get config
        config = configparser.ConfigParser()
        config_path = self._get_config_path()
        config.read(config_path, encoding='gb2312' if os.name == 'nt' else 'utf-8')

        # get pin mapping
        pin = config['PIN']
        id_pin = pin[gpio_name]
        command = f"""from machine import Pin
p{id_pin} = Pin({id_pin}, Pin.OUT)
p{id_pin}.value(1)
print(p{id_pin}.value())"""

        data = exec_micropython(self.port, command)
        logger.info(f"_set_gpio_default_high_level ret: {data}")

    def inject_watchdog(self):
        watchdog = f"""
reset_flag = False

def watchdog(cb):
    global reset_flag
    if reset_flag:
        machine.reset()
    else:
        reset_flag = True

scheduler_wd = machine.Timer(-1)
scheduler_wd.init(period=61000, mode=machine.Timer.PERIODIC, callback=watchdog)
        """
        exec_micropython(self.port, watchdog, soft_reset=True)

    def rebind_xhci(self):
        """
        Ubuntu下可能存在USB口全部不加载的情况，尝试rebind xHCI。
        :return: None
        """
        # 先刷新
        logger.error("Linux下获取Pico端口失败，尝试刷新xHCI")
        cwd = os.path.abspath(os.path.dirname(sys.argv[0]))
        bash_path = os.path.join(cwd, 'rebind_xhci.sh')
        logger.info(f"bash_path: {bash_path}")
        logger.info(subprocess.getoutput(f'chmod 777 {bash_path}'))
        output = subprocess.getoutput(bash_path)
        logger.info(f"bash_path: {output}")

        # 等待3S重新获取
        logger.info("wait 3 seconds.")
        time.sleep(3)
        self.port = self._get_pico_port()

        # 获取DMESG log
        logger.info("获取DMESG log")
        dmesg_log_path = os.path.join(cwd, 'dmesg.log')
        logger.info(f"save dmesg log into: {dmesg_log_path}")
        output = subprocess.getoutput(f'dmesg > {dmesg_log_path}')
        logger.info(f"dmesg > {dmesg_log_path} : '{output}'")

    def run(self):

        while True:

            try:

                self.port = self._get_pico_port()  # 每次运行前重新获取Pico 端口
                if self.port == '' and os.name != 'nt':  # Ubuntu下可能存在USB口全部不加载的情况，尝试rebind xHCI
                    self.rebind_xhci()

                self._start_led()  # 启动LED状态灯
                self.init()  # 初始化引脚状态
                # self.inject_watchdog()

                with Pyboard(device=self.port, baudrate=115200, write_timeout=10) as pyb:  # 10秒钟的 Write timeout
                    logger.info(f"Port: {self.port} opened success.")

                    start_time = time.perf_counter()
                    while True:
                        # get command
                        time.sleep(0.001)
                        queue_info = None if self.queue_in.empty() else self.queue_in.get()

                        # exec command
                        if queue_info:
                            pyb.enter_raw_repl(soft_reset=False)
                            logger.info(f"start exec command: {queue_info}")
                            exec_start_time = time.time()
                            ret, ret_err = pyb.exec_raw(queue_info.encode("utf-8"))
                            self.queue_out.put(ret)
                            logger.info(f"ret: {ret}; ret_err: {ret_err}")
                            logger.info(f"exec time used: {round(time.time() - exec_start_time, 2) * 1000}ms")
                            pyb.exit_raw_repl()

                        # reset watchdog
                        if time.perf_counter() - start_time > 60:  # set watchdog after about 60s.
                            pyb.enter_raw_repl(soft_reset=False)
                            exec_start_time = time.time()
                            ret, ret_err = pyb.exec_raw('reset_flag = False')
                            logger.info(f"exec command: 'reset_flag = False', "
                                        f"ret: {repr(ret)}, ret_err: {repr(ret_err)}, "
                                        f"time used: {round(time.time() - exec_start_time, 3)}s.")
                            logger.info(f"reset watchdog: {round(time.perf_counter() - start_time, 0)}s")
                            pyb.exit_raw_repl()
                            start_time = time.perf_counter()  # 重置

            except Exception as e:
                logger.error(f"\nMicroPython APP异常，等待5S重启，请检查USB线连接状态和树莓派状态，异常原因：{e}")
                logger.debug(traceback.format_exc())
                time.sleep(5)


class PyboardError(Exception):
    pass


class Pyboard:
    def __init__(self, device, baudrate=115200, exclusive=True, write_timeout=None):
        self.in_raw_repl = False
        self.use_raw_paste = True
        self.device = device
        self.baudrate = baudrate
        self.exclusive = exclusive
        self.write_timeout = write_timeout

    def __enter__(self):
        # Set options, and exclusive if pyserial supports it
        serial_kwargs = {"baudrate": self.baudrate, "interCharTimeout": 1}
        if serial.__version__ >= "3.3":
            serial_kwargs["exclusive"] = self.exclusive
            serial_kwargs['write_timeout'] = self.write_timeout
        self.serial = serial.Serial(self.device, **serial_kwargs)

        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def close(self):
        self.serial.close()

    def read_until(self, min_num_bytes, ending, timeout=10, data_consumer=None):
        # if data_consumer is used then data is not accumulated and the ending must be 1 byte long
        assert data_consumer is None or len(ending) == 1

        data = self.serial.read(min_num_bytes)
        if data_consumer:
            data_consumer(data)
        timeout_count = 0
        while True:
            if data.endswith(ending):
                break
            elif self.serial.inWaiting() > 0:
                new_data = self.serial.read(1)
                if data_consumer:
                    data_consumer(new_data)
                    data = new_data
                else:
                    data = data + new_data
                timeout_count = 0
            else:
                timeout_count += 1
                if timeout is not None and timeout_count >= 100 * timeout:
                    break
                time.sleep(0.01)
        return data

    def enter_raw_repl(self, soft_reset=True):
        logger.info("#" * 80)
        logger.info(f'0 enter_raw_repl, soft_reset: {soft_reset}')
        self.serial.write(b"\r\x03\x03")  # ctrl-C twice: interrupt any running program

        # flush input (without relying on serial.flushInput())
        n = self.serial.inWaiting()
        while n > 0:
            self.serial.read(n)
            n = self.serial.inWaiting()

        self.serial.write(b"\r\x01")  # ctrl-A: enter raw REPL

        if soft_reset:
            data = self.read_until(1, b"raw REPL; CTRL-B to exit\r\n>")
            if not data.endswith(b"raw REPL; CTRL-B to exit\r\n>"):
                logger.error(data)
                raise PyboardError("could not enter raw repl")

            self.serial.write(b"\x04")  # ctrl-D: soft reset

            # Waiting for "soft reboot" independently to "raw REPL" (done below)
            # allows boot.py to print, which will show up after "soft reboot"
            # and before "raw REPL".
            data = self.read_until(1, b"soft reboot\r\n")
            if not data.endswith(b"soft reboot\r\n"):
                logger.error(data)
                raise PyboardError("could not enter raw repl")

        data = self.read_until(1, b"raw REPL; CTRL-B to exit\r\n")
        if not data.endswith(b"raw REPL; CTRL-B to exit\r\n"):
            logger.error(data)
            raise PyboardError("could not enter raw repl")

        self.in_raw_repl = True
        logger.info(f'1 enter_raw_repl, soft_reset: {soft_reset}')

    def exit_raw_repl(self):
        logger.info("0 exit raw repl")
        self.serial.write(b"\r\x02")  # ctrl-B: enter friendly REPL
        self.in_raw_repl = False
        logger.info("1 exit raw repl")

    def follow(self, timeout, data_consumer=None):
        # wait for normal output
        data = self.read_until(1, b"\x04", timeout=timeout, data_consumer=data_consumer)
        if not data.endswith(b"\x04"):
            raise PyboardError("timeout waiting for first EOF reception")
        data = data[:-1].strip()

        # wait for error output
        data_err = self.read_until(1, b"\x04", timeout=timeout)
        if not data_err.endswith(b"\x04"):
            raise PyboardError("timeout waiting for second EOF reception")
        data_err = data_err[:-1].strip()

        # return normal and error output
        return data.decode('utf-8'), data_err.decode('utf-8')

    def raw_paste_write(self, command_bytes):
        # Read initial header, with window size.
        data = self.serial.read(2)
        window_size = data[0] | data[1] << 8
        window_remain = window_size

        # Write out the command_bytes data.
        i = 0
        while i < len(command_bytes):
            while window_remain == 0 or self.serial.inWaiting():
                data = self.serial.read(1)
                if data == b"\x01":
                    # Device indicated that a new window of data can be sent.
                    window_remain += window_size
                elif data == b"\x04":
                    # Device indicated abrupt end.  Acknowledge it and finish.
                    self.serial.write(b"\x04")
                    return
                else:
                    # Unexpected data from device.
                    raise PyboardError(f"unexpected read during raw paste: {data}")
            # Send out as much data as possible that fits within the allowed window.
            b = command_bytes[i: min(i + window_remain, len(command_bytes))]
            self.serial.write(b)
            window_remain -= len(b)
            i += len(b)

        # Indicate end of data.
        self.serial.write(b"\x04")

        # Wait for device to acknowledge end of data.
        data = self.read_until(1, b"\x04")
        if not data.endswith(b"\x04"):
            raise PyboardError(f"could not complete raw paste: {data}")

    def exec_raw_no_follow(self, command):
        if isinstance(command, bytes):
            command_bytes = command
        else:
            command_bytes = bytes(command, encoding="utf8")

        # check we have a prompt
        data = self.read_until(1, b">")
        if not data.endswith(b">"):
            raise PyboardError("could not enter raw repl")

        if self.use_raw_paste:
            # Try to enter raw-paste mode.
            self.serial.write(b"\x05A\x01")
            data = self.serial.read(2)
            if data == b"R\x00":
                # Device understood raw-paste command but doesn't support it.
                pass
            elif data == b"R\x01":
                # Device supports raw-paste mode, write out the command using this mode.
                return self.raw_paste_write(command_bytes)
            else:
                # Device doesn't support raw-paste, fall back to normal raw REPL.
                data = self.read_until(1, b"w REPL; CTRL-B to exit\r\n>")
                if not data.endswith(b"w REPL; CTRL-B to exit\r\n>"):
                    logger.error(data)
                    raise PyboardError("could not enter raw repl")
            # Don't try to use raw-paste mode again for this connection.
            self.use_raw_paste = False

        # Write command using standard raw REPL, 256 bytes every 10ms.
        for i in range(0, len(command_bytes), 256):
            self.serial.write(command_bytes[i: min(i + 256, len(command_bytes))])
            time.sleep(0.01)
        self.serial.write(b"\x04")

        # check if we could exec command
        data = self.serial.read(2)
        if data != b"OK":
            raise PyboardError("could not exec command (response: %r)" % data)

    def exec_raw(self, command, timeout=10, data_consumer=None):
        self.exec_raw_no_follow(command)
        return self.follow(timeout, data_consumer)


def exec_micropython(port, command, follow=True, soft_reset=False):
    ret = ''
    with Pyboard(port, 115200) as pyb:
        pyb.enter_raw_repl(soft_reset)
        logger.info(f"follow: {follow}")
        logger.info(f"exec command: {command}")
        start_time = time.time()
        if follow:
            ret, ret_err = pyb.exec_raw(command.encode("utf-8"))
            logger.info(f"\nret: {ret}\nret_err: {ret_err}")
        else:
            pyb.exec_raw_no_follow(command.encode("utf-8"))
        logger.info(f"exec time used: {round(time.time() - start_time, 2) * 1000}ms")

        # exiting raw-REPL just drops to friendly-REPL mode
        pyb.exit_raw_repl()
    return ret


if __name__ == '__main__':

    pin_id = 2
    pin_level0 = 0
    pin_level1 = 1

    command1 = f"""from machine import Pin
if 'p{pin_id}' not in globals():
    p{pin_id} = Pin({pin_id}, Pin.OUT)
p{pin_id}.value({pin_level1})
print(p{pin_id}.value())"""

    command0 = f"""from machine import Pin
if 'p{pin_id}' not in globals():
    p{pin_id} = Pin({pin_id}, Pin.OUT)
p{pin_id}.value({pin_level0})
print(p{pin_id}.value())"""

    q_out = Queue()
    q_in = Queue()
    micropython = MicroPythonThread(queue_in=q_out, queue_out=q_in)

    while True:
        time.sleep(1)
        q_out.put(command1)
        time.sleep(1)
        q_out.put(command0)
