��Ҫ�ŵ�server�ϵ�http����ģ��

/home/auto/Services/HTTP

����Nginx
```bash
apt update
sudo apt-get install nginx
sudo gedit /etc/nginx/conf.d/file_server.conf
sudo vim /etc/nginx/conf.d/file_server.conf
sudo rm /etc/nginx/sites-enabled/default
sudo service nginx reload
sudo service nginx restart
sudo service nginx restart
systemctl status nginx.service
service nginx stop
service nginx start
```

file_server.conf
```
server {
    listen  80;          # �����˿�
    server_name    10.66.98.85; # �Լ�PC��ip���߷�����������
    charset utf-8; # ������������
    root /home/auto/Services/HTTP;    # �ļ�·��
    location / {
        autoindex on; # ����
        autoindex_exact_size on; # ��ʾ�ļ���С
        autoindex_localtime on; # ��ʾ�ļ�ʱ��
    }
}
```
