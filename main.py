# --coding: utf-8 --
import configparser
import argparse
import sys
import time

from manager.network import NetworkManager
from utils.email import Email
from utils.mac import Mac
from utils.logger import logger


class HeartBeat:

    def __init__(self, config_file="setting.ini"):
        # 获取系统类型
        self.system = sys.platform
        # 配置文件路径
        self.config_file = config_file
        # 初始化
        self._init()

    def load_config(self, config_file):
        config = configparser.ConfigParser()
        config.read(config_file)

        # 确保所有必需的节存在
        default_config = {
            "ACCOUNT": {
                "username": "***",
                "passwd": "***",
                "ip": None,
            },
            "IP": {
                "ipv4": "***",
                "ipv6": "***",
                "last_online_time": "***",
                "is_online": "0",
            },
            "EMAIL": {
                "email_send": "false",
                "smtp_server": "smtp.qq.com",
                "smtp_port": "465",
                "email_account": "***",
                "email_pass": "***",
                "email_to": "***",
            },
        }

        # 检查并创建缺失的节和键
        modified = False
        for section, keys in default_config.items():
            if section not in config:
                config.add_section(section)
                modified = True

            for key, value in keys.items():
                if section in config and key not in config[section]:
                    config[section][key] = str(value) if value is not None else ""
                    modified = True

        # 如果配置文件被修改，保存更新
        if modified:
            with open(config_file, "w") as f:
                config.write(f)

        sections = set(config.sections())
        return {section: dict(config.items(section)) for section in sections}

    def update_config(self, section, key, value):
        config = configparser.ConfigParser()
        config.read(self.config_file)
        if section not in config:
            config.add_section(section)
        config[section][key] = value
        with open(self.config_file, "w") as f:
            config.write(f)

    def _init(self):
        self.config = self.load_config(self.config_file)

        # 账号配置
        account_config = self.config["ACCOUNT"]
        self.ip = account_config.get("ip", None)  # 登录ip
        self.username = account_config["username"]  # 登录用户名
        self.password = account_config["passwd"]  # 登录密码

        # 邮箱配置
        self.email_config = self.config["EMAIL"]

        # IP 配置
        self.ip_config = self.config["IP"]

        # 确保IP配置中有is_online字段
        if "is_online" not in self.ip_config:
            self.update_config("IP", "is_online", "0")
            self.ip_config["is_online"] = "0"

        self.mac = Mac()
        self.email = Email()

        # 校园网登录实例
        self.network_manager = NetworkManager(ip=self.ip)
        self.ip = self.network_manager.ip

    def try_list(self):
        return self.network_manager.list(self.username, self.password)

    def try_login(self):
        return self.network_manager.login(self.username, self.password)

    def try_logout(self):
        return self.network_manager.logout(self.username)

    def try_check(self):
        return self.network_manager.check(self.username)

    def try_guard(self):
        while True:
            # 刷新配置
            self._init()
            self.is_online = self.ip_config.get("is_online", "0")

            # 检查网络连接状态
            online_status = self.network_manager.check(self.username)

            if online_status == "not_online":
                # 可选：重启网卡
                # self.mac.restart_network_interfaces()

                # 尝试重新登录
                self.try_login()

                # 更新状态为离线
                self.update_config("IP", "is_online", "0")
                continue

            # --- 处理在线状态 ---
            # 获取当前IP地址
            current_ipv4 = online_status.get("ipv4", "")
            current_ipv6 = online_status.get("ipv6", "")
            if current_ipv6 == "::":
                current_ipv6 = None

            # 检查IP地址是否变更并更新
            ip_changed = False
            if current_ipv4 and self.ip_config.get("ipv4", "") != current_ipv4:
                self.update_config("IP", "ipv4", current_ipv4)
                ip_changed = True

            if current_ipv6 and self.ip_config.get("ipv6", "") != current_ipv6:
                self.update_config("IP", "ipv6", current_ipv6)
                ip_changed = True

            # 如果IP变更，发送通知
            if ip_changed:
                self.email.send_email(
                    f"📡 服务器 IP地址变更",
                    f"新 IP 信息如下：\n{current_ipv4}\n{current_ipv6}",
                    self.email_config,
                )

            # 如果之前是离线状态，处理恢复上线
            if self.is_online == "0":
                last_online_time = self.ip_config.get("last_online_time", "")
                offline_duration_str = "无"
                minutes_offline = 0

                try:
                    # 转换时间并计算时长
                    offline_seconds = time.time() - time.mktime(
                        time.strptime(last_online_time, "%Y-%m-%d %H:%M:%S")
                    )

                    # 计算小时、分钟、秒
                    hours, remainder = divmod(offline_seconds, 3600)
                    minutes, seconds = divmod(remainder, 60)

                    minutes_offline = int(minutes)
                    offline_duration_str = (
                        f"{int(hours)}小时{int(minutes)}分钟{int(seconds)}秒"
                    )

                except Exception as e:
                    self.update_config("IP", "last_online_time", "")
                    logger.error(f"计算离线时长出错: {e}")

                # 仅当离线超过1分钟时发送通知
                if minutes_offline > 1:
                    self.email.send_email(
                        "✅ 服务器恢复上线",
                        f"""服务器上次在线时间：{last_online_time}
                        断网时长：{offline_duration_str}
                        网络连接已恢复，现在的IP地址信息如下：
                        {self.ip_config.get('ipv4', '')}
                        {self.ip_config.get('ipv6', '')}""",
                        self.email_config,
                    )
                    logger.info(
                        f"Last Online Time：{last_online_time}，Offline Duration：{offline_duration_str}"
                    )

            # 更新状态为在线
            self.update_config("IP", "is_online", "1")
            # 更新上次在线时间
            self.update_config(
                "IP", "last_online_time", time.strftime("%Y-%m-%d %H:%M:%S")
            )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="NYIST ONLINE TOOL",
        epilog="Example: python server.py --option list --config_file setting.ini",
    )
    parser.add_argument(
        "--config_file",
        type=str,
        default="setting.ini",
        help="Path to the configuration file. Default is 'setting.ini'.",
    )
    parser.add_argument(
        "--option",
        type=str,
        choices=["list", "guard", "login", "logout", "check"],
        default="list",
        help=(
            "Operation to perform: Default is 'list'"
            "'list' to list online info."
            "'login' to log in, "
            "'logout' to log out, "
            "'check' to verify online status, "
            "'guard' to guard online, "
        ),
    )

    args = parser.parse_args()

    heartbeat = HeartBeat(config_file=args.config_file)

    operations = {
        "list": lambda: print(
            f"{heartbeat.username}@{heartbeat.ip} [List_Info]: {heartbeat.try_list()}"
        ),
        "login": lambda: print(
            f"{heartbeat.username}@{heartbeat.ip} [Login_Info]: {heartbeat.try_login()}"
        ),
        "logout": lambda: print(
            f"{heartbeat.username}@{heartbeat.ip} [Logout_Info]: {heartbeat.try_logout()}"
        ),
        "check": lambda: print(
            f"{heartbeat.username}@{heartbeat.ip} [Check_Info]: {heartbeat.try_check()}"
        ),
        "guard": lambda: heartbeat.try_guard(),
    }

    operations[args.option]()
