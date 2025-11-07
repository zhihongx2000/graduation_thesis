"""日志管理模块，进行一些日志配置的记录"""

import logging
from logging.handlers import TimedRotatingFileHandler
import os

import yaml

from .paths import CONFIG_FILE_PATH, PROJECT_ROOT

# ------------------------------
# 通用日志模块
# ------------------------------

# 读取config.yaml文件，获取日志配置
with open(CONFIG_FILE_PATH, "r") as f:
    all_config = yaml.safe_load(f)

    log_config = all_config.get("logging", "")
    LOG_DIR = log_config.get("log_dir", os.getenv("PROJECT_ROOT"))
    os.makedirs(LOG_DIR, exist_ok=True) # 保证目录存在
    
    LOG_FORMAT = log_config.get(
        "log_format", "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
    )
    DATE_FORMAT = log_config.get("date_format", "%Y-%m-%d %H:%M:%S")
    LOG_LEVEL = log_config.get("log_level", "INFO")
    LOG_FILE = os.path.join(
        PROJECT_ROOT, LOG_DIR, log_config.get("file_name", "app.log")
    )

def get_logger(name: str = "app") -> logging.Logger:
    """
    获取指定名称的 logger。
    若已存在则直接返回同一实例，避免重复添加 handler。
    """
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger  # 避免重复添加 handler

    logger.setLevel(LOG_LEVEL)

    # ===== 控制台输出 =====
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG)
    console_formatter = logging.Formatter(LOG_FORMAT, datefmt=DATE_FORMAT)
    console_handler.setFormatter(console_formatter)

    # ===== 文件输出（按日期滚动）=====
    file_handler = TimedRotatingFileHandler(
        LOG_FILE, when="midnight", interval=1, backupCount=7, encoding="utf-8"
    )
    file_handler.suffix = "%Y-%m-%d.log"
    file_formatter = logging.Formatter(LOG_FORMAT, datefmt=DATE_FORMAT)
    file_handler.setFormatter(file_formatter)

    # ===== 添加处理器 =====
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)

    # 防止日志重复输出（父 logger 传播）
    logger.propagate = False

    return logger

if __name__ == "__main__":
    logger = get_logger()
    logger.info("测试logger模块...")