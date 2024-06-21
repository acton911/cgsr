from utils.logger.logging_handles import all_logger
from utils.exception.exceptions import FatalError
from windows_laptop_lowpower import WindowsLapTopLowPower
import sys
import pickle
from utils.functions.arg_parser import ParameterParser


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
all_logger.info("WindowsLapTopLowPower: {} , type{}".format(WindowsLapTopLowPower, type(WindowsLapTopLowPower)))

# 判断name_sub_version是否存在，对应QVMS送测单中的标准软件包名称
name_sub_version = original_setting.get('name_sub_version', False)
if name_sub_version is False:
    raise FatalError("获取original_setting的name_sub_version字段失败，请确认送测单标准软件包名称是否填写")

# 参数解析 name_sub_version, main_device, custom_fields_name, task_property,
params = {
    'name_sub_version': name_sub_version,
    'main_device': main_device,
    'task_property': original_setting,
}
args_5g = ParameterParser(**params)
all_logger.info("args_5g: {} , type{}".format(args_5g, type(args_5g)))

# 从MySQL中获取相关参数，注意类型转换
mbim_pcie_driver_name = args_5g.dev_mbim_pcie_driver_name

# 解压的属性
at_port, dm_port, nema_port = main_device['usbat'], main_device['upgrade'], main_device['usbNmea']
debug_port = main_device['debug']
phone_number = main_device['deviceCardList'][0]['phonenumber']
func = script_context['func']
for i in range(len(main_device['custom_com_port'])):
    if main_device['custom_com_port'][i]['device_com_description'] == 'power_port':
        power_port = "COM{}".format(main_device['custom_com_port'][i]['device_com_port'])
        all_logger.info("power_port为{}".format(power_port))
        break
else:
    raise Exception('resource中没有填写程控电源电源power_port')

params_dict = {
    "at_port": at_port,
    "dm_port": dm_port,
    "nema_port": nema_port,
    "debug_port": debug_port,
    "phone_number": phone_number,
    "mbim_pcie_driver_name": mbim_pcie_driver_name,
    "power_port": power_port,
}

all_logger.info('进行测试项:{}: {}'.format(func, case_setting['summary']))
exec("WindowsLapTopLowPower(**{}).{}()".format(params_dict, func))
