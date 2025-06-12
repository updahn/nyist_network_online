import os
import threading
import configparser
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from flask import Flask, request, url_for, send_from_directory
from flask_login import LoginManager
from werkzeug.middleware.dispatcher import DispatcherMiddleware
from werkzeug.wrappers import Response
from werkzeug.serving import run_simple

from src.models.models import db, init_db
from src.models import User
from src.routes import init_routes
from src.utils.config import get_config, get_bool_config
from src.utils.logger import logger

# 应用的URL前缀
PRE_URL = "/network"
CONFIG_FILE = "src/data/setting.ini"
DB_FILE = "src/data/nyist_network.db"


def ensure_directory_exists(file_path):
    """确保文件所在目录存在"""
    directory = os.path.dirname(os.path.abspath(file_path))
    if not os.path.exists(directory):
        os.makedirs(directory)
        logger.info(f"创建目录: {directory}")
    return directory


def initialize_config_file():
    """初始化配置文件"""
    if not os.path.exists(CONFIG_FILE):
        config = configparser.ConfigParser()

        # 确保所有必需的节存在
        default_config = {
            "ACCOUNT": {
                "username": "admin",
                "passwd": "admin",
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
            # 确保配置文件目录存在
            ensure_directory_exists(CONFIG_FILE)
            with open(CONFIG_FILE, "w") as f:
                config.write(f)

        logger.info("创建了默认配置文件: src/data/setting.ini")


def create_main_app():
    """创建并配置主Flask应用"""
    # 初始化配置文件
    initialize_config_file()

    # 确保数据库目录存在
    ensure_directory_exists(DB_FILE)

    # 创建Flask应用
    app = Flask(__name__, static_folder="src/static", template_folder="src/static/html")

    # 基本配置
    app.config.update(
        SECRET_KEY=os.urandom(24),
        SQLALCHEMY_DATABASE_URI=f"sqlite:///{os.path.abspath(DB_FILE)}",
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        APPLICATION_ROOT=PRE_URL,
        SEND_FILE_MAX_AGE_DEFAULT=31536000,  # 静态文件缓存时间为1年
    )

    # 添加全局Jinja2变量
    app.jinja_env.globals["PRE_URL"] = PRE_URL

    # 初始化数据库
    init_db(app)

    # 配置登录管理器
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = "main.login"

    @login_manager.user_loader
    def load_user(user_id):
        """加载用户信息的回调函数"""
        return User.query.get(int(user_id))

    # URL前缀处理
    @app.context_processor
    def override_url_for():
        """添加上下文处理器，确保所有url_for生成的URL都包含正确的前缀"""

        def _url_for(*args, **kwargs):
            if "SCRIPT_NAME" not in request.environ:
                request.environ["SCRIPT_NAME"] = PRE_URL
            return url_for(*args, **kwargs)

        return dict(url_for=_url_for)

    # 初始化管理员用户
    with app.app_context():
        try:
            initialize_admin_user()
        except Exception as e:
            logger.error(f"初始化管理员用户时出错: {e}")

    # 注册路由
    init_routes(app)

    return app


def create_static_app():
    """创建静态文件服务的Flask应用"""
    static_app = Flask("static_app")
    static_app.config["SEND_FILE_MAX_AGE_DEFAULT"] = 31536000  # 静态文件缓存时间为1年

    # 创建一个全局的静态资源请求信号量，限制并发数
    static_semaphore = threading.Semaphore(20)  # 限制最大并发数为20

    @static_app.route("/<path:filename>")
    def serve_static(filename):
        # 使用信号量控制并发
        with static_semaphore:
            return send_from_directory(
                os.path.join(os.path.dirname(__file__), "src/static"), filename
            )

    return static_app


def initialize_admin_user():
    """初始化管理员用户"""
    # 检查是否已有管理员用户
    admin = User.query.filter_by(is_admin=True).first()
    if not admin:
        username = get_config("ACCOUNT", "username")

        # 检查用户名是否已存在
        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            # 如果用户名已存在但不是管理员，则升级为管理员
            if not existing_user.is_admin:
                existing_user.is_admin = True
                existing_user.is_active = True
                db.session.commit()
            return

        # 创建默认管理员
        default_admin = User(
            username=username,
            password=get_config("ACCOUNT", "passwd"),
            email=get_config("EMAIL", "email_to"),
            email_send=get_bool_config("EMAIL", "email_send"),
            is_admin=True,
            is_active=True,
        )
        db.session.add(default_admin)
        try:
            db.session.commit()
            logger.info(f"已创建管理员用户: {username}")
        except Exception as e:
            db.session.rollback()
            logger.error(f"创建管理员用户时出错: {e}")


# 创建应用实例
app = create_main_app()
static_app = create_static_app()

# 应用挂载
application = DispatcherMiddleware(
    Response("Not Found", status=404),
    {
        PRE_URL: app,  # 主应用挂载到 /network
        f"{PRE_URL}/static": static_app,  # 静态文件挂载到 /network/static
    },
)

# 应用启动入口
if __name__ == "__main__":
    # 创建线程池用于处理后台任务
    executor = ThreadPoolExecutor(max_workers=50)

    # 启动服务器
    run_simple(
        "0.0.0.0",  # 监听所有网络接口
        5000,  # 端口号
        application,  # WSGI应用
        use_reloader=True,  # 启用热重载
        use_debugger=True,  # 启用调试器
        threaded=True,  # 启用多线程处理请求
        processes=1,  # 使用单进程模式
    )
