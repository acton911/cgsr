MicroPython RESTful API

# ����ԭ��
��MicroPython�Ķ˿ڣ�PC������HTTP server��Server���ݲ�ͬ������������ŵĿ��ƺͶ�ȡ������

# ֧�ֹ���
1. ������ݮ��Pico��PID��VID�Զ����Ҳ��򿪶˿�
2. ��ݮ�ɲ��֮���Զ����򿪿ڣ����ָ�Ĭ�ϵĳ�ʼ��ƽ
3. Windows��������
4. Ubuntu��������

# �Զ����������
�ڽű���һ������ʱ��

1. Windows��Ŀ¼C:\Users\<username>\AppData\Roaming\Microsoft\Windows\Start Menu\Programs\Startup\Ŀ¼�»��Զ�����
micropython.bat�ļ�����Ŀ¼���ļ�Ϊ�˿���PC�˿���֮���Զ�����MicroPython Server;

2. Ubuntu��/lib/systemd/system�»ᴴ��micropython.service�ļ����������̨���Զ�����micropython����ͨ��
`journalctl -u micropython.service -r`���Բ鿴micropython������״̬

# ����
1. Linux����MicroPython
    ```
    service micropython start
    ```
2. Linux�鿴micropython log
    ```
    journalctl -u micropython.service -r
    ```
