import hashlib
import json
import time

"""
模拟数据
"""
server_message = {
    'fw_info_rpm': '',
    'name_sub_version': 'RG501QEUAAR12A06M4G_04.001.04.001_V03',
    'task_id': '1569595881529806849',
    'id_ci_task': '0',
    'name_svn': '39',
    'fw_info_modem': '',
    'version_path': '\\\\\\\\192.168.11.252\\\\quectel\\\\Project\\\\ModuleProjectFiles\\\\5GProject\\\\SDX55\\\\RG501QEU\\\\Release\\\\RG501QEU_VD_R12\\\\RG501QEUAAR12A06M4G_04.001.04.001_V03',
    'suggest_base_fw': '',
    'fw_info_sbl': '',
    'name_sdk_name': '',
    'case_addr': 'https: //stres.quectel.com: 8139/quectel5/M00/27/8F/rBEAA2MgN7KADfN8AAAjKJA6kfA22.json',
    'name_sale_fwpath': '',
    'name_ati_version': 'RG501QEUAAR12A06M4G',
    'env_type': '1',
    'name_base_sdk_name': '',
    'fw_info_tz': '',
    'timestamp': '2022-09-1315: 56: 40',
    'path_sub_version': '\\\\\\\\192.168.11.252\\\\quectel\\\\Project\\\\ModuleProjectFiles\\\\5GProject\\\\SDX55\\\\RG501QEU\\\\Release\\\\RG501QEU_VD_R12\\\\RG501QEUAAR12A06M4G_04.001.04.001_V03',
    'res': [
        {
            'meid': '111',
            'imei_number_hex': '383630333032303530303037393533',
            'deviceCardList': [
                {
                    'sim_imsi': '460027150204290',
                    'sim_operator': 'CMCC',
                    'sim_iccid_crsm': '9868001E210050202409',
                    'phonenumber_PDU': '8117841119F7',
                    'sca_number_PDU': '0891683108501505F0',
                    'phonenumber': '18714811917',
                    'evb_slot_number': 1,
                    'switcher': '',
                    'imsi_cdma': '460027150204290',
                    'phonenumber_HEX': '3138373134383131393137',
                    'sim_iccid': '898600E1120005024290',
                    'phonenumber_UCS2': '00310038003700310034003800310031003900310037',
                    'sca_number': '+8613800551500',
                    'sim_puk': '123456',
                    'operator_servicenumber': '10086',
                    'slot_number': 1
                },
                {
                    'sim_imsi': '01001',
                    'sim_operator': 'Verizon',
                    'sim_iccid_crsm': '',
                    'phonenumber_PDU': '1000F1',
                    'sca_number_PDU': '0891683108501505F0',
                    'phonenumber': '01001',
                    'evb_slot_number': 2,
                    'switcher': '',
                    'phonenumber_HEX': '3031303031',
                    'sim_iccid': '',
                    'phonenumber_UCS2': '00300031003000300031',
                    'sca_number': '+8613800551500',
                    'sim_puk': '111111',
                    'operator_servicenumber': '01001',
                    'slot_number': 1
                }
            ],
            'switcher': [

            ],
            'wiring_method': '0',
            'adb_id': '6cf251b1',
            'usbat': '/dev/ttyUSBAT',
            'imei_number': '860302050007953',
            'sim_info': [
                {
                    'sim_operator': 'CMCC',
                    'slot_number': 1
                },
                {
                    'sim_operator': 'Verizon',
                    'slot_number': 1
                }
            ],
            'log_port': '/dev/ttyUSBDM',
            'sn': 'P1Q21GA24000022',
            'chipPlatform': 'SDX55-1-AA',
            'sim_card_type': '2',
            'baud_rate': 115200,
            'debug': '/dev/ttyUSBDEBUG',
            'usbmodem': '/dev/ttyUSBMODEM',
            'device_id': '1451009068666720258',
            'upgrade': '/dev/ttyUSBDM',
            'version_type': '1',
            'ip': '10.66.98.253',
            'relay': '',
            'hardwareType': 'RG501QEUAA',
            'node_name': 'RG501QEUAA_Ubuntu_USB_ETH_CMCC',
            'version_upgrade': '1',
            'custom_com_port': [
                {
                    'device_com_key': 'COM1',
                    'device_com_port': '/dev/ttyUSBDM'
                }
            ],
            'device_number': 'RG501QEUAA_Ubuntu_USB_ETH_CMCC',
            'uart': '/dev/ttyUSBUART',
            'custom_fields_name': {
                'dev_manufacturer_model': 'RG501Q-EU',
                'dev_imei_2': '869710030002905',
                'dev_gobinet_driver_path': '/home/ubuntu/Tools_Ubuntu_SDX55/Drivers/GobiNet',
                'dev_rtl8125_ethernet_name': 'eth0',
                'dev_ppp_scripts': '/home/ubuntu/Desktop/linux-ppp-scripts',
                'dev_pc_ethernet_name': 'eth1',
                'dev_ecm_network_card_name': 'usb0',
                'dev_vid_pid_rev': '11388,2048',
                'dev_quectel_cm_path': '/home/ubuntu/Tools_Ubuntu_SDX55/quectel-CM',
                'dev_wwan_driver_path': '/home/ubuntu/Tools_Ubuntu_SDX55/Drivers/qmi_wwan_q',
                'dev_gobinet_network_card_name': 'usb0',
                'dev_sm_store': '50',
                'dev_qmi_network_card_name': 'wwan0_1',
                'dev_mbim_driver_name': 'wwan0',
                'dev_eth_test_mode': '2',
                'dev_rgmii_ethernet_name': 'eth2',
                'dev_me_store': '127'
            },
            'usbNmea': '/dev/ttyUSBNMEA'
        }
    ],
    'fw_network_type': '双卡单待',
    'name_version': 'RG501QEUAAR12A06M4G_04.001.04.001',
    'app_url': 'https: //stres.quectel.com: 8139/quectel5/M00/21/2F/rBEAA2MNyniAVjH0ARbK42OZamo516.zip?attname=execute_app.zip',
    'name_group': 'Eth_Backhaul',
    'name_branch': '//depot3/Qualcomm/SDX55/MCU_R12',
    'name_qsub': '-',
    'name_group_type': 'other',
    'test_type': '1',
    'token': 'EDFCB630692FF342FEE5603F61A65A79E5653C75D359EC67',
    'name_qefsver': 'RG501QEU_VD_V00007_202207221',
    'name_sale_fw': '',
    'app_name': 'execute_app.zip',
    'fw_basic_type': '普通版本',
    'name_csub': 'V03',
    'version_name': 'RG501QEUAAR12A06M4G_04.001.04.001_V03',
    'custom_info': '',
    'name_qapsub': '-',
    'name_real_version': 'RG501QEUAAR12A06M4G_04.001.04.001',
    'name_factory_fwname': 'RG501QEUAAR12A06M4G_04.001.04.001_V03_factory',
    'name_qapver_version': '',
    'socket_port': 35147,
    'running_mode': 1,
    'script_temp_path': '/tmp/script_temp/tmpw88az4xj'
}

