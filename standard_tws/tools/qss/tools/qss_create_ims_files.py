from tools.qss.logger import logger
import os
import csv
"""
功能：批量生成ims文件
主要逻辑：
1、从ims模板中读取文件内容
2、找到plmn位置
3、修改plmn生成新的ims文件
"""
# ***************关键参数，需要修改确认***********************************************************************************************************
# 模板ims文件位置，用来复制和参考
base_ims_file_path_now = r'E:\project\qss_config_files\standard_tws\tools\qss\files\10.66.129.204\2022-06-18\ltemme-linux-2022-06-18\config\50501-ims.cfg'
# 新ims文件plmn
ims_plmn_now = '44051'
# 当前已有的ims文件集合路径
search_file_path = r'E:\project\qss_config_files\standard_tws\tools\qss\files\10.66.129.204\2022-06-18\ltemme-linux-2022-06-18\config'
# 新ims文件plmn合集列表，有则填写，没有则不用关注,需要有一列列名为plmn的数据
ims_plmns_path_now = r'E:\project\qss_config_files\standard_tws\tools\qss\files\Record.csv'
# 新生成ims文件存位置，用来存放新ims文件，没有或者路径不对，则会生成到脚本运行的路径
save_new_ims_file_path = r'E:\project\qss_config_files\standard_tws\tools\qss\files\10.66.129.204\2022-06-18\ltemme-linux-2022-06-18\config\ims_new_20230217'

# *****************默认参数，一般无需修改**********************************************************************************************************
# 其他参数，一般无需修改
# domain:"ims.mnc001.mcc505.3gppnetwork.org",
ims_plmn_place_start = 'domain:"ims.mnc'
ims_plmn_place_end = '.3gppnetwork.org'
colmn_name_plmn = 'plmn'


def read_csv_culmn(ims_plmns_path, colmn_name):
    if os.path.exists(ims_plmns_path):
        with open(ims_plmns_path, 'r') as csvfile:
            reader = csv.DictReader(csvfile)
            column = [row[colmn_name] for row in reader]
            logger.info(column)
            return column
    else:
        logger.error(f"未找到 {ims_plmns_path}")


def write_ims_files(base_ims_file_path, ims_plmn):
    old_ims_files_name = os.path.basename(base_ims_file_path)
    old_plmn = old_ims_files_name.split('-')[0]
    new_ims_files_name = old_ims_files_name.replace(old_plmn, ims_plmn)
    logger.info(new_ims_files_name)
    find_flag = False
    for _, _, files in os.walk(search_file_path):
        for file in files:
            if file == new_ims_files_name:
                find_flag = True
                break
    if find_flag:
        logger.info(f'此配置文件已存在，无需再生成:{new_ims_files_name}')
    else:
        mcc = ims_plmn[:3]
        if len(ims_plmn) >= 6:
            mnc = ims_plmn[3:6]
        elif len(ims_plmn) == 5:
            mnc = '0' + ims_plmn[3:5]
        else:
            logger.error(f'plmn信息异常！{ims_plmn}')
            return False
        logger.info(mcc)
        logger.info(mnc)
        logger.info(base_ims_file_path)
        if os.path.exists(base_ims_file_path):
            with open(base_ims_file_path, 'r', encoding='utf-8') as file_read:
                content = file_read.read()
            pos1 = content.find(ims_plmn_place_start)
            logger.info(pos1)
            pos2 = content.find(ims_plmn_place_end)
            logger.info(pos2)
            if pos1 != -1 and pos2 != -1:
                content_write = content[:pos1] + 'domain:"ims.mnc' + mnc + '.mcc' + mcc + content[pos2:]
            else:
                logger.error("创建ims文件异常")
                raise Exception
            if os.path.exists(save_new_ims_file_path):
                new_ims_file_path = os.path.join(save_new_ims_file_path, ims_plmn + '-ims.cfg')
            else:
                new_ims_file_path = os.path.join(os.getcwd(), ims_plmn + '-ims.cfg')
            with open(new_ims_file_path, 'w', encoding='utf-8') as file_write:
                file_write.write(content_write)
                logger.info(new_ims_file_path)
        else:
            logger.error(f"未找到 {base_ims_file_path}")


if os.path.exists(ims_plmns_path_now):
    ims_file_name_list = read_csv_culmn(ims_plmns_path_now, colmn_name_plmn)
    for i in ims_file_name_list:
        logger.info(i)
        write_ims_files(base_ims_file_path_now, i)
else:
    write_ims_files(base_ims_file_path_now, ims_plmn_now)
