from utils.logger.logging_handles import all_logger
from utils.exception.exceptions import FatalError
from linux_rgmii import LinuxRGMII
import sys
import pickle
from utils.functions.linux_api import disable_network_card, enable_network_card_and_check, enable_network_card
import time
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
all_logger.info("LinuxRGMII: {} , type{}".format(LinuxRGMII, type(LinuxRGMII)))

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
pc_ethernet_name = args_5g.dev_pc_ethernet_name
rgmii_ethernet_name = args_5g.dev_rgmii_ethernet_name

# Script Context中获取的相关参数
at_port = main_device['usbat']  # TWS系统返回的AT口的端口号
dm_port = main_device['upgrade']  # 获取DM口端口号
debug_port = main_device['debug']  # debug口端口号
phone_number = main_device['deviceCardList'][0]['phonenumber']  # 模块上插的卡
func = script_context['func']

params_dict = {
    'at_port': at_port,
    'dm_port': dm_port,
    'debug_port': debug_port,
    'pc_ethernet_name': pc_ethernet_name,  # 公司内网网卡名称
    'rgmii_ethernet_name': rgmii_ethernet_name,  # rgmii 网线连接的网卡名称
    'phone_number': phone_number  # 设置电话号码
}

# 禁用网卡
try:
    # 禁用公司网络
    disable_network_card(pc_ethernet_name)

    # 启用RGMII网卡
    enable_network_card(rgmii_ethernet_name)
    all_logger.info('wait 5 seconds')
    time.sleep(5)

    all_logger.info('params_dict: {}'.format(params_dict))
    all_logger.info('进行测试项:{}: {}'.format(func, case_setting['summary']))
    exec("LinuxRGMII(**{}).{}()".format(params_dict, func))

finally:
    # 禁用RGMII网卡
    disable_network_card(rgmii_ethernet_name)
    # 启用公司网络
    enable_network_card_and_check(pc_ethernet_name)

    all_logger.info('wait 10 seconds')
    time.sleep(10)
