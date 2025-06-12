from flask import Blueprint, jsonify, request
from flask_login import current_user, login_required
import json
import traceback

from src.models.models import db
from src.models import User, Account, Device
from src.utils.network_utils import *
from src.routes.account import *
from src.routes.device import *

# 创建管理员蓝图
admin_bp = Blueprint("admin", __name__)


@admin_bp.route("/api/admin/users")
@login_required
def get_admin_users():
    """获取所有用户列表。

    检查当前用户是否为管理员，如果是，则返回系统中所有用户的列表。

    Returns:
        JSON响应，包含用户列表或错误信息。
        成功格式：{"success": True, "users": [user1_dict, user2_dict, ...]}
        失败格式：{"success": False, "message": "没有权限"}

    Raises:
        无
    """
    result = {"success": False, "message": ""}

    try:
        if not current_user.is_admin:
            result = {"success": False, "message": "没有权限"}
        else:
            users = User.query.all()
            result = {"success": True, "users": [user.to_dict() for user in users]}
    except Exception as e:
        traceback.print_exc()
        result = {"success": False, "message": str(e)}

    finally:
        return jsonify(result)


@admin_bp.route("/api/admin/accounts")
@login_required
def get_admin_accounts():
    """获取所有账号列表。

    检查当前用户是否为管理员，如果是，则返回系统中所有校园网账号的列表。

    Returns:
        JSON响应，包含账号列表或错误信息。
        成功格式：{"success": True, "accounts": [account1_dict, account2_dict, ...]}
        失败格式：{"success": False, "message": "没有权限"}

    Raises:
        无
    """
    result = {"success": False, "message": ""}

    try:
        if not current_user.is_admin:
            result = {"success": False, "message": "没有权限"}
        else:
            accounts = Account.query.all()
            result = {
                "success": True,
                "accounts": [account.to_dict() for account in accounts],
            }
    except Exception as e:
        traceback.print_exc()
        result = {"success": False, "message": str(e)}

    finally:
        return jsonify(result)


@admin_bp.route("/api/admin/devices")
@login_required
def get_admin_devices():
    """获取设备列表。

    根据用户权限获取设备列表，管理员可查看所有设备，普通用户只能查看自己的设备。
    返回的设备信息中包含关联的用户信息。

    Returns:
        JSON响应，包含设备列表。
        格式：{"success": True, "devices": [device1_dict, device2_dict, ...]}

    Raises:
        无
    """
    result = {"success": False, "message": ""}

    try:
        # 根据用户权限获取不同的设备列表
        if not current_user.is_admin:
            devices = Device.query.filter(
                Device.username == current_user.username
            ).all()
        else:
            devices = Device.query.all()

        # 转换设备列表，包括用户信息
        device_list = []
        for device in devices:
            device_dict = device.to_dict()
            if device.user_id:
                user = User.query.get(device.user_id)
                if user:
                    device_dict["user"] = {"id": user.id, "username": user.username}
            device_list.append(device_dict)

        result = {"success": True, "devices": device_list}
    except Exception as e:
        traceback.print_exc()
        result = {"success": False, "message": str(e)}

    finally:
        return jsonify(result)


@admin_bp.route("/api/admin/users/<int:user_id>/toggle_status", methods=["POST"])
@login_required
def toggle_user_status(user_id):
    """切换用户激活状态。

    管理员可以启用或禁用指定用户的账号状态。

    Args:
        user_id: 要操作的用户ID。

    Returns:
        JSON响应，包含操作结果。
        成功格式：{"success": True, "status": 是否激活}
        失败格式：{"success": False, "message": "没有权限"}

    Raises:
        无
    """
    result = {"success": False, "message": ""}

    try:
        if not current_user.is_admin:
            result = {"success": False, "message": "没有权限"}
        else:
            user = User.query.get_or_404(user_id)
            user.is_active = not user.is_active
            db.session.commit()
            result = {"success": True, "status": user.is_active}
    except Exception as e:
        db.session.rollback()
        traceback.print_exc()
        result = {"success": False, "message": str(e)}

    finally:
        return jsonify(result)


@admin_bp.route("/api/admin/users/<int:user_id>/toggle_admin", methods=["POST"])
@login_required
def toggle_user_admin(user_id):
    """切换用户管理员权限。

    管理员可以授予或撤销指定用户的管理员权限。

    Args:
        user_id: 要操作的用户ID。

    Returns:
        JSON响应，包含操作结果。
        成功格式：{"success": True, "is_admin": 是否为管理员}
        失败格式：{"success": False, "message": "没有权限"}

    Raises:
        无
    """
    result = {"success": False, "message": ""}

    try:
        if not current_user.is_admin:
            result = {"success": False, "message": "没有权限"}
        else:
            user = User.query.get_or_404(user_id)
            user.is_admin = not user.is_admin
            db.session.commit()
            result = {"success": True, "is_admin": user.is_admin}
    except Exception as e:
        db.session.rollback()
        traceback.print_exc()
        result = {"success": False, "message": str(e)}

    finally:
        return jsonify(result)


