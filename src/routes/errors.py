from flask import Blueprint, render_template, request, jsonify, send_file
import os

# 创建错误处理蓝图
errors_bp = Blueprint("errors", __name__)

# 支持的图片文件扩展名列表
IMAGE_EXTENSIONS = [".jpg", ".jpeg", ".png", ".gif", ".svg", ".ico", ".webp", ".bmp"]


@errors_bp.app_errorhandler(500)
def handle_500_error(e):
    """处理500内部服务器错误。

    根据请求类型返回不同的响应：图片请求返回默认图片，
    API请求返回JSON格式错误信息，网页请求返回500错误页面。

    Args:
        e: 捕获的异常对象。

    Returns:
        Response: 根据请求类型返回不同的响应。
    """

    # 处理图片请求 - 返回默认图片或404
    path_lower = request.path.lower()
    if any(path_lower.endswith(ext) for ext in IMAGE_EXTENSIONS):
        return "", 404

    # 处理API请求 - 返回JSON格式错误
    if request.path.startswith("/api/"):
        return (
            jsonify({"success": False, "message": "服务器内部错误，请联系管理员"}),
            500,
        )

    # 处理网页请求 - 返回错误页面
    return render_template("500.html"), 500


@errors_bp.app_errorhandler(404)
def handle_404_error(e):
    """处理404页面未找到错误。

    根据请求类型返回不同的响应：图片请求返回默认图片，
    API请求返回JSON格式错误信息，网页请求返回404错误页面。

    Args:
        e: 捕获的异常对象。

    Returns:
        Response: 根据请求类型返回不同的响应。
    """

    # 处理图片请求 - 返回默认图片或404
    path_lower = request.path.lower()
    if any(path_lower.endswith(ext) for ext in IMAGE_EXTENSIONS):
        return "", 404

    # 处理API请求 - 返回JSON格式错误
    if request.path.startswith("/api/"):
        return (
            jsonify({"success": False, "message": f"找不到请求的资源: {request.path}"}),
            404,
        )

    # 处理网页请求 - 返回错误页面
    return render_template("404.html"), 404


@errors_bp.app_errorhandler(Exception)
def handle_unhandled_exception(e):
    """处理所有未捕获的异常。

    作为最后的防线，捕获所有未被特定错误处理器处理的异常，
    根据请求类型返回不同的响应。

    Args:
        e: 捕获的异常对象。

    Returns:
        Response: 根据请求类型返回不同的响应。
    """

    # 处理图片请求 - 返回默认图片或404
    path_lower = request.path.lower()
    if any(path_lower.endswith(ext) for ext in IMAGE_EXTENSIONS):
        return "", 404

    # 处理API请求 - 返回JSON格式错误
    if request.path.startswith("/api/"):
        return jsonify({"success": False, "message": f"服务器异常: {str(e)}"}), 500

    # 处理网页请求 - 返回错误页面
    return render_template("500.html"), 500
