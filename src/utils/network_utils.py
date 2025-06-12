from flask import jsonify
from flask_login import current_user
from datetime import datetime
import time
import traceback

from src.manager.network import NetworkManager
from src.models.models import db
from src.models import Account, Device


def check_permission(obj, error_message="没有权限"):
    """检查当前用户是否有权限操作对象。

    验证用户对指定对象的操作权限，管理员拥有所有权限，
    普通用户只能操作自己的对象。

    Args:
        obj: 需要检查权限的对象，必须有user_id属性
        error_message: 权限不足时的错误消息

    Returns:
        bool: 有权限返回True，否则返回False
    """
    result = False

    try:
        # 管理员有所有权限
        if current_user.is_admin:
            result = True
        else:
            # 非管理员只能操作自己的对象
            result = obj.user_id == current_user.id
    except Exception as e:
        traceback.print_exc()
        result = False

    finally:
        return result


def get_permission_error():
    """返回权限错误的标准响应。

    创建并返回统一格式的权限错误JSON响应。

    Returns:
        Response: JSON格式的权限错误响应
        格式：{"success": False, "message": "没有操作权限"}
    """
    result = None

    try:
        result = jsonify({"success": False, "message": "没有操作权限"})
    except Exception as e:
        traceback.print_exc()
        result = jsonify({"success": False, "message": str(e)})

    finally:
        return result


def update_device_status(device, check_result):
    """根据检查结果更新设备状态。

    更新设备的在线状态、使用信息以及关联账号的信息。

    Args:
        device: 需要更新状态的设备对象
        check_result: 设备检查结果

    Returns:
        bool: 设备在线返回True，否则返回False
    """
    is_online = False

    try:
        is_online = check_result and check_result != "not_online"

        if is_online:
            # 设备在线，更新信息
            device.is_online = True
            device.username = check_result.get("username", device.username)
            device.ipv6 = check_result.get("ipv6", device.ipv6)
            device.used_bytes = check_result.get("used_bytes", device.used_bytes)
            device.used_second = check_result.get("used_second", device.used_second)
            device.last_online_time = datetime.now()

            # 更新账号信息
            if device.username:
                account = Account.query.filter_by(username=device.username).first()
                if account:
                    account.last_check_at = datetime.now()
                    account.online_devices_count = check_result.get(
                        "online_devices", account.online_devices_count
                    )
        else:
            # 设备离线
            device.is_online = False
            device.username = None

        db.session.commit()
    except Exception as e:
        db.session.rollback()
        traceback.print_exc()

    finally:
        return is_online


def get_account_for_device(device, find_default=True):
    """获取设备使用的校园网账号。

    查找设备关联的账号，如果没有则根据配置寻找默认账号。

    Args:
        device: 需要获取账号的设备对象
        find_default: 是否在没有关联账号时寻找默认账号

    Returns:
        tuple: (账号对象, 用户名, 密码)
    """
    result = (None, None, None)

    try:
        account = None
        username = None
        password = None

        # 查找设备已关联的账号
        if device.username:
            username = device.username
            account = Account.query.filter_by(username=username).first()
            if account:
                password = account.password

        # 如果没有找到账号且需要寻找默认账号
        if not username and find_default:
            default_account = Account.query.filter_by(
                user_id=device.user_id, is_default=True
            ).first()
            if default_account:
                username = default_account.username
                password = default_account.password
                device.username = username
                account = default_account
                db.session.commit()

        result = (account, username, password)
    except Exception as e:
        db.session.rollback()
        traceback.print_exc()

    finally:
        return result


def get_reload_accounts(accounts):
    """更新多个校园网账号的在线设备信息。

    获取并更新每个账号的在线设备数量和最后检查时间。

    Args:
        accounts: 需要更新信息的账号对象列表

    Returns:
        list: 更新后的账号对象列表
    """
    result = accounts

    try:
        for account in accounts:
            try:
                username = account.username
                password = account.password

                device_infos = handle_device_list(username, password)

                # 更新结果统计
                online_devices_count = device_infos.get("online_devices", 0)

                # 更新账号信息
                if online_devices_count > 0:
                    account.online_devices_count = online_devices_count
                    account.last_check_at = datetime.now()
                    db.session.commit()
            except Exception as e:
                db.session.rollback()
                traceback.print_exc()
    except Exception as e:
        traceback.print_exc()

    finally:
        return result


