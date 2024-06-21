# 勿滥用
import requests
import logging
from pandas import DataFrame
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


df = DataFrame(columns=['Case', 'version', 'all',
                        'auto_all', 'auto_p0', 'auto_p1', 'auto_p2', 'auto_p3', 'auto_others',
                        "manual_all", 'manual_p0', 'manual_p1', 'manual_p2', 'manual_p3', 'manual_others'])

# 需要设置的部分
# 1. 打开https://tws.quectel.com:8152/case/caseLibrary?idGroup=847&nameGroup=MBIM%28Windows%29_SDX55
# 2. F12 -> Network -> F5
# 3. Cookie搜索"Qt-Function-Token-3"，复制token
token = "547cfbbf-0ec8-4cdb-aafc-65c7308b3388"
platform = "Universal"
snapshot_case = []
# 如果需要统计某个case的snapshot版本，则直接创建snapshot.txt文件，每一行一个case名称，不能多字符也不能少字符
if os.path.exists('snapshot.txt'):
    with open('snapshot.txt', 'r', encoding='utf-8') as f:
        snapshot_case = f.read().replace('\r', '').split('\n')
logger.info("snapshot_case: {}".format(snapshot_case))

# case mapping
platform_cases = {
    "Universal": "29",
}

# 获取Case页数
platform_id = platform_cases.get(platform)
logger.info('platform: {}'.format(platform))
logger.info('platform id: {}'.format(platform_id))
platform_str = '&id_function_group={}'.format(platform_id) if platform else ''
cases = dict()
r = requests.get("https://tws.quectel.com:8152/api/qt-case/casegroups/lte"
                 "?size=10&page=1{}&access_token={}".format(platform_str, token))
pages = r.json()['data']['pages']
logger.info('pages: {}'.format(pages))

# 获取所有Case页中的Case和ID
for page in range(1, pages + 1):
    r = requests.get("https://tws.quectel.com:8152/api/qt-case/casegroups/lte"
                     "?size=10&page={}{}&access_token={}".format(page, platform_str, token))
    records = r.json()['data']['records']
    for record in records:
        cases[record['id']] = record['name']

# 记录所有Case和ID
with open('{}_Cases.csv'.format(platform), 'w', encoding='utf-8') as f:
    f.write('id,case\n')
    for case_id, case in cases.items():
        f.write("{},{}\n".format(case_id, case))

