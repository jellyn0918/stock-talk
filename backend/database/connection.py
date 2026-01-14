"""
数据库连接管理模块
"""
import pymysql
from contextlib import contextmanager
from typing import Optional, Dict, Any
from database.config import db_config


class DatabaseConnection:
    """数据库连接管理器"""

    def __init__(self):
        self.config = db_config
        self._pool = None

    def get_connection(self):
        """获取数据库连接"""
        return pymysql.connect(
            host=self.config.host,
            port=self.config.port,
            user=self.config.user,
            password=self.config.password,
            database=self.config.database,
            charset=self.config.charset,
            cursorclass=pymysql.cursors.DictCursor
        )

    @contextmanager
    def get_cursor(self):
        """获取数据库游标（上下文管理器）"""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            yield cursor
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            cursor.close()
            conn.close()

    def execute_query(self, sql: str, params: Optional[tuple] = None) -> list[Dict[str, Any]]:
        """执行查询并返回结果"""
        with self.get_cursor() as cursor:
            cursor.execute(sql, params or ())
            result = cursor.fetchall()
            return result

    def execute_update(self, sql: str, params: Optional[tuple] = None) -> int:
        """执行更新操作并返回影响行数"""
        with self.get_cursor() as cursor:
            cursor.execute(sql, params or ())
            return cursor.rowcount

    def test_connection(self) -> bool:
        """测试数据库连接"""
        try:
            with self.get_cursor() as cursor:
                cursor.execute("SELECT 1")
                return True
        except Exception as e:
            print(f"数据库连接失败: {e}")
            return False


# 全局数据库连接实例
db = DatabaseConnection()
