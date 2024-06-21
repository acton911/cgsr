import serial
from threading import Thread
from utils.exception.exceptions import UARTError
from utils.logger.logging_handles import all_logger
import time


class Uart(Thread):
    def __init__(self, uart_port):
        super().__init__()
        self.uart_port = uart_port
        self.stop_flag = False

    def run(self):
        try:
            self.uart_port = serial.Serial(self.uart_port, baudrate=115200, timeout=0)
            self.set_dtr_false()
        except serial.serialutil.SerialException:
            raise UARTError('UART端口:{}被占用或端口设置错误，请检查端口是否填写正确并重新运行'.format(self.uart_port))
        while True:
            time.sleep(0.001)
            if self.stop_flag:
                self.uart_port.close()
                break

    def set_dtr_true(self):
        time.sleep(1)
        self.uart_port.setDTR(True)
        all_logger.info('dtr: {}'.format(self.uart_port.dtr))

    def set_dtr_false(self):
        time.sleep(1)
        self.uart_port.setDTR(False)
        all_logger.info('dtr: {}'.format(self.uart_port.dtr))

    def set_rts_true(self):
        time.sleep(1)
        self.uart_port.setRTS(True)
        all_logger.info('rts: {}'.format(self.uart_port.rts))

    def set_rts_false(self):
        time.sleep(1)
        self.uart_port.setRTS(False)
        all_logger.info('rts: {}'.format(self.uart_port.rts))

    def stop(self):
        self.stop_flag = True


if __name__ == '__main__':
    uart = Uart('COM8')
    uart.setDaemon(True)
    uart.start()
