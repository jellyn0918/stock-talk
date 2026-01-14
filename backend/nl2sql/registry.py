"""
表注册和元数据管理框架

这个模块实现了一个可扩展的表注册系统，用于管理数据库表的元数据。
新表可以通过注册表（TableRegistry）动态添加，无需修改核心代码。
"""
from typing import Dict, List, Optional, Set, Any
from dataclasses import dataclass, field
from enum import Enum


class FieldType(Enum):
    """字段类型枚举"""
    STRING = "string"
    NUMBER = "number"
    DATE = "date"
    TIME = "time"
    DATETIME = "datetime"
    DECIMAL = "decimal"
    INTEGER = "integer"


@dataclass
class FieldMetadata:
    """字段元数据"""
    name: str                    # 数据库字段名
    display_name: str            # 显示名称（中文）
    type: FieldType              # 字段类型
    description: str = ""        # 字段描述
    sortable: bool = True        # 是否可排序
    filterable: bool = True      # 是否可过滤
    aggregatable: bool = False   # 是否可聚合（用于COUNT、SUM等）
    example_values: List[str] = field(default_factory=list)  # 示例值


@dataclass
class TableMetadata:
    """表元数据"""
    table_name: str                      # 数据库表名
    display_name: str                    # 显示名称（中文）
    description: str                     # 表描述
    fields: Dict[str, FieldMetadata]     # 字段映射（field_name -> FieldMetadata）
    primary_key: str = "id"              # 主键字段

    def get_field(self, field_name: str) -> Optional[FieldMetadata]:
        """获取字段元数据"""
        # 支持通过显示名称或字段名查找
        if field_name in self.fields:
            return self.fields[field_name]

        # 尝试通过display_name查找
        for fm in self.fields.values():
            if fm.display_name == field_name:
                return fm

        return None

    def get_field_names(self) -> Set[str]:
        """获取所有字段名（包括显示名称）"""
        names = set(self.fields.keys())
        for fm in self.fields.values():
            names.add(fm.display_name)
        return names

    def get_db_field_name(self, user_input: str) -> Optional[str]:
        """将用户输入的字段名转换为数据库字段名"""
        # 直接匹配
        if user_input in self.fields:
            return user_input

        # 通过display_name匹配
        for name, fm in self.fields.items():
            if fm.display_name == user_input:
                return name

        return None


class TableRegistry:
    """
    表注册表 - 框架化的核心

    管理所有可查询的表及其元数据
    新表通过register_table()方法注册
    """

    def __init__(self):
        self._tables: Dict[str, TableMetadata] = {}

    def register_table(self, metadata: TableMetadata):
        """注册表"""
        self._tables[metadata.table_name] = metadata

    def get_table(self, table_name: str) -> Optional[TableMetadata]:
        """获取表元数据"""
        return self._tables.get(table_name)

    def list_tables(self) -> List[str]:
        """列出所有注册的表名"""
        return list(self._tables.keys())

    def get_all_metadata(self) -> Dict[str, TableMetadata]:
        """获取所有表元数据"""
        return self._tables.copy()

    def validate_field(self, table_name: str, field_name: str) -> bool:
        """验证字段是否存在于表中"""
        table = self.get_table(table_name)
        if not table:
            return False
        return table.get_db_field_name(field_name) is not None


# 全局表注册表实例
registry = TableRegistry()


# ============== 表注册区域 ==============
# 新表的注册代码添加到这个区域

