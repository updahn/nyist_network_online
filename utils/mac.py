import time
import sys
import re
import psutil
import socket
import subprocess


from utils.logger import logger


class Mac:
    def __init__(self):
        # 获取系统类型
        self.system = sys.platform

    def get_network_interfaces(self):
        """
        获取本机所有物理网卡名称。
        Returns:
            list: 网卡名称列表
        """

        interfaces = []

        if self.system.startswith("win"):
            result = subprocess.run(
                "ipconfig", shell=True, capture_output=True, text=True
            )
            matches = re.findall(r"adapter (.+):", result.stdout)
            interfaces = [match.strip() for match in matches]
        elif self.system.startswith("linux"):
            result = subprocess.run(
                "ls /sys/class/net", shell=True, capture_output=True, text=True
            )
            interfaces = result.stdout.strip().split("\n")
        elif self.system == "darwin":  # macOS
            result = subprocess.run(
                "networksetup -listallhardwareports",
                shell=True,
                capture_output=True,
                text=True,
            )
            matches = re.findall(r"Device: (.+)", result.stdout)
            interfaces = matches
        else:
            logger.warning(f"Unsupported platform: {self.system}")
            return
        return interfaces

    def is_interface_reachable(self, target_ip="auth.nyist.edu.cn", source_ip=None):
        """
        检查是否可以 ping 通目标 IP 地址。
        Args:
            ip (str): 要 ping 的 IP
        Returns:
            bool: True 表示可达，False 表示不可达
        """

        cmd = ["ping", target_ip]
        if self.system.startswith("win"):
            cmd += ["-n", "3", "-w", "1000"]  # 次数，超时（毫秒）
        else:
            cmd += ["-c", "3", "-W", "2"]  # 次数，超时（秒）
            if source_ip:
                cmd += ["-I", source_ip]

        return (
            subprocess.run(
                cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
            ).returncode
            == 0
        )

    def get_valid_interfaces(self):
        """
        获取所有可用网卡（具有 IPv4 地址）并能 ping 通 `auth.nyist.edu.cn` 的网卡接口和 IP 地址。
        使用 psutil 跨平台获取网卡信息。
        返回格式: [(interface, ipv4, ipv6), ...]
        """
        valid = []
        interfaces = psutil.net_if_addrs()
        for interface, addrs in interfaces.items():
            ipv4 = ipv6 = None

            for addr in addrs:
                if addr.family == socket.AF_INET:
                    ipv4 = addr.address
                elif addr.family == socket.AF_INET6:
                    ipv6 = addr.address.split("%")[0]  # 去掉作用域标识

            if ipv4 and self.is_interface_reachable(source_ip=ipv4):
                valid.append((interface, ipv4, ipv6))

        return valid

    def restart_network_interfaces(self):
        """
        重启所有物理网卡
        """
        logger.info("Restarting Network Interfaces...")

        try:
            self.interface_list = self.get_network_interfaces()
            if self.system.startswith("win"):
                for iface in self.interface_list:
                    subprocess.run(
                        [
                            "netsh",
                            "interface",
                            "set",
                            "interface",
                            iface,
                            "admin=disable",
                        ],
                        check=False,
                    )
                    subprocess.run(
                        [
                            "netsh",
                            "interface",
                            "set",
                            "interface",
                            iface,
                            "admin=enable",
                        ],
                        check=False,
                    )
            elif self.system.startswith("linux"):
                subprocess.run(["systemctl", "restart", "NetworkManager"], check=False)
                for iface in self.interface_list:
                    subprocess.run(
                        ["ip", "link", "set", "dev", iface, "down"], check=False
                    )
                    subprocess.run(
                        ["ip", "link", "set", "dev", iface, "up"], check=False
                    )
            elif self.system == "darwin":
                for iface in self.interface_list:
                    subprocess.run(["ifconfig", iface, "down"], check=False)
                    subprocess.run(["ifconfig", iface, "up"], check=False)

            else:
                logger.warning(f"Unsupported platform: {self.system}")
                return

            logger.info("Network interfaces restarted successfully.")
            time.sleep(15)  # Allow network to stabilize

        except Exception as e:
            return
