from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime
import os

# 初始化数据库
db = SQLAlchemy()


# 格式化日期时间为统一格式
def format_date(date_obj):
    if not date_obj:
        return None
    # 确保使用精确到秒的格式，去掉毫秒部分
    # 先创建一个没有微秒的新日期对象
    date_without_microsecond = date_obj.replace(microsecond=0)
    return date_without_microsecond.strftime("%Y-%m-%d %H:%M:%S")


# 数据库模型
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    email_send = db.Column(db.Boolean, default=False)
    is_admin = db.Column(db.Boolean, default=False)
    is_active = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.now)

    # 用户拥有多个设备
    devices = db.relationship("Device", backref="owner", lazy="dynamic")

    # 用户拥有的账号集合
    accounts = db.relationship("Account", backref="owner", lazy="dynamic")

    def is_authenticated(self):
        return True

    def to_dict(self):
        return {
            "id": self.id,
            "username": self.username,
            "email": self.email,
            "email_send": self.email_send,
            "is_admin": self.is_admin,
            "is_active": self.is_active,
            "created_at": format_date(self.created_at),
            "account_count": self.accounts.count(),
        }


# 校园网账号模型
class Account(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(120), nullable=False, index=True)
    password = db.Column(db.String(120), nullable=False)
    description = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.now)
    last_check_at = db.Column(db.DateTime)
    online_devices_count = db.Column(db.Integer, default=0)
    is_default = db.Column(db.Boolean, default=False)

    # 账号所属用户
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)

    def to_dict(self):
        return {
            "id": self.id,
            "username": self.username,
            "password": self.password,
            "description": self.description,
            "created_at": format_date(self.created_at),
            "last_check_at": format_date(self.last_check_at),
            "online_devices_count": self.online_devices_count,
            "is_default": self.is_default,
            "user_id": self.user_id,
        }


class Device(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(120), nullable=True)  # 当前登录的校园网账号用户名
    name = db.Column(db.String(120), nullable=False)
    ipv4 = db.Column(db.String(120), nullable=False)
    ipv6 = db.Column(db.String(120), nullable=True)
    used_bytes = db.Column(db.String(120), nullable=True)
    used_second = db.Column(db.String(120), nullable=True)
    last_online_time = db.Column(db.DateTime, nullable=True)
    is_online = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.now)

    # 设备归属用户
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)

    def to_dict(self):
        account_username = self.username

        return {
            "id": self.id,
            "name": self.name,
            "ipv4": self.ipv4,
            "ipv6": self.ipv6,
            "used_bytes": self.used_bytes,
            "used_second": self.used_second,
            "last_online_time": format_date(self.last_online_time),
            "is_online": self.is_online,
            "created_at": format_date(self.created_at),
            "username": account_username,
        }


# 初始化数据库和创建表
def init_db(app):
    """初始化数据库并创建表"""
    db.init_app(app)

    with app.app_context():
        try:
            # 获取数据库文件路径
            db_uri = app.config["SQLALCHEMY_DATABASE_URI"]
            db_path = db_uri.replace("sqlite:///", "")

            # 确保数据库文件所在目录存在
            db_dir = os.path.dirname(os.path.abspath(db_path))
            if not os.path.exists(db_dir):
                os.makedirs(db_dir)
                print(f"创建数据库目录: {db_dir}")

            # 创建表
            db.create_all()

            if not os.path.exists(db_path):
                print(f"已创建新数据库: {db_path}")
            else:
                print(f"数据库连接成功: {db_path}")

        except Exception as e:
            print(f"数据库初始化错误: {str(e)}")
            raise
