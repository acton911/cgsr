from modules.logger import logger
import getpass
import os
import sys
import shutil
import configparser
import socket


def user_check():
    """
    In linux, serial must accept in super user mode.
    :return: None
    """
    user = getpass.getuser()
    # if unix user not root
    if os.name != 'nt' and user != 'root':
        print("Please enter superuser mode: sudo -s.")
        exit()


def init_service():
    script_path = os.path.join(sys.path[0], 'app.py')

    if os.name == 'nt':  # windows添加到自启目录，开机自启动
        start_path = fr"C:\Users\{getpass.getuser()}\AppData\Roaming\Microsoft\Windows\Start Menu\Programs\Startup\micropython.bat"
        orig_path = os.path.abspath(os.path.dirname(sys.argv[0]))
        with open(start_path, 'w', encoding='utf-8') as f:
            f.write(f"""@echo off\n:home\ncd {orig_path} && python app.py\ngoto home\n""")
    else:
        service_path = "/lib/systemd/system/micropython.service"
        with open(service_path, 'w', encoding='utf-8') as f:
            f.write(f"[Unit]\nDescription=Micro Python APP Service\nAfter=network.target\n\n"
                    f"[Service]\nType=simple\nUser=root\nRestart=on-failure\nRestartSec=5s\nExecStart=python3 {script_path}\nLimitNOFILE=1048576\n\n"
                    f"[Install]\nWantedBy=multi-user.target\n")
        logger.info(os.popen('systemctl daemon-reload').read())
        logger.info(os.popen('systemctl enable micropython.service').read())


def get_config_path():
    if os.name == 'nt':
        config_path = os.path.join("C:\\Users", getpass.getuser(), 'gpio_config.ini')
    else:
        config_path = os.path.join('/root', 'gpio_config.ini')
    return config_path


def get_evb_flag_path():
    """
    RG的大EVB如果要自动设置项目则在C盘或Ubuntu根目录创建EVB文件或文件夹，不需要填写内容；
    RM的M.2的EVB如果要自动设置项目则在C盘或Ubuntu根目录创建M2EVB文件或文件夹，不需要填写内容；
    :return: M2EVB存在返回1、EVB存在返回0、都没有返回None
    """
    m2_evb = os.path.exists(os.path.join("C:\\", "M2EVB")) if os.name == 'nt'\
        else os.path.exists(os.path.join("/", "M2EVB"))
    evb = os.path.exists(os.path.join("C:\\", "EVB")) if os.name == 'nt'\
        else os.path.exists(os.path.join("/", "EVB"))
    if evb and m2_evb:
        raise NotImplementedError("根目录不能存在M.2 EVB和普通EVB两个标志位")
    if m2_evb:
        return 1
    elif evb:
        return 0
    else:
        return None


def config_check():
    """
    Check if "gpio_config.ini" in path. if not exist, generate it.
    :return: None
    """
    config_path = get_config_path()
    if not os.path.exists(config_path):
        shutil.copy('gpio_config.ini', config_path)


def evb_check():
    config_path = get_config_path()
    input_str = None

    # 自动化部署Check部分
    script_path = os.getcwd()
    logger.info(f"cwd: {script_path}")
    evb_flag = get_evb_flag_path()
    # windows开机后通过Startup文件夹自启动自启动。Ubuntu下service方式启动后，os.getcwd()为根目录 /
    if os.name == 'nt' and (script_path.endswith('Startup') or script_path.endswith('system32'))\
            or 'TWS_TEST_DATA' in script_path or script_path == '/':
        if evb_flag is None:
            logger.error("如有需要，请在C盘根目录创建名为EVB或M2EVB文件或文件夹，用于自启后项目自动判断")
        else:
            input_str = evb_flag
    if input_str is not None or evb_flag is not None:
        logger.info(f"\n当前默认EVB为{evb_flag}，如果需要取消默认设置请删除根目录标志位" * 3)
        config_path = get_config_path()
        config = configparser.ConfigParser()
        config.read(config_path, encoding='utf-8')
        config.set('PIN', 'FLAG', str(evb_flag))
        with open(config_path, 'w') as f:
            config.write(f)
        return True

    # 手动填写Check
    logger.info("请输入当前项目：RG请输入0，RM请输入1")

    while True:

        input_str = input()

        if input_str == '0' or input_str == '1':
            config = configparser.ConfigParser()
            config.read(config_path, encoding='gb2312')
            config.set('PIN', 'FLAG', input_str)
            with open(config_path, 'w') as f:
                config.write(f)
            return True
        else:
            logger.error("请输入正确的项目编号：RG请输入0，RM请输入1")
            continue


def create_qcn_path():
    logger.info("检查QCNpath是否存在")
    if os.name == 'nt':
        qcn_path = os.path.join(fr'C:\Users\{getpass.getuser()}\QCN')
    else:
        qcn_path = os.path.join(r'/root/QCN')

    if os.path.exists(qcn_path) is False:
        logger.info("创建QCN PATH")
        os.makedirs(qcn_path)

    orig_path = os.path.abspath(os.path.dirname(sys.argv[0]))
    orig_qcn_generator_path = os.path.join(orig_path, 'qcn_backup.py')

    shutil.copy(orig_qcn_generator_path, os.path.join(qcn_path, 'qcn_backup.py'))


def socket_check():
    """
    通过端口来检查是否已经打开了MicroPython，如果55555端口被占用，就退出。
    :return: None
    """
    sock = socket.socket()
    try:
        sock.bind(("", 55555))
    except OSError as e:
        logger.error(e)
        logger.error("55555端口被占用，请检查是否已经打开MicroPython或后台已有MicroPython启动")
        exit(1)


if __name__ == '__main__':
    socket_check()
