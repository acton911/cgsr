import re
import sys
import pickle
from utils.functions.arg_parser import ParameterParser
from utils.logger.logging_handles import all_logger
from utils.exception.exceptions import FatalError
from windows_linux_upgrade_onoff import WindowsLinuxUpgradeOnOff


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
all_logger.info("WindowsLinuxUpgradeOnOff: {} , type{}".format(WindowsLinuxUpgradeOnOff, type(WindowsLinuxUpgradeOnOff)))

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
revision = args_5g.ati
sub_edition = args_5g.csub
cur_version = re.sub(r'[\r\n]', '', revision + sub_edition)
svn = args_5g.svn
firmware_path = args_5g.firmware_path
prev_firmware_path = args_5g.prev_firmware_path
prev_upgrade_revision = args_5g.prev_ati
prev_upgrade_sub_edition = args_5g.prev_csub
prev_version = re.sub(r'[\r\n]', '', prev_upgrade_revision + prev_upgrade_sub_edition)
port_info = args_5g.dev_vid_pid_rev  # Windows下PIDVID信息
usb_id = args_5g.dev_vid_pid_rev  # AT+QCFG="USBID"返回值,Ubuntu下的值
prev_svn = args_5g.prev_svn  # 上个A版本的svn号
prev_name_sub_version = args_5g.prev_name_sub_version  # 上个A版本的svn号

# 解压的属性
func = script_context['func']
at_port, dm_port, modem_port, uart_port = main_device['usbat'], main_device['upgrade'], \
    main_device['usbmodem'], main_device['uart']
imei = main_device['imei_number']

params_dict = {
    "at_port": at_port,
    "dm_port": dm_port,
    "modem_port": modem_port,
    "imei": imei,
    "svn": svn,
    "firmware_path": firmware_path,
    "prev_firmware_path": prev_firmware_path,
    "uart_port": uart_port,
    "port_info": port_info,
    "prev_version": prev_version,
    "usb_id": usb_id,
    "prev_svn": prev_svn,
    "cur_version": cur_version,
    'package_name': name_sub_version,
    'prev_package_name': prev_name_sub_version,
}

all_logger.info('进行测试项:{}: {}'.format(func, case_setting['summary']))
exec("WindowsLinuxUpgradeOnOff(**{}).{}()".format(params_dict, func))
