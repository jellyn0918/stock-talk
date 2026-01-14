"""
NL2SQL模块 - 自然语言转SQL框架

这是一个可扩展的框架，用于将用户的自然语言查询转换为结构化的QuerySpec，
然后由后端安全地生成和执行SQL查询。

主要组件:
- models: QuerySpec数据模型
- registry: 表注册和元数据管理
- generator: SQL生成器
- executor: 查询执行器
"""
from nl2sql.models import (
    QuerySpec, QueryResult, QueryType,
    FilterSpec, Condition, DateRange,
    AggregationSpec, Metric, SortSpec, PaginationSpec
)
from nl2sql.registry import registry, TableRegistry, TableMetadata, FieldMetadata
from nl2sql.generator import generator, SQLGenerator
from nl2sql.executor import executor, QueryExecutor

__all__ = [
    # Models
    'QuerySpec', 'QueryResult', 'QueryType',
    'FilterSpec', 'Condition', 'DateRange',
    'AggregationSpec', 'Metric', 'SortSpec', 'PaginationSpec',

    # Registry
    'registry', 'TableRegistry', 'TableMetadata', 'FieldMetadata',

    # Generator
    'generator', 'SQLGenerator',

    # Executor
    'executor', 'QueryExecutor',
]
