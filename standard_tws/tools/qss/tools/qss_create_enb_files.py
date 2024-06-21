from tools.qss.logger import logger
import os
import csv
"""
功能：批量生成enb文件
主要逻辑：
1、从enb模板中读取文件内容
2、找到plmn位置
3、修改plmn生成新的enb文件
"""
# ***************关键参数，需要修改确认***********************************************************************************************************
# 模板enb文件位置，用来复制和参考
base_enb_file_path_now = r'E:\project\qss_config_files\standard_tws\tools\qss\files\10.66.129.204\2022-06-18\lteenb-linux-2022-06-18\config\Limit_R_And_I\25001-fdd-enb-lte-b3.cfg'
# 新enb文件plmn
enb_plmn_now = '25001'
# 当前已有的enb文件集合路径
search_file_path = r'E:\project\qss_config_files\standard_tws\tools\qss\files\10.66.129.204\2022-06-18\lteenb-linux-2022-06-18\config'
# 新enb文件plmn合集列表，有则填写，没有则不用关注,需要有一列列名为plmn的数据
enb_plmns_path_now = r'E:\project\qss_config_files\standard_tws\tools\qss\files\Record.csv'
# 新生成enb文件存位置，用来存放新enb文件，没有或者路径不对，则会生成到脚本运行的路径
save_new_enb_file_path = r'E:\project\qss_config_files\standard_tws\tools\qss\files\10.66.129.204\2022-06-18\ltemme-linux-2022-06-18\config\enb_new_20230217'

# *****************默认参数，一般无需修改**********************************************************************************************************
# 其他参数，一般无需修改
colmn_name_plmn = 'plmn'


def read_csv_culmn(enb_plmns_path, colmn_name):
    if os.path.exists(enb_plmns_path):
        with open(enb_plmns_path, 'r') as csvfile:
            reader = csv.DictReader(csvfile)
            column = [row[colmn_name] for row in reader]
            logger.info(column)
            return column
    else:
        logger.error(f"未找到 {enb_plmns_path}")


def write_enb_files(base_enb_file_path, enb_plmn):
    old_enb_files_name = os.path.basename(base_enb_file_path)
    old_plmn = old_enb_files_name.split('-')[0]
    new_enb_files_name = old_enb_files_name.replace(old_plmn, enb_plmn)
    logger.info(new_enb_files_name)
    find_flag = False
    for _, _, files in os.walk(search_file_path):
        for file in files:
            if file == new_enb_files_name:
                find_flag = True
                break
    if find_flag:
        logger.info(f'此配置文件已存在，无需再生成:{new_enb_files_name}')
    else:
        logger.info(base_enb_file_path)
        if os.path.exists(base_enb_file_path):
            with open(base_enb_file_path, 'r', encoding='utf-8') as file_read:
                content = file_read.read()
            content_write = content.replace(old_plmn, enb_plmn)
            new_enb_file_name = old_enb_files_name.replace(old_plmn, enb_plmn)
            if os.path.exists(save_new_enb_file_path):
                new_enb_file_path = os.path.join(save_new_enb_file_path, new_enb_file_name)
            else:
                new_enb_file_path = os.path.join(os.getcwd(), new_enb_file_name)
            with open(new_enb_file_path, 'w', encoding='utf-8') as file_write:
                file_write.write(content_write)
                logger.info(new_enb_file_path)
        else:
            logger.error(f"未找到 {base_enb_file_path}")


if os.path.exists(enb_plmns_path_now):
    enb_file_name_list = read_csv_culmn(enb_plmns_path_now, colmn_name_plmn)
    for i in enb_file_name_list:
        logger.info(i)
        write_enb_files(base_enb_file_path_now, i)
else:
    write_enb_files(base_enb_file_path_now, enb_plmn_now)
