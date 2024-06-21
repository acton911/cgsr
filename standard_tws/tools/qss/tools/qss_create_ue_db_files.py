from tools.qss.logger import logger
import os
from tools.qss.qss_client import WriteSimcard
import csv
"""
功能：批量生成ue_db文件
主要逻辑：
1、根据plmn生成sim卡imsi信息
2、根据imsi信息生成新的ue_db信息
"""
# ***************关键参数，需要修改确认***********************************************************************************************************
# 新ue_db文件plmn
ue_db_plmn_now = '44051'
# 当前已有的ue_db路径
search_file_path = r'E:\project\qss_config_files\standard_tws\tools\qss\files\10.66.129.204\2022-06-18\ltemme-linux-2022-06-18\config\0826-ue_db-ims.cfg'
# 新ue_db文件plmn合集列表，有则填写，没有则不用关注,需要有一列列名为plmn的数据
ue_db_plmns_path_now = r'E:\project\qss_config_files\standard_tws\tools\qss\files\Record.csv'
# 新生成ue_db文件存位置，用来存放新ue_db文件，没有或者路径不对，则会生成到脚本运行的路径
save_new_ue_db_file_path = r'E:\project\qss_config_files\standard_tws\tools\qss\files\10.66.129.204\2022-06-18\ltemme-linux-2022-06-18\config\ue_db_new_20230217'

# *****************默认参数，一般无需修改**********************************************************************************************************
# 其他参数，一般无需修改
colmn_name_plmn = 'plmn'


def read_csv_culmn(ue_db_plmns_path, colmn_name):
    if os.path.exists(ue_db_plmns_path):
        with open(ue_db_plmns_path, 'r') as csvfile:
            reader = csv.DictReader(csvfile)
            column = [row[colmn_name] for row in reader]
            logger.info(column)
            return column
    else:
        logger.error(f"未找到 {ue_db_plmns_path}")


def write_ue_db_info(imsi_sim):
    mcc = imsi_sim[:3]
    if len(imsi_sim) >= 6:
        mnc = imsi_sim[3:6]
    elif len(imsi_sim) == 5:
        mnc = '0' + imsi_sim[3:5]
    else:
        logger.error(f'imsi信息异常！{imsi_sim}')
        return ''
    ismi_ue_db = imsi_sim if len(imsi_sim) == 15 else WriteSimcard("_").get_white_simcard_imsi(imsi_sim)
    find_flag = False
    with open(search_file_path, 'r') as f:
        content_read = f.read()
        if ismi_ue_db in content_read:
            find_flag = True
    if find_flag:
        logger.info('此sim配置文件中已经包含')
        return ''
    else:
        simcard_info_ue_db = "},{" + f"""
    sim_algo: "milenage",
    imsi: "{ismi_ue_db}",
    opc: "000102030405060708090A0B0C0D0E0F",
    amf: 0x9001,
    sqn: "000000000000",
    K: "00112233445566778899AABBCCDDEEFF",
    impu: ["sip:{ismi_ue_db}", "tel:{ismi_ue_db[:6]}{ismi_ue_db[-3:]}"],
    impi: "{ismi_ue_db}@ims.mnc{mnc}.mcc{mcc}.3gppnetwork.org",
    multi_sim: false,
            """
        return simcard_info_ue_db


if os.path.exists(ue_db_plmns_path_now):
    ue_db_file_name_list = read_csv_culmn(ue_db_plmns_path_now, colmn_name_plmn)
    content_write = ''
    for i in ue_db_file_name_list:
        logger.info(i)
        ue_db_new_i = write_ue_db_info(i)
        if ue_db_new_i != '' and ue_db_new_i not in content_write:
            content_write += ue_db_new_i
    if os.path.exists(save_new_ue_db_file_path):
        new_enb_file_path = os.path.join(save_new_ue_db_file_path, 'ue_db_info.txt')
    else:
        new_enb_file_path = os.path.join(os.getcwd() + 'ue_db_info.txt')
    with open(new_enb_file_path, 'w', encoding='utf-8') as file_write:
        file_write.write(content_write)
        logger.info(new_enb_file_path)
else:
    ue_db = write_ue_db_info(ue_db_plmn_now)
    logger.info(ue_db)
    if os.path.exists(save_new_ue_db_file_path):
        new_enb_file_path = os.path.join(save_new_ue_db_file_path, 'ue_db_info.txt')
    else:
        new_enb_file_path = os.path.join(os.getcwd(), 'ue_db_info.txt')
    with open(new_enb_file_path, 'w', encoding='utf-8') as file_write:
        file_write.write(ue_db)
    logger.info(new_enb_file_path)
