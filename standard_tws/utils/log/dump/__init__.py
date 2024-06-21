from utils.functions.driver_check import DriverChecker
from utils.logger.logging_handles import all_logger
import serial.tools.list_ports
from utils.log import log
import time
import os


def catch_dump(at_port, dm_port, save_path=os.getcwd()):
    """
    根据AT口DM口抓取DUMP，并保存到当前目录。
    :param at_port: AT口
    :param dm_port: DM口
    :param save_path: 日志保存路径
    :return: None
    """

    def get_laptop_dump_port():
        """
        笔电的DUMP口名字是Quectel UDE Sahara Port xxx
        :return:
        """
        for i, j, *_ in serial.tools.list_ports.comports():
            if 'UDE Sahara Port' in j:
                return i
        return ''

    # 判断当前是否是DUMP模式
    driver_check = DriverChecker(at_port, dm_port)
    port_list = driver_check.get_port_list()
    if at_port in port_list and dm_port in port_list:
        all_logger.info(f"当前非DUMP模式, AT口{at_port}DM口{dm_port}存在于端口列表{port_list}")
        return True

    if at_port not in port_list and dm_port in port_list:
        all_logger.error("当前模块可能进入了DUMP模式，等待10S后重新检测")
        time.sleep(10)
        port_list = driver_check.get_port_list()
        if at_port not in port_list and dm_port in port_list:
            all_logger.error("当前模块已经DUMP，尝试进行恢复")
    else:
        all_logger.error(f"当前无需抓取DUMP，端口列表：{port_list}")
        return True

    # 抓取DUMP前首先停止QUTS Service
    log.stop_quts_service()
    time.sleep(5)

    if os.name == 'nt':
        from utils.log.dump.dump_windows import QPSTAtmnServer

        # 此处IF语句为了兼容笔电的DUMP抓取，笔电DM口非DUMP口，要替换为Quectel UDE Sahara Port xxx
        if get_laptop_dump_port():
            dm_port = get_laptop_dump_port()

        with QPSTAtmnServer() as atmn:
            all_logger.info('wait 5 seconds.')
            time.sleep(5)
            atmn.add_port(dm_port)
            all_logger.info('wait 5 seconds.')
            time.sleep(5)
            atmn.catch_dump(at_port)
            atmn.copy_dump_log(save_path)
    else:
        from utils.log.dump.dump_linux import QLogDUMP
        with QLogDUMP() as dump:
            dump.catch_dump()
        driver_check.check_usb_driver_dis()
        driver_check.check_usb_driver()

    all_logger.info("wait 30 seconds")
    time.sleep(30)
