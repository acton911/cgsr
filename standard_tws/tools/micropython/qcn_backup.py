# Basic import
import sys
import logging
import pickle
sys.path.append(r'C:\Program Files (x86)\Qualcomm\QUTS\Support\python')

sn = input("请输入模块的SN号(SN号将用作模块记录，仅SN匹配的模块才会进行QCN恢复动作): ")

# QUTS import
import QutsClient  # noqa
import Common.ttypes  # noqa
import DeviceConfigService.DeviceConfigService  # noqa
import DeviceConfigService.constants  # noqa
import DeviceConfigService.ttypes  # noqa

# Basic logging set
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Create QUTS client
quts_client = QutsClient.QutsClient("Sample")

# Get device manager
dev_manager = quts_client.getDeviceManager()
logger.info(f"dev_manager: {dev_manager}")

# Get all device list
device_list = dev_manager.getDeviceList()
logger.info(f"device_list: {device_list}")

# Devices support DeviceConfigService
devices = dev_manager.getDevicesForService(DeviceConfigService.constants.DEVICE_CONFIG_SERVICE_NAME)
logger.info(f"devices support device config service: {devices}")

# Create DeviceConfigService Use quts_client
device_config_service = DeviceConfigService.DeviceConfigService.Client(
    quts_client.createService(
        DeviceConfigService.constants.DEVICE_CONFIG_SERVICE_NAME,
        devices[0]
    )
)
logger.info(f"device_config_service: {device_config_service}")

# Initial DeviceConfigService
initial_status = device_config_service.initializeService()
logger.info(f"The status of DeviceConfigService: {initial_status}")

# Backup XQCN
backup_status = device_config_service.backupToXqcn('000000', True, 180, '')
logger.info(f"backup_status: {backup_status}")
error_no = device_config_service.getLastError()
logger.info(f"error_no: {error_no}")

# pickle dump
with open(f'{sn}.xqcn', 'wb') as p:
    pickle.dump(backup_status, p)
