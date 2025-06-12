---

# 南阳理工学院 深澜校园网登录 Web 管理版本

[![commit](https://img.shields.io/github/last-commit/updahn/nyist_network_online)](https://github.com/updahn/nyist_network_online/commits/master)

## 介绍

本 Python 脚本基于 [BIT-srun-login-script](https://github.com/coffeehat/BIT-srun-login-script)（北京理工大学深澜校园网登录 Python 脚本）。原项目包含基本的登录逻辑，本项目在此基础上加入了以下功能：

深澜校园网操作类，本软件包内容仅在 [NYIST](https://www.nyist.edu.cn/) 经过测试。

支持

- [x] Web 管理界面
- [x] Windows ，Linx ， Mac
- [x] 查询设备
- [x] 登出网络
- [x] 检查网络
- [x] 守卫网络
- [x] 远程操作设备


## 使用示例

- **查询设备**:

  ```bash
  python3 /home/nyoj/workspace/nyist_network/main.py \
    --config_file=/home/nyoj/workspace/nyist_network/setting.ini \
    --option=list
  ```

- **登录网络**:

  ```bash
  python3 /home/nyoj/workspace/nyist_network/main.py \
    --config_file=/home/nyoj/workspace/nyist_network/setting.ini \
    --option=login
  ```

- **登出网络**:

  ```bash
  python3 /home/nyoj/workspace/nyist_network/main.py \
    --config_file=/home/nyoj/workspace/nyist_network/setting.ini \
    --option=logout
  ```

- **检查网络**:

  ```bash
  python3 /home/nyoj/workspace/nyist_network/main.py \
    --config_file=/home/nyoj/workspace/nyist_network/setting.ini \
    --option=check
  ```

- **守卫网络**:

  ```bash
  python3 /home/nyoj/workspace/nyist_network/main.py \
    --config_file=/home/nyoj/workspace/nyist_network/setting.ini \
    --option=guard
  ```

## 安装和挂载

# 1. 创建镜像

```bash
docker build -t hoj-network .
```

# 2. 启动镜像

```bash
docker compose up -d hoj-network
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
[EMAIL]
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
2. 邮件提醒已删除，有需要自加
```

## 目录结构

```txt
src/
├── static/
│ ├── css/ # CSS 样式文件
│ ├── js/ # JavaScript 文件
│ ├── html/ # HTML 模板文件
│ └── img/ # 图片资源
│
├── routes/ # 路由文件
├── utils/ # 工具函数
│ └── network_utils.py # 网络相关工具函数
└── manager/ # 管理器类
```

