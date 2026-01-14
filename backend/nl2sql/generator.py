"""
SQL生成器引擎

负责将QuerySpec转换为可执行的SQL语句
包含安全验证、字段映射、条件构建等功能
生成的SQL语句包含实际值，可以直接在数据库中执行
"""
from datetime import datetime, timedelta
from typing import List
from nl2sql.models import QuerySpec, QueryType
from nl2sql.registry import registry, TableMetadata


class SQLGenerator:
    """
    SQL生成器

    将QuerySpec转换为可执行的SQL查询语句
    所有字段都经过白名单验证，防止SQL注入
    生成的SQL包含实际值，可直接在数据库执行
    """

    # 允许的操作符白名单
    ALLOWED_OPERATORS = {">", ">=", "<", "<=", "=", "!=", "LIKE", "IN"}

    def __init__(self):
        self.registry = registry

    def generate(self, query_spec: QuerySpec) -> str:
        """
        生成SQL查询

        返回: 可直接执行的sql语句（值已内嵌）
        """
        # 验证表是否存在
        table = self.registry.get_table(query_spec.table)
        if not table:
            raise ValueError(f"表 '{query_spec.table}' 未注册")

        # 根据查询类型生成SQL
        if query_spec.query_type == QueryType.LIST.value:
            return self._generate_list_query(query_spec, table)
        elif query_spec.query_type == QueryType.STATS.value:
            return self._generate_stats_query(query_spec, table)
        elif query_spec.query_type == QueryType.DETAIL.value:
            return self._generate_detail_query(query_spec, table)
        else:
            raise ValueError(f"不支持的查询类型: {query_spec.query_type}")

    def _generate_list_query(self, query_spec: QuerySpec, table: TableMetadata) -> str:
        """生成列表查询SQL"""
        # SELECT子句
        select_fields = self._build_select_fields(table)

        # FROM子句
        from_clause = f"FROM {query_spec.table}"

        # WHERE子句（值已内嵌）
        where_clause = self._build_where_clause(query_spec, table)

        # ORDER BY子句
        order_clause = self._build_order_clause(query_spec, table)

        # LIMIT子句
        limit_clause = self._build_limit_clause(query_spec)

        # 组装SQL
        sql_parts = [f"SELECT {select_fields}", from_clause]
        if where_clause:
            sql_parts.append(where_clause)
        if order_clause:
            sql_parts.append(order_clause)
        if limit_clause:
            sql_parts.append(limit_clause)

        return " ".join(sql_parts)

    def _generate_stats_query(self, query_spec: QuerySpec, table: TableMetadata) -> str:
        """生成统计查询SQL"""
        if not query_spec.aggregation or not query_spec.aggregation.metrics:
            raise ValueError("统计查询必须包含聚合指标")

        # SELECT子句（聚合）
        select_parts = []
        if query_spec.aggregation.group_by:
            # 分组字段
            for field in query_spec.aggregation.group_by:
                db_field = table.get_db_field_name(field)
                if not db_field:
                    raise ValueError(f"无效的分组字段: {field}")
                select_parts.append(f"`{db_field}`")

        # 聚合指标
        for metric in query_spec.aggregation.metrics:
            db_field = table.get_db_field_name(metric.field)
            if not db_field:
                raise ValueError(f"无效的聚合字段: {metric.field}")

            agg_func = metric.agg_func.upper()
            if agg_func not in {"COUNT", "SUM", "AVG", "MAX", "MIN"}:
                raise ValueError(f"不支持的聚合函数: {metric.agg_func}")

            select_parts.append(f"{agg_func}(`{db_field}`) as `{metric.alias}`")

        select_clause = ", ".join(select_parts)

        # FROM子句
        from_clause = f"FROM {query_spec.table}"

        # WHERE子句
        where_clause = self._build_where_clause(query_spec, table)

        # GROUP BY子句
        group_clause = ""
        if query_spec.aggregation.group_by:
            group_fields = []
            for field in query_spec.aggregation.group_by:
                db_field = table.get_db_field_name(field)
                group_fields.append(f"`{db_field}`")
            group_clause = f"GROUP BY {', '.join(group_fields)}"

        # ORDER BY子句
        order_clause = ""
        if query_spec.sort:
            order_parts = []
            for sort_spec in query_spec.sort:
                db_field = table.get_db_field_name(sort_spec.field)
                if not db_field:
                    continue
                order = sort_spec.order.upper() if sort_spec.order.upper() in ["ASC", "DESC"] else "DESC"
                order_parts.append(f"{db_field} {order}")
            if order_parts:
                order_clause = "ORDER BY " + ", ".join(order_parts)

        # LIMIT子句
        limit_clause = self._build_limit_clause(query_spec)

        # 组装SQL
        sql_parts = [f"SELECT {select_clause}", from_clause]
        if where_clause:
            sql_parts.append(where_clause)
        if group_clause:
            sql_parts.append(group_clause)
        if order_clause:
            sql_parts.append(order_clause)
        if limit_clause:
            sql_parts.append(limit_clause)

        return " ".join(sql_parts)

    def _generate_detail_query(self, query_spec: QuerySpec, table: TableMetadata) -> str:
        """生成详情查询SQL"""
        return self._generate_list_query(query_spec, table)

    def _build_select_fields(self, table: TableMetadata) -> str:
        """构建SELECT字段"""
        fields = []
        for field_name, field_meta in table.fields.items():
            # 给字段名和别名都加反引号，避免保留字冲突
            fields.append(f"`{field_name}` as `{field_meta.display_name}`")
        return ", ".join(fields)

    def _build_where_clause(self, query_spec: QuerySpec, table: TableMetadata) -> str:
        """构建WHERE子句（值已内嵌）"""
        conditions = []

        if not query_spec.filters:
            return ""

        # 1. 日期范围条件
        if query_spec.filters.date_range:
            date_condition = self._build_date_condition(
                query_spec.filters.date_range, table
            )
            if date_condition:
                conditions.append(date_condition)

        # 2. 股票代码条件
        if query_spec.filters.stocks:
            db_field = table.get_db_field_name("股票代码")
            if db_field:
                values = ", ".join([f"'{self._escape_string(s)}'" for s in query_spec.filters.stocks])
                conditions.append(f"`{db_field}` IN ({values})")

        # 3. 行业条件
        if query_spec.filters.industries:
            db_field = table.get_db_field_name("行业")
            if db_field:
                values = ", ".join([f"'{self._escape_string(s)}'" for s in query_spec.filters.industries])
                conditions.append(f"`{db_field}` IN ({values})")

        # 4. 其他条件
        if query_spec.filters.conditions:
            for cond in query_spec.filters.conditions:
                cond_sql = self._build_condition(cond, table)
                if cond_sql:
                    conditions.append(cond_sql)

        if not conditions:
            return ""

        return "WHERE " + " AND ".join(conditions)

    def _build_date_condition(self, date_range, table: TableMetadata) -> str:
        """构建日期条件（值已内嵌）"""
        db_field = table.get_db_field_name("交易日期")
        if not db_field:
            return ""

        conditions = []

        # 处理相对日期
        if date_range.relative:
            resolved_dates = self._resolve_relative_date(date_range.relative)
            if resolved_dates.get("start"):
                conditions.append(f"`{db_field}` >= '{resolved_dates['start']}'")
            if resolved_dates.get("end"):
                conditions.append(f"`{db_field}` <= '{resolved_dates['end']}'")

        # 处理绝对日期
        if date_range.start:
            conditions.append(f"`{db_field}` >= '{date_range.start}'")

        if date_range.end:
            conditions.append(f"`{db_field}` <= '{date_range.end}'")

        if not conditions:
            return ""

        return " AND ".join(conditions)

    def _build_condition(self, condition, table: TableMetadata) -> str:
        """构建单个条件（值已内嵌）"""
        db_field = table.get_db_field_name(condition.field)
        if not db_field:
            raise ValueError(f"字段 '{condition.field}' 不存在于表中")

        operator = condition.operator.upper()
        if operator not in self.ALLOWED_OPERATORS:
            raise ValueError(f"不支持的操作符: {condition.operator}")

        if operator == "IN":
            if not condition.values:
                raise ValueError(f"IN操作符需要提供values参数")
            escaped_values = [f"'{self._escape_string(v)}'" for v in condition.values]
            values_str = ", ".join(escaped_values)
            return f"`{db_field}` IN ({values_str})"

        elif operator == "LIKE":
            escaped_value = self._escape_string(condition.value)
            return f"`{db_field}` LIKE '%{escaped_value}%'"

        elif operator in {"IS NULL", "IS NOT NULL"}:
            return f"`{db_field}` {operator}"

        else:
            # 数值或字符串比较
            formatted_value = self._format_value(condition.value)
            return f"`{db_field}` {operator} {formatted_value}"

    def _build_order_clause(self, query_spec: QuerySpec, table: TableMetadata) -> str:
        """构建ORDER BY子句"""
        if not query_spec.sort:
            # 默认按日期降序
            date_field = table.get_db_field_name("交易日期")
            if date_field:
                return f"ORDER BY `{date_field}` DESC"
            return ""

        order_parts = []
        for sort_spec in query_spec.sort:
            db_field = table.get_db_field_name(sort_spec.field)
            if not db_field:
                continue

            order = sort_spec.order.upper() if sort_spec.order.upper() in ["ASC", "DESC"] else "DESC"
            order_parts.append(f"`{db_field}` {order}")

        if not order_parts:
            return ""

        return "ORDER BY " + ", ".join(order_parts)

    def _build_limit_clause(self, query_spec: QuerySpec) -> str:
        """构建LIMIT子句"""
        if not query_spec.pagination:
            return "LIMIT 100"  # 默认限制

        page = query_spec.pagination.page
        page_size = query_spec.pagination.page_size
        offset = (page - 1) * page_size

        return f"LIMIT {page_size} OFFSET {offset}"

    def _resolve_relative_date(self, relative: str) -> dict:
        """解析相对日期"""
        today = datetime.now().date()
        result = {}

        if relative == "today":
            result["start"] = today.strftime("%Y-%m-%d")
            result["end"] = today.strftime("%Y-%m-%d")

        elif relative == "yesterday":
            yesterday = today - timedelta(days=1)
            result["start"] = yesterday.strftime("%Y-%m-%d")
            result["end"] = yesterday.strftime("%Y-%m-%d")

        elif relative == "last_week":
            week_ago = today - timedelta(days=7)
            result["start"] = week_ago.strftime("%Y-%m-%d")
            result["end"] = today.strftime("%Y-%m-%d")

        elif relative == "last_month":
            month_ago = today - timedelta(days=30)
            result["start"] = month_ago.strftime("%Y-%m-%d")
            result["end"] = today.strftime("%Y-%m-%d")

        return result

    def _format_value(self, value) -> str:
        """
        格式化值用于SQL

        数值直接返回，字符串用引号包裹并转义
        """
        if value is None:
            return "NULL"
        elif isinstance(value, (int, float)):
            return str(value)
        elif isinstance(value, bool):
            return "1" if value else "0"
        else:
            # 字符串：转义并添加引号
            escaped = self._escape_string(str(value))
            return f"'{escaped}'"

    def _escape_string(self, value: str) -> str:
        """
        转义字符串用于SQL

        防止SQL注入
        """
        if not isinstance(value, str):
            value = str(value)

        # 转义特殊字符
        value = value.replace("\\", "\\\\")
        value = value.replace("'", "\\'")
        value = value.replace('"', '\\"')
        value = value.replace("\n", "\\n")
        value = value.replace("\r", "\\r")
        value = value.replace("\x00", "\\x00")

        return value


# 全局SQL生成器实例
generator = SQLGenerator()
