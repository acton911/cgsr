from threading import Thread
import serial
from utils.exception.exceptions import UARTError, WindowsLowPowerError
import time
import numpy as np
import datetime
from utils.logger.logging_handles import all_logger


class LowPower(Thread):
    def __init__(self, power_port):
        super().__init__()
        self.power_port = power_port
        self.stop_flag = False

    def run(self) -> None:
        try:
            self.power_port = serial.Serial(self.power_port, baudrate=9600, timeout=0)
        except serial.serialutil.SerialException:
            raise UARTError('程控电源端口:{}被占用或端口设置错误，请检查端口是否填写正确并重新运行'.format(self.power_port))
        self.power_port.write('syst:rem\r\n'.encode('utf-8'))
        while True:
            time.sleep(0.001)
            if self.stop_flag:
                self.power_port.close()
                break

    def get_current_volt(self, mode, max_electric=6, max_rate=30, check_time=60, check_frequency=1):
        '''
        进入慢时钟后存在偶有唤醒的正常现象，故比对耗流值过大时所占比例作为主要参考依据
        :param max_electric: 设定最大电流值
        :param max_rate: 设定超过耗流标准值最大比例
        :param check_time:  检测耗流时长
        :param check_frequency:  每隔多久检测一次耗流
        :param mode:  0，进入慢时钟后检测耗流；1，退出慢时钟后检测耗流值
        :return:
        '''
        get_volt_start_timestamp = time.time()
        volt_list = []
        time.sleep(1)
        all_logger.info("开始获取耗流值")
        while True:
            time.sleep(0.001)
            self.power_port.write('meas:curr?\r\n'.encode('UTF-8'))
            return_value = self.power_port.readline().decode('utf-8', 'ignore')
            if time.time() - get_volt_start_timestamp > check_time:  # 到达检测时间
                upset_list = [volt for volt in volt_list if volt > max_electric]  # 电流大于设定值时加入此列表
                curr_avg = np.round(np.mean(volt_list), 2)  # 计算电流平均值
                real_rate = round(len(upset_list) / len(volt_list), 2) * 100  # 大于设定值的比率
                if mode == 0:
                    if real_rate > max_rate:
                        all_logger.info('进入睡眠后休眠耗流值偏高频率为{}%，频率过大'.format(real_rate))
                        if curr_avg > max_electric:
                            all_logger.info(['[{}] 进入睡眠后耗流平均值实测为{}ma'.format(datetime.datetime.now(), curr_avg)])
                            raise WindowsLowPowerError('进入睡眠后模块平均耗流值高于{}ma，未进入慢时钟'.format(max_electric))
                        else:
                            all_logger.info(['[{}] 进入睡眠后耗流平均值实测为{}ma'.format(datetime.datetime.now(), curr_avg)])
                    else:
                        all_logger.info('进入睡眠后耗流值偏高频率为{}%，频率正常'.format(real_rate))
                        all_logger.info(['[{}] 进入睡眠后耗流平均值实测为{}ma'.format(datetime.datetime.now(), curr_avg)])
                elif mode == 1:
                    if real_rate > max_rate:
                        all_logger.info('退出睡眠后耗流值偏高频率为{}%，频率正常'.format(real_rate))
                        all_logger.info(['[{}] 退出睡眠后耗流平均值实测为{}ma'.format(datetime.datetime.now(), curr_avg)])
                    else:
                        all_logger.info('退出睡眠后耗流值偏高频率为{}%，频率过低'.format(real_rate))
                        all_logger.info(['[{}] 退出睡眠后耗流平均值实测为{}ma'.format(datetime.datetime.now(), curr_avg)])
                        raise WindowsLowPowerError('模块平均耗流值低于{}ma，未退出慢时钟'.format(max_electric))
                break
            if return_value != '':
                current_voltage = float(return_value) * 1000
                all_logger.info(['[{} power] {} ma'.format(datetime.datetime.now(), round(current_voltage, 4))])
                volt_list.append(current_voltage)
            time.sleep(check_frequency)

    def stop(self):
        self.stop_flag = True
        time.sleep(1)


if __name__ == '__main__':
    lp = LowPower('COM26')
    lp.start()
    time.sleep(10)
    print('stop')
    lp.stop()
    lp.join()
    time.sleep(10)