def handle_device_list(username, password):
    """获取校园网账号的在线设备列表。

    通过网络管理器获取账号的在线设备信息，并更新数据库中的设备记录。

    Args:
        username: 校园网账号用户名
        password: 校园网账号密码

    Returns:
        dict: 包含在线设备信息的字典
        格式：{"online_devices": 数量, "online_info": [设备列表]}
    """
    result = {"online_devices": 0, "online_info": []}

    try:
        network_manager = NetworkManager()
        result = network_manager.list(username, password)

        # 处理在线设备信息
        for device_info in result.get("online_info", []):
            ipv4 = device_info.get("ipv4", "")
            if not ipv4:
                continue

            # 检查设备是否已存在
            existing_device = Device.query.filter_by(
                ipv4=ipv4, user_id=current_user.id
            ).first()

            if existing_device:
                # 更新现有设备信息
                existing_device.used_bytes = device_info.get("used_bytes", "")
                existing_device.used_second = device_info.get("used_second", "")
                existing_device.last_online_time = datetime.now()
                existing_device.is_online = True
                existing_device.username = device_info.get("username", username)
            else:
                # 创建新设备
                new_device = Device(
                    name=device_info.get("device", "自动发现的设备"),
                    ipv4=ipv4,
                    used_bytes=device_info.get("used_bytes", ""),
                    used_second=device_info.get("used_second", ""),
                    last_online_time=datetime.now(),
                    is_online=True,
                    user_id=current_user.id,
                    username=device_info.get("username", username),
                )
                db.session.add(new_device)

        db.session.commit()
    except Exception as e:
        db.session.rollback()
        traceback.print_exc()

    finally:
        return result


def handle_device_check(device):
    """检查设备状态并更新数据库。

    通过网络管理器检查设备的在线状态，并更新设备信息。

    Args:
        device: 需要检查状态的设备对象

    Returns:
        tuple: (成功标志, 消息)
        格式：(True/False, "online"/"offline"/错误信息)
    """
    result = (False, "检查设备状态失败")

    try:
        network_manager = NetworkManager(ip=device.ipv4)
        check_result = network_manager.check(device.username)

        is_online = update_device_status(device, check_result)
        result = (is_online, check_result)
    except Exception as e:
        traceback.print_exc()
        result = (False, str(e))

    finally:
        return result


def handle_device_login(device, username=None, password=None):
    """处理设备登录校园网。

    通过网络管理器执行设备登录操作，并更新设备状态。

    Args:
        device: 需要登录的设备对象
        username: 可选，登录用的用户名
        password: 可选，登录用的密码

    Returns:
        tuple: (成功标志, 消息)
        格式：(True/False, "login_ok"/错误信息)
    """
    result = (False, "登录失败")

    try:
        # 获取登录凭据
        if not username or not password:
            account, username, password = get_account_for_device(device)
        else:
            account = Account.query.filter_by(username=username).first()

        # 验证账号信息
        if not username or not password:
            result = (False, "没有可用账号")
        else:
            # 执行登录
            network_manager = NetworkManager(ip=device.ipv4)
            login_result = network_manager.login(username, password)

            result = (True if login_result == "login_ok" else False, login_result)

            # 登录后检查状态
            time.sleep(0.5)
            handle_device_check(device)
    except Exception as e:
        traceback.print_exc()
        result = (False, str(e))

    finally:
        return result


def handle_device_logout(device):
    """处理设备登出校园网。

    通过网络管理器执行设备登出操作，并更新设备状态。

    Args:
        device: 需要登出的设备对象

    Returns:
        tuple: (成功标志, 消息)
        格式：(True/False, "logout_ok"/错误信息)
    """
    result = (False, "登出失败")

    try:
        # 检查设备是否已登录
        if not device.username:
            result = (False, "设备未登录任何账号")
        else:
            # 执行登出
            network_manager = NetworkManager(ip=device.ipv4)
            logout_result = network_manager.logout(device.username)

            result = (True if logout_result == "logout_ok" else False, logout_result)

            # 登出后检查状态
            time.sleep(0.5)
            handle_device_check(device)
    except Exception as e:
        traceback.print_exc()
        result = (False, str(e))

    finally:
        return result
