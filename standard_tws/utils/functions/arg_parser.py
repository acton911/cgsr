# -*- encoding=utf-8 -*-
from utils.logger.logging_handles import all_logger
import requests


class ParameterParser:

    EXTRA_MESSAGE = '\n查询表从SDX55_XX变为5G_XX，请在5G_XX表中填写\n' \
                    'pylite本地调试获取不到参数需要重装pylite_base库:\n' \
                    'pip uninstall pylite_base\n' \
                    'pip install git+ssh://git@stgit.quectel.com:222/5G-SDX55/standard_tws_pylite_base.git\n' \
                    '或https://stgit.quectel.com/5G-SDX55/standard_tws_pylite_base下载安装包使用下面命令安装：\n' \
                    'pip install standard_tws_pylite_base-master.zip'

    def __init__(self, name_sub_version, main_device, task_property, ip="10.66.98.85", port=55556):
        self.name_sub_version = name_sub_version
        self.task_property = task_property
        self.main_device = main_device
        self.ip = ip
        self.port = 55556
        self.url = f"http://{ip}:{port}/query"
        self.version()
        self.project()
        self.prepare()
        self.resource()

    def project(self):
        sql = f'select * from 5G_Project where hardware_type="{self.hardware_type}";'  # noqa
        all_logger.info(f'project sql: {sql}')
        r = requests.post(self.url, json={'sql': sql})
        if r.status_code == 500:
            if getattr(self, 'hardware_type'):
                all_logger.error('Project数据库中型号：{self.hardware_type} 查询为空，'
                                 '如果用到WCDMA、LTE、NSA、SA的Band相关参数请与项目负责人联系{self.EXTRA_MESSAGE}')
            else:
                all_logger.error('chip platform或hardware type获取异常，WCDMA、LTE、NSA、SA的Band相关参数获取异常')
        else:
            for k, v in r.json().items():
                setattr(self, k, v)

    def resource(self):
        if not isinstance(self.main_device, dict) and getattr(self.main_device, 'custom_fields_name', None):  # pylite: 有custom_fields_name属性，且非dict # noqa
            for k, v in self.main_device.custom_fields_name.items():
                setattr(self, k, v)
        elif isinstance(self.main_device, dict) and self.main_device.get("custom_fields_name", None):  # auto_python
            for k, v in self.main_device.get("custom_fields_name").items():
                setattr(self, k, v)
        else:
            all_logger.error("TWS Resource Custom Fields 未填写任何内容，如果Case中有需要，请配置参数后使用")

    def prepare(self):
        sql = "select * from 5G_Prepare;"
        all_logger.info(f'prepare sql: {sql}')
        r = requests.post(self.url, json={'sql': sql})
        r.raise_for_status()
        for k, v in r.json().items():
            setattr(self, k, v)

    def version(self):
        # SQL查询参数
        sql = f'select * from 5G_Version where name_sub_version="{self.name_sub_version}";'  # noqa
        all_logger.info(f'version sql: {sql}')
        r = requests.post(self.url, json={'sql': sql})
        if r.status_code == 500:
            if getattr(self, 'name_sub_version'):
                all_logger.info(f'Version数据库中标准软件包名称：{self.name_sub_version} 查询为空，'
                                 f'如果用到gmi、cversion、prev_ati、prev_csub、prev_svn、prev_firmware_path等相关参数请检查送测单Version数据库参数配置{self.EXTRA_MESSAGE}')  # noqa
            else:
                all_logger.error(f'name_sub_version获取异常，mi、cversion、prev_ati、prev_csub、prev_svn、prev_firmware_path等相关参数获取异常')  # noqa
        else:
            for k, v in r.json().items():
                setattr(self, k, v)

        if getattr(self.task_property, 'versionATI', None):  # pylite
            print("解析pylite参数")
            # taskProperty参数
            setattr(self, 'ati', self.task_property.versionATI)
            setattr(self, 'csub', self.task_property.versionCSUB.replace('-', ''))
            setattr(self, 'svn', self.task_property.svnNumber)
            setattr(self, 'qefsver', self.task_property.versionQEFSVER)
            setattr(self, 'qgmr', self.task_property.versionQGMR)
            setattr(self, 'gmr', self.task_property.versionATI)
            setattr(self, 'firmware_path', self.task_property.subVersionPath)
            # customPipeLineParams参数
            if getattr(self.task_property, 'customPipeLineParams', None) and isinstance(self.task_property.customPipeLineParams, dict):
                for k, v in self.task_property.customPipeLineParams.items():
                    setattr(self, k, v)
            # 避免系统下发customPipeLineParams为custom_params
            if getattr(self.task_property, 'custom_params', None) and isinstance(self.task_property.custom_params, dict):
                for k, v in self.task_property.custom_params.items():
                    setattr(self, k, v)
            # main_device参数
            setattr(self, 'dev_imei_1', self.main_device.imei_number)
            try:
                setattr(self, 'sn', self.main_device.sn)
            except AttributeError:
                all_logger.error("Resource中未发现SN相关配置，如需要获取SN号请在TWS的Resource界面填写正确的SN号")
            setattr(self, 'hardware_type', self.ati[:10])  # hardwareType值为RG500QEAAA，截取前七位为RG500QEA
        else:
            print("解析auto python参数")
            # taskProperty参数
            setattr(self, 'ati', self.task_property.get("name_ati_version", ''))
            setattr(self, 'csub', self.task_property.get("name_csub", '').replace('-', ''))
            setattr(self, 'svn', self.task_property.get("name_svn", ''))
            setattr(self, 'qefsver', self.task_property.get("name_qefsver", ''))
            setattr(self, 'qgmr', self.task_property.get("name_real_version", ''))
            setattr(self, 'gmr', self.task_property.get("name_ati_version", ''))
            setattr(self, 'firmware_path', self.task_property.get("path_sub_version", ''))
            # customPipeLineParams参数(Auto_Python里面是custom_params)
            if self.task_property.get("custom_params", '') and isinstance(self.task_property.get("custom_params"), dict):
                for k, v in self.task_property.get("custom_params").items():
                    setattr(self, k, v)
            # 避免系统下发custom_params为customPipeLineParams
            if self.task_property.get("customPipeLineParams", '') and isinstance(self.task_property.get("customPipeLineParams"), dict):
                for k, v in self.task_property.get("customPipeLineParams").items():
                    setattr(self, k, v)
            # main_device参数
            setattr(self, 'dev_imei_1', self.main_device.get("imei_number", ''))
            setattr(self, 'sn', self.main_device.get("sn", ''))
            if self.sn == '':
                all_logger.error("Resource中未发现SN相关配置，如需要获取SN号请在TWS的Resource界面填写正确的SN号")
            setattr(self, 'hardware_type', self.ati[:10])  # hardwareType值为RG500QEAAA，截取前七位为RG500QEA # noqa

    def __getattr__(self, item):
        return self.__dict__.get(item, '')


# params = {
#     'ip': '10.66.98.85',
#     'port': '55556',
#     'main_device': {},
#     'task_property': {},
#     'name_sub_version': "RG500QEAAAR11A06M4G_01.001V01.01.001V01"
# }
#
# args_5g = ParameterParser(**params)
#
# print(f"args.default_lte_band: {args_5g.default_lte_band}")
# print(f"args.ipv6_address: {args_5g.ipv6_address}")
# print(f"args.cversion: {args_5g.cversion}")
# print(f"args.ati: {args_5g.ati}")
# print(f"args.dev_imei_1: {args_5g.dev_imei_1}")
# print(f"args.prev_ati: {args_5g.prev_ati}")
# print(f"args.dev_mbim_driver_name: {args_5g.dev_mbim_driver_name}")