# 任务ID      优先级		case		    项目		        持续时间		    任务状态			        task
# 唯一生成     p1-p5		name_group	    node_name+ip	tesk_duration	新建-排队中-执行中-已完成	运营商、band组合


task_priority_list = [1, 2, 3, 4, 5]
task_priority = task_priority_list[2]

name_group = server_message['name_group']

node_name = server_message['res'][0]['node_name']  # noqa

ip = server_message['res'][0]['ip']  # noqa

md5 = hashlib.md5()
start_time_str = str(int(time.time()))[:10]
md5.update(f'{name_group}{node_name}{start_time_str}'.encode('utf-8'))
task_id = md5.hexdigest()[:10]
# task_id = '7fe75dac8e'

test_devices = node_name + ':' + ip

tesk_duration = 300
# tesk_duration = 120

task_status_list = [0, 1, 2, 3]  # 新建-排队中-执行中-已完成
task_status = task_status_list[0]

# task = 'CMCC_B3N78'
# task = ['00101-mme-ims.cfg', '00101-gnb-nsa-b3n78-OK.cfg']
task = ['00101-mme-ims.cfg', '00101-nsa-b2n41-OK.cfg']

# task = 'CMCC_N78'

qss_ip = '10.66.98.136'

# print(task)


def is_json(myjson):
    try:
        json.loads(myjson)
    except Exception as e:
        print(e)
        return False
    return True


