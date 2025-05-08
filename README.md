
---

# 南阳理工学院 深澜校园网登录 Python 脚本

[![commit](https://img.shields.io/github/last-commit/updahn/nyist_network_online)](https://github.com/updahn/nyist_network_online/commits/master)

## 介绍

本 Python 脚本基于 [BIT-srun-login-script](https://github.com/coffeehat/BIT-srun-login-script)（北京理工大学深澜校园网登录 Python 脚本）。原项目包含基本的登录逻辑，本项目在此基础上加入了以下功能：

深澜校园网操作类，本软件包内容仅在 [NYIST](https://www.nyist.edu.cn/) 经过测试。


支持
- [X] Windows ，Linx ， Mac
- [X] 查询设备
- [X] 登出网络
- [X] 检查网络
- [x] 守卫网络
- [X] 远程操作设备

脚本的主要文件包括：

- **network.py**: 校园网类
- **check.py**: 检查类
- **email.py**: 邮箱类
- **logger.py**: 日志类
- **mac.py**: 网关类
<p>

- **server.py**: 完整代码。

## 使用示例

- **查询设备**:

    ```bash
    python3 /home/nyoj/workspace/nyist_network/server.py \
      --config_file=/home/nyoj/workspace/nyist_network/setting.ini \
      --option=list
    ```

- **登录网络**:

    ```bash
    python3 /home/nyoj/workspace/nyist_network/server.py \
      --config_file=/home/nyoj/workspace/nyist_network/setting.ini \
      --option=login
    ```

- **登出网络**:

    ```bash
    python3 /home/nyoj/workspace/nyist_network/server.py \
      --config_file=/home/nyoj/workspace/nyist_network/setting.ini \
      --option=logout
    ```

- **检查网络**:

    ```bash
    python3 /home/nyoj/workspace/nyist_network/server.py \
      --config_file=/home/nyoj/workspace/nyist_network/setting.ini \
      --option=check
    ```

- **守卫网络**:

    ```bash
    python3 /home/nyoj/workspace/nyist_network/server.py \
      --config_file=/home/nyoj/workspace/nyist_network/setting.ini \
      --option=guard
    ```

## 安装和挂载

### 推荐Linux部署

### 1. 安装 Python

首先，确保系统中安装了 Python 3 和对应的环境：

Linux 操作如下：

```bash
sudo apt-get update -y && sudo apt-get install -y python3 python3-pip
sudo pip3 install -r requirements.txt
```

### 2. 设置后台任务

使用 `nohup` 设置后台任务，并记录日志。

```bash
nohup python3 /home/nyoj/workspace/nyist_network/server.py \
  --config_file=/home/nyoj/workspace/nyist_network/setting.ini \
  --option=guard > /home/nyoj/workspace/nyist_network/network.log 2>&1 &
```

### 3. 常用命令

查询后台程序

```bash
ps -ef | grep server.py
```

关闭后台程序

```bash
kill XXXXX
```

## 更改账号信息

要修改登录账号信息，编辑 `setting.ini` 文件，更新默认的用户名和密码：

```ini
[ACCOUNT]
ip = ****                                         # 这一行可以不填入，内容为想控制的本机或者远程ip地址
username = ******                                 # 填入你的用户名
passwd = ******                                   # 填入你的密码

[IP]
ipv4 = ***
ipv6 = ***
is_online = 0
last_online_time = ***
```

## 更新邮箱配置

编辑 `setting.ini` 文件

```ini
[HOST]
email_send = false                                # 默认为false发送邮件提示
smtp_server = smtp.qq.com                         # 默认为qq邮箱发送
smtp_port = 465                                   # 默认qq邮箱发送邮件默认端口
email_account = ******                            # 发送邮件的邮箱
email_pass = ******                               # 发送邮件邮箱的stmp授权码
email_to = ******@example.com, ******@example.com # 发送到邮箱，邮箱之间用英文逗号隔开
```

## Tips
```
1. 如果登录提示 `E2620: You are already online.`，尝试退出其他账号后重试

```
---
