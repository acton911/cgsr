import sys


def handle_uncaught_exception(exc_type, exc_value, exc_trace):
    old_hook(exc_type, exc_value, exc_trace)

    if isinstance(exc_value, ExitCode1):
        sys.exit(exc_value.set_exit_code())
    if isinstance(exc_value, ExitCode4):
        sys.exit(exc_value.set_exit_code())


sys.excepthook, old_hook = handle_uncaught_exception, sys.excepthook


class ExitCode1(Exception):
    """
    正常ERROR的状态码
    """

    @staticmethod
    def set_exit_code():
        return 1


class ExitCode4(Exception):
    """
    中断APP继续运行状态码
    """

    @staticmethod
    def set_exit_code():
        return 4


class GPIOError(ExitCode1):
    """
    GPIO设置异常
    """


class FatalError(ExitCode4):
    """
    阻止脚本运行的致命错误
    """


class JenkinsError(ExitCode4):
    """
    Jenkins异常，版本包制作失败，直接结束
    """


class MBIMError(ExitCode1):
    """
    如果出现MBIM相关的错误
    """


class CCLKError(ExitCode1):
    """
    如果出现CCLK相关的错误
    """


class FrameworkError(ExitCode1):
    """
    如果传参错误
    """


class NormalError(ExitCode1):
    """
    脚本运行中的常规错误
    """


class WindowsAPIError(ExitCode1):
    """
    windows api异常
    """


class WindowsDFOTAError(ExitCode1):
    """
    windows下DFOTA异常
    """


class LinuxDFOTAError(ExitCode1):
    """
    windows下DFOTA异常
    """


class LinuxABSystemError(ExitCode1):
    """
    linux下AB_System异常
    """


class LinuxPCIEDFOTAError(ExitCode1):
    """
    Linux PCIE DFOTA Error
    """


class ATError(ExitCode1):
    """
    AT指令发送异常
    """


class LinuxAPIError(ExitCode1):
    """
    Linux api异常
    """


class QMIError(ExitCode1):
    """
    如果出现QMI相关错误
    """


class LinuxGobiNetError(ExitCode1):
    """
    Gobinet相关异常
    """


class ECMError(ExitCode1):
    """
    ECM拨号相关异常
    """


class PretestError(ExitCode1):
    """
    Pretest异常
    """


class UARTError(ExitCode1):
    """
    AT指令发送异常
    """


class WindowsLowPowerError(ExitCode1):
    """
    windows下慢时钟异常
    """


class LinuxPcieMBIMError(ExitCode1):
    """
    Linux下PCIE模块MBIM拨号异常
    """


class LinuxPcieQMIError(ExitCode1):
    """
    Linux下PCIE模块QMIE拨号异常
    """


class LinuxATQMIError(ExitCode1):
    """
    Linux下AT配置模块QMI拨号异常
    """


class LinuxATUpgradeError(ExitCode1):
    """
    Linux下AT配置模块PCIE升级异常
    """


class LinuxLowPowerError(ExitCode1):
    """
    Linux下慢时钟异常
    """


class WindowsDSSSError(ExitCode1):
    """
    Windows下DSSS异常
    """


class LinuxRGMIIError(ExitCode1):
    """
    Linux RGMII Error
    """


class UpgradeOnOffError(ExitCode1):
    """
    升级开关机异常
    """


class LinuxRTL8125Error(ExitCode1):
    """
    Linux RTL8125 Error
    """


class IPerfError(ExitCode1):
    """
    IPerf Error
    """


class LinuxRIURCError(ExitCode1):
    """
    Linux RI&URC Error
    """


class WindowsEsimError(ExitCode1):
    """
    Windows Esim Error
    """


class LinuxESIMError(ExitCode1):
    """
    Linux Esim Error
    """


class WindowsNetLightError(ExitCode1):
    """
    Windows NetLight Error
    """


class LinuxCloudOTAError(ExitCode1):
    """
    Linux CloudOTA Error
    """


class WindowsSMSError(ExitCode1):
    """
    Windows SMS Error
    """


class LinuxSMSError(ExitCode1):
    """
    Linux SMS Error
    """


class WindowsLaptopUpgradeonoffError(ExitCode1):
    """
    Windows laptop_Upgradeonoff Error
    """


class LinuxETHError(ExitCode1):
    """
    Linux ETH Error Error
    """


class QSSDialRateError(ExitCode1):
    """
    如果出现QSS 测速相关错误
    """


class QSSBandTraversalError(ExitCode1):
    """
    如果出现QSS band遍历相关错误
    """


class QSSWeakSignalError(ExitCode1):
    """
    如果出现QSS弱信号相关错误
    """


class QSSLimitRAndIError(ExitCode1):
    """
    如果出现禁R&I相关错误
    """