json_qss_dict = {
    'task_id': task_id,  # 任务唯一ID
    'task_priority': task_priority,  # 任务优先级
    'task_status': task_status,  # 任务状态
    'task': task,  # 任务内容
    'tesk_duration': tesk_duration,  # 任务持续时间 + 增加测试时间
    'name_group': name_group,  # 任务所属case
    'test_devices': test_devices,  # 任务所属设备
    'qss_ip': qss_ip,
}
json_qss = json.dumps(json_qss_dict)

# json.loads(json_qss)
# print(is_json(json_qss))
# print(is_json("""{"a":1}"""))
# print(is_json(server_message))

# print(json.loads(json_qss)['task_priority'])

# s1 = """deque([(3, "{"task_id": "7fe75dac8e", "task_priority": 3, "task_status": 0, "task": "CMCC_B3N78", "tesk_duration": 300, "name_group": "Eth_Backhaul", "test_devices": "RG501QEUAA_Ubuntu_USB_ETH_CMCC:10.66.98.253"}'), (3, '{"task_id": "7fe75dac8e", "task_priority": 3, "task_status": 0, "task": "CMCC_B3N78", "tesk_duration": 300, "name_group": "Eth_Backhaul", "test_devices": "RG501QEUAA_Ubuntu_USB_ETH_CMCC:10.66.98.253"}'), (3, '{"task_id": "7fe75dac8e", "task_priority": 3, "task_status": 0, "task": "CMCC_B3N78", "tesk_duration": 300, "name_group": "Eth_Backhaul", "test_devices": "RG501QEUAA_Ubuntu_USB_ETH_CMCC:10.66.98.253"}'), (3, '{"task_id": "7fe75dac8e", "task_priority": 3, "task_status": 0, "task": "CMCC_B3N78", "tesk_duration": 300, "name_group": "Eth_Backhaul", "test_devices": "RG501QEUAA_Ubuntu_USB_ETH_CMCC:10.66.98.253"}'), (3, '{"task_id": "7fe75dac8e", "task_priority": 3, "task_status": 0, "task": "CMCC_B3N78", "tesk_duration": 300, "name_group": "Eth_Backhaul", "test_devices": "RG501QEUAA_Ubuntu_USB_ETH_CMCC:10.66.98.253"}'), (3, '{"task_id": "7fe75dac8e", "task_priority": 3, "task_status": 0, "task": "CMCC_B3N78", "tesk_duration": 300, "name_group": "Eth_Backhaul", "test_devices": "RG501QEUAA_Ubuntu_USB_ETH_CMCC:10.66.98.253"}')])"""
# s2 = {"task_id": "7fe75dac8e", "task_priority": 3, "task_status": 0, "task": "CMCC_B3N78", "tesk_duration": 300, "name_group": "Eth_Backhaul", "test_devices": "RG501QEUAA_Ubuntu_USB_ETH_CMCC:10.66.98.253"}
# print(s2 in s1)
# json_2 = json.loads(json_qss)
# json_2['task_status'] = 5
# json_3 = json.dumps(json_2)
# print(json_2)

# q = queue.Queue()
# q.put((3, s2))
# task = q.get()
# task_key = task[1]['task_status']
# print(task)
# print(task_key)


