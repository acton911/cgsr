修改记录

time:2021/12/13

update:按STSDX55-4169要求，去除卸载安装驱动操作


注意事项：
由于已经去除卸载安装驱动操作，故第一次开机后需进入到驱动目录，要先rmmod mhi-pcie-genirci(否则可能冲突导致驱动加载异常)，然后手动insmod mhi_pci.ko



time:2021/12/14

update:
参数改为默认，如下：
#### 驱动包路径：
'pcie_driver_path': '/home/ubuntu/Tools_Ubuntu_SDX55/Drivers/pcie_mhi',
#### USBAT口：
'at_port': '/dev/ttyUSBAT',
#### USBDM口：
'dm_port': '/dev/ttyUSBDM',
#### PCIE卡槽位置:
'pci_path': '/sys/bus/pci/devices/0000\:01\:00.0',
