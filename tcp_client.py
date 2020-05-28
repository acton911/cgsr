import socket
import TCP_utils


# 发送内容到服务器
while True:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    addr = ("10.66.98.111", 9089)
    sock.connect(addr)
    msg = input("发送消息：")
    head_len, head_info = TCP_utils.create_header("client1", msg)
    sock.send(head_len)
    sock.send(head_info)
    sock.sendall(msg.encode("utf-8"))

    # 接受反馈
    data_head = TCP_utils.parse_header(sock)
    data_len = data_head['data_len']
    data = sock.recv(data_len)
    print('收到消息', data.decode("utf-8"))
    # 关闭链路通路
    sock.close()