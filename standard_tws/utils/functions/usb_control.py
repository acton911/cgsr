import serial


def usb_disconnect(port):
    """
    控制USB断开连接
    @param port:usb控制器端口
    @return:
    """
    with serial.Serial(port, baudrate=9600, timeout=0) as _usb_port:
        _usb_port.write(bytes.fromhex('00'))


def usb_connect(port):
    """
    控制USB连接
    @param port:usb控制器端口
    @return:
    """
    with serial.Serial(port, baudrate=9600, timeout=0) as _usb_port:
        _usb_port.write(bytes.fromhex('01'))
