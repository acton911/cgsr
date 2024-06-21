需要放到server上的http导入模块

/home/auto/Services/HTTP

开启Nginx
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
    listen  80;          # 监听端口
    server_name    10.66.98.85; # 自己PC的ip或者服务器的域名
    charset utf-8; # 避免中文乱码
    root /home/auto/Services/HTTP;    # 文件路径
    location / {
        autoindex on; # 索引
        autoindex_exact_size on; # 显示文件大小
        autoindex_localtime on; # 显示文件时间
    }
}
```
