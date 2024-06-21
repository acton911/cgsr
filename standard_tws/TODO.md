# 创建temp并运行脚本

- [x] 创建tempfile目录
    - ref: https://docs.python.org/zh-cn/3/library/tempfile.html?highlight=tempfile#tempfile.TemporaryDirectory

- [x] 通过git(pip install gitlab)拉取脚本
    - 使用token拉取

- [x] 在TEMP目录中放入python脚本，运行后删除


# Ansible环境统一部署
ref:
- https://github.com/ansible/ansible
- https://github.com/ansible/ansible-examples

- [x] Windows Python 部署脚本

- [x] Linux Python 部署脚本

- [x] Windows 其他依赖部署

- [x] Linux 其他依赖部署

- [x] 搭建常用应用内网服务器(HTTP)

# 通用APP制作

- [x] 创建Windows/Linux/Raspberry的通用APP
    - 集成TWS参数获取部分
    - 集成TWS Case状态上传
    - 脚本指的是单个或者多个功能项

# 优化
- [x] 优化异常等级
- [ ] 优化log文件
- [x] 版本包下载慢
- [ ] APP运行前检查
    - 通过某种检查列表？
- [ ] 测试结果优化
    - 存档mysql，redis
	- Speedtest类的数据记录
	- 错误尊崇原则：快速失败（有异常，立刻上报）
- [ ] 覆盖率
	- Mock
    - Pytest
    - CI
- [ ] 目标检测有效性（低优先级）
