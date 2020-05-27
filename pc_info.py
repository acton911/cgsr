import platform


def TestPlatform():

    print("----------Operation System----------")
    print(platform.python_version())
    # 获取python版本

    print(platform.architecture())
    # 获取操作系统可执行程序的结构，，（'32bit' , 'windowsPE' ）

    print(platform.node())
    # 计算机的网络名称，'acer-PC'

    print(platform.platform())
    # 获取操作系统名称及版本号

    print(platform.processor())
    # 计算机处理器信息

    print(platform.python_build())
    # 获取操作系统中Python的构建日期

    print(platform.python_compiler())
    # 获取系统中python结束前的信息

    if platform.python_branch() == "":
        print(platform.python_implementation())
        print(platform.python_revision())
    print(platform.release())
    print(platform.system())

    print(platform.version())
    # 获取操作系统的版本

    print(platform.uname())
    # 所有的信息汇总


def UsePlatform():

    sysstr = platform.system()
    if(sysstr == "Windows"):
        print("Call Windows tasks")
    elif(sysstr == "Linux"):
        print("Call Linux tasks")
    else:
        print("Other System tasks")


if __name__ == "__main__":
    TestPlatform()
    UsePlatform()