"""
数据库配置模块
"""
from dataclasses import dataclass
from typing import Optional

@dataclass
class DatabaseConfig:
    """数据库配置类"""
    host: str = "140.143.124.70"
    port: int = 3306
    user: str = "root"
    password: str = "LIUnan901104!"
    database: str = "qtdb_pro"
    charset: str = "utf8mb4"

    def get_connection_url(self) -> str:
        """获取数据库连接URL"""
        return f"mysql+pymysql://{self.user}:{self.password}@{self.host}:{self.port}/{self.database}?charset={self.charset}"

# 默认数据库配置实例
db_config = DatabaseConfig()
