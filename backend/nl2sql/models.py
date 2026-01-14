"""
QuerySpec数据模型定义
"""
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any, Literal
from enum import Enum


class QueryType(Enum):
    """查询类型枚举"""
    LIST = "list"       # 列表查询
    STATS = "stats"     # 统计查询
    DETAIL = "detail"   # 详情查询


class AggFunction(Enum):
    """聚合函数枚举"""
    COUNT = "count"
    SUM = "sum"
    AVG = "avg"
    MAX = "max"
    MIN = "min"


class Operator(Enum):
    """操作符枚举"""
    GT = ">"          # 大于
    GTE = ">="        # 大于等于
    LT = "<"          # 小于
    LTE = "<="        # 小于等于
    EQ = "="          # 等于
    NEQ = "!="        # 不等于
    LIKE = "LIKE"     # 模糊匹配
    IN = "IN"         # 包含于
    IS_NULL = "IS NULL"
    IS_NOT_NULL = "IS NOT NULL"


@dataclass
class DateRange:
    """日期范围条件"""
    start: Optional[str] = None      # 开始日期 YYYY-MM-DD
    end: Optional[str] = None        # 结束日期 YYYY-MM-DD
    relative: Optional[str] = None   # 相对日期: today, yesterday, last_week, last_month


@dataclass
class Condition:
    """查询条件"""
    field: str                       # 字段名
    operator: str                    # 操作符
    value: Optional[Any] = None      # 值
    values: Optional[List[Any]] = None  # 值列表（用于IN操作符）


@dataclass
class FilterSpec:
    """过滤器规范"""
    date_range: Optional[DateRange] = None
    stocks: Optional[List[str]] = None        # 股票代码列表
    industries: Optional[List[str]] = None    # 行业列表
    conditions: Optional[List[Condition]] = None  # 其他条件列表


@dataclass
class Metric:
    """聚合指标"""
    field: str                 # 字段名
    agg_func: str              # 聚合函数
    alias: str                 # 别名


@dataclass
class AggregationSpec:
    """聚合规范"""
    group_by: Optional[List[str]] = None  # 分组字段
    metrics: Optional[List[Metric]] = None  # 聚合指标列表


@dataclass
class SortSpec:
    """排序规范"""
    field: str                 # 字段名
    order: str = "desc"        # 排序方向: asc, desc


@dataclass
class PaginationSpec:
    """分页规范"""
    page: int = 1              # 页码（从1开始）
    page_size: int = 20        # 每页数量


@dataclass
class QuerySpec:
    """
    查询规范（QuerySpec）- 核心数据结构

    这是LLM应该输出的结构化查询意图，后端根据此规范生成SQL
    """
    query_type: str                              # 查询类型: list, stats, detail
    table: str                                   # 表名
    filters: Optional[FilterSpec] = None         # 过滤条件
    aggregation: Optional[AggregationSpec] = None # 聚合配置（仅stats类型）
    sort: Optional[List[SortSpec]] = None        # 排序配置
    pagination: Optional[PaginationSpec] = None  # 分页配置

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        result = {
            "query_type": self.query_type,
            "table": self.table
        }

        if self.filters:
            filters_dict = {}
            if self.filters.date_range:
                filters_dict["date_range"] = {
                    "start": self.filters.date_range.start,
                    "end": self.filters.date_range.end,
                    "relative": self.filters.date_range.relative
                }
            if self.filters.stocks:
                filters_dict["stocks"] = self.filters.stocks
            if self.filters.industries:
                filters_dict["industries"] = self.filters.industries
            if self.filters.conditions:
                filters_dict["conditions"] = [
                    {"field": c.field, "operator": c.operator, "value": c.value, "values": c.values}
                    for c in self.filters.conditions
                ]
            result["filters"] = filters_dict

        if self.aggregation:
            agg_dict = {}
            if self.aggregation.group_by:
                agg_dict["group_by"] = self.aggregation.group_by
            if self.aggregation.metrics:
                agg_dict["metrics"] = [
                    {"field": m.field, "agg_func": m.agg_func, "alias": m.alias}
                    for m in self.aggregation.metrics
                ]
            result["aggregation"] = agg_dict

        if self.sort:
            result["sort"] = [
                {"field": s.field, "order": s.order}
                for s in self.sort
            ]

        if self.pagination:
            result["pagination"] = {
                "page": self.pagination.page,
                "page_size": self.pagination.page_size
            }

        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'QuerySpec':
        """从字典创建QuerySpec"""
        filters = None
        if data.get("filters"):
            filters_data = data["filters"]
            date_range = None
            if filters_data.get("date_range"):
                dr = filters_data["date_range"]
                date_range = DateRange(
                    start=dr.get("start"),
                    end=dr.get("end"),
                    relative=dr.get("relative")
                )

            conditions = None
            if filters_data.get("conditions"):
                conditions = [
                    Condition(
                        field=c["field"],
                        operator=c["operator"],
                        value=c.get("value"),
                        values=c.get("values")
                    )
                    for c in filters_data["conditions"]
                ]

            filters = FilterSpec(
                date_range=date_range,
                stocks=filters_data.get("stocks"),
                industries=filters_data.get("industries"),
                conditions=conditions
            )

        aggregation = None
        if data.get("aggregation"):
            agg_data = data["aggregation"]
            metrics = None
            if agg_data.get("metrics"):
                metrics = [
                    Metric(
                        field=m["field"],
                        agg_func=m["agg_func"],
                        alias=m["alias"]
                    )
                    for m in agg_data["metrics"]
                ]

            aggregation = AggregationSpec(
                group_by=agg_data.get("group_by"),
                metrics=metrics
            )

        sort = None
        if data.get("sort"):
            sort = [
                SortSpec(field=s["field"], order=s.get("order", "desc"))
                for s in data["sort"]
            ]

        pagination = None
        if data.get("pagination"):
            pag_data = data["pagination"]
            pagination = PaginationSpec(
                page=pag_data.get("page", 1),
                page_size=pag_data.get("page_size", 20)
            )

        return cls(
            query_type=data["query_type"],
            table=data["table"],
            filters=filters,
            aggregation=aggregation,
            sort=sort,
            pagination=pagination
        )


@dataclass
class QueryResult:
    """查询结果"""
    success: bool                           # 是否成功
    data: Optional[List[Dict[str, Any]]] = None  # 数据
    sql: Optional[str] = None               # 执行的SQL
    error: Optional[str] = None             # 错误信息
    total: Optional[int] = None             # 总记录数
    columns: Optional[List[str]] = None     # 列名
