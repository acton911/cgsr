# 起因
为不能自定义LiteAPI，但是我们又需要去支持pylite脚本查询数据库，故使用RESTful API进行查询。

# 用法
```shell script
ssh auto@10.66.98.85
cd /home/auto/Services/Params
nohup python3 -u parameter_server.py > out.log 2>&1 &
```
