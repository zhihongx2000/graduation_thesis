"""加载环境变量, 定义路径常量 (STORAGE_PATH 等)"""

import os

from pathlib import Path

class Settings:

    # 项目根目录
    BASE_DIR = Path(__file__).resolve().parent.parent.parent 

    # 存储相关目录
    STORAGE_DIR = BASE_DIR / "storage"
    UPLOAD_DIR = STORAGE_DIR / "upload"
    ARTIFACT_DIR = STORAGE_DIR / "artifacts"
    DB_PATH = STORAGE_DIR / "db" / "metadata.sqlite" # 数据库文件
    VECTOR_STORE_DIR = STORAGE_DIR / "vector_store"

    # 日志相关文件
    LOG_DIR = BASE_DIR / "log"

    # 进行初始化
    def init_dirs(self):
        "初始化目录结构"
        self.UPLOAD_DIR.mkdir(parents=True,exist_ok=True)
        self.ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
        self.DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        self.VECTOR_STORE_DIR.mkdir(parents=True, exist_ok=True)
        self.LOG_DIR.mkdir(parents=True, exist_ok=True)

settings = Settings()
settings.init_dirs() # 导入配置文件时，自动初始化目录

# print(settings.BASE_DIR)
# print(settings.STORAGE_DIR)
# print(settings.UPLOAD_DIR)
# print(settings.ARTIFACT_DIR)
# print(settings.DB_PATH)
# print(settings.VECTOR_STORE_DIR)