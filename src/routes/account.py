from flask import Blueprint, jsonify, request
from flask_login import current_user, login_required
from datetime import datetime
import traceback

from src.models.models import db
from src.models import Account, Device, User
from src.utils.network_utils import *

account_bp = Blueprint("account", __name__)


@account_bp.route("/api/accounts", methods=["GET"])
@login_required
def get_accounts():
    """获取校园网账号列表。

    根据用户权限获取校园网账号，管理员可获取所有账号或指定用户的账号，
    普通用户只能获取自己的账号。

    Args:
        all: URL参数，值为'true'且用户是管理员时，返回所有账号
        user_id: URL参数，指定用户ID且用户是管理员时，返回该用户的账号

    Returns:
        Response: JSON格式的账号列表
        成功格式：{"success": True, "accounts": [account1, account2, ...]}
        失败格式：{"success": False, "message": "错误信息"}
    """
    result = {"success": False, "message": ""}

    try:
        accounts = current_user.accounts

        if current_user.is_admin:
            if request.args.get("all") == "true":
                accounts = Account.query.all()

            user_id = request.args.get("user_id")
            if user_id:
                user = User.query.get_or_404(int(user_id))
                accounts = user.accounts

        accounts = get_reload_accounts(accounts)
        result = {
            "success": True,
            "accounts": [account.to_dict() for account in accounts],
        }
    except Exception as e:
        traceback.print_exc()
        result = {"success": False, "message": str(e)}
    finally:
        return jsonify(result)


@account_bp.route("/api/account/add", methods=["POST"])
@login_required
def add_account():
    """添加校园网账号。

    创建新的校园网账号记录，根据用户权限决定操作范围，
    普通用户只能为自己添加账号，管理员可以为任何用户添加账号。

    Args:
        从request.json获取：
            username: 校园网账号用户名
            password: 校园网账号密码
            description: 账号描述（可选）
            user_id: 账号所属用户ID（仅管理员可指定，可选）

    Returns:
        Response: JSON格式的操作结果
        成功格式：{"success": True, "account": account_dict}
        失败格式：{"success": False, "message": "错误信息"}
    """
    result = {"success": False, "message": ""}

    try:
        data = request.json
        if not data:
            result = {"success": False, "message": "无效的请求数据"}
        elif not data.get("username") or not data.get("password"):
            result = {"success": False, "message": "用户名和密码不能为空"}
        else:
            username = data.get("username")
            password = data.get("password")
            description = data.get("description", "")

            # 确定目标用户
            target_user_id = data.get("user_id")
            target_user = (
                User.query.get_or_404(int(target_user_id))
                if target_user_id and current_user.is_admin
                else current_user
            )

            # 检查重复账号
            existing_account = Account.query.filter_by(
                username=username, user_id=target_user.id
            ).first()
            if existing_account and existing_account in target_user.accounts:
                result = {"success": False, "message": "已经存在相同用户名的账号"}
            else:
                # 创建新账号
                account = Account(
                    username=username,
                    password=password,
                    description=description,
                    created_at=datetime.now(),
                    online_devices_count=0,
                    user_id=target_user.id,
                )

                # 设置默认账号
                if not any(acc.is_default for acc in target_user.accounts):
                    account.is_default = True

                db.session.add(account)
                target_user.accounts.append(account)
                db.session.commit()
                result = {"success": True, "account": account.to_dict()}

    except Exception as e:
        db.session.rollback()
        traceback.print_exc()
        result = {"success": False, "message": str(e)}

    finally:
        return jsonify(result)


