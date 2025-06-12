# --coding: utf-8 --
import re
import math
import hashlib
import hmac
import time
import urllib.request
import urllib.parse
import urllib.error
import http.cookiejar
import ddddocr
import ssl
import json
from bs4 import BeautifulSoup

from src.utils.logger import logger
from src.utils.check import checkvars, infomanage


class NetworkManager:

    def __init__(self, ip=None):
        # urls
        server_format = "https://auth.nyist.edu.cn"
        self.url_login_page = server_format + "/srun_portal_pc?ac_id=1&theme=pro"
        self.url_get_challenge_api = server_format + "/cgi-bin/get_challenge"
        self.url_login_api = server_format + "/cgi-bin/srun_portal"
        self.url_online_api = server_format + "/cgi-bin/rad_user_info"
        self.url_home_login_page = server_format + ":8800/login"
        self.url_home_page = server_format + ":8800/home"
        self.url_captcha_api = server_format + ":8800/site/captcha?refresh=1"
        self.base_url = server_format + ":8800"

        self.header = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/63.0.3239.26 Safari/537.36",
            "Accept": "application/json, text/javascript, */*; q=0.01",
        }

        # static parameters
        self.n = "200"
        self.vtype = "1"
        self.ac_id = "1"
        self.enc = "srun_bx1"
        self._PADCHAR = "="
        self._ALPHA = "LVoJPiCN2R8G90yg+hmFHuacZ1OWMnrsSTXkYpUq/3dlbfKwv6xztjI7DeBE45QA"

        # login ip
        self.ip = ip
        if not self.ip:
            self.get_ip()

        # login and ocr max attempts
        self.ocr_max_attempts = 5
        self.login_max_attempts = 5

        self.cookie_jar = http.cookiejar.CookieJar()

        # Create SSL context and add to handler
        self.ctx = ssl.create_default_context()
        self.ctx.check_hostname = False
        self.ctx.verify_mode = ssl.CERT_NONE
        https_handler = urllib.request.HTTPSHandler(context=self.ctx)

        # Create opener and add cookie handling
        self.opener = urllib.request.build_opener(
            urllib.request.HTTPCookieProcessor(self.cookie_jar), https_handler
        )
        self.opener.addheaders = [("User-Agent", "Mozilla/5.0")]

        self.csrf_token = None

        # User-related attributes
        self.username = None
        self.password = None

    def list(self, username, password):
        self.username = username
        self.password = password

        try:
            list_info = self._get_home_page_data()
            logger.info(f"{self.username}@{self.ip} [List Info]: {list_info}")
            return list_info
        except Exception as e:
            logger.error(f"{self.username}@{self.ip} [List failed]: {str(e)}")
            raise

    def login(self, username, password):
        self.username = username
        self.password = password

        try:
            if not self.get_check_response():
                self.get_token()
                self.get_login_response()
                result = self._login_response_text
                logger.info(f"{self.username}@{self.ip} [Login Info]: {result}")
                return result
            return "already_online"
        except Exception as e:
            logger.error(f"{self.username}@{self.ip} [Login failed]: {str(e)}")
            raise

    def logout(self, username):
        self.username = username

        try:
            if self.get_check_response():
                self.get_logout_response()
                result = self._logout_response_text
                logger.info(f"{self.username}@{self.ip} [Logout Info]: {result}")
                return result
            return "not_online"
        except Exception as e:
            logger.error(f"{self.username}@{self.ip} [Logout failed]: {str(e)}")
            raise

    def check(self, username):
        self.username = username

        try:
            check_info = self.get_check_response()
            if not check_info:
                check_info = "not_online"

            logger.info(f"{self.username}@{self.ip} [Check Info]: {check_info}")
            return check_info
        except Exception as e:
            logger.error(f"{self.username}@{self.ip} [Check failed]: {str(e)}")
            raise

    def get_ip(self):
        self._get_login_page()
        self._resolve_ip_from_login_page()

    def get_token(self):
        logger.info("Step 1: Getting login token")
        try:
            self._get_challenge()
            self._resolve_token_from_challenge_response()
            return self.token
        except Exception as e:
            raise

    def get_login_response(self):
        logger.info("Step 2: Login and parse response")
        try:
            self._generate_encrypted_login_info()
            self._send_login_info()
            self._resolve_login_response()
            logger.info(f"Login result: {self._login_response_text}")
            return self._login_response_text
        except Exception as e:
            raise

    def get_logout_response(self):
        try:
            self._send_logout_info()
            self._resolve_logout_response()
            return self._logout_response_text
        except Exception as e:
            raise

    def get_check_response(self):
        try:
            return self._send_check_info()
        except Exception as e:
            return None

    @infomanage(
        successinfo="Successfully get login page",
        errorinfo="Failed to get login page, maybe the login page url is not correct",
    )
    def _get_login_page(self):
        req = urllib.request.Request(self.url_login_page, headers=self.header)
        with urllib.request.urlopen(req) as resp:
            self._page_response_text = resp.read().decode("utf-8")

    @checkvars(
        varlist="_page_response_text",
        errorinfo="Lack of login page html. Need to run '_get_login_page' in advance to get it",
    )
    @infomanage(
        successinfo="Successfully resolve IP",
        errorinfo="Failed to resolve IP",
    )
    def _resolve_ip_from_login_page(self):
        self.ip = re.search(
            r'ip\s*:\s*["\'](.*?)["\']', self._page_response_text
        ).group(1)

    @checkvars(
        varlist="ip",
        errorinfo="Lack of local IP. Need to run '_resolve_ip_from_login_page' in advance to get it",
    )
    @infomanage(
        successinfo="Challenge response successfully received",
        errorinfo="Failed to get challenge response, maybe the url_get_challenge_api is not correct."
        "Else check params_get_challenge",
    )
    def _get_challenge(self):
        """
        The 'get_challenge' request aims to ask the server to generate a token
        """
        params_get_challenge = {
            "callback": self.generate_jsonp_string(),  # This value can be any string, but cannot be absent
            "username": self.username,
            "ip": self.ip,
        }
        query_string = urllib.parse.urlencode(params_get_challenge)
        url = f"{self.url_get_challenge_api}?{query_string}"

        req = urllib.request.Request(url, headers=self.header)
        with urllib.request.urlopen(req) as resp:
            self._challenge_response_text = resp.read().decode("utf-8")

    @checkvars(
        varlist="_challenge_response_text",
        errorinfo="Lack of challenge response. Need to run '_get_challenge' in advance",
    )
    @infomanage(
        successinfo="Successfully resolve token",
        errorinfo="Failed to resolve token",
    )
    def _resolve_token_from_challenge_response(self):
        self.token = re.search(
            '"challenge":"(.*?)"', self._challenge_response_text
        ).group(1)

    @checkvars(
        varlist="ip",
        errorinfo="Lack of local IP. Need to run '_resolve_ip_from_login_page' in advance to get it",
    )
    def _generate_info(self):
        info_params = {
            "username": self.username,
            "password": self.password,
            "ip": self.ip,
            "acid": self.ac_id,
            "enc_ver": self.enc,
        }
        info = re.sub("'", '"', str(info_params))
        self.info = re.sub(" ", "", info)

    @checkvars(
        varlist="info",
        errorinfo="Lack of info. Need to run '_generate_info' in advance",
    )
    @checkvars(
        varlist="token",
        errorinfo="Lack of token. Need to run '_resolve_token_from_challenge_response' in advance",
    )
    def _encrypt_info(self):
        self.encrypted_info = "{SRBX1}" + self.get_base64(
            self.get_xencode(self.info, self.token)
        )

    @checkvars(
        varlist="token",
        errorinfo="Lack of token. Need to run '_resolve_token_from_challenge_response' in advance",
    )
    def _generate_md5(self):
        self.md5 = self.get_md5("", self.token)

    @checkvars(
        varlist="md5", errorinfo="Lack of md5. Need to run '_generate_md5' in advance"
    )
    def _encrypt_md5(self):
        self.encrypted_md5 = "{MD5}" + self.md5

    @checkvars(
        varlist="token",
        errorinfo="Lack of token. Need to run '_resolve_token_from_challenge_response' in advance",
    )
    @checkvars(
        varlist="ip",
        errorinfo="Lack of local IP. Need to run '_resolve_ip_from_login_page' in advance to get it",
    )
    @checkvars(
        varlist="encrypted_info",
        errorinfo="Lack of encrypted_info. Need to run '_encrypt_info' in advance",
    )
    def _generate_chksum(self):
        self.chkstr = self.token + self.username
        self.chkstr += self.token + self.md5
        self.chkstr += self.token + self.ac_id
        self.chkstr += self.token + self.ip
        self.chkstr += self.token + self.n
        self.chkstr += self.token + self.vtype
        self.chkstr += self.token + self.encrypted_info

    @checkvars(
        varlist="chkstr",
        errorinfo="Lack of chkstr. Need to run '_generate_chksum' in advance",
    )
    def _encrypt_chksum(self):
        self.encrypted_chkstr = self.get_sha1(self.chkstr)

    def _generate_encrypted_login_info(self):
        self._generate_info()
        self._encrypt_info()
        self._generate_md5()
        self._encrypt_md5()

        self._generate_chksum()
        self._encrypt_chksum()

    @checkvars(
        varlist="ip",
        errorinfo="Lack of local IP. Need to run '_resolve_ip_from_login_page' in advance to get it",
    )
    @checkvars(
        varlist="encrypted_md5",
        errorinfo="Lack of encrypted_md5. Need to run '_encrypt_md5' in advance",
    )
    @checkvars(
        varlist="encrypted_info",
        errorinfo="Lack of encrypted_info. Need to run '_encrypt_info' in advance",
    )
    @checkvars(
        varlist="encrypted_chkstr",
        errorinfo="Lack of encrypted_chkstr. Need to run '_encrypt_chksum' in advance",
    )
    @infomanage(
        successinfo="Login info send successfully",
        errorinfo="Failed to send login info",
    )
    def _send_login_info(self):
        login_info_params = {
            "callback": self.generate_jsonp_string(),  # This value can be any string, but cannot be absent
            "action": "login",
            "username": self.username,
            "password": self.encrypted_md5,
            "ac_id": self.ac_id,
            "ip": self.ip,
            "info": self.encrypted_info,
            "chksum": self.encrypted_chkstr,
            "n": self.n,
            "type": self.vtype,
        }
        query_string = urllib.parse.urlencode(login_info_params)
        url = f"{self.url_login_api}?{query_string}"

        req = urllib.request.Request(url, headers=self.header)
        with urllib.request.urlopen(req) as resp:
            self._login_responce_text = resp.read().decode("utf-8")

    @infomanage(
        successinfo="Logout info send successfully",
        errorinfo="Failed to send logout info",
    )
    def _send_logout_info(self):
        payload = {
            "action": "logout",
            "ac_id": 1,
            "username": self.username,
            "type": 2,
            "ip": self.ip,
        }
        data = urllib.parse.urlencode(payload).encode("utf-8")
        req = urllib.request.Request(self.url_login_api, data=data, headers=self.header)
        with urllib.request.urlopen(req) as resp:
            self._logout_responce_text = resp.read().decode("utf-8")
            self._resolve_logout_response()

    @infomanage(
        successinfo="Check info send successfully",
        errorinfo="Failed to send check info",
    )
    def _send_check_info(self):
        try:
            payload = {
                "ip": self.ip,
                "ac_id": 1,
            }
            data = urllib.parse.urlencode(payload).encode("utf-8")

            req = urllib.request.Request(
                self.url_online_api, data=data, headers=self.header
            )
            with urllib.request.urlopen(req) as resp:
                resp_text = resp.read().decode("utf-8")

            if "not_online" in resp_text:
                return None

            # Parse JSON response
            data = json.loads(resp_text)

            # Confirm response success
            if data.get("error") != "ok":
                return None

            online_info = {
                "username": data.get("user_name"),
                "ipv4": data.get("online_ip"),
                "ipv6": data.get("online_ip6"),
                "login_time": self.time2date(data.get("add_time")),
                "now_time": self.time2date(data.get("keepalive_time")),
                "used_bytes": self.humanable_bytes(data.get("sum_bytes")),
                "used_second": self.humanable_seconds(data.get("sum_seconds")),
                "remain_bytes": (
                    -1
                    if data.get("remain_bytes") == 0
                    else self.humanable_bytes(data.get("remain_bytes"))
                ),
                "remain_second": (
                    -1
                    if data.get("remain_seconds") == 0
                    else self.humanable_seconds(data.get("remain_seconds"))
                ),
                "balance": data.get("user_balance"),
                "online_devices": data.get("online_device_total"),
                "products_name": data.get("products_name"),
            }

            return online_info
        except Exception as e:
            return None

    @checkvars(
        varlist="_login_responce_text",
        errorinfo="Need _login_responce_text. Run _send_login_info in advance",
    )
    @infomanage(
        successinfo="Login result successfully resolved",
        errorinfo="Cannot resolve login result. Maybe the srun response format is changed",
    )
    def _resolve_login_response(self):
        """Parse login response information"""
        logger.info("Login response: " + self._login_responce_text)
        match = re.search('"suc_msg":"(.*?)"', self._login_responce_text)

        if match:
            self._login_response_text = match.group(1)
        else:
            self._login_response_text = re.search(
                '"error_msg":"(.*?)"', self._login_responce_text
            ).group(1)

    @checkvars(
        varlist="_logout_responce_text",
        errorinfo="Need _logout_responce_text. Run _send_logout_info in advance",
    )
    @infomanage(
        successinfo="Logout result successfully resolved",
        errorinfo="Cannot resolve logout result. Maybe the srun response format is changed",
    )
    def _resolve_logout_response(self):
        """Parse logout response information"""
        logger.info("Logout response: " + self._logout_responce_text)
        match = re.search('"res":"(.*?)"', self._logout_responce_text)

        if match:
            if match.group(1) == "ok":
                self._logout_response_text = "logout_ok"
            else:
                self._logout_response_text = match.group(1)
        else:
            self._logout_response_text = re.search(
                '"error_msg":"(.*?)"', self._logout_responce_text
            ).group(1)

    @infomanage(
        successinfo="CSRF token obtained successfully",
        errorinfo="Failed to obtain CSRF token",
    )
    def get_csrf_token(self):
        # Directly use opener to open URL
        request = urllib.request.Request(self.url_home_login_page)

        try:
            response = self.opener.open(request)
            content = response.read()

            try:
                text = content.decode("utf-8")
            except UnicodeDecodeError:
                logger.warning(
                    f"Unable to decode response as UTF-8 from {self.url_home_login_page}"
                )
                raise Exception("Unable to decode login page content")

            csrf_match = re.search(
                r'<input type="hidden" name="_csrf-8800" value="([^"]+)"', text
            )
            if csrf_match:
                self.csrf_token = csrf_match.group(1)
            else:
                raise Exception("CSRF token not found")
        except Exception as e:
            raise

    @checkvars(
        varlist="csrf_token",
        errorinfo="Missing CSRF token, cannot get captcha",
    )
    @infomanage(
        successinfo="Captcha obtained successfully",
        errorinfo="Failed to obtain captcha",
    )
    def get_captcha(self):
        headers = {
            **self.header,
            "Referer": self.url_home_login_page,
            "X-Requested-With": "XMLHttpRequest",
            "X-CSRF-Token": self.csrf_token,
        }

        for _ in range(self.ocr_max_attempts):
            try:
                timestamp = int(time.time() * 1000)
                captcha_url = "{}_{:d}".format(self.url_captcha_api + "&", timestamp)

                # Get captcha JSON data
                request = urllib.request.Request(captcha_url)
                for key, value in headers.items():
                    request.add_header(key, value)

                captcha_response = self.opener.open(request)
                captcha_content = captcha_response.read()

                try:
                    captcha_data = json.loads(captcha_content.decode("utf-8"))
                except (UnicodeDecodeError, json.JSONDecodeError) as e:
                    logger.warning(f"Failed to decode captcha response: {str(e)}")
                    continue

                if "url" not in captcha_data:
                    logger.warning("Unable to get captcha URL")
                    continue

                captcha_img_url = "{}{url}".format(self.base_url, **captcha_data)
                logger.info(f"Captcha image URL: {captcha_img_url}")

                # Download captcha image
                img_request = urllib.request.Request(captcha_img_url)
                img_request.add_header("Referer", self.url_home_login_page)

                img_response = self.opener.open(img_request)
                img_data = img_response.read()

                # Use ddddocr to recognize captcha
                self.ocr = ddddocr.DdddOcr()
                verify_code = self.ocr.classification(img_data)
                logger.info(f"Captcha recognized: {verify_code}")

                if len(verify_code) == 4:
                    return verify_code
            except Exception as e:
                continue

        return None

    @checkvars(
        varlist="csrf_token",
        errorinfo="Missing CSRF token, cannot login to home page",
    )
    @infomanage(
        successinfo="Login Home page successful",
        errorinfo="Login Home page failed",
    )
    def _get_home_page(self):
        self.get_csrf_token()
        verify_code = self.get_captcha()
        if not verify_code:
            raise Exception("Failed to get captcha")

        data = {
            "_csrf-8800": self.csrf_token,
            "LoginForm[username]": self.username,
            "LoginForm[password]": self.password,
            "LoginForm[verifyCode]": verify_code,
            "login-button": "",
        }

        headers = {"Content-Type": "application/x-www-form-urlencoded"}

        # 将数据编码
        encoded_data = urllib.parse.urlencode(data).encode("utf-8")

        # 创建POST请求
        request = urllib.request.Request(
            self.url_home_login_page, data=encoded_data, method="POST"
        )
        for key, value in headers.items():
            request.add_header(key, value)

        try:
            response = self.opener.open(request)
            response_url = response.geturl()

            # 检查是否有重定向（登录成功的标志）
            if response_url != self.url_home_login_page:
                logger.info("Login Home page successful")

                # 获取home页面内容
                home_request = urllib.request.Request(self.url_home_page)
                home_response = self.opener.open(home_request)
                home_content = home_response.read()

                try:
                    self._page_response_text = home_content.decode("utf-8")
                except UnicodeDecodeError:
                    raise Exception("Unable to decode home page content")
            else:
                raise Exception("Login failed - no redirect to home page")
        except Exception as e:
            raise

    @infomanage(
        successinfo="Home page data retrieved successfully",
        errorinfo="Failed to retrieve home page data",
    )
    def _get_home_page_data(self):
        for _ in range(self.login_max_attempts):
            try:
                self._get_home_page()
                table_data = self._extract_tbody_text()
                if table_data:
                    return table_data
            except Exception as e:
                continue

        raise Exception("Failed to get home page data after multiple attempts")

    @infomanage(
        successinfo="Table data extraction successful",
        errorinfo="Table data extraction failed",
    )
    @checkvars(
        varlist="_page_response_text",
        errorinfo="Missing _page_response_text, cannot extract table data",
    )
    def _extract_tbody_text(self):
        soup = BeautifulSoup(self._page_response_text, "html.parser")

        user_info = {}
        list_items = soup.find_all("li", class_="list-group-item")

        for item in list_items:
            label = item.find("label", class_="list-group-label")
            if not label:
                continue

            label_text = label.text.strip()
            value = item.text.replace(label.text, "").strip()

            if "Name" in label_text or "姓名" in label_text:
                user_info["name"] = value
            elif "E-Wallet" in label_text or "电子钱包" in label_text:
                user_info["balance"] = value
            elif "Status" in label_text or "状态" in label_text:
                user_info["status"] = value
            elif "Username" in label_text or "用户名" in label_text:
                user_info["user_id"] = value

        tbody = soup.find("tbody")
        online_devices = []

        if tbody:
            for row in tbody.find_all("tr"):
                cells = [
                    cell.get_text(strip=True) for cell in row.find_all(["td", "th"])
                ]
                if cells and len(cells) >= 6:
                    device = {
                        "ipv4": cells[0],
                        "login_time": cells[1],
                        "used_bytes": cells[2],
                        "used_second": cells[3],
                        "device": cells[4],
                        "system": cells[5],
                    }
                    online_devices.append(device)

        return {
            "username": self.username,
            "realname": user_info.get("name", ""),
            "purse": user_info.get("purse", ""),
            "status": user_info.get("status", ""),
            "online_info": online_devices,
            "online_devices": len(online_devices),
        }

    def _getbyte(self, s, i):
        x = ord(s[i])
        if x > 255:
            raise ValueError("INVALID_CHARACTER_ERR: DOM Exception 5")
        return x

    def get_base64(self, s):
        if not s:
            return ""

        i = 0
        b10 = 0
        x = []
        imax = len(s) - len(s) % 3

        while i < imax:
            b10 = (
                (self._getbyte(s, i) << 16)
                | (self._getbyte(s, i + 1) << 8)
                | self._getbyte(s, i + 2)
            )
            x.append(self._ALPHA[(b10 >> 18) & 63])
            x.append(self._ALPHA[(b10 >> 12) & 63])
            x.append(self._ALPHA[(b10 >> 6) & 63])
            x.append(self._ALPHA[b10 & 63])
            i += 3

        if len(s) - imax == 1:
            b10 = self._getbyte(s, i) << 16
            x.append(self._ALPHA[(b10 >> 18) & 63])
            x.append(self._ALPHA[(b10 >> 12) & 63])
            x.append(self._PADCHAR)
            x.append(self._PADCHAR)
        elif len(s) - imax == 2:
            b10 = (self._getbyte(s, i) << 16) | (self._getbyte(s, i + 1) << 8)
            x.append(self._ALPHA[(b10 >> 18) & 63])
            x.append(self._ALPHA[(b10 >> 12) & 63])
            x.append(self._ALPHA[(b10 >> 6) & 63])
            x.append(self._PADCHAR)

        return "".join(x)

    def get_md5(self, password, token):
        return hmac.new(token.encode(), password.encode(), hashlib.md5).hexdigest()

    def get_sha1(self, value):
        return hashlib.sha1(value.encode()).hexdigest()

    def force(self, msg):
        return bytes(ord(w) for w in msg)

    def ordat(self, msg, idx):
        return ord(msg[idx]) if idx < len(msg) else 0

    def sencode(self, msg, key):
        l = len(msg)
        pwd = []
        for i in range(0, l, 4):
            pwd.append(
                self.ordat(msg, i)
                | (self.ordat(msg, i + 1) << 8)
                | (self.ordat(msg, i + 2) << 16)
                | (self.ordat(msg, i + 3) << 24)
            )
        if key:
            pwd.append(l)
        return pwd

    def lencode(self, msg, key):
        l = len(msg)
        ll = (l - 1) << 2
        if key:
            m = msg[l - 1]
            if m < ll - 3 or m > ll:
                raise ValueError("Invalid length in lencode")
            ll = m
        result = []
        for i in range(l):
            result.append(
                chr(msg[i] & 0xFF)
                + chr((msg[i] >> 8) & 0xFF)
                + chr((msg[i] >> 16) & 0xFF)
                + chr((msg[i] >> 24) & 0xFF)
            )
        return "".join(result)[:ll] if key else "".join(result)

    def get_xencode(self, msg, key):
        if not msg:
            return ""

        pwd = self.sencode(msg, True)
        pwdk = self.sencode(key, False)
        if len(pwdk) < 4:
            pwdk += [0] * (4 - len(pwdk))

        n = len(pwd) - 1
        z = pwd[n]
        y = pwd[0]
        c = 0x86014019 | 0x183639A0
        q = math.floor(6 + 52 / (n + 1))
        d = 0

        while q > 0:
            q -= 1
            d = (d + c) & (0x8CE0D9BF | 0x731F2640)
            e = (d >> 2) & 3
            for p in range(n):
                y = pwd[p + 1]
                m = ((z >> 5) ^ (y << 2)) + (((y >> 3) ^ (z << 4)) ^ (d ^ y))
                m += pwdk[(p & 3) ^ e] ^ z
                pwd[p] = (pwd[p] + m) & (0xEFB8D130 | 0x10472ECF)
                z = pwd[p]
            y = pwd[0]
            m = ((z >> 5) ^ (y << 2)) + (((y >> 3) ^ (z << 4)) ^ (d ^ y))
            m += pwdk[(n & 3) ^ e] ^ z
            pwd[n] = (pwd[n] + m) & (0xBB390742 | 0x44C6F8BD)
            z = pwd[n]

        return self.lencode(pwd, False)

    def generate_jsonp_string(self):
        return f"nyist{str(int(time.time() * 1000))}"

    def time2date(self, timestamp):
        """
        将时间戳转换为标准日期格式：YYYY-MM-DD HH:MM:SS
        """
        if not timestamp:
            return None

        # 处理整数或浮点数时间戳
        if isinstance(timestamp, (int, float)) or (
            isinstance(timestamp, str) and timestamp.isdigit()
        ):
            timestamp = int(float(timestamp))
            time_arry = time.localtime(timestamp)
            return time.strftime("%Y-%m-%d %H:%M:%S", time_arry)

        # 如果已经是字符串日期格式，尝试解析并重新格式化
        if isinstance(timestamp, str):
            try:
                # 尝试解析各种可能的日期格式
                for fmt in [
                    "%Y-%m-%d %H:%M:%S",
                    "%Y/%m/%d %H:%M:%S",
                    "%Y年%m月%d日 %H:%M:%S",
                ]:
                    try:
                        dt = time.strptime(timestamp, fmt)
                        return time.strftime("%Y-%m-%d %H:%M:%S", dt)
                    except ValueError:
                        continue
            except Exception:
                pass

            # 如果无法解析，返回原始字符串
            return timestamp

        # 处理其他情况，比如datetime对象
        try:
            return timestamp.strftime("%Y-%m-%d %H:%M:%S")
        except Exception:
            return str(timestamp)

    def humanable_bytes(self, num_byte):
        num_byte = float(num_byte)
        if num_byte >= 1024**3:
            return "{:.3f}G".format(num_byte / (1024**3))
        elif num_byte >= 1024**2:
            return "{:.3f}M".format(num_byte / (1024**2))
        elif num_byte >= 1024:
            return "{:.3f}K".format(num_byte / 1024)
        else:
            return "{:.3f}B".format(num_byte)

    def humanable_seconds(self, seconds):
        seconds = int(seconds)
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        secs = seconds % 60
        return f"{hours}时{minutes}分{secs}秒"

    def _is_defined(self, varname):
        """
        Check whether variable is defined in the object
        """
        allvars = vars(self)
        return varname in allvars
