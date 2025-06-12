import configparser

# 初始化配置解析器
config = configparser.ConfigParser()
config.read("src/data/setting.ini")

# 获取设备最大连接数配置
MAX_DEVICE_CONNECTIONS = config.getint("ACCOUNT", "max_device_connections", fallback=2)


# 获取其他配置
def get_config(section, key, fallback=None):
    """
    获取配置项

    参数:
        section: 配置节
        key: 配置键
        fallback: 默认值

    返回:
        配置值，如果不存在则返回默认值
    """
    return config.get(section, key, fallback=fallback)


def get_int_config(section, key, fallback=None):
    """
    获取整数类型配置项

    参数:
        section: 配置节
        key: 配置键
        fallback: 默认值

    返回:
        整数类型配置值，如果不存在则返回默认值
    """
    return config.getint(section, key, fallback=fallback)


def get_bool_config(section, key, fallback=None):
    """
    获取布尔类型配置项

    参数:
        section: 配置节
        key: 配置键
        fallback: 默认值

    返回:
        布尔类型配置值，如果不存在则返回默认值
    """
    return config.getboolean(section, key, fallback=fallback)
