"""
管理文件元数据 (ID, Path, Status) 的增删改查：便于展示上传文件的信息：
负责记录文件的“身份证”（ID、原名、存储路径、当前状态）
"""

import sqlite3
import datetime
from ..core.config import settings

class FileManager:
    
    def __init__(self):
        self.db_path = settings.DB_PATH
        self._init_db()

    # 获得数据库连接
    def _get_conn(self):
        # check_same_thread=False 允许在 FastAPI 多线程环境中使用
        return sqlite3.connect(self.db_path, check_same_thread=False)
    
    # 初始化数据表
    def _init_db(self):
        """初始化表结构"""
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS files (
                id TEXT PRIMARY KEY,
                filename TEXT NOT NULL,
                storage_path TEXT NOT NULL,
                status TEXT DEFAULT 'idle',  -- idle, parsing, ready, error
                progress INTEGER DEFAULT 0,
                error_msg TEXT NULL,
                create_time TEXT,
                index_name TEXT DEFAULT 'default_index' -- 所属向量库
            )
        ''')
        conn.commit()
        conn.close()
    
    # 增
    def add_file(self, file_id: str, filename: str, storage_path: str, index_name: str):
        conn = self._get_conn()
        cursor = conn.cursor()
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute(
            "INSERT INTO files (id, filename, storage_path, create_time, index_name) VALUES (?, ?, ?, ?, ?)",
            (file_id, filename, str(storage_path), now, index_name)
        )
        conn.commit()
        conn.close()
    
    # 删
    def delete_file(self, file_id: str):
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM files WHERE id = ? AND index_name = ?", (file_id, index_name))
        deleted_rows = cursor.rowcount  # 获取影响的行数
        conn.commit()
        conn.close()
        return deleted_rows > 0

    # 改
    def update_status(self, file_id: str, status: str, progress: int = None, error_msg: str = None):
        conn = self._get_conn()
        cursor = conn.cursor()
        
        # 动态构建 SQL，只更新传入的字段
        updates = ["status = ?"]
        params = [status]
        
        if progress is not None:
            updates.append("progress = ?")
            params.append(progress)
            
        if error_msg is not None:
            updates.append("error_msg = ?")
            params.append(error_msg)
            
        params.append(file_id)
        
        sql = f"UPDATE files SET {', '.join(updates)} WHERE id = ?"
        cursor.execute(sql, params)
        conn.commit()
        conn.close()        
    
    # 查
    def get_file(self, file_id: str):
        "根据 file_id，获取文件全部信息"
        conn = self._get_conn()
        conn.row_factory = sqlite3.Row # 允许通过字段名访问
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM files WHERE id = ?", (file_id, ))
        row = cursor.fetchone()
        conn.close()
        return dict(row) if row else None
    
    def get_file_name(self, file_id: str):
        "根据 file_id，获取文件名"
        file_info = self.get_file(file_id)

        return file_info["filename"]
    
    def list_index_files(self, index_name: str = None):
        "列出指定知识库中存放的文件"
        conn = self._get_conn()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        if index_name:
            cursor.execute("SELECT * FROM files WHERE index_name = ? ORDER BY create_time DESC", (index_name,))
        else:
            cursor.execute("SELECT * FROM files ORDER BY create_time DESC")
            
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]
    
# 单例模式，供 API 调用
file_manager = FileManager()