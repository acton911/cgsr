import sys
import pickle
from utils.functions.arg_parser import ParameterParser
from utils.logger.logging_handles import all_logger
from utils.exception.exceptions import FatalError
from windows_laptop_UpgradePowerONOFF import WindowsLaptopUpgradeOnOff


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
        all_logger.info(f"original_setting: {original_setting} , type{type(original_setting)}")
        # case_setting
        case_setting = pickle.load(p)
        all_logger.info(f"case_setting: {case_setting} , type{type(case_setting)}")
        # script_context
        script_context = eval(case_setting["script_context"])  # 脚本所有TWS系统传参
        all_logger.info(f"script_context: {script_context} , type{type(script_context)}")
except SyntaxError:
    raise FatalError(f"\n系统参数解析异常：\n原始路径: \n {repr(params_path)}")

# 继续解析原始参数
# main device, 主设备, 很多参数都在主设备
main_device = original_setting['res'][0]
all_logger.info(f"main_device: {main_device} , type{type(main_device)}")
# minor device, 辅助测试设备，暂未用上
minor_device = original_setting['res'].pop()
all_logger.info(f"minor_device: {minor_device} , type{type(minor_device)}")
# all device, 所有的设备
devices = original_setting['res']
all_logger.info(f"devices: {devices} , type{type(devices)}")
# debug
all_logger.info(f"WindowsLaptopUpgradeOnOff: {WindowsLaptopUpgradeOnOff} , type{type(WindowsLaptopUpgradeOnOff)}")

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
all_logger.info(f"args_5g: {args_5g} , type{type(args_5g)}")
all_logger.info(f"dir(args_5g): {dir(args_5g)}")


# 从args_5g中取出对应参数
ati = args_5g.ati
csub = args_5g.csub
firmware_path = args_5g.firmware_path
prev_ati = args_5g.prev_ati
prev_csub = args_5g.prev_csub
prev_firmware_path = args_5g.prev_firmware_path


# 解压的属性
func = script_context['func']
at_port, dm_port, sahara_port = main_device['usbat'], main_device['upgrade'], main_device['relay']
imei = main_device['imei_number']

params_dict = {
    "at_port": at_port,
    "dm_port": dm_port,
    "sahara_port": sahara_port,
    "firmware_path": firmware_path,
    "ati": ati,
    "csub": csub,
    "prev_firmware_path": prev_firmware_path,
    "prev_ati": prev_ati,
    "prev_csub": prev_csub
}

all_logger.info('进行测试项:{}: {}'.format(func, case_setting['summary']))
exec(f"WindowsLaptopUpgradeOnOff(**{params_dict}).{func}()")
