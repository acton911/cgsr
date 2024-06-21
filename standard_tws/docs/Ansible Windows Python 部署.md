# 下载任意Python包

https://www.python.org/ftp/python/3.9.0/python-3.9.0-embed-amd64.zip

# 下载安装pip

```
curl https://bootstrap.pypa.io/get-pip.py -o get-pip.py

python get-pip.py -i https://pypi.tuna.tsinghua.edu.cn/simple
```
[get-pip.py](:/92f34a44b26242029f31d9bbc9b03838)


# 安装其他Python包

```
pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple
cd Scripts
pip install -r requirements.txt
```

# 简化处理

直接安装所有依赖后zip打包，然后分发

#  ref
1. Anaconda 静默安装
https://docs.anaconda.com/anaconda/install/silent-mode/
2. Python 静默安装
https://docs.python.org/3/using/windows.html#installing-without-ui