# cases = {2328: 'PCIE_QMI(IPQ)_SDX55', 2327: 'PCIE_Upgrade(IPQ)_SDX55', 2315: 'BackupRestore_SDX55', 2298: 'LowPower_UDX710', 2297: 'CommonInfoQuery_UDX710', 2293: 'ECM_UDX710', 2292: 'RNDIS_UDX710', 2268: 'QuecOpen_产线ATCheck_T750', 2265: 'VOLTE&VOICE CALL_UDX710', 2257: 'SMS_UDX710', 2165: 'QuecOpen_EINT_T750', 2164: 'QuecOpen_DATACALL_T750', 2163: 'QuecOpen_SLIC_T750', 2162: 'QuecOpen_SMS_T750', 2161: 'QuecOpen_SIM_T750', 2160: 'QuecOpen_FOTA_T750', 2159: 'QuecOpen_Commoninfo_T750', 2158: 'QuecOpen_ADC_T750', 2155: 'QuecOpen_DSSS_T750', 2144: 'QuecOpen_GPIO_T750', 2142: 'QuecOpen_UART_T750', 2139: 'QuecOpen_DM_T750', 2138: 'QuecOpen_I2C_T750', 2116: 'QuecOpen_Pretest_Checklist_T750', 2115: 'QuecOpen_PowerONOFF_T750', 2114: 'QuecOpen_SGMII_T750', 2113: 'QuecOpen_RNDIS_T750', 2112: 'QuecOpen_NW_T750', 2095: 'Eve_DTMF_Tets', 2072: 'Yocto_BL_RTL8125_SDX55', 2047: 'QuecOpen_WIFI_T750', 1996: 'OPEN_UART_VERSION', 1989: 'QuecOpen_NITZ_UDX710', 1959: 'QuecOpen_DFOTA_UDX710', 1855: '备份还原_UDX710', 1822: '跨基线测试_SDX55', 1821: 'Lowpower(PCIE)_SDX55', 1810: 'QuecOpen_Audio', 1803: 'QuecOpen_VoiceCall', 1794: 'QuecOpen_ATC_UDX710', 1793: 'QuecOpen_SMS_UDX710', 1792: 'QuecOpen_VoiceCall_UDX710', 1791: 'QuecOpen_Uart_UDX710', 1790: 'QuecOpen_Audio_UDX710', 1789: 'QuecOpen_PM_UDX710', 1788: 'QuecOpen_SPI_UDX710', 1787: 'QuecOpen_GPIO_UDX710', 1786: 'QuecOpen_I2C_UDX710', 1785: 'QuecOpen_ADC_UDX710', 1784: 'QuecOpen_SimCard_UDX710', 1783: 'QuecOpen_Wan_UDX710', 1782: 'QuecOpen_Network_UDX710', 1781: 'QuecOpen_DM_UDX710', 1771: 'DFOTA(RGMII AT)_Hi9500', 1749: 'backup_recover_Hi9500', 1739: 'Secureboot_Hi9500', 1737: 'Upgrade(Ubuntu)', 1736: 'Emergency Call', 1734: 'AQC_SDX55', 1733: 'HTTP(S)', 1732: 'TCP&UDP', 1730: 'RTL8125_SDX55', 1703: 'RGMII AT_Hi9500', 1675: 'MBIM(Windows)_UDX710', 1663: 'DSSS_SDX55', 1599: 'ATFWD_SDX55', 1587: 'Certification_CTCC_UDX710', 1582: 'Pretest_Checklist_UDX710', 1523: 'ALLATC_SDX55', 1430: 'QMI_WWAN_SDX55', 1414: 'Carla_File_test', 1402: 'GNSS_SDX55', 1401: 'Network_Xenia_Auto', 1398: 'Audio record&play', 1396: 'Telstra', 1384: 'Android_SDX55', 1294: 'Upgrade_PowerONOFF_UDX710', 1209: 'QuecOpen_WIFI_SDX55', 1204: 'Pretest_Checklist_SDX55', 1200: 'NetLight_SDX55&UDX710', 1171: 'Flynn_Test', 1125: 'DFOTA(PCIE)_SDX55', 1123: 'DSSS_UDX710&Hi9500', 1119: 'Certification_CTCC_Hi9500', 1118: 'Certification_CMCC_Hi9500', 1116: 'SIMCARD', 1115: 'RI&URC', 1114: 'Network', 1113: 'PhoneBook', 1111: 'FILE', 1108: 'VOLTE&VOICE CALL', 1105: 'SLIC', 1104: 'SMS', 1103: 'PPP', 1102: 'RGMII_SDX55', 1085: 'DFOTA_SDX55', 1084: 'CCLK&NITZ', 1071: 'DFOTA_Hi9500', 1070: 'MBIM(Linux)_UDX710', 1067: 'AUDIO', 1065: 'DFOTA_UDX710', 1064: 'ProductiveATCheck_SDX55', 1054: 'ALLATC_Hi9500', 1034: 'ProductiveATCheck_Hi9500', 1031: 'USBcontrol_Hi9500', 1028: 'GNSS_Hi9500', 989: 'CommonInfoQuery', 956: 'ALLATC_UDX710', 893: 'PreChecklist_Hi9500', 890: 'UpgradePowerONOFF_Hi9500', 882: 'LowPower_UDX710&Hi9500', 881: 'SIMCardCompatibility_UDX710&Hi9500', 874: 'NDIS(win10)_SDX55', 870: 'SIMCardCompatibility_SDX55', 868: 'PCIE_UpgradePowerONOFF(Win10)_SDX55', 863: 'QuecOpen_NF', 862: 'PCIE_Upgrade(IPQ8074)_SDX55', 861: 'PCIE_QMI(linux)_SDX55', 860: 'PCIE_QMI(IPQ8074)_SDX55', 856: 'PCIE_MBIM(Windows)_SDX55', 854: 'PCIE_MBIM(linux)_SDX55', 852: 'PCIE_MBIM(IPQ8074)_SDX55', 848: 'Voice_of_USB_SDX55', 847: 'MBIM(Windows)_SDX55', 845: 'MBIM(Linux)_SDX55', 844: 'GobiNet_SDX55', 842: 'ECM_SDX55', 839: 'LowPower(Windows)_SDX55', 830: 'RGMII_Hi9500', 823: 'QuecOpen_EINT', 822: 'LowPower(Linux)_SDX55', 818: 'QuecOpen_WIFI', 817: 'QuecOpen_UpgradePowerONOFF', 815: 'QuecOpen_DFOTA', 814: 'QuecOpen_LowPower', 813: 'QuecOpen_SIMCardCompatibility', 812: 'QuecOpen_Network', 811: 'QuecOpen_UART', 810: 'Yocto_SDX55', 809: 'Yocto_UCL_DataCall_SDX55', 808: 'Yocto_UCL_CommInfo_SDX55', 807: 'Yocto_UCL_SIMCARD_SDX55', 806: 'Yocto_UCL_Network_SDX55', 801: 'QuecOpen_SMS', 800: 'QuecOpen_SIMCARD', 798: 'QuecOpen_DataCall', 797: 'QuecOpen_CommonInfoQuery', 791: 'QuecOpen_NITZ', 789: 'QuecOpen_SPI', 788: 'QuecOpen_I2C', 787: 'QuecOpen_GPIO', 785: 'QuecOpen_DM', 784: 'QuecOpen_ATC', 781: 'QuecOpen_ADC', 766: 'NCM(Linux)_Hi9500', 765: 'RNDIS_Hi9500', 754: 'ECM(Linux)_Hi9500', 748: 'NCM(Windows)_Hi9500', 729: 'NetLight_Hi9500', 699: 'Win10 SMS_SDX55', 698: 'ESIM_SDX55', 697: 'DTMF_SDX55', 693: 'RILC_UDX710', 692: 'Ethernet(Windows)_UDX710', 691: 'Ethernet(Linux)_UDX710', 690: 'Upgrade/PowerONOFF_SDX55', 684: '产线ATCheck_UDX710', 683: 'NCM(Linux)_UDX710'} # noqa
logger.info('cases: {}, len: {}'.format(cases, len(cases)))

