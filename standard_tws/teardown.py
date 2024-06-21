from utils.functions.case import FatalError
from utils.logger.logging_handles import all_logger
from utils.functions.case import FlattenNestDict
from utils.cases.teardown_manager import TeardownManager
import pickle
import sys

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
        args = pickle.load(p).test_setting
        if not isinstance(args, dict):
            args = eval(args)
        all_logger.info(f"args: {args} , type{type(args)}")
    # 参数解析
    args = FlattenNestDict(args)
    arg_dict = {
        "version_type": int(args.version_type),  # 工厂还是标准标志位，0/None不关注、1：Factory、2：Standard
        "version_upgrade": int(args.version_upgrade),  # 是否要升级判断，0：不升级、1：升级
        "at_port": args.usbat,  # AT口端口号
        "dm_port": args.upgrade,  # DM口端口号
        "ati": args.name_ati_version,  # ATI 版本号
        "csub": args.name_csub,  # CSUB版本号
        "name_sub_version": args.name_sub_version,  # 标准软件包名称
        "firmware_path": args.path_sub_version,  # 版本包SVN地址
        "args": args  # 系统参数
    }
except SyntaxError:
    raise FatalError("\n系统参数解析异常：\n原始路径: \n {}".format(repr(params_path)))

# 初始化管理类
teardown = TeardownManager(**arg_dict)
teardown.reset_usbnet_0()
teardown.get_mbn_status()
teardown.delete_files()
teardown.delete_firmware_dir()
if not teardown.is_audio:  # AUDIO设备不做GPIO恢复
    teardown.reset_switch_4()
teardown.change_slot()
