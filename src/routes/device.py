from flask import Blueprint, jsonify, request
from flask_login import current_user, login_required
from datetime import datetime
import traceback

from src.models.models import db
from src.models import Device, Account
from src.utils.config import MAX_DEVICE_CONNECTIONS
from src.utils.network_utils import *

# 创建设备管理蓝图
device_bp = Blueprint("device", __name__)


@device_bp.route("/api/devices", methods=["GET"])
@login_required
def get_devices():
    """获取所有设备信息。

    根据用户权限获取设备列表，管理员可查看所有设备，
    普通用户只能查看自己的设备。

    Returns:
        Response: JSON格式的设备列表
        成功格式：{"success": True, "devices": [device1, device2, ...]}
        失败格式：{"success": False, "message": "错误信息"}
    """
    result = {"success": False, "message": ""}

    try:
        devices = current_user.devices

        for device in devices:
            handle_device_check(device)

        result = {"success": True, "devices": [device.to_dict() for device in devices]}
    except Exception as e:
        traceback.print_exc()
        result = {"success": False, "message": str(e)}

    finally:
        return jsonify(result)


@device_bp.route("/api/devices/refresh", methods=["POST"])
@login_required
def refresh_devices():
    """刷新设备列表。

    从校园网获取最新的设备列表，并更新数据库中的设备信息。

    Returns:
        Response: JSON格式的刷新结果
        成功格式：{"success": True, "devices": [device1, device2, ...]}
        失败格式：{"success": False, "message": "错误信息"}
    """
    result = {"success": False, "message": ""}

    try:
        accounts = current_user.accounts
        if not accounts:
            result = {"success": False, "message": "没有可用的校园网账号"}
        else:
            get_reload_accounts(accounts)
            devices = current_user.devices
            result = {
                "success": True,
                "devices": [device.to_dict() for device in devices],
            }
    except Exception as e:
        traceback.print_exc()
        result = {"success": False, "message": str(e)}

    finally:
        return jsonify(result)


@device_bp.route("/api/device/add", methods=["POST"])
@login_required
def add_device():
    """添加新设备。

    接收设备信息并创建新的设备记录，关联到当前用户。

    Args:
        从request.json获取：
            name: 设备名称，默认为"新设备"
            ipv4: 设备IPv4地址
            ipv6: 设备IPv6地址，默认为"::"
            used_bytes: 已使用流量，默认为空
            used_second: 已使用时间，默认为空

    Returns:
        Response: JSON格式的操作结果
        成功格式：{"success": True}
        失败格式：{"success": False, "message": "错误信息"}
    """
    result = {"success": False, "message": ""}

    try:
        data = request.json

        new_device = Device(
            name=data.get("name", "新设备"),
            ipv4=data.get("ipv4", ""),
            ipv6=data.get("ipv6", "::"),
            used_bytes=data.get("used_bytes", ""),
            used_second=data.get("used_second", ""),
            is_online=False,
            user_id=current_user.id,
        )

        db.session.add(new_device)
        db.session.commit()
        result = {"success": True}
    except Exception as e:
        db.session.rollback()
        traceback.print_exc()
        result = {"success": False, "message": str(e)}

    finally:
        return jsonify(result)


@device_bp.route("/api/device/<int:device_id>/name", methods=["POST"])
@login_required
def set_name_device(device_id):
    """更新设备名称。

    修改指定设备的名称，根据用户权限决定能否操作。

    Args:
        device_id: 要更新名称的设备ID
        从request.json获取：
            name: 新的设备名称

    Returns:
        Response: JSON格式的更新结果
        成功格式：{"success": True}
        失败格式：{"success": False, "message": "错误信息"}
    """
    result = {"success": False, "message": ""}

    try:
        device = Device.query.get_or_404(device_id)
        if not check_permission(device):
            result = {"success": False, "message": "无权限操作此设备"}
        else:
            new_name = request.json.get("name")
            if not new_name:
                result = {"success": False, "message": "设备名称不能为空"}
            else:
                device.name = new_name
                db.session.commit()
                result = {"success": True}
    except Exception as e:
        db.session.rollback()
        traceback.print_exc()
        result = {"success": False, "message": str(e)}

    finally:
        return jsonify(result)


