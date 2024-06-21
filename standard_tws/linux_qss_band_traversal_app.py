from utils.logger.logging_handles import all_logger
from utils.exception.exceptions import FatalError
from linux_qss_band_traversal import LinuxQSSBandTraversal
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
all_logger.info("LinuxQSSBandTraversal: {} , type{}".format(LinuxQSSBandTraversal, type(LinuxQSSBandTraversal)))

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


qmi_usb_network_card_name = args_5g.dev_qmi_network_card_name
mbim_usb_network_card_name = args_5g.dev_mbim_driver_name
gobinet_usb_network_card_name = args_5g.dev_gobinet_network_card_name
ecm_usb_network_card_name = args_5g.dev_ecm_network_card_name
pcie_network_card_name = args_5g.dev_linux_pcie_network_card_name
local_network_card_name = args_5g.dev_pc_ethernet_name
wwan_path = args_5g.dev_wwan_driver_path
gobinet_path = args_5g.dev_gobinet_driver_path
pcie_driver_path = args_5g.dev_pcie_driver_path
qss_ip = args_5g.dev_qss_ip
eth_test_mode = args_5g.dev_eth_test_mode
chrome_driver_path = args_5g.dev_chrome_driver_path
default_wcdma_band = args_5g.default_wcdma_band
default_sa_band = args_5g.default_sa_band
default_nsa_band = args_5g.default_nsa_band
default_lte_band = args_5g.default_lte_band


# 解压的属性
at_port, dm_port, uart_port, nema_port = main_device['usbat'], main_device['upgrade'], main_device['uart'], main_device['usbNmea']
func = script_context['func']
node_name = main_device['node_name']
local_ip = main_device['ip']
mme_file_name = script_context['mme_file_name']
enb_file_name = script_context['enb_file_name']
ims_file_name = script_context['ims_file_name']


params_dict = {
    'at_port': at_port,
    'dm_port': dm_port,
    'wwan_path': wwan_path,
    'qmi_usb_network_card_name': qmi_usb_network_card_name,
    'local_network_card_name': local_network_card_name,
    'qss_ip': qss_ip,
    'local_ip': local_ip,
    'node_name': node_name,
    "mme_file_name": mme_file_name,
    "enb_file_name": enb_file_name,
    "ims_file_name": ims_file_name,
    'name_sub_version': name_sub_version,
    'chrome_driver_path': chrome_driver_path,
    'default_sa_band': default_sa_band,
    'default_nsa_band': default_nsa_band,
    'default_lte_band': default_lte_band,
    'default_wcdma_band': default_wcdma_band,
}

all_logger.info('进行测试项:{}: {}'.format(func, case_setting['summary']))
exec("LinuxQSSBandTraversal(**{}).{}()".format(params_dict, func))
