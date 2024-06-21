from utils.exception.exceptions import FatalError
from utils.logger.logging_handles import all_logger
from utils.functions.case import FlattenNestDict
from utils.cases.startup_manager import StartupManager
from utils.log import log
import os
import sys
import pickle

# TODO: 暂不实现：发送AT DUMP不重启，抓取DUMP
# TODO: 暂不实现：PCIE_MBIM AT设置

# 获取原始参数
try:
    params_path = sys.argv[1]
except IndexError:
    raise FatalError(f"APP传参异常，sys.argv: {sys.argv}")


# 解析原始参数
try:
    # pickle反序列化
    with open(params_path, 'rb') as p:
        # original_setting
        args = pickle.load(p).test_setting  # noqa
        if not isinstance(args, dict):
            args = eval(args)
        all_logger.info(f"args: {args} , type{type(args)}")
    # 参数解析
    args = FlattenNestDict(args)

except SyntaxError:
    raise FatalError(f"\n系统参数解析异常：\n原始路径: \n {repr(params_path)}")

for num, res in enumerate(args.res):  # args.res节点(test_setting dict中的res节点包含当前PC的Resource信息，遍历对每个设备进行初始化)

    device_number = res.get("device_number", "")  # noqa 当前Resource在TWS系统上的Device Number(https://tws.quectel.com:8152/Cluster/Device)
    all_logger.info(f"当前{len(args.res)}套设备，进行第{num + 1}套资源初始化，资源名称：{device_number}")
    all_logger.info(f"res: {res}, type(res):{type(res)}")

    imei = res.get("imei_number", '')
    sn = res.get("sn", '')
    arg_dict = {
        "version_type": int(res.get("version_type", "")),  # 工厂还是标准标志位，0/None不关注、1：Factory、2：Standard
        "version_upgrade": int(res.get("version_upgrade", "")),  # 是否要升级判断，0：不升级、1：升级
        "at_port": res.get("usbat", ""),  # AT口端口号
        "dm_port": res.get("upgrade", ""),  # DM口端口号
        "ati": args.name_ati_version,  # ATI 版本号
        "csub": args.name_csub,  # CSUB版本号
        "name_sub_version": args.name_sub_version,  # 标准软件包名称
        "firmware_path": args.path_sub_version,  # 版本包SVN地址
        "qgmr": args.name_real_version,  # QGMR版本号，对应送测单的QGMR
        "args": args,  # 系统参数
        "imei": imei,  # IMEI1
        "sn": sn,  # SN号
    }
    all_logger.info(f"arg_dict: {arg_dict}")
    # 初始化管理类
    log.stop_quts_service()  # 防止QXDM API异常结束占用DM口
    startup = StartupManager(**arg_dict)
    debug_mode = startup.get_debug_flag()
    # 切卡器恢复
    startup.restore_sim_switch()
    if debug_mode is False:
        if startup.is_audio:  # AUDIO设备不做异常处理
            startup.upgrade()
        elif startup.is_laptop:  # 笔电项目不做异常处理
            startup.upgrade()
            startup.set_modem_port()
            startup.enable_sim_1()
        else:  # 非笔电项目进行环境判断
            # 紧急下载模式恢复
            startup.emergency_download_mode_check()
            # 检查模块AT口DM口是否正常加载
            startup.power_on_check()
            # 判断是否升级，需要升级则升级
            startup.upgrade()
            # 检测NDIS驱动是否正常
            startup.ndis_driver_resume()
    # 检测SIM卡SC锁
    startup.check_clck()
    # RM520NGLAA版本CFUN默认是0，修改NV强制为1
    startup.set_cfun_nv()
    # 检查模块CFUN值
    startup.check_cfun()
    if 'Jeckson' not in res.get("device_number", "") and 'QSS' not in res.get("device_number", ""):
        # 获取MBN状态
        startup.get_mbn_status()
        # 检查模块网络
        startup.check_network()
    # 获取版本号
    startup.get_version()
    # 切换开关至RTL8125或者PCIE
    if not startup.is_audio:  # 如果不是AUDIO设备
        startup.switch_rtl8125()
    # 检查当前是否开启慢时钟注册表，如果开启需要关闭
    if os.name == 'nt':
        startup.disable_low_power_registry()
    else:
        startup.linux_quit_low_power()
    # 设置DUMP模式
    startup.set_dump_mode()
    # 如果是Ubuntu系统，默认执行umount指令解除文件挂载
    if os.name == 'posix':
        startup.umount_directory()
    # 如果是PCIE测试机，需要检查是否加载PCIE驱动(雷蛇版本除外，不能设置DATA_INTERFACE值)
    if os.name != 'nt' and 'PCIE' in res.get("device_number", "") and '_RZ_' not in args.name_sub_version:
        startup.auto_insmode_pcie()
    # MH8100EUAC SIM默认低电平检测
    startup.resume_sim_det()