"""
def motify_task(task, motify_key, motify_value):
    # 修改任务内容
    json_2 = json.loads(task)
    json_2[motify_key] = motify_value
    json_3 = json.dumps(json_2)
    return json_3

def motify_task_with_priority(task_witth_priority, motify_key, motify_value, recv_queue_now):
    print('now to motify task')
    print(json.loads(task_witth_priority[1]))
    task = task_witth_priority[1]
    task_priority = json.loads(task_witth_priority[1])['task_priority']
    json_motify = motify_task(task, motify_key, motify_value)
    recv_queue_now.put((task_priority, json_motify))  # 不在则加入任务队列并修改任务状态


def query_task_content(task_id, content, recv_queue_now):
    for i in range(recv_queue_now.qsize()):
        task = recv_queue_now.get()
        if json.loads(task[1])["task_id"] == task_id:
            print(f'已找到{task_id}任务')
            recv_queue_now.put(task)
            print(f'所查询内容为:{json.loads(task[1])[content]}')
            return json.loads(task[1])[content]
        else:
            recv_queue_now.put(task)
            time.sleep(0.01)
    else:
        print(f'未找到该任务：{task_id}')


qss_json_list_que = queue.Queue()
qss_json_list_que.put((3, '{"task_id": "1111111111", "task_priority": 3, "task_status": 1, "task": "CMCC_B3N78", "tesk_duration": 300, "name_group": "Eth_Backhaul", "test_devices": "RG501QEUAA_Ubuntu_USB_ETH_CMCC:10.66.98.253"}'))
qss_json_list_que.put((3, '{"task_id": "2222222222", "task_priority": 3, "task_status": 2, "task": "CMCC_B3N78", "tesk_duration": 300, "name_group": "Eth_Backhaul", "test_devices": "RG501QEUAA_Ubuntu_USB_ETH_CMCC:10.66.98.253"}'))
qss_json_list_que.put((3, '{"task_id": "3333333333", "task_priority": 3, "task_status": 2, "task": "CMCC_B3N78", "tesk_duration": 300, "name_group": "Eth_Backhaul", "test_devices": "RG501QEUAA_Ubuntu_USB_ETH_CMCC:10.66.98.253"}'))
print(qss_json_list_que.queue)
print(qss_json_list_que.qsize())

for i in range(qss_json_list_que.qsize()):
    task = qss_json_list_que.get()
    print(f'{json.loads(task[1])["task_id"]}')
    if json.loads(task[1])["task_id"] == '3333333333':
        print('更新任务状态')
        motify_task_with_priority(task, 'task_status', 3, qss_json_list_que)
    else:
        qss_json_list_que.put(task)

query_task_content('134', 'tesk_duration', qss_json_list_que)
print(qss_json_list_que.queue)
"""

"""
qss_json_list_que = queue.PriorityQueue()
qss_json_list_que.put((3, '{"task_id": "1111111111", "task_priority": 3, "task_status": 1, "task": "CMCC_B3N78", "tesk_duration": 300, "name_group": "Eth_Backhaul", "test_devices": "RG501QEUAA_Ubuntu_USB_ETH_CMCC:10.66.98.253"}'))
qss_json_list_que.put((3, '{"task_id": "2222222222", "task_priority": 3, "task_status": 2, "task": "CMCC_B3N78", "tesk_duration": 300, "name_group": "Eth_Backhaul", "test_devices": "RG501QEUAA_Ubuntu_USB_ETH_CMCC:10.66.98.253"}'))
qss_json_list_que.put((1, '{"task_id": "3333333333", "task_priority": 3, "task_status": 2, "task": "CMCC_B3N78", "tesk_duration": 300, "name_group": "Eth_Backhaul", "test_devices": "RG501QEUAA_Ubuntu_USB_ETH_CMCC:10.66.98.253"}'))
print(qss_json_list_que.queue)
print(qss_json_list_que.qsize())
print(qss_json_list_que.)
"""
"""
import heapq


class Empty(Exception):
    print('队列为空')


class PriorityQueue(object):
    # 优先级队列
    def __init__(self):
        self._queue = []  # 建立一个空列表用于存放队列
        self._index = 0  # 指针用于记录push的次序

    def push(self, priority, item):
        #队列由（priority, index, item)形式的元祖构成
        heapq.heappush(self._queue, (priority, self._index, item))
        self._index += 1

    def pop(self):
        if len(self._queue) != 0:
            return heapq.heappop(self._queue)[-1]  # 返回拥有最高优先级的项
        else:
            raise Empty

    @property
    def queue(self):
        return self._queue
"""
"""
if __name__ == '__main__':
    q = queue.PriorityQueue()
    q.put((5, 1, '{"task_id": "1111111111", "task_priority": 3, "task_status": 1, "task": "CMCC_B3N78", "tesk_duration": 300, "name_group": "Eth_Backhaul", "test_devices": "RG501QEUAA_Ubuntu_USB_ETH_CMCC:10.66.98.253"}'))
    q.put((1, 2, '{"task_id": "4444444444", "task_priority": 3, "task_status": 1, "task": "CMCC_B3N78", "tesk_duration": 300, "name_group": "Eth_Backhaul", "test_devices": "RG501QEUAA_Ubuntu_USB_ETH_CMCC:10.66.98.253"}'))
    q.put((3, 3, '{"task_id": "3333333333", "task_priority": 3, "task_status": 1, "task": "CMCC_B3N78", "tesk_duration": 300, "name_group": "Eth_Backhaul", "test_devices": "RG501QEUAA_Ubuntu_USB_ETH_CMCC:10.66.98.253"}'))
    q.put((1, 4, '{"task_id": "2222222222", "task_priority": 3, "task_status": 1, "task": "CMCC_B3N78", "tesk_duration": 300, "name_group": "Eth_Backhaul", "test_devices": "RG501QEUAA_Ubuntu_USB_ETH_CMCC:10.66.98.253"}'))

    for i in range(5):
        # print(q.queue)
        print(q.get_nowait())
"""
"""
test = []
print(test)
test.append(1)
print(test)
test.append(2)
print(test)
test.append(3)
print(test)
"""
"""
name = task[0]
path = f"E:"

print(name)
for p, dirs, f in os.walk(path):
    for dir1 in dirs:
        if 'ltemme-linux-' in dir1:
            print(dir1)
            print(p)
            print(os.path.join(p, dir1))
"""

