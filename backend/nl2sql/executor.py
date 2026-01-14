"""
查询执行器

负责执行SQL查询并格式化结果
"""
from typing import Dict, Any, List, Optional
from datetime import date, time, datetime, timedelta
from decimal import Decimal
from database.connection import db
from nl2sql.models import QuerySpec, QueryResult
from nl2sql.generator import generator
from nl2sql.registry import registry


class QueryExecutor:
    """
    查询执行器

    执行QuerySpec并返回格式化的结果
    """

    def __init__(self):
        self.generator = generator
        self.db = db
        self.registry = registry

    def _serialize_value(self, value: Any) -> Any:
        """
        序列化值为JSON兼容类型

        将date、time、datetime、decimal、timedelta等类型转换为字符串或浮点数
        """
        if value is None:
            return None
        elif isinstance(value, (date, datetime)):
            return value.strftime("%Y-%m-%d")
        elif isinstance(value, time):
            return value.strftime("%H:%M:%S")
        elif isinstance(value, timedelta):
            # 将timedelta转换为总秒数
            return value.total_seconds()
        elif isinstance(value, Decimal):
            return float(value)
        else:
            return value

    def _serialize_data(self, data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        序列化查询结果中的所有值

        确保所有值都是JSON可序列化的
        """
        if not data:
            return []

        serialized = []
        for row in data:
            serialized_row = {}
            for key, value in row.items():
                serialized_row[key] = self._serialize_value(value)
            serialized.append(serialized_row)

        return serialized

    def execute(self, query_spec: QuerySpec) -> QueryResult:
        """
        执行查询

        Args:
            query_spec: 查询规范

        Returns:
            QueryResult: 查询结果
        """
        try:
            # 生成SQL（值已内嵌）
            sql = self.generator.generate(query_spec)

            # 执行查询（不需要参数，值已在SQL中）
            data = self.db.execute_query(sql)

            # 序列化数据（处理date、time、decimal等类型）
            serialized_data = self._serialize_data(data)

            # 获取列名
            columns = []
            if serialized_data:
                columns = list(serialized_data[0].keys())

            # 获取总数（如果需要分页）
            total = len(serialized_data) if serialized_data else 0

            return QueryResult(
                success=True,
                data=serialized_data,
                sql=sql,
                total=total,
                columns=columns
            )

        except Exception as e:
            return QueryResult(
                success=False,
                error=str(e),
                sql=sql if 'sql' in locals() else None
            )

    def execute_with_explanation(self, query_spec: QuerySpec) -> Dict[str, Any]:
        """
        执行查询并生成可读的结果说明

        Returns:
            包含查询结果和人类可读说明的字典
        """
        # 执行查询
        result = self.execute(query_spec)

        if not result.success:
            return {
                "success": False,
                "error": result.error,
                "sql": result.sql
            }

        # 获取表元数据
        table = self.registry.get_table(query_spec.table)

        # 生成说明
        explanation = self._generate_explanation(query_spec, result, table)

        return {
            "success": True,
            "data": result.data,
            "sql": result.sql,
            "total": result.total,
            "columns": result.columns,
            "explanation": explanation,
            "query_type": query_spec.query_type
        }

    def _generate_explanation(self, query_spec: QuerySpec, result: QueryResult, table) -> str:
        """生成查询结果的人类可读说明"""
        parts = []

        # 查询类型说明
        if query_spec.query_type == "list":
            parts.append(f"📊 查询{table.display_name}列表")

        elif query_spec.query_type == "stats":
            parts.append(f"📈 统计{table.display_name}数据")

        # 过滤条件说明
        if query_spec.filters:
            filter_desc = self._describe_filters(query_spec.filters, table)
            if filter_desc:
                parts.append(f"🔍 筛选条件: {filter_desc}")

        # 结果说明
        if result.data:
            parts.append(f"✅ 查询成功，共 {result.total} 条记录")
        else:
            parts.append("⚠️ 查询成功，但没有找到符合条件的数据")

        # 统计结果说明
        if query_spec.query_type == "stats" and result.data:
            stats_desc = self._describe_stats_result(result.data, query_spec)
            if stats_desc:
                parts.append(f"📋 统计结果:\n{stats_desc}")

        return "\n".join(parts)

    def _describe_filters(self, filters, table) -> str:
        """描述过滤条件"""
        conditions = []

        # 日期范围
        if filters.date_range:
            if filters.date_range.relative:
                conditions.append(f"日期: {filters.date_range.relative}")
            elif filters.date_range.start or filters.date_range.end:
                date_parts = []
                if filters.date_range.start:
                    date_parts.append(f"{filters.date_range.start}之后")
                if filters.date_range.end:
                    date_parts.append(f"{filters.date_range.end}之前")
                conditions.append("日期: " + "到".join(date_parts))

        # 股票代码
        if filters.stocks:
            count = len(filters.stocks)
            if count <= 3:
                conditions.append(f"股票: {', '.join(filters.stocks)}")
            else:
                conditions.append(f"股票: {filters.stocks[0]}等{count}只")

        # 行业
        if filters.industries:
            conditions.append(f"行业: {', '.join(filters.industries)}")

        # 其他条件
        if filters.conditions:
            for cond in filters.conditions:
                field_meta = table.get_field(cond.field)
                field_name = field_meta.display_name if field_meta else cond.field
                conditions.append(f"{field_name} {cond.operator} {cond.value}")

        return "; ".join(conditions)

    def _describe_stats_result(self, data: List[Dict], query_spec: QuerySpec) -> str:
        """描述统计结果"""
        if not data:
            return ""

        lines = []
        for i, row in enumerate(data[:5], 1):  # 最多显示5条
            parts = []
            for key, value in row.items():
                # 格式化数值
                if isinstance(value, float):
                    if value > 1000000:  # 大数字显示为万/亿
                        value = f"{value/100000000:.2f}亿"
                    else:
                        value = f"{value:.2f}"
                parts.append(f"{key}: {value}")
            lines.append(f"  {i}. {' | '.join(parts)}")

        result = "\n".join(lines)
        if len(data) > 5:
            result += f"\n  ... (共{len(data)}条)"

        return result

    def test_connection(self) -> bool:
        """测试数据库连接"""
        return self.db.test_connection()

    def get_table_schema(self, table_name: str) -> Optional[Dict[str, Any]]:
        """获取表结构信息（用于LLM理解）"""
        table = self.registry.get_table(table_name)
        if not table:
            return None

        fields_info = []
        for field_name, field_meta in table.fields.items():
            fields_info.append({
                "name": field_name,
                "display_name": field_meta.display_name,
                "type": field_meta.type.value,
                "description": field_meta.description,
                "example_values": field_meta.example_values
            })

        return {
            "table_name": table.table_name,
            "display_name": table.display_name,
            "description": table.description,
            "fields": fields_info
        }

    def list_available_tables(self) -> List[Dict[str, Any]]:
        """列出所有可用的表（用于LLM理解）"""
        tables_info = []
        for table_name in self.registry.list_tables():
            table = self.registry.get_table(table_name)
            tables_info.append({
                "table_name": table.table_name,
                "display_name": table.display_name,
                "description": table.description
            })
        return tables_info


# 全局查询执行器实例
executor = QueryExecutor()
