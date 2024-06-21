from subprocess import getoutput
import re


def getpass(qid, mode='console', version='v1.0|v1'):
    if version.lower() == 'v1.0|v1':
        adb_key = 'SH_adb_quectel'
        console_key = 'SH_console_quectel'
    elif version.lower() in 'v1.1':
        adb_key = 'reserver'
        console_key = 'reserver'
    elif version.lower() in 'v2.0':
        adb_key = 'reserver'
        console_key = 'reserver'
    else:
        raise ValueError("Version must in ['v1.0', 'v1', 'v1.1', 'v2.0']")

    if mode.lower() == 'console':
        cmd = 'openssl passwd -1 -salt {} {}'.format(qid, console_key)
    elif mode.lower() == 'adb':
        cmd = 'openssl passwd -1 -salt {} {}'.format(qid, adb_key)
    else:
        raise ValueError("Mode must in ['console', 'adb']")

    output = getoutput(cmd)
    if mode.lower() == 'console':
        key = ''.join(re.findall(r'^.*\$(.*?)$', output))
    else:
        key = ''.join(re.findall(r'\$.*?\$.*?\$([\s\S]{15})', output))

    if key:
        return key
    else:
        raise ValueError("Fail to get {} key. 请打开命令行，输入openssl检查openssl是否安装".format(mode))


if __name__ == '__main__':
    k = getpass('50321462', mode='adb')
    print(k)
