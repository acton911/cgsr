from utils.logger.logging_handles import all_logger
from utils.exception.exceptions import FatalError
from windows_mbim import WindowsMBIM
from utils.functions.arg_parser import ParameterParser
from utils.functions.screen_capture import ScreenCapture
import traceback
import sys
import time
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
all_logger.info("WindowsMBIM: {} , type{}".format(WindowsMBIM, type(WindowsMBIM)))

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
all_logger.info("dir(args_5g): {}".format(dir(args_5g)))

# 从args_5g中取出对应参数
ipv6_address = args_5g.ipv6_address
mbim_driver_name = args_5g.dev_mbim_driver_name

# Script Context中获取的相关参数
at_port = main_device['usbat']  # TWS系统返回的AT口的端口号
dm_port = main_device['upgrade']  # 获取DM口端口号
phone_number = main_device['deviceCardList'][0]['phonenumber']
func = script_context['func']

params_dict = {
    "at_port": at_port,
    "dm_port": dm_port,
    "ipv6_address": ipv6_address,
    "mbim_driver_name": mbim_driver_name,
    "phone_number": phone_number,
    "params_path": params_path
}

video = ScreenCapture(func)
video.start()
flag = False
exc_type = None
exc_value = None
try:
    all_logger.info('params_dict: {}'.format(params_dict))
    all_logger.info('进行测试项:{}: {}'.format(func, case_setting['summary']))
    exec("WindowsMBIM(**{}).{}()".format(params_dict, func))  # noqa
except Exception as e:  # noqa
    all_logger.error(traceback.format_exc())
    exc_type, exc_value, exc_tb = sys.exc_info()
    flag = True
finally:
    video.flag = True
    time.sleep(1)
    if flag is False:
        video.remove()
    if exc_type and exc_value:
        raise exc_type(exc_value)
