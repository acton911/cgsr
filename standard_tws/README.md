# 待解决的问题

- 集群控制和环境部署
- Case独立化，所有Case都可独立运行
- 不打包直接运行APP
- pylite无法调用第三方库，嵌入Pylite脚本直接运行相应Case

# 设计思路

分为4个状态：
部署 —— 拉取 —— 运行 —— 上报结果

## 部署

部署主要使用 [Ansible](https://github.com/ansible/ansible) 自动化运维工具控制每个节点环境的布置和新依赖的安装，避免手动配置环境不一致的状况。

- 环境部署
    - Ansible Server
    - Ansible Script
    - Ansible Client
        - Windows
        - Linux
        - Raspberry
- 环境检查

## 拉取

从Gitlab拉取脚本到本地运行

*安全性: 文件写入缓存，运行成功后删除*

## 运行

通过编写通用的APP后编译成Windows/Linux/Raspberry，后除TWS系统重大更新外，无需重新编译或者修改。

运行的流程：
环境检查（Ansible已自动部署） ->  Python运行Gitlab上拉取的脚本

## 结果上报

由通用的APP上报最终结果。