def register_hq_stk_limit_list_d():
    """注册涨停板数据表"""

    fields = {
        "trade_date": FieldMetadata(
            name="trade_date",
            display_name="交易日期",
            type=FieldType.DATE,
            description="交易日期",
            sortable=True,
            filterable=True,
            aggregatable=False
        ),
        "ts_code": FieldMetadata(
            name="ts_code",
            display_name="股票代码",
            type=FieldType.STRING,
            description="股票代码（如：000001.SZ）",
            sortable=True,
            filterable=True,
            aggregatable=True,  # 可以COUNT
            example_values=["000001.SZ", "600000.SH", "600519.SH"]
        ),
        "name": FieldMetadata(
            name="name",
            display_name="股票名称",
            type=FieldType.STRING,
            description="股票名称",
            sortable=True,
            filterable=True,
            example_values=["平安银行", "贵州茅台", "中国平安"]
        ),
        "industry": FieldMetadata(
            name="industry",
            display_name="行业",
            type=FieldType.STRING,
            description="所属行业",
            sortable=True,
            filterable=True,
            aggregatable=True,
            example_values=["银行", "半导体", "医药生物", "房地产"]
        ),
        "close": FieldMetadata(
            name="close",
            display_name="收盘价",
            type=FieldType.DECIMAL,
            description="当日收盘价",
            sortable=True,
            filterable=True,
            aggregatable=True  # 可以SUM, AVG, MAX, MIN
        ),
        "pct_chg": FieldMetadata(
            name="pct_chg",
            display_name="涨跌幅",
            type=FieldType.DECIMAL,
            description="涨跌幅百分比",
            sortable=True,
            filterable=True,
            aggregatable=True
        ),
        "amount": FieldMetadata(
            name="amount",
            display_name="成交额",
            type=FieldType.DECIMAL,
            description="成交金额（元）",
            sortable=True,
            filterable=True,
            aggregatable=True
        ),
        "limit_amount": FieldMetadata(
            name="limit_amount",
            display_name="板上成交金额",
            type=FieldType.DECIMAL,
            description="板上成交金额(成交价格为该股票跌停价的所有成交额的总和，涨停无此数据)",
            sortable=True,
            filterable=True,
            aggregatable=True
        ),
        "float_mv": FieldMetadata(
            name="float_mv",
            display_name="流通市值",
            type=FieldType.DECIMAL,
            description="流通市值（元）",
            sortable=True,
            filterable=True,
            aggregatable=True
        ),
        "total_mv": FieldMetadata(
            name="total_mv",
            display_name="总市值",
            type=FieldType.DECIMAL,
            description="总市值（元）",
            sortable=True,
            filterable=True,
            aggregatable=True
        ),
        "turnover_ratio": FieldMetadata(
            name="turnover_ratio",
            display_name="换手率",
            type=FieldType.DECIMAL,
            description="换手率百分比",
            sortable=True,
            filterable=True,
            aggregatable=True
        ),
        "fd_amount": FieldMetadata(
            name="fd_amount",
            display_name="封单金额",
            type=FieldType.DECIMAL,
            description="封单金额（以涨停价买入挂单的资金总量）",
            sortable=True,
            filterable=True,
            aggregatable=True
        ),
        "first_time": FieldMetadata(
            name="first_time",
            display_name="首次封板时间",
            type=FieldType.STRING,
            description="首次封板时间（跌停无此数据）",
            sortable=True,
            filterable=True,
            aggregatable=False
        ),
        "last_time": FieldMetadata(
            name="last_time",
            display_name="最后封板时间",
            type=FieldType.STRING,
            description="最后封板时间",
            sortable=True,
            filterable=True,
            aggregatable=False
        ),
        "open_times": FieldMetadata(
            name="open_times",
            display_name="炸板次数",
            type=FieldType.INTEGER,
            description="炸板次数(跌停为开板次数)",
            sortable=True,
            filterable=True,
            aggregatable=True
        ),
        "up_stat": FieldMetadata(
            name="up_stat",
            display_name="涨停统计",
            type=FieldType.STRING,
            description="涨停统计（N/T T天有N次涨停）",
            sortable=True,
            filterable=True,
            example_values=["4/4", "3/5", "1/1"]
        ),
        "limit_times": FieldMetadata(
            name="limit_times",
            display_name="连板数",
            type=FieldType.INTEGER,
            description="连板数（个股连续封板数量）",
            sortable=True,
            filterable=True,
            aggregatable=True
        ),
        "limit_l": FieldMetadata(
            name="limit_l",
            display_name="涨跌停标识",
            type=FieldType.STRING,
            description="D跌停U涨停Z炸板",
            sortable=True,
            filterable=True,
            example_values=["U", "D", "Z"]
        )
    }

    table_metadata = TableMetadata(
        table_name="hq_stk_limit_list_d",
        display_name="涨跌停板数据表",
        description="A股涨停和跌停股票的日线数据，包含封板时间、封单金额、炸板次数等信息。注意：此表同时包含涨停(U)、跌停(D)、炸板(Z)三种数据",
        fields=fields,
        primary_key="id"
    )

    registry.register_table(table_metadata)


def register_all_tables():
    """注册所有表"""
    register_hq_stk_limit_list_d()
    # 在这里添加其他表的注册
    # register_other_table()


# 模块加载时自动注册所有表
register_all_tables()
