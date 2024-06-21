import getpass
import pickle
import os
import sys
import logging
import subprocess
import time  # noqa used for debugging
from collections import defaultdict
from tempfile import TemporaryDirectory
from modules.logger import logger
import threading
sys.path.append(r'C:\Program Files (x86)\Qualcomm\QUTS\Support\python')
import QutsClient  # noqa # pylint: disable=E0401
import Common.ttypes  # noqa # pylint: disable=E0401

import DiagService.DiagService  # noqa # pylint: disable=E0401
import DiagService.constants  # noqa # pylint: disable=E0401
import DiagService.ttypes  # noqa # pylint: disable=E0401

import DeviceConfigService.DeviceConfigService  # noqa # pylint: disable=E0401
import DeviceConfigService.constants  # noqa # pylint: disable=E0401
import DeviceConfigService.ttypes  # noqa # pylint: disable=E0401

import LogSession  # noqa # pylint: disable=E0401


class QUTSInitError(Exception):
    """
    QUTS初始化异常
    """


class QUTSNVError(Exception):
    """
    QUTS NV写入异常
    """


class QUTS:

    def __init__(self):
        self.log_watchdog = None
        self.quts_client = QutsClient.QutsClient("Sample")
        self.device_manager = self.quts_client.getDeviceManager()
        logger.info(f"quts_client: {self.quts_client}")
        logger.info(f"device_manager: {self.device_manager}")
        logger.info(f"available services: {', '.join(self.device_manager.getServicesList())}")

    def __getattr__(self, item):
        return self.__dict__.get(item, None)

    @staticmethod
    def _restart_quts_service():
        """
        重启QUTS服务
        :return: None
        """
        output = subprocess.getoutput('powershell.exe "Stop-Service QUTS"')
        logger.info(f"Stop-Service QUTS: {output}")
        output = subprocess.getoutput('powershell.exe "Start-Service QUTS"')
        logger.info(f"Start-Service QUTS: {output}")

    def _refresh_quts_client(self):
        """
        重新实例化quts_client，如果长时间使用一个Client，会导致TTransport Error。
        """
        if getattr(self, 'quts_client', None):
            del self.quts_client  # safety exit quts in QUTSClient.QUTSClient.__del__
        try:
            self.quts_client = QutsClient.QutsClient("Sample")
        except Exception as e:
            logger.info(f"重新启动quts_client异常: {e}")
            self._restart_quts_service()  # 重启启动QUTS服务
            self.quts_client = QutsClient.QutsClient("Sample")

    def _get_port_handler(self):
        logger.info("refresh quts_client")
        self._refresh_quts_client()
        logger.info('get device manager')
        self.device_manager = self.quts_client.getDeviceManager()  # 此处要重新获取Handler，不获取getDeviceList可能会报错
        logger.info("get device list")
        device_list = self.device_manager.getDeviceList()
        logger.info(f"device_list: {device_list}")
        for device in device_list:
            d = device.deviceHandle
            for p in self.device_manager.getProtocolList(d):
                logger.debug(p)
                if p.protocolType == 0 and "DM" in p.description:
                    device_handle = p.deviceHandle
                    protocol_handle = p.protocolHandle
                    logger.info(f"{p}\ndevice_handle: {device_handle}\nprotocol_handle: {protocol_handle}\n"
                                f"description: {p.description}")
                    return device_handle, protocol_handle
        raise QUTSInitError("Fail to get diag port handle")

    def _get_port_handler_with_log_file(self, log_path):
        self._define_data_packet_filter()
        self._define_packet_return_config()
        self.log_session = self.quts_client.openLogSession([log_path])
        device_list = self.log_session.getDeviceList()
        for device in device_list:
            d = device.deviceHandle
            for p in self.log_session.getProtocolList(d):
                # Windows下的Log Diag口description里有DM字样，如果Log文件不是.hdf文件，则仅需判断p.protocolType == 0
                if p.protocolType == 0 and ("DM" in p.description or log_path.endswith(".hdf") is False):
                    device_handle = p.deviceHandle
                    protocol_handle = p.protocolHandle
                    logger.info(f"{p}\ndevice_handle: {device_handle}\nprotocol_handle: {protocol_handle}\n"
                                f"description: {p.description}")
                    self.data_packet_filter.protocolHandleList = [protocol_handle]
                    return device_handle, protocol_handle
        raise QUTSInitError("Fail to get diag port handle")

    def _create_diag_service(self):
        # Get handles
        self.device_handle, self.protocol_handle = self._get_port_handler()

        diag_service = DiagService.DiagService.Client(
            self.quts_client.createService(
                DiagService.constants.DIAG_SERVICE_NAME, self.device_handle
            )
        )
        logger.info(f"diag_service: {diag_service}")

        if diag_service.initializeService() != 0:
            raise QUTSInitError("Fail to init QUTS diag service")

        setattr(self, 'diag_service', diag_service)

    def _create_device_config_service(self):
        # Get handles
        self.device_handle, self.protocol_handle = self._get_port_handler()

        device_config_service = DeviceConfigService.DeviceConfigService.Client(
            self.quts_client.createService(
                DeviceConfigService.constants.DEVICE_CONFIG_SERVICE_NAME, self.device_handle
            )
        )
        logger.info(f"device_config_service: {device_config_service}")

        if device_config_service.initializeService() != 0:
            raise QUTSInitError("Fail to init device_config_service service")

        setattr(self, 'device_config_service', device_config_service)

    def _set_log_mask(self, dmc_file="default_template.dmc"):
        if dmc_file == "default_template.dmc":
            dmc_file = os.path.join(os.getcwd(), "default_template.dmc")
        self.diag_service.setLoggingMask(QutsClient.readFile(dmc_file), Common.ttypes.LogMaskFormat.DMC_FORMAT)

    def _define_diag_packet_filter(self, filters):
        """
        :param filters: {"LOG_PACKET": ["0xB821", "0xB808", "0xB80A", "0xB800"]}
        """
        diag_packet_filter = Common.ttypes.DiagPacketFilter()
        diag_packet_filter.idOrNameMask = defaultdict(list)
        for k, v in filters.items():
            for i in v:
                diag_packet_filter.idOrNameMask[getattr(Common.ttypes.DiagPacketType, k)].append(
                    Common.ttypes.DiagIdFilterItem(idOrName=i)
                )

        logger.info(f"diag_packet_filter: {diag_packet_filter}")
        setattr(self, "diag_packet_filter", diag_packet_filter)

    def _define_data_packet_filter(self):
        self.data_packet_filter = LogSession.ttypes.DataPacketFilter()
        logger.info(f"Created data_packet_filter: {self.data_packet_filter}")

    def _define_diag_return_config(self, filters):
        """
        :param filters: ["DEFAULT_FORMAT_TEXT", "PACKET_NAME", "PACKET_ID", "PACKET_TYPE", "TIME_STAMP_STRING", "RECEIVE_TIME_STRING", "SUMMARY_TEXT"]  # noqa
        """

        def calc_diag_return_flags(symbols):
            v0, v1, *vx = symbols
            v0 = getattr(Common.ttypes.DiagReturnFlags, v0) if isinstance(v0, int) is False else v0
            v1 = getattr(Common.ttypes.DiagReturnFlags, v1) if isinstance(v1, int) is False else v1
            if vx:
                vx.append(v0 | v1)
                return calc_diag_return_flags(vx)
            return v0 | v1

        diag_return_config = Common.ttypes.DiagReturnConfig()
        diag_return_config.flags = calc_diag_return_flags(filters)

        logger.info(f"diag_return_config: {diag_return_config}")
        setattr(self, "diag_return_config", diag_return_config)

    def _define_packet_return_config(self):
        self.packet_return_config = LogSession.ttypes.PacketReturnConfig()
        logger.info(f"Created packet_return_config: {self.packet_return_config}")

    def _create_data_queue(self, data_queue_name="TEST"):
        ret_code = self.diag_service.createDataQueue(data_queue_name, self.diag_packet_filter, self.diag_return_config)
        if ret_code != 0:
            raise QUTSInitError("Failed to init DataQueue")

    def _create_data_view(self,
                          message_types,
                          interested_return_filed,
                          data_view_name="TEST"):
        self._define_diag_packet_filter(message_types)
        self._define_diag_return_config(interested_return_filed)
        self.data_packet_filter.diagFilter = self.diag_packet_filter
        self.packet_return_config.diagConfig = self.diag_return_config
        logger.info(f"data_packet_filter: {self.data_packet_filter}")
        logger.info(f"packet_return_config: {self.packet_return_config}")
        self.log_session.createDataView(data_view_name, self.data_packet_filter, self.packet_return_config)

    def _set_data_queue_callback(self):
        def on_data_queue_updated(queue_name, queue_size):
            logger.info(f"queue_name: {queue_name}, update {queue_size}")

        self.quts_client.setOnDataQueueUpdatedCallback(on_data_queue_updated)

    def _destroy_data_queue(self, data_queue_name="TEST"):
        self.diag_service.removeDataQueue(data_queue_name)

    def destroy_data_view(self, data_view_name="TEST"):
        try:
            self.log_session.removeDataView(data_view_name)
            self.log_session.destroyLogSession()
        except Exception as e:
            logger.warning(e)
        try:  # 防止已经删除之后的重复调用
            del self.log_session
            del self.diag_packet_filter
            del self.data_packet_filter
            del self.diag_return_config
            del self.packet_return_config
        except NameError:
            pass

    def destroy_data_queue(self, data_queue_name="TEST"):
        try:
            self._destroy_data_queue(data_queue_name)
            logger.info(f"destroyed data queue {data_queue_name}")
        except Common.ttypes.AppException as e:
            logger.warning(e)
        try:  # 防止已经删除过重复调用
            del self.diag_packet_filter
            del self.diag_return_config
        except NameError:
            pass

    def set_log_watchdog(self, log_save_path):
        logger.info(f"set log save watchdog. save path: {log_save_path}")
        self.log_watchdog = threading.Timer(1800, function=self.stop_catch_log_and_save, args=(log_save_path,))
        self.log_watchdog.setDaemon(True)
        self.log_watchdog.start()

    def cancel_log_watchdog(self):
        if getattr(self, 'log_watchdog', None) and getattr(self.log_watchdog, "cancel", None):
            logger.info("cancel log save watchdog.")
            self.log_watchdog.cancel()
            self.log_watchdog = None

    def catch_log(self, dmc_file_path="default_template.dmc", log_save_path=os.getcwd()):
        # 判断之前是否有启动的Log捕获线程
        qxdm_status = self.stop_catch_log_and_save(log_save_path)
        if qxdm_status:  # 之前有的话，捕获后删除
            self.del_all_qxdm_log(log_save_path)

        # 设置过的log watchdog没有正确关闭，首先要正确关闭
        self.cancel_log_watchdog()

        # 开始抓Log
        logger.info(f"\ndmc_file_path: {dmc_file_path}\nlog_save_path: {log_save_path}")
        self._create_diag_service()
        self._set_log_mask(dmc_file=dmc_file_path)
        self.device_manager.startLogging()
        logger.info("Start logging.")

        # 设置Log的看门狗，默认超时时间1800s，也就是1800s后即使Case结束，Log也自动结束
        self.set_log_watchdog(log_save_path)

    def stop_catch_log_and_save(self, log_save_path=os.getcwd()):
        # 取消log watchdog
        self.cancel_log_watchdog()

        if getattr(self, "diag_service", None) and\
                getattr(self.diag_service, "destroyService", None):  # 为了防止重复保存Log导致报错，首先获取是否有diag_service，然后判断是否有destroyService属性
            try:
                self.device_manager.saveLogFiles(log_save_path)
                logger.info(f"Stop logging and save log to {log_save_path}")
                if os.name == 'nt':
                    logger.info(f'dir: {subprocess.getoutput(f"dir: {log_save_path}")}')
            except Exception as e:
                logger.error(f"Save QXDM from QUTS failed：{e}")
            finally:
                self.diag_service.destroyService()
                del self.diag_service
                del self.device_handle
                del self.protocol_handle
                return True

        # 重复调用忽略
        logger.error("ignore stop_catch_log_and_save")

    def read_nv(self, nv_path="/nv/item_files/modem/mmode/lte_bandpref"):
        logger.info("Start reading NV.")
        self._create_device_config_service()
        self.get_nvitem(nv_path)
        logger.info("End reading NV.")

    def backup_qcn(self, qcn_file_path):
        self._create_device_config_service()
        backup_qcn_success = False
        try:
            response = self.device_config_service.backupToXqcn("000000", False, 100000000, "")
            # logger.info(response)
            backup_path, backup_name = os.path.split(qcn_file_path)
            if not os.path.exists(backup_path):
                os.makedirs(backup_path)
            with open(qcn_file_path, 'w', encoding='utf-8') as f:
                f.write(response)
            logger.info(f"qcn文件位置：{qcn_file_path}")
            qcn_file_size = os.path.getsize(qcn_file_path)
            if qcn_file_size == 0:
                raise QUTSInitError("QCN备份失败，文件大小为0")
            backup_qcn_success = True
        except Exception as e:
            logger.info("Exception in backup qcn")
            logger.info(str(e))
        finally:
            self.device_config_service.destroyService()
            del self.device_config_service
            del self.device_handle
            del self.protocol_handle
            logger.info("qcn备份结束")
            return backup_qcn_success

    @staticmethod
    def find_qcn(sn):
        """
        从指定的路径查找是否有QCN
        :param sn: 模块的SN号
        :return: True，找到了SN对应的QCN，False，未找到文件
        """
        if os.name == 'nt':
            qcn_path = os.path.join(fr'C:\Users\{getpass.getuser()}\QCN')
        else:
            qcn_path = os.path.join('/root/QCN')
        for file in os.listdir(qcn_path):
            if file.startswith(sn):
                qcn_file_path = os.path.join(qcn_path, f'{sn}.xqcn')
                logger.info(f"QCN File PATH: {qcn_file_path}")
                return qcn_file_path
        return False

    def restore_qcn(self, sn):
        """
        从QCN文件内部恢复QCN
        :param sn: 模块的SN号
        :return: False: 未找到SN对应的QCN，True：找到并恢复了QCN
        """
        # 不管SN传入了啥，检查是否有SN号对应的QCN，没有的话直接跳出，不创建deviceConfigService
        qcn_file_full_path = self.find_qcn(sn)
        if qcn_file_full_path is False:
            logger.info(f"未找到SN为{sn}的qcn文件")
            return 1

        # 创建deviceConfigService
        self._create_device_config_service()
        try:
            # pickle load
            with open(qcn_file_full_path, 'rb') as p:
                qcn_content = pickle.load(p)  # noqa

            # Restore XQCN
            logger.info("")
            restore_xqcn = self.device_config_service.restoreFromXqcn(qcn_content, '000000', True, True, 180, '')
            logger.info(f"restore_xqcn status: {restore_xqcn}")

        except Exception as e:
            logger.info("Exception in backup qcn")
            logger.info(str(e))
            return 2
        finally:
            self.device_config_service.destroyService()
            del self.device_config_service
            del self.device_handle
            del self.protocol_handle
            logger.info("QCN恢复结束，模块即将重启")

    def get_nvitem(self, nv_path):
        """
        读取单个NV值
        :param nv_path: NV ID 或 旧名称 或 EFS路径
        :return: NV详情
        """
        try:
            nv_return_obj = DeviceConfigService.ttypes.NvReturns()
            nv_return_obj.flags = DeviceConfigService.ttypes.NvReturnFlags.JSON_TEXT
            nv_data = self.device_config_service.nvReadItem(nv_path, DeviceConfigService.constants.NO_SUBSCRIPTION_ID, 0, nv_return_obj)
            if nv_data == 'False':
                logger.info(self.device_config_service)
                logger.info("Couldn't read NV Item")
            else:
                logger.info(f"\r\nerrorCode:\r\n{nv_data.errorCode}"
                            f"\r\npayload:\r\n{nv_data.payload}"
                            f"\r\nJSON data:\r\n{nv_data.parsedJson}"
                            f"\r\nText:\r\n{nv_data.parsedText}"
                            f"\r\nvalueList:\r\n{nv_data.valueList}"
                            f"\r\nqueryResultJson:\r\n{nv_data.queryResultJson}")
        except Exception as e:
            logger.info("Exception in NV")
            logger.info(str(e))
        finally:
            self.device_config_service.destroyService()
            del self.device_config_service
            del self.device_handle
            del self.protocol_handle
            logger.info("查询结束")

    def stop_quts_service(self):
        # 取消log watchdog
        self.cancel_log_watchdog()

        if getattr(self, "diag_service", None) and\
                getattr(self.diag_service, "destroyService", None):  # 为了防止重复保存Log导致报错，首先获取是否有diag_service，然后判断是否有destroyService属性
            with TemporaryDirectory() as temp:
                self.device_manager.saveLogFiles(temp)
                logger.info(f"Stop logging and save log to {temp}")
                self.diag_service.destroyService()
                del self.diag_service
                del self.device_handle
                del self.protocol_handle
                logger.info("wait 3 seconds")
                time.sleep(3)
                return True

    def create_data_queue(self,
                          message_types={"LOG_PACKET": ["0xB821", "0xB808", "0xB80A", "0xB800"]},  # which message you want to filter
                          interested_return_filed=["DEFAULT_FORMAT_TEXT", "PACKET_NAME", "PACKET_ID", "PACKET_TYPE", "TIME_STAMP_STRING", "RECEIVE_TIME_STRING", "SUMMARY_TEXT"],  # which return filed you want
                          data_queue_name="TEST",
                          ):
        self._define_diag_packet_filter(message_types)
        self._define_diag_return_config(interested_return_filed)
        self._create_data_queue(data_queue_name)
        self._set_data_queue_callback()

    def load_log_from_file(self,
                           log_path,
                           message_types={"LOG_PACKET": ["0xB821", "0xB808", "0xB80A", "0xB800"]},  # which message you want ti filter
                           interested_return_filed=["DEFAULT_FORMAT_TEXT", "PACKET_NAME", "PACKET_ID", "PACKET_TYPE", "TIME_STAMP_STRING", "RECEIVE_TIME_STRING", "SUMMARY_TEXT"],  # which return filed you want
                           data_view_name="TEST"):
        self._get_port_handler_with_log_file(log_path)
        self._create_data_view(
            message_types=message_types,
            interested_return_filed=interested_return_filed,
            data_view_name=data_view_name
        )

    def read_from_data_queue(self, data_queue_name="TEST"):
        diag_packets = self.diag_service.getDataQueueItems(data_queue_name, 1000000, 5)
        logger.info(f"len of diag_packets: {len(diag_packets)}")
        if diag_packets:
            logger.info(f"dir(diag_packets[i]): {diag_packets[0]}")
        for i in range(len(diag_packets)):
            logging.info(f"{diag_packets[i].packetId} {diag_packets[i].parsedText}\n{'-' * 20}")

        # 读取完毕删除所有的DataQueue相关内容
        self.destroy_data_queue(data_queue_name=data_queue_name)

        return diag_packets

    def read_from_data_view(self, data_view_name="TEST"):
        packet_range = LogSession.ttypes.PacketRange()
        packet_range.beginIndex = 0
        packet_range.endIndex = self.log_session.getDataPacketCount(self.data_packet_filter.protocolHandleList[0])

        try:
            data_packets = self.log_session.getDataViewItems(data_view_name, packet_range)
        except Exception as e:
            logger.info(e)
            packet_range = LogSession.ttypes.PacketRange()
            packet_range.beginIndex = 0
            packet_range.endIndex = 10000
            data_packets = self.log_session.getDataViewItems(data_view_name, packet_range)
        logger.info(f"Packets received: {len(data_packets)}")

        # 读取完毕删除所有的DataView相关内容
        self.destroy_data_view(data_view_name=data_view_name)

        # 删除所有的qxdm log，避免存储占用
        self.del_all_qxdm_log()

        return data_packets

    @staticmethod
    def del_all_qxdm_log(path=os.getcwd()):
        """
        删除目录下的所有QXDM Log文件
        :return: None
        """

        if os.name == 'nt':
            del_cmd = 'del /F /S /Q "{}"'
        else:
            del_cmd = f'sudo rm -rf "{path}"'

        for path, _, files in os.walk(path):
            for file in files:
                if file.endswith(('.hdf', '.qmdl2', 'isf', '.bin', '.qdb')):
                    cmd = del_cmd.format(os.path.join(path, file))  # noqa
                    logger.info(f"del cmd: {cmd}")
                    logger.info(subprocess.getstatusoutput(cmd))


if __name__ == '__main__':
    quts = QUTS()

    quts.restore_qcn("AAA")

    time.sleep(120)

    # Catch log
    quts.catch_log()
    time.sleep(10)
    quts.stop_catch_log_and_save()

    # # Process real-time
    # quts.catch_log()
    # quts.create_data_queue()
    # time.sleep(10)
    # logger.info(quts.read_from_data_queue())
    # quts.destroy_data_queue()
    # quts.stop_catch_log_and_save()

    # # Process log file
    # quts.load_log_from_file(log_path=r"C:\Users\Flynn.Chen\Desktop\test1.hdf")
    # data = quts.read_from_data_view()
    # logger.info(data)
    # quts.destroy_data_view()
