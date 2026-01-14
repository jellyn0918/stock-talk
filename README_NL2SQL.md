# A股行情分析助手 - NL2SQL框架

基于DeepSeek AI的A股涨停板数据查询分析助手，采用NL2SQL架构。

## 🎯 核心特性

- **自然语言查询**: 用中文直接询问股票数据
- **结构化意图提取**: LLM只输出QuerySpec，不直接生成SQL
- **安全可控**: 后端硬编码SQL生成，完全避免SQL注入
- **框架化设计**: 易于添加新表和新功能
- **智能分析**: 自动生成数据洞察报告

## 📁 项目结构

```
stock-talk/
├── backend/
│   ├── database/              # 数据库模块
│   │   ├── config.py          # 数据库配置
│   │   ├── connection.py      # 连接管理
│   │   └── __init__.py
│   ├── nl2sql/                # NL2SQL框架
│   │   ├── models.py          # QuerySpec数据模型
│   │   ├── registry.py        # 表注册和元数据管理
│   │   ├── generator.py       # SQL生成器
│   │   ├── executor.py        # 查询执行器
│   │   └── __init__.py
│   ├── app.py                 # Flask API服务
│   └── requirements.txt       # Python依赖
├── frontend/
│   ├── index.html             # 主页面
│   ├── style.css              # 样式文件
│   └── app.js                 # 前端逻辑（支持数据表格）
└── README.md
```

## 🏗️ NL2SQL架构

### 工作流程

```
用户输入
    ↓
LLM理解意图
    ↓
生成QuerySpec (JSON)
    ↓
后端接收QuerySpec
    ↓
安全验证（字段白名单、操作符白名单）
    ↓
硬编码SQL生成
    ↓
参数化查询执行
    ↓
返回数据 + LLM生成分析报告
```

### QuerySpec结构

```json
{
  "query_type": "list | stats | detail",
  "table": "hq_stk_limit_list_d",
  "filters": {
    "date_range": {
      "start": "2024-01-01",
      "end": "2024-01-15",
      "relative": "today | yesterday | last_week | last_month"
    },
    "stocks": ["000001.SZ", "600000.SH"],
    "industries": ["半导体", "金融"],
    "conditions": [
      {
        "field": "涨跌停标识",
        "operator": "=",
        "value": "U"
      }
    ]
  },
  "aggregation": {
    "group_by": ["行业"],
    "metrics": [
      {
        "field": "股票代码",
        "agg_func": "count",
        "alias": "涨停数量"
      }
    ]
  },
  "sort": [{"field": "封单金额", "order": "desc"}],
  "pagination": {"page": 1, "page_size": 20}
}
```

## 📊 已注册数据表

### 涨跌停板数据表 (hq_stk_limit_list_d)

**重要提示**: 这张表包含涨停和跌停两种数据，查询时需要根据需求添加limit_l字段过滤条件。

**字段列表**:
- 交易日期、股票代码、股票名称、行业
- 收盘价、涨跌幅、成交额
- 板上成交金额、流通市值、总市值、换手率
- 封单金额、首次封板时间、最后封板时间
- 炸板次数、涨停统计、连板数
- **涨跌停标识 (limit_l)**: D=跌停, U=涨停, Z=炸板

## 🔌 API接口

### 1. 智能分析接口
```
POST /api/chat/analyze
Content-Type: application/json

{
  "message": "今天有哪些股票涨停了？"
}

返回: {
  "type": "query_result",
  "data": [...],
  "total": 10,
  "sql": "...",
  "analysis": "数据概览和分析..."
}
```

### 2. 获取表列表
```
GET /api/tables

返回: {
  "tables": [
    {
      "table_name": "hq_stk_limit_list_d",
      "display_name": "涨停板数据表",
      "description": "..."
    }
  ]
}
```

### 3. 获取表结构
```
GET /api/tables/{table_name}/schema

返回: {
  "table_name": "...",
  "fields": [...]
}
```

### 4. 直接查询接口
```
POST /api/query
Content-Type: application/json

{
  "query_spec": {...}
}
```

## 🚀 快速启动

### 1. 安装依赖

```bash
cd backend
pip install -r requirements.txt
```

### 2. 启动后端

```bash
python app.py
```

后端运行在: http://localhost:5001

### 3. 启动前端

```bash
cd frontend
python -m http.server 8001
```

前端访问: http://localhost:8001

## 📝 查询示例

### 基础查询
- "今天有哪些股票涨停了？" → 自动添加 limit_l='U'
- "今天有哪些股票跌停了？" → 自动添加 limit_l='D'
- "昨天半导体行业的涨停股" → 自动添加 limit_l='U'
- "最近的涨跌停数据" → 不添加limit_l条件

### 统计查询
- "统计今天各行业的涨停数量" → 自动添加 limit_l='U'
- "统计今天跌停股票的行业分布" → 自动添加 limit_l='D'
- "按行业统计平均封单金额" → 不添加limit_l条件

### 条件查询
- "封单金额超过1亿的涨停股" → 自动添加 limit_l='U'
- "炸板次数超过2次的股票" → 不添加limit_l条件
- "换手率超过20%的涨停股" → 自动添加 limit_l='U'

## 🔧 添加新表

### 1. 在 `nl2sql/registry.py` 中注册表

```python
def register_your_table():
    fields = {
        "field_name": FieldMetadata(
            name="field_name",
            display_name="显示名称",
            type=FieldType.STRING,
            description="字段描述",
            sortable=True,
            filterable=True,
            aggregatable=False
        ),
        # ... 更多字段
    }

    table_metadata = TableMetadata(
        table_name="your_table",
        display_name="你的表",
        description="表描述",
        fields=fields
    )

    registry.register_table(table_metadata)
```

### 2. 在系统提示词中添加表说明

编辑 `app.py` 中的 `STOCK_ANALYST_SYSTEM_PROMPT`，添加新表的字段说明。

## 🛡️ 安全机制

1. **字段白名单**: 只能查询预定义的字段
2. **操作符白名单**: 只允许安全的操作符
3. **参数化查询**: 防止SQL注入
4. **类型校验**: 严格检查数据类型
5. **表名验证**: 只能访问注册的表

## 🎨 前端特性

- ChatGPT风格界面
- 实时数据表格展示
- 自动格式化数值（亿、万）
- SQL语句预览
- 分析报告展示
- 响应式设计

## 📈 性能优化

- 数据库连接池管理
- 查询结果分页
- 前端虚拟滚动（TODO）
- 查询缓存（TODO）

## 🔄 未来扩展

- [ ] 支持多表关联查询
- [ ] 添加图表可视化
- [ ] 导出查询结果
- [ ] 历史查询记录
- [ ] 自定义指标计算
- [ ] 实时数据推送

## 📄 License

MIT License
