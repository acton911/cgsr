MicroPython RESTful API

# 基本原理
打开MicroPython的端口，PC端启用HTTP server，Server根据不同的命令进行引脚的控制和读取动作；

# 支持功能
1. 根据树莓派Pico的PID、VID自动查找并打开端口
2. 树莓派插拔之后自动检测打开口，并恢复默认的初始电平
3. Windows开机自启
4. Ubuntu开机自启

# 自动化部署相关
在脚本第一次运行时候

1. Windows端目录C:\Users\<username>\AppData\Roaming\Microsoft\Windows\Start Menu\Programs\Startup\目录下会自动创建
micropython.bat文件，此目录的文件为了控制PC端开机之后自动运行MicroPython Server;

2. Ubuntu端/lib/systemd/system下会创建micropython.service文件，重启后后台会自动运行micropython服务，通过
`journalctl -u micropython.service -r`可以查看micropython的运行状态

# 问题
1. Linux启动MicroPython
    ```
    service micropython start
    ```
2. Linux查看micropython log
    ```
    journalctl -u micropython.service -r
    ```
