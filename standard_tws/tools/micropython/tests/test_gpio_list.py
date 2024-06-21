# 此文件保存着GPIO的一些信息，仅供参考

import time
import logging
import requests
import configparser
from getpass import getuser
import os

logging.basicConfig(level=logging.DEBUG)
all_logger = logging.getLogger(__name__)


class GPIOError(Exception):
    pass


class GPIO:

    def __init__(self):
        # read profile
        self.config = configparser.ConfigParser()
        self.config_name = 'gpio_config.ini'
        self.config_path = os.path.join("C:\\Users", getuser(), 'gpio_config.ini') \
            if os.name == 'nt' else os.path.join("/root", 'gpio_config.ini')
        if os.name == 'nt':
            self.config.read(self.config_path)
        else:
            self.config.read(self.config_path, encoding='gb2312')
        # get pin mapping
        self.pin = self.config['PIN']
        self.pin_vbat = self.pin.getint('VBAT')
        self.pin_reset = self.pin['RESET']
        self.pin_pwk = self.pin['PWK']
        self.pin_dtr = self.pin['DTR']
        self.pin_sim1_det = self.pin['SIM1_DET']
        self.pin_sim2_det = self.pin['SIM2_DET']
        self.pin_w_disable = self.pin['W_DISABLE']
        self.pin_ri = self.pin['RI']
        self.pin_dcd = self.pin['DCD']
        self.pin_gpio_86 = self.pin['GPIO_86']
        self.pin_net_mode = self.pin['NET_MODE']
        self.pin_net_status = self.pin['NET_STATUS']
        self.pin_wwan_led = self.pin['WWAN_LED']
        self.flag = self.pin.getint("FLAG", 0)  # noqa  RG项目，flag为0；RM项目，flag为1。

    def set_vbat_high_level(self):
        if self.flag == 0:  # RG项目
            all_logger.info('RG项目设置VBAT引脚为高电平，EVB断电')

            # 请求ESP32线程
            requests_data = {"id": self.pin_vbat, "level": 1}
            r = requests.post('http://127.0.0.1:55555/set', json=requests_data)

            # 状态码异常
            if r.status_code != 200:
                raise GPIOError(f"设置VBAT引脚{self.pin_vbat}为高电平失败，status_code: {r.status_code}")

            # 返回值异常，返回数据为 {'error': f"fail to set GPIO x level"}
            if r.json().get('error', False):
                raise GPIOError(f"设置VBAT引脚{self.pin_vbat}为高电平失败，JSON: {r.json()}")
            else:
                all_logger.info(f'设置VBAT引脚为高电平成功，状态码: {r.status_code}，返回值:{r.json()}')
        else:
            all_logger.info('RM项目设置VBAT引脚为低电平，EVB断电')

            # 请求ESP32线程
            requests_data = {"id": self.pin_vbat, "level": 0}
            r = requests.post('http://127.0.0.1:55555/set', json=requests_data)

            # 状态码异常
            if r.status_code != 200:
                raise GPIOError(f"设置VBAT引脚{self.pin_vbat}为低电平失败，status_code: {r.status_code}")

            # 返回值异常，返回数据为 {'error': f"fail to set GPIO x level"}
            if r.json().get('error', False):
                raise GPIOError(f"设置VBAT引脚{self.pin_vbat}为低电平失败，JSON: {r.json()}")
            else:
                all_logger.info(f'设置VBAT引脚为低电平成功，状态码: {r.status_code}，返回值: {r.json()}')

    def set_vbat_low_level(self):
        if self.flag == 0:
            all_logger.info('RG项目设置VBAT引脚为低电平，EVB上电')

            # 请求ESP32线程
            requests_data = {"id": self.pin_vbat, "level": 0}
            r = requests.post('http://127.0.0.1:55555/set', json=requests_data)

            # 状态码异常
            if r.status_code != 200:
                raise GPIOError(f"设置VBAT引脚{self.pin_vbat}为低电平失败，status_code: {r.status_code}")

            # 返回值异常，返回数据为 {'error': f"fail to set GPIO x level"}
            if r.json().get('error', False):
                raise GPIOError(f"设置VBAT引脚{self.pin_vbat}为低电平失败，JSON: {r.json()}")
            else:
                all_logger.info(f'设置VBAT引脚为低电平成功，状态码: {r.status_code}，返回值: {r.json()}')
        else:
            all_logger.info('RM项目设置VBAT引脚为高电平，EVB上电')

            # 请求ESP32线程
            requests_data = {"id": self.pin_vbat, "level": 1}
            r = requests.post('http://127.0.0.1:55555/set', json=requests_data)

            # 状态码异常
            if r.status_code != 200:
                raise GPIOError(f"设置VBAT引脚{self.pin_vbat}为高电平失败，status_code: {r.status_code}")

            # 返回值异常，返回数据为 {'error': f"fail to set GPIO x level"}
            if r.json().get('error', False):
                raise GPIOError(f"设置VBAT引脚{self.pin_vbat}为高电平失败，JSON: {r.json()}")
            else:
                all_logger.info(f'设置VBAT引脚为高电平成功，状态码: {r.status_code}，返回值:{r.json()}')

    def set_dtr_high_level(self):
        all_logger.info('设置DTR引脚为高电平')

        # 请求ESP32线程
        requests_data = {"id": self.pin_dtr, "level": 1}
        r = requests.post('http://127.0.0.1:55555/set', json=requests_data)

        # 状态码异常
        if r.status_code != 200:
            raise GPIOError(f"设置DTR引脚{self.pin_vbat}为高电平失败，status_code: {r.status_code}")

        # 返回值异常，返回数据为 {'error': f"fail to set GPIO x level"}
        if r.json().get('error', False):
            raise GPIOError(f"设置DTR引脚{self.pin_vbat}为高电平失败，JSON: {r.json()}")
        else:
            all_logger.info(f'设置DTR引脚为高电平成功，状态码: {r.status_code}，返回值:{r.json()}')

    def set_dtr_low_level(self):
        all_logger.info('设置DTR引脚为低电平')

        # 请求ESP32线程
        requests_data = {"id": self.pin_dtr, "level": 0}
        r = requests.post('http://127.0.0.1:55555/set', json=requests_data)

        # 状态码异常
        if r.status_code != 200:
            raise GPIOError(f"设置DTR引脚{self.pin_vbat}为低电平失败，status_code: {r.status_code}")

        # 返回值异常，返回数据为 {'error': f"fail to set GPIO x level"}
        if r.json().get('error', False):
            raise GPIOError(f"设置DTR引脚{self.pin_vbat}为低电平失败，JSON: {r.json()}")
        else:
            all_logger.info(f'设置DTR引脚为低电平成功，状态码: {r.status_code}，返回值: {r.json()}')

    def set_pwk_low_level(self):
        """
        设置powerkey引脚低电平
        :return:
        """
        all_logger.info('设置Powerkey引脚为低电平')

        # 请求ESP32线程
        requests_data = {"id": self.pin_pwk, "level": 0}
        r = requests.post('http://127.0.0.1:55555/set', json=requests_data)

        # 状态码异常
        if r.status_code != 200:
            raise GPIOError(f"设置Powerkey引脚{self.pin_pwk}为低电平失败，status_code: {r.status_code}")

        # 返回值异常，返回数据为 {'error': f"fail to set GPIO x level"}
        if r.json().get('error', False):
            raise GPIOError(f"设置Powerkey引脚{self.pin_pwk}为低电平失败，JSON: {r.json()}")
        else:
            all_logger.info(f'设置Powerkey引脚为低电平成功，状态码: {r.status_code}，返回值: {r.json()}')

    def set_pwk_high_level(self):
        """
        设置powerkey引脚高电平
        :return:
        """
        all_logger.info('设置Powerkey引脚为高电平')

        # 请求ESP32线程
        requests_data = {"id": self.pin_pwk, "level": 1}
        r = requests.post('http://127.0.0.1:55555/set', json=requests_data)

        # 状态码异常
        if r.status_code != 200:
            raise GPIOError(f"设置Powerkey引脚{self.pin_pwk}为高电平失败，status_code: {r.status_code}")

        # 返回值异常，返回数据为 {'error': f"fail to set GPIO x level"}
        if r.json().get('error', False):
            raise GPIOError(f"设置Powerkey引脚{self.pin_pwk}为高电平失败，JSON: {r.json()}")
        else:
            all_logger.info(f'设置Powerkey引脚为高电平成功，状态码: {r.status_code}，返回值:{r.json()}')

    def set_vbat_low_level_and_pwk(self):
        if self.flag == 0:  # RG
            # TODO：此处时间需要优化
            self.set_vbat_low_level()
            time.sleep(1)
            self.set_pwk_low_level()  # RG需要先拉低再拉高再拉低关机
            time.sleep(1)
            self.set_pwk_high_level()
            time.sleep(1)
            self.set_pwk_low_level()
        else:
            self.set_vbat_low_level()  # 上电
            time.sleep(1)
            self.set_pwk_high_level()

    def set_reset_high_level(self):
        """
        设置Reset引脚高电平
        :return:
        """
        all_logger.info('设置Reset引脚为高电平')

        # 请求ESP32线程
        requests_data = {"id": self.pin_reset, "level": 1}
        r = requests.post('http://127.0.0.1:55555/set', json=requests_data)

        # 状态码异常
        if r.status_code != 200:
            raise GPIOError(f"设置Reset引脚{self.pin_reset}为高电平失败，status_code: {r.status_code}")

        # 返回值异常，返回数据为 {'error': f"fail to set GPIO x level"}
        if r.json().get('error', False):
            raise GPIOError(f"设置Reset引脚{self.pin_reset}为高电平失败，JSON: {r.json()}")
        else:
            all_logger.info(f'设置Reset引脚为高电平成功，状态码: {r.status_code}，返回值:{r.json()}')

    def set_reset_low_level(self):
        """
        设置Reset引脚低电平
        :return:
        """
        all_logger.info('设置Reset引脚为低电平')

        # 请求ESP32线程
        requests_data = {"id": self.pin_reset, "level": 0}
        r = requests.post('http://127.0.0.1:55555/set', json=requests_data)

        # 状态码异常
        if r.status_code != 200:
            raise GPIOError(f"设置Reset引脚{self.pin_reset}为低电平失败，status_code: {r.status_code}")

        # 返回值异常，返回数据为 {'error': f"fail to set GPIO x level"}
        if r.json().get('error', False):
            raise GPIOError(f"设置Reset引脚{self.pin_reset}为低电平失败，JSON: {r.json()}")
        else:
            all_logger.info(f'设置Reset引脚为低电平成功，状态码: {r.status_code}，返回值: {r.json()}')

    def set_sim1_det_high_level(self):
        all_logger.info('设置SIM1 DET引脚为高电平')

        # 请求ESP32线程
        requests_data = {"id": self.pin_sim1_det}
        r = requests.post('http://127.0.0.1:55555/get', json=requests_data)   # 对于SIM_DET引脚，拉高直接调用_get_gpio方法即可

        # 状态码异常
        if r.status_code != 200:
            raise GPIOError(f"设置SIM1 DET引脚{self.pin_sim1_det}为高电平失败，status_code: {r.status_code}")

        # 返回值异常，返回数据为 {'error': f"fail to set GPIO x level"}
        if r.json().get('error', False):
            raise GPIOError(f"设置SIM1 DET引脚{self.pin_sim1_det}为高电平失败，JSON: {r.json()}")
        else:
            all_logger.info(f'设置SIM1 DET引脚为高电平成功，状态码: {r.status_code}，返回值:{r.json()}')

    def set_sim1_det_low_level(self):
        all_logger.info('设置SIM1 DET引脚为低电平')

        # 请求ESP32线程
        requests_data = {"id": self.pin_sim1_det, "level": 0}
        r = requests.post('http://127.0.0.1:55555/set', json=requests_data)

        # 状态码异常
        if r.status_code != 200:
            raise GPIOError(f"设置SIM1 DET引脚{self.pin_sim1_det}为低电平失败，status_code: {r.status_code}")

        # 返回值异常，返回数据为 {'error': f"fail to set GPIO x level"}
        if r.json().get('error', False):
            raise GPIOError(f"设置SIM1 DET引脚{self.pin_sim1_det}为低电平失败，JSON: {r.json()}")
        else:
            all_logger.info(f'设置SIM1 DET引脚为低电平成功，状态码: {r.status_code}，返回值: {r.json()}')

    def set_sim2_det_high_level(self):
        all_logger.info('设置SIM2 DET引脚为高电平')

        # 请求ESP32线程
        requests_data = {"id": self.pin_sim2_det}
        r = requests.post('http://127.0.0.1:55555/get', json=requests_data)   # 对于SIM_DET引脚，拉高直接调用_get_gpio方法即可

        # 状态码异常
        if r.status_code != 200:
            raise GPIOError(f"设置SIM2 DET引脚{self.pin_sim2_det}为高电平失败，status_code: {r.status_code}")

        # 返回值异常，返回数据为 {'error': f"fail to set GPIO x level"}
        if r.json().get('error', False):
            raise GPIOError(f"设置SIM2 DET引脚{self.pin_sim2_det}为高电平失败，JSON: {r.json()}")
        else:
            all_logger.info(f'设置SIM2 DET引脚为高电平成功，状态码: {r.status_code}，返回值:{r.json()}')

    def set_sim2_det_low_level(self):
        all_logger.info('设置SIM2 DET引脚为低电平')

        # 请求ESP32线程
        requests_data = {"id": self.pin_sim2_det, "level": 0}
        r = requests.post('http://127.0.0.1:55555/set', json=requests_data)

        # 状态码异常
        if r.status_code != 200:
            raise GPIOError(f"设置SIM2 DET引脚{self.pin_sim2_det}为低电平失败，status_code: {r.status_code}")

        # 返回值异常，返回数据为 {'error': f"fail to set GPIO x level"}
        if r.json().get('error', False):
            raise GPIOError(f"设置SIM2 DET引脚{self.pin_sim2_det}为低电平失败，JSON: {r.json()}")
        else:
            all_logger.info(f'设置SIM2 DET引脚为低电平成功，状态码: {r.status_code}，返回值: {r.json()}')

    def set_w_disable_high_level(self):
        all_logger.info('设置W_DISABLE引脚为高电平')

        # 请求ESP32线程
        requests_data = {"id": self.pin_w_disable, "level": 1}
        r = requests.post('http://127.0.0.1:55555/set', json=requests_data)

        # 状态码异常
        if r.status_code != 200:
            raise GPIOError(f"设置W_DISABLE引脚{self.pin_w_disable}为高电平失败，status_code: {r.status_code}")

        # 返回值异常，返回数据为 {'error': f"fail to set GPIO x level"}
        if r.json().get('error', False):
            raise GPIOError(f"设置W_DISABLE引脚{self.pin_w_disable}为高电平失败，JSON: {r.json()}")
        else:
            all_logger.info(f'设置W_DISABLE引脚为高电平成功，状态码: {r.status_code}，返回值:{r.json()}')

    def set_w_disable_low_level(self):
        all_logger.info('设置W_DISABLE引脚为低电平')

        # 请求ESP32线程
        requests_data = {"id": self.pin_w_disable, "level": 0}
        r = requests.post('http://127.0.0.1:55555/set', json=requests_data)

        # 状态码异常
        if r.status_code != 200:
            raise GPIOError(f"设置W_DISABLE引脚{self.pin_w_disable}为低电平失败，status_code: {r.status_code}")

        # 返回值异常，返回数据为 {'error': f"fail to set GPIO x level"}
        if r.json().get('error', False):
            raise GPIOError(f"设置W_DISABLE引脚{self.pin_w_disable}为低电平失败，JSON: {r.json()}")
        else:
            all_logger.info(f'设置W_DISABLE引脚为低电平成功，状态码: {r.status_code}，返回值: {r.json()}')

    def set_gpio_86_high_level(self):
        all_logger.info('设置GPIO 86引脚为高电平')

        # 请求ESP32线程
        requests_data = {"id": self.pin_gpio_86, "level": 1}
        r = requests.post('http://127.0.0.1:55555/set', json=requests_data)

        # 状态码异常
        if r.status_code != 200:
            raise GPIOError(f"设置GPIO 86引脚{self.pin_gpio_86}为高电平失败，status_code: {r.status_code}")

        # 返回值异常，返回数据为 {'error': f"fail to set GPIO x level"}
        if r.json().get('error', False):
            raise GPIOError(f"设置GPIO 86引脚{self.pin_gpio_86}为高电平失败，JSON: {r.json()}")
        else:
            all_logger.info(f'设置GPIO 86引脚为高电平成功，状态码: {r.status_code}，返回值:{r.json()}')

    def set_gpio_86_low_level(self):
        all_logger.info('设置GPIO 86引脚为低电平')

        # 请求ESP32线程
        requests_data = {"id": self.pin_gpio_86, "level": 0}
        r = requests.post('http://127.0.0.1:55555/set', json=requests_data)

        # 状态码异常
        if r.status_code != 200:
            raise GPIOError(f"设置GPIO 86引脚{self.pin_gpio_86}为低电平失败，status_code: {r.status_code}")

        # 返回值异常，返回数据为 {'error': f"fail to set GPIO x level"}
        if r.json().get('error', False):
            raise GPIOError(f"设置GPIO 86引脚{self.pin_gpio_86}为低电平失败，JSON: {r.json()}")
        else:
            all_logger.info(f'设置GPIO 86引脚为低电平成功，状态码: {r.status_code}，返回值: {r.json()}')

    def get_ri_gpio_level(self):
        all_logger.info('获取RI引脚电平')

        # 请求ESP32线程
        requests_data = {"id": self.pin_ri}
        r = requests.post('http://127.0.0.1:55555/get', json=requests_data)

        # 状态码异常
        if r.status_code != 200:
            raise GPIOError(f"获取RI引脚{self.pin_ri}电平失败，status_code: {r.status_code}")

        ri_status = r.json()
        all_logger.info(f"获取RI引脚{self.pin_ri}电平状态：{ri_status}")
        return ri_status

    def get_dcd_gpio_level(self):
        all_logger.info('获取DCD引脚电平')

        # 请求ESP32线程
        requests_data = {"id": self.pin_dcd}
        r = requests.post('http://127.0.0.1:55555/get', json=requests_data)

        # 状态码异常
        if r.status_code != 200:
            raise GPIOError(f"获取DCD引脚{self.pin_dcd}电平失败，status_code: {r.status_code}")

        dcd_status = r.json()
        all_logger.info(f"获取DCD引脚{self.pin_dcd}电平状态：{dcd_status}")
        return dcd_status

    def get_net_mode_gpio_level(self):
        all_logger.info('获取NET MODE引脚电平')

        # 请求ESP32线程
        requests_data = {"id": self.pin_net_mode}
        r = requests.post('http://127.0.0.1:55555/get', json=requests_data)

        # 状态码异常
        if r.status_code != 200:
            raise GPIOError(f"获取NET MODE引脚{self.pin_net_mode}电平失败，status_code: {r.status_code}")

        net_mode_status = r.json()
        all_logger.info(f"获取NET MODE引脚{self.pin_net_mode}电平状态：{net_mode_status}")
        return net_mode_status

    def get_net_status_gpio_level(self):
        all_logger.info('获取NET STATUS引脚电平')

        # 请求ESP32线程
        requests_data = {"id": self.pin_net_status}
        r = requests.post('http://127.0.0.1:55555/get', json=requests_data)

        # 状态码异常
        if r.status_code != 200:
            raise GPIOError(f"获取NET STATUS引脚{self.pin_net_status}电平失败，status_code: {r.status_code}")

        net_status = r.json()
        all_logger.info(f"获取NET STATUS引脚{self.pin_net_status}电平状态：{net_status}")
        return net_status


if __name__ == '__main__':
    gpio = GPIO()
    # VBAT重启后PWK开机
    gpio.set_vbat_high_level()
    gpio.set_vbat_low_level_and_pwk()
