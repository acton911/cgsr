# -*- encoding=utf-8 -*-

# 必备的一些依赖项
import configparser  # noqa
import getpass  # noqa
import os  # noqa
import subprocess  # noqa
import multiprocessing  # noqa
import sys  # noqa
import tarfile  # noqa
import time  # noqa
from tempfile import TemporaryDirectory  # noqa
import gitlab  # noqa
from urllib.request import urlopen

# 备用的依赖项
import re  # noqa
import shutil  # noqa
import pickle  # noqa
import json  # noqa

# 拉取远程的脚本文件并调用
print("[execute app] pull")
r = urlopen('http://autonr.quectel.com/file/execute_app_operation.py')
print(f"[execute app] r.status: {r.status}\n[execute app] r.reason: {r.reason}")
exec(r.read().decode('utf-8'), globals())  # noqa