# 用户校园网账号管理API
@admin_bp.route("/api/admin/users/<int:user_id>/accounts", methods=["GET"])
@login_required
def get_user_accounts(user_id):
    """获取指定用户的校园网账号列表。

    管理员可以查看任何用户的校园网账号列表。

    Args:
        user_id: 目标用户的ID。

    Returns:
        JSON响应，重定向到通用账号获取接口的返回结果。

    Raises:
        无
    """
    result = {"success": False, "message": ""}

    try:
        if not current_user.is_admin:
            result = {"success": False, "message": "没有权限"}
        else:
            # 设置参数并重定向到通用接口
            request.args = request.args.copy()
            request.args["user_id"] = str(user_id)
            result = get_accounts()
    except Exception as e:
        traceback.print_exc()
        result = {"success": False, "message": str(e)}

    finally:
        return result


@admin_bp.route("/api/admin/users/<int:user_id>/accounts/add", methods=["POST"])
@login_required
def add_user_account(user_id):
    """为指定用户添加校园网账号。

    管理员可以为任何用户添加新的校园网账号。

    Args:
        user_id: 目标用户的ID。

    Returns:
        JSON响应，重定向到通用账号添加接口的返回结果。

    Raises:
        无
    """
    result = {"success": False, "message": ""}

    try:
        if not current_user.is_admin:
            result = {"success": False, "message": "没有权限"}
        else:
            # 修改请求数据并重定向到通用接口
            data = request.get_json()
            data["user_id"] = user_id
            request.data = json.dumps(data).encode("utf-8")
            result = add_account()
    except Exception as e:
        traceback.print_exc()
        result = {"success": False, "message": str(e)}

    finally:
        return result


# 校园网账号管理API
@admin_bp.route("/api/admin/accounts/<int:account_id>", methods=["GET"])
@login_required
def get_account_details(account_id):
    """获取指定校园网账号的详细信息。

    管理员可以查看任何校园网账号的详细信息。

    Args:
        account_id: 目标账号的ID。

    Returns:
        JSON响应，重定向到通用账号详情接口的返回结果。

    Raises:
        无
    """
    result = {"success": False, "message": ""}

    try:
        if not current_user.is_admin:
            result = {"success": False, "message": "没有权限"}
        else:
            result = get_account(account_id)
    except Exception as e:
        traceback.print_exc()
        result = {"success": False, "message": str(e)}

    finally:
        return result


@admin_bp.route("/api/admin/accounts/<int:account_id>/update", methods=["POST"])
@login_required
def update_admin_account(account_id):
    """更新指定校园网账号的信息。

    管理员可以修改任何校园网账号的信息。

    Args:
        account_id: 目标账号的ID。

    Returns:
        JSON响应，重定向到通用账号更新接口的返回结果。

    Raises:
        无
    """
    result = {"success": False, "message": ""}

    try:
        if not current_user.is_admin:
            result = {"success": False, "message": "没有权限"}
        else:
            result = update_account(account_id)
    except Exception as e:
        traceback.print_exc()
        result = {"success": False, "message": str(e)}

    finally:
        return result


@admin_bp.route("/api/admin/accounts/<int:account_id>/delete", methods=["POST"])
@login_required
def delete_admin_account(account_id):
    """删除指定的校园网账号。

    管理员可以删除任何校园网账号。

    Args:
        account_id: 目标账号的ID。

    Returns:
        JSON响应，重定向到通用账号删除接口的返回结果。

    Raises:
        无
    """
    result = {"success": False, "message": ""}

    try:
        if not current_user.is_admin:
            result = {"success": False, "message": "没有权限"}
        else:
            result = delete_account(account_id)
    except Exception as e:
        traceback.print_exc()
        result = {"success": False, "message": str(e)}

    finally:
        return result


@admin_bp.route("/api/admin/devices/<int:device_id>/account", methods=["POST"])
@login_required
def set_device_account(device_id):
    """设置设备使用的校园网账号。

    管理员可以为任何设备设置使用的校园网账号。

    Args:
        device_id: 目标设备的ID。

    Returns:
        JSON响应，重定向到通用设备账号设置接口的返回结果。

    Raises:
        无
    """
    result = {"success": False, "message": ""}

    try:
        if not current_user.is_admin:
            result = {"success": False, "message": "没有权限"}
        else:
            result = set_account_device(device_id)
    except Exception as e:
        traceback.print_exc()
        result = {"success": False, "message": str(e)}

    finally:
        return result
