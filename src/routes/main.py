from flask_login import current_user, login_user, logout_user, login_required
from datetime import datetime
import os
from flask import (
    Blueprint,
    redirect,
    url_for,
    flash,
    send_from_directory,
    render_template,
    request,
)

from src.models.models import db
from src.models import Device, User, Account
from src.utils.config import MAX_DEVICE_CONNECTIONS
from src.utils.network_utils import *

# 创建认证蓝图
main_bp = Blueprint("main", __name__)


@main_bp.route("/")
def index():
    """首页路由重定向处理。

    根据用户登录状态将用户重定向到相应页面，已登录用户重定向到仪表盘，
    未登录用户重定向到登录页面。

    Returns:
        Response: 重定向响应对象，指向仪表盘或登录页面。
    """
    return redirect(
        url_for("main.dashboard" if current_user.is_authenticated else "main.login")
    )


@main_bp.route("/login", methods=["GET", "POST"])
def login():
    """用户登录处理。

    处理用户登录请求，验证用户凭据，并在成功时创建用户会话。

    Args:
        从request.form获取：
            username: 用户名。
            password: 用户密码。

    Returns:
        Response: GET请求返回登录页面，POST请求在验证成功后重定向到仪表盘，
        验证失败则返回登录页面并显示错误消息。
    """
    # 已登录用户直接重定向到仪表盘
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))

    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        user = User.query.filter_by(username=username).first()

        # 验证用户名和密码
        if user and user.password == password:
            # 检查账户是否已激活（管理员账户除外）
            if not user.is_active and not user.is_admin:
                flash("您的账户尚未激活，请联系管理员", "danger")
                return render_template("login.html")

            login_user(user)
            return redirect(url_for("main.dashboard"))
        else:
            flash("用户名或密码错误", "danger")

    return render_template("login.html")


@main_bp.route("/register", methods=["GET", "POST"])
def register():
    """用户注册处理。

    处理新用户注册请求，创建新用户账户。

    Args:
        从request.form获取：
            username: 新用户的用户名。
            password: 新用户的密码。
            email: 新用户的电子邮件地址。
            email_send: 是否接收电子邮件通知。

    Returns:
        Response: GET请求返回注册页面，POST请求在注册成功后重定向到登录页面，
        或在用户名已存在时返回注册页面并显示错误消息。
    """
    # 已登录用户直接重定向到仪表盘
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))

    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        email = request.form.get("email")
        email_send = request.form.get("email_send") == "on"

        # 检查用户名是否已存在
        if User.query.filter_by(username=username).first():
            flash("用户名已存在", "danger")
            return render_template("register.html")

        # 创建新用户（默认非激活状态）
        new_user = User(
            username=username,
            password=password,
            email=email,
            email_send=email_send,
            is_admin=False,
            is_active=False,  # 默认为非激活状态，需管理员审核
        )

        db.session.add(new_user)
        db.session.commit()

        flash("注册成功，请等待管理员审核", "success")
        return redirect(url_for("main.login"))

    return render_template("register.html")


@main_bp.route("/logout")
@login_required
def logout():
    """用户登出处理。

    结束当前用户会话并重定向到登录页面。

    Returns:
        Response: 重定向响应对象，指向登录页面。

    Raises:
        Unauthorized: 当未登录用户尝试访问此路由时（由login_required装饰器处理）。
    """
    logout_user()
    return redirect(url_for("main.login"))


@main_bp.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    """用户个人资料管理。

    允许用户查看和更新个人资料信息。

    Args:
        从request.form获取：
            email: 用户的电子邮件地址。
            email_send: 是否接收电子邮件通知。
            password: 用户的新密码。

    Returns:
        Response: GET请求返回个人资料页面，POST请求在更新成功后重定向到个人资料页面。

    Raises:
        Unauthorized: 当未登录用户尝试访问此路由时（由login_required装饰器处理）。
    """
    if request.method == "POST":
        # 更新用户信息
        current_user.email = request.form.get("email")
        current_user.email_send = request.form.get("email_send") == "on"
        current_user.password = request.form.get("password")  # 生产环境应使用加密
        current_user.updated_at = datetime.now()

        db.session.commit()
        flash("个人信息更新成功", "success")
        return redirect(url_for("main.profile"))

    return render_template("profile.html", user=current_user)


@main_bp.route("/dashboard")
@login_required
def dashboard():
    """用户仪表盘页面。

    显示用户的设备列表和相关信息。如果用户没有设备，
    尝试从网络获取设备信息并保存到数据库。

    Returns:
        Response: 包含仪表盘页面的响应对象。

    Raises:
        Unauthorized: 当未登录用户尝试访问此路由时（由login_required装饰器处理）。
    """
    devices = current_user.devices
    accounts = current_user.accounts

    if not accounts:
        flash("没有配置校园网账号，无法获取设备", "danger")

        return render_template(
            "dashboard.html",
            user=current_user,
            max_device_connections=MAX_DEVICE_CONNECTIONS,
        )

    # 如果用户没有设备，尝试从网络获取
    if not devices:

        # 获取设备列表
        get_reload_accounts(accounts)

    devices = current_user.devices

    return render_template(
        "dashboard.html",
        devices=devices,
        user=current_user,
        max_device_connections=MAX_DEVICE_CONNECTIONS,
    )


@main_bp.route("/admin")
@login_required
def admin():
    """管理后台页面。

    显示所有用户、账户和设备信息，仅管理员可访问。

    Returns:
        Response: 包含管理后台页面的响应对象或重定向到仪表盘。

    Raises:
        Unauthorized: 当未登录用户尝试访问此路由时（由login_required装饰器处理）。
    """

    users = User.query.all() if current_user.is_admin else []
    accounts = Account.query.all() if current_user.is_admin else []

    if not current_user.is_admin:
        devices = Device.query.filter(Device.username == current_user.username).all()
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

    return render_template(
        "admin.html",
        users=users,
        accounts=accounts,
        devices=device_list,
        user=current_user,
        max_device_connections=MAX_DEVICE_CONNECTIONS,
    )


@main_bp.route("/public/<path:filename>")
def serve_public_file(filename):
    """提供public目录下的静态文件。

    从应用的public目录中提供静态文件。

    Args:
        filename: 请求的文件路径。

    Returns:
        Response: 包含请求文件的响应对象。
    """
    public_folder = os.path.join(os.path.dirname(os.path.dirname(__file__)), "public")
    return send_from_directory(public_folder, filename)
