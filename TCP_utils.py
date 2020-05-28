import struct
import json
import time


def create_header(id, data):
    """
    客户端编号
    :param id:
    :param data:
    :return:
    """

    data_len = len(data)
    head_info = {'id': id, 'data_length': data_len}
    head_json = json.dumps(head_info)
    head_bytes = head_json.encode('utf-8')
    head_bytes_len = len(head_bytes)
    head_length = struct.pack('i', head_bytes_len)
    return head_length, head_bytes


def parse_header(conn):
    """
    建立的连接
    :param conn:
    :return:
    """
    head_info = conn.recv(4)
    head_length = struct.unpack('i', head_info)[0]  # 元组格式
    data_head = conn.recv(head_length).decode('utf-8')
    data_head = json.loads(data_head)
    return data_head