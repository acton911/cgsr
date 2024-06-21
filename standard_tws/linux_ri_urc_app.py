from utils.logger.logging_handles import all_logger
from utils.exception.exceptions import FatalError
from linux_ri_urc import LinuxRiUrc
import sys
import pickle


# 获取原始参数
try:
    params_path = sys.argv[1]
except IndexError:
    raise FatalError(f"APP传参异常，sys.argv: {sys.argv}")


# 解析原始参数
try:
    with open(params_path, 'rb') as p:
        # original_setting
        original_setting = pickle.load(p).test_setting
        if not isinstance(original_setting, dict):
            original_setting = eval(original_setting)
        all_logger.info("original_setting: {} , type{}".format(original_setting, type(original_setting)))
        # case_setting
        case_setting = pickle.load(p)
        all_logger.info("case_setting: {} , type{}".format(case_setting, type(case_setting)))
        # script_context
        script_context = eval(case_setting["script_context"])  # 脚本所有TWS系统传参
        all_logger.info("script_context: {} , type{}".format(script_context, type(script_context)))
except SyntaxError:
    raise FatalError("\n系统参数解析异常：\n原始路径: \n {}".format(repr(params_path)))


# 继续解析原始参数
# main device, 主设备, 很多参数都在主设备
main_device = original_setting['res'][0]
all_logger.info("main_device: {} , type{}".format(main_device, type(main_device)))
# minor device, 辅助测试设备，暂未用上
minor_device = original_setting['res'].pop()
all_logger.info("minor_device: {} , type{}".format(minor_device, type(minor_device)))
# all device, 所有的设备
devices = original_setting['res']
all_logger.info("devices: {} , type{}".format(devices, type(devices)))
# debug
all_logger.info("LinuxRiUrc: {} , type{}".format(LinuxRiUrc, type(LinuxRiUrc)))

# 解压的属性
at_port, dm_port, uart_port, modem_port = main_device['usbat'], main_device['upgrade'], \
    main_device['uart'], main_device['usbmodem']
phone_number = main_device['deviceCardList'][0]['phonenumber']
func = script_context['func']

params_dict = {
    "at_port": at_port,
    "dm_port": dm_port,
    "uart_port": uart_port,
    "modem_port": modem_port,
    "phone_number": phone_number,
}

all_logger.info('进行测试项:{}: {}'.format(func, case_setting['summary']))
exec("LinuxRiUrc(**{}).{}()".format(params_dict, func))