@account_bp.route("/api/account/<int:account_id>", methods=["GET"])
@login_required
def get_account(account_id):
    """获取单个校园网账号详情。

    获取指定ID的账号详细信息，根据用户权限决定能否获取，
    普通用户只能查看自己的账号，管理员可以查看所有账号。

    Args:
        account_id: 要获取详情的账号ID

    Returns:
        Response: JSON格式的账号详情
        成功格式：{"success": True, "account": account_dict}
        失败格式：{"success": False, "message": "错误信息"}
    """
    result = {"success": False, "message": ""}

    try:
        account = Account.query.get_or_404(account_id)
        if not check_permission(account):
            result = {"success": False, "message": "无权限访问此账号"}
        else:
            result = {"success": True, "account": account.to_dict()}
    except Exception as e:
        traceback.print_exc()
        result = {"success": False, "message": str(e)}

    finally:
        return jsonify(result)


@account_bp.route("/api/account/<int:account_id>", methods=["POST"])
@login_required
def update_account(account_id):
    """更新校园网账号信息。

    修改指定账号的信息，根据用户权限决定能否操作，
    普通用户只能更新自己的账号，管理员可以更新所有账号。

    Args:
        account_id: 要更新的账号ID
        从request.json获取：
            username: 账号用户名（仅管理员可修改）
            password: 账号密码
            description: 账号描述

    Returns:
        Response: JSON格式的更新结果
        成功格式：{"success": True, "account": account_dict}
        失败格式：{"success": False, "message": "错误信息"}
    """
    result = {"success": False, "message": ""}

    try:
        account = Account.query.get_or_404(account_id)
        if not check_permission(account):
            result = {"success": False, "message": "无权限操作此账号"}
        else:
            data = request.json
            if not data:
                result = {"success": False, "message": "无效的请求数据"}
            else:
                # 更新账号信息
                if "username" in data and current_user.is_admin:
                    account.username = data.get("username")
                if "password" in data:
                    account.password = data.get("password")
                if "description" in data:
                    account.description = data.get("description")

                db.session.commit()
                result = {"success": True, "account": account.to_dict()}

    except Exception as e:
        db.session.rollback()
        traceback.print_exc()
        result = {"success": False, "message": str(e)}

    finally:
        return jsonify(result)


@account_bp.route("/api/account/<int:account_id>/delete", methods=["POST"])
@login_required
def delete_account(account_id):
    """删除校园网账号。

    从系统中删除指定账号，根据用户权限决定能否操作，
    普通用户只能删除自己的账号，管理员可以删除所有账号。

    Args:
        account_id: 要删除的账号ID

    Returns:
        Response: JSON格式的删除结果
        成功格式：{"success": True, "message": "账号已删除"}
        失败格式：{"success": False, "message": "错误信息"}
    """
    result = {"success": False, "message": ""}

    try:
        account = Account.query.get_or_404(account_id)
        if not check_permission(account):
            result = {"success": False, "message": "无权限操作此账号"}
        else:
            db.session.delete(account)
            db.session.commit()
            result = {"success": True, "message": "账号已删除"}

    except Exception as e:
        db.session.rollback()
        traceback.print_exc()
        result = {"success": False, "message": str(e)}

    finally:
        return jsonify(result)


@account_bp.route("/api/account/<int:account_id>/default", methods=["POST"])
@login_required
def set_default_account(account_id):
    """设置默认校园网账号。

    将指定账号设置为用户的默认账号，根据用户权限决定能否操作，
    普通用户只能设置自己的账号，管理员可以设置任何账号。

    Args:
        account_id: 要设置为默认的账号ID

    Returns:
        Response: JSON格式的设置结果
        成功格式：{"success": True, "message": "已设置为默认账号"}
        失败格式：{"success": False, "message": "错误信息"}
    """
    result = {"success": False, "message": ""}

    try:
        account = Account.query.get_or_404(account_id)
        if not check_permission(account):
            result = {"success": False, "message": "无权限操作此账号"}
        else:
            # 清除其他默认账号
            for user_account in current_user.accounts:
                if user_account.id != account_id:
                    user_account.is_default = False

            # 设置新的默认账号
            account.is_default = True
            db.session.commit()
            result = {"success": True, "message": "已设置为默认账号"}

    except Exception as e:
        db.session.rollback()
        traceback.print_exc()
        result = {"success": False, "message": str(e)}

    finally:
        return jsonify(result)
