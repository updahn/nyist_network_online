from src.routes.main import main_bp
from src.routes.device import device_bp
from src.routes.account import account_bp
from src.routes.admin import admin_bp
from src.routes.errors import errors_bp


def init_routes(app):
    """注册所有路由蓝图"""
    # 直接注册蓝图，不需要添加额外前缀，因为已经通过 DispatcherMiddleware 配置了 PRE_URL 前缀
    # 这样所有请求都会自动加上 PRE_URL 前缀
    app.register_blueprint(main_bp)
    app.register_blueprint(device_bp)
    app.register_blueprint(account_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(errors_bp)