@device_bp.route("/api/device/<int:device_id>/account", methods=["POST"])
@login_required
def set_account_device(device_id):
    """设置设备使用的校园网账号。

    为指定设备设置默认使用的校园网账号，根据用户权限决定能否操作。

    Args:
        device_id: 要设置账号的设备ID
        从request.json获取：
            account_id: 要设置的账号ID

    Returns:
        Response: JSON格式的设置结果
        成功格式：{"success": True}
        失败格式：{"success": False, "message": "错误信息"}
    """
    # 初始化结果
    result = {"success": False, "message": ""}

    try:
        # 获取设备并检查权限
        device = Device.query.get_or_404(device_id)
        if not check_permission(device):
            result = {"success": False, "message": "无权限操作此设备"}
        else:
            # 获取请求中的账号ID
            account_id = request.json.get("account_id")

            # 如果没有提供账号ID，清除设备关联的账号
            if not account_id:
                device.username = None
                result = {"success": True, "message": "已清除设备关联的账号"}
            else:
                # 获取账号并检查权限
                account = Account.query.get_or_404(account_id)
                if not check_permission(account):
                    result = {"success": False, "message": "无权限操作此账号"}
                else:
                    # 检查并处理设备当前状态
                    is_online, _ = handle_device_check(device)

                    # 如果设备当前在线，先登出
                    if is_online:
                        handle_device_logout(device)

                    # 使用新账号登录
                    login_success, message = handle_device_login(
                        device, account.username, account.password
                    )

                    # 处理登录结果
                    if not login_success:
                        result = {"success": False, "message": message}
                    else:
                        # 登录成功，更新设备关联的账号
                        device.username = account.username
                        db.session.commit()

                        # 更新设备状态
                        is_online, message = handle_device_check(device)

                        if is_online:
                            result = {"success": True, "message": message}
    except Exception as e:
        # 发生异常时回滚数据库事务
        db.session.rollback()
        traceback.print_exc()
        result = {"success": False, "message": str(e)}

    finally:
        return jsonify(result)


@device_bp.route("/api/device/<int:device_id>/delete", methods=["POST"])
@login_required
def delete_device(device_id):
    """删除设备。

    删除指定的设备记录，根据用户权限决定能否操作。

    Args:
        device_id: 要删除的设备ID

    Returns:
        Response: JSON格式的删除结果
        成功格式：{"success": True, "message": "设备已删除"}
        失败格式：{"success": False, "message": "错误信息"}
    """
    result = {"success": False, "message": ""}

    try:
        device = Device.query.get_or_404(device_id)
        if not check_permission(device):
            result = {"success": False, "message": "无权限操作此设备"}
        else:
            db.session.delete(device)
            db.session.commit()
            result = {"success": True, "message": "设备已删除"}
    except Exception as e:
        db.session.rollback()
        traceback.print_exc()
        result = {"success": False, "message": str(e)}

    finally:
        return jsonify(result)


@device_bp.route("/api/device/<int:device_id>/check", methods=["POST"])
@login_required
def check_device(device_id):
    """检查设备状态。

    检查指定设备的在线状态和网络使用情况，根据用户权限决定能否操作。

    Args:
        device_id: 要检查的设备ID

    Returns:
        Response: JSON格式的设备状态信息
        成功格式：{"success": True, "message": "online/offline"}
        失败格式：{"success": False, "message": "错误信息"}
    """
    result = {"success": False, "message": ""}

    try:
        device = Device.query.get_or_404(device_id)
        if not check_permission(device):
            result = {"success": False, "message": "无权限操作此设备"}
        else:
            success, message = handle_device_check(device)
            result = {"success": success, "message": message}
    except Exception as e:
        traceback.print_exc()
        result = {"success": False, "message": str(e)}

    finally:
        return jsonify(result)


@device_bp.route("/api/device/<int:device_id>/login", methods=["POST"])
@login_required
def login_device(device_id):
    """设备登录校园网。

    使用关联的校园网账号登录指定设备，根据用户权限决定能否操作。

    Args:
        device_id: 要登录的设备ID

    Returns:
        Response: JSON格式的登录结果
        成功格式：{"success": True, "message": "login_ok"}
        失败格式：{"success": False, "message": "错误信息"}
    """
    result = {"success": False, "message": ""}

    try:
        device = Device.query.get_or_404(device_id)
        if not check_permission(device):
            result = {"success": False, "message": "无权限操作此设备"}
        else:
            account, username, password = get_account_for_device(device)

            if not username or not password:
                result = {
                    "success": False,
                    "message": "未配置校园网账号，请先添加校园网账号并设置默认账号",
                }
            elif account and account.online_devices_count >= MAX_DEVICE_CONNECTIONS:
                result = {
                    "success": False,
                    "message": f"账号 {username} 已达到最大在线设备数量({MAX_DEVICE_CONNECTIONS}台)",
                }
            else:
                success, message = handle_device_login(device)
                result = {"success": success, "message": message}
    except Exception as e:
        traceback.print_exc()
        result = {"success": False, "message": str(e)}

    finally:
        return jsonify(result)


@device_bp.route("/api/device/<int:device_id>/logout", methods=["POST"])
@login_required
def logout_device(device_id):
    """设备登出校园网。

    登出指定设备当前使用的校园网账号，根据用户权限决定能否操作。

    Args:
        device_id: 要登出的设备ID

    Returns:
        Response: JSON格式的登出结果
        成功格式：{"success": True, "message": "logout_ok"}
        失败格式：{"success": False, "message": "错误信息"}
    """
    result = {"success": False, "message": ""}

    try:
        device = Device.query.get_or_404(device_id)
        if not check_permission(device):
            result = {"success": False, "message": "无权限操作此设备"}
        else:
            success, message = handle_device_logout(device)
            result = {"success": success, "message": message}
    except Exception as e:
        traceback.print_exc()
        result = {"success": False, "message": str(e)}

    finally:
        return jsonify(result)
