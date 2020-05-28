# import socket
# import TCP_utils
# import time
#
#
# # socket.AF_INET使用ipv4协议族
# # socket.SOCK_STREAM使用tcp通讯
# sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
#
# # 绑定端口和地址
# addr = ("10.66.98.111", 9089)  # 改为自己的服务器ip或者本地回环
# sock.bind(addr)
#
# # 监听接入访问的socket
# sock.listen(10)
# while True:
#     print("server is waiting")
#     # 接收消息
#     conn, addr = sock.accept()  # 接收客户端连接
#     data_head = TCP_utils.parse_header(conn)
#     data_len = data_head['data_len']
#     data = conn.recv(data_len)
#     print("服务端收到消息：{}".format(data.decode("utf-8")))
#     # 发送反馈
#     time.sleep(3)
#     msg = 'finish connect'
#     head_len, head_bytes = TCP_utils.create_header('server', msg)
#     conn.send(head_len)
#     conn.send(head_bytes)
#     conn.sendall(msg.encode('utf-8'))
#
#     conn.close()

import socket
import TCP_utils
import time
# socket.AF_INET使用ipv4协议族
# socket.SOCK_STREAM使用tcp通讯
sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
# 绑定端口和地址
addr = ("10.66.98.111", 9089)  # 改为自己的服务器ip或者本地环回
sock.bind(addr)
# 监听接入访问的socket
sock.listen(10)
while True:
    print("server is waiting")
    # 接收消息
    time.sleep(1)
    conn, addr = sock.accept()  # 接受客户端连接
    data_head = TCP_utils.parse_header(conn)
    print(data_head, type(data_head))
    time.sleep(3)
    data_len = data_head['data_len']
    data = conn.recv(data_len)
    print("服务端收到消息：{}".format(data.decode("utf-8")))
    # 发送反馈
    msg = 'finish connect'
    head_len, head_bytes = TCP_utils.create_header('server', msg)
    conn.send(head_len)
    conn.send(head_bytes)
    conn.sendall(msg.encode('utf-8'))

    conn.close()