for seq, (case_id, case_desc) in enumerate(cases.items()):
    if str(case_desc) == "AUTL定制" or str(case_desc) == "EG9x项目定制":
        continue
    if int(case_id) == 313 or int(case_id) == 312 or int(case_id) == 309:
        continue
    # 获取最新的Release或者Snapshot版本
    version = requests.get('https://tws.quectel.com:8152/api/qt-case/vcs/version/page?'
                           'size=100&page=1&id_group={}&data_label=1&access_token={}'.format(case_id, token))
    logger.debug('version_content: {}'.format(version.content.decode('utf-8')))
    records = version.json()['data']['records']
    versions = list()
    for record in records:
        versions.append("{}_{}_{}".format(record['type'], record['version_number'], record['id']))
    logger.debug("versions: {}, type: {}".format(versions, type(versions)))
    if not versions:  # 没有发过Snapshot和Release版本
        version = ('', '', '')
    elif 'release' not in ''.join(versions):  # 没有Release版本
        version = versions[0].split('_')
    elif case_desc not in snapshot_case:  # 如果想要获取Release版本
        for v in versions:
            if v.startswith('release'):
                version = v.split('_')
                break
    elif case_desc in snapshot_case:  # 如果想获取Snapshot版本
        for v in versions:
            if v.startswith('snapshot'):
                version = v.split('_')
                break
    else:  # 不存在
        if isinstance(version, tuple) is False:
            raise ValueError(f"Fail to get {case_desc} Case version.")

    version_str = '_'.join(version)
    logger.info(f'正在获取：{seq + 1} / {len(cases.keys())}, Case ID: {case_id}, Case名称: {case_desc}，version: {version_str}')

    # 获取Case中每条测试用例ID
    _, _, id_version = version
    id_version_str = "&id_version={}".format(id_version) if id_version else ''
    id_version_str_upper = "&idVersion={}".format(id_version) if id_version else ''
    ids = list()
    r = requests.get("https://tws.quectel.com:8152/api/qt-case/cases/group/tree?"
                     "id_group={}{}&access_token={}".format(case_id, id_version_str, token))
    for _cases in r.json()['data']:
        try:
            for case in _cases['children']:
                ids.append(case['id'])
        except TypeError:
            continue
    logger.info(ids)
    # 获取每条测试用例ID的属性
    ma = 0
    ap = 0
    ab = 0
    apy = 0
    alp = 0
    ado = 0
    aa = 0
    as1 = 0
    ape = 0
    for d in ids:
        r = requests.get("https://tws.quectel.com:8152/api/qt-case/cases/{}"
                         "?access_token={}{}".format(d, token, id_version_str_upper))
        if r.json()['data']['type_exec'] == 'ma':
            ma += 1
        if r.json()['data']['type_exec'] == 'ap':
            ap += 1
        if r.json()['data']['type_exec'] == 'ab':
            ab += 1
        if r.json()['data']['type_exec'] == 'apy':
            apy += 1
        if r.json()['data']['type_exec'] == 'alp':
            alp += 1
        if r.json()['data']['type_exec'] == 'ado':
            ado += 1
        if r.json()['data']['type_exec'] == 'aa':
            aa += 1
        if r.json()['data']['type_exec'] == 'as1':
            as1 += 1
        if r.json()['data']['type_exec'] == 'ape':
            ape += 1

    # df = DataFrame(columns=['Case名称', '总条数', "手动条数", '自动化条数', 'P0自动化Case数', 'P1自动化Case数',
    #                         'P2自动化Case数', 'P3自动化Case数', '其他条数'])
    df.loc[seq, 'Case'] = case_desc
    df.loc[seq, 'version'] = version_str
    df.loc[seq, 'ma'] = ma
    df.loc[seq, 'ap'] = ap
    df.loc[seq, 'ab'] = ab
    df.loc[seq, 'apy'] = apy
    df.loc[seq, 'alp'] = alp
    df.loc[seq, 'ado'] = ado
    df.loc[seq, 'aa'] = aa
    df.loc[seq, 'as1'] = as1
    df.loc[seq, 'ape'] = ape


df.to_csv('{}_statistic.csv'.format(platform), index=False, encoding='GBK')

logger.info("统计完成，按任意键退出")
os.system('pause')