"""
imsi = '311480110325476'
print(len(imsi))
if len(imsi) > 10:
    print("YES")
else:
    print("NO")

imsi_command_need = imsi[0] + '9'
imsi_need = imsi[1:]
print(f"now to change : {imsi_need}")
imsi_list = []
for i in range(len(imsi_need)):
    imsi_list.append(imsi_need[i])
    if i % 2 != 0:
        str_change_mid = imsi_list[i]
        imsi_list[i] = imsi_list[i-1]
        imsi_list[i-1] = str_change_mid
str_change_result = "".join(imsi_list)
print(f"change result : {str_change_result}")

imsi_command_need = imsi_command_need + str_change_result
print(f'imsi_command_need : {imsi_command_need}')

"""


simcard_info_ue_db = """
},{
    sim_algo: "milenage",
    imsi: "111111111111111",
    opc: "000102030405060708090A0B0C0D0E0F",
    amf: 0x9001,
    sqn: "000000000000",
    K: "00112233445566778899AABBCCDDEEFF",
    impu: ["sip:2222222222222", "tel:444444444"],
    impi: "333333333333333@ims.mnc010.mcc001.3gppnetwork.org",
    multi_sim: false,
"""

"""
print(ue_db_file_path)
for p, d, f in os.walk(ue_db_file_path):
    for file in f:
        if file == ue_db_file_name:
            print(file)
            ue_db_file_name = os.path.join(p, file)
            print(ue_db_file_name)
            with open(ue_db_file_name, 'r', encoding='utf-8') as file_read:
                content = file_read.read()
            content_add = simcard_info_ue_db
            pos = content.find("},")
            if pos != -1:
                content = content[:pos] + content_add + content[pos:]
            with open(os.path.join(ue_db_file_path, '0826-ue_db-ims_test20221016.cfg'), 'w', encoding='utf-8') as file_write:
                file_write.write(content)
                print(os.path.join(ue_db_file_path, '0826-ue_db-ims_test20221016.cfg'))
            break
    else:
        print(f"未找到 {ue_db_file_name}")
"""
"""
imsi = '311480110325476'
print(imsi[:6])
print(imsi[-3:])
"""
return_value = """
AT+QNWCFG="ctrl_plane_dly"

+QNWCFG: "ctrl_plane_dly",1,"LTE",0

OK
"""
"""
result = re.findall(r'QNWCFG: "ctrl_plane_dly",1,"(.*)",(.*)', return_value)
print(result[0][0])
"""
