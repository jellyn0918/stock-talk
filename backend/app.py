from flask import Flask, request, jsonify, Response, stream_with_context
from flask_cors import CORS
import openai
import json
import os
from datetime import datetime
from typing import List, Dict

# 导入NL2SQL模块
from nl2sql import QuerySpec, executor
from nl2sql.registry import registry

# 导入Vanna NL2SQL模块
from vanna_nl2sql import nl2sql_query

app = Flask(__name__)
CORS(app)

# 配置DeepSeek API
client = openai.OpenAI(
    api_key="sk-d5723e824a8b421ba055a52e8effdafc",
    base_url="https://api.deepseek.com"
)

# 存储对话历史（内存存储，生产环境应使用数据库）
conversations: Dict[str, List[Dict]] = {}

# ============== 系统提示词 ==============

STOCK_ANALYST_SYSTEM_PROMPT = """
你是一个专业的A股行情分析助手。你可以帮助用户查询和分析涨跌停板数据。

## 可用的数据表

### 表名: hq_stk_limit_list_d (涨跌停板数据表)
包含A股涨停和跌停股票的日线数据，记录了封板时间、封单金额、炸板次数等信息。
**重要**: 这张表同时包含涨停(U)和跌停(D)数据，需要根据用户问题自动过滤。

**主要字段:**
- 交易日期 (trade_date): 交易日期
- 股票代码 (ts_code): 股票代码，如 000001.SZ
- 股票名称 (name): 股票名称
- 行业 (industry): 所属行业
- 收盘价 (close): 当日收盘价
- 涨跌幅 (pct_chg): 涨跌幅百分比
- 成交额 (amount): 成交金额
- 板上成交金额 (limit_amount): 板上成交金额(成交价格为该股票跌停价的所有成交额的总和，涨停无此数据)
- 流通市值 (float_mv): 流通市值
- 总市值 (total_mv): 总市值
- 换手率 (turnover_ratio): 换手率百分比
- 封单金额 (fd_amount): 封单金额（以涨停价买入挂单的资金总量）
- 首次封板时间 (first_time): 首次封板时间（跌停无此数据）
- 最后封板时间 (last_time): 最后封板时间
- 炸板次数 (open_times): 炸板次数(跌停为开板次数)
- 涨停统计 (up_stat): 涨停统计（N/T T天有N次涨停）
- 连板数 (limit_times): 连板数（个股连续封板数量）
- 涨跌停标识 (limit_l): **D=跌停, U=涨停, Z=炸板**

## 工作流程

当用户询问关于涨跌停数据时，你需要：

1. **理解用户意图** - 分析用户想要查询什么数据
2. **判断涨跌停类型** - 根据用户问题自动添加对应的limit_l过滤条件
   - 用户问"涨停"、"涨停板"、"封板"等 → 添加 `limit_l = 'U'` 条件
   - 用户问"跌停"、"跌停板"等 → 添加 `limit_l = 'D'` 条件
   - 用户问"炸板" → 添加 `limit_l = 'Z'` 条件
   - 用户没有明确说明 → 不添加limit_l条件（返回所有数据）
3. **生成QuerySpec** - 输出一个JSON格式的QuerySpec结构
4. **返回给用户** - QuerySpec会由后端转换为SQL并执行查询

## QuerySpec格式规范

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
        "field": "open_times",
        "operator": "> | >= | < | <= | = | !=",
        "value": 0
      }
    ]
  },
  "aggregation": {
    "group_by": ["industry", "date"],
    "metrics": [
      {
        "field": "ts_code",
        "agg_func": "count | sum | avg | max | min",
        "alias": "涨停数量"
      }
    ]
  },
  "sort": [
    {
      "field": "fd_amount",
      "order": "desc | asc"
    }
  ],
  "pagination": {
    "page": 1,
    "page_size": 20
  }
}
```

## QueryType说明

- **list**: 列表查询 - 返回符合条件的数据列表
- **stats**: 统计查询 - 返回聚合统计结果（如按行业分组统计）
- **detail**: 详情查询 - 返回单条详细数据

## 示例

用户: "今天有哪些股票涨停了？"
回复:
```json
{
  "query_type": "list",
  "table": "hq_stk_limit_list_d",
  "filters": {
    "date_range": {"relative": "today"},
    "conditions": [
      {"field": "涨跌停标识", "operator": "=", "value": "U"}
    ]
  },
  "sort": [{"field": "封单金额", "order": "desc"}],
  "pagination": {"page": 1, "page_size": 20}
}
```

用户: "统计今天各行业的涨停数量"
回复:
```json
{
  "query_type": "stats",
  "table": "hq_stk_limit_list_d",
  "filters": {
    "date_range": {"relative": "today"},
    "conditions": [
      {"field": "涨跌停标识", "operator": "=", "value": "U"}
    ]
  },
  "aggregation": {
    "group_by": ["行业"],
    "metrics": [
      {"field": "股票代码", "agg_func": "count", "alias": "涨停数量"}
    ]
  }
}
```

用户: "封单金额超过1亿的涨停股"
回复:
```json
{
  "query_type": "list",
  "table": "hq_stk_limit_list_d",
  "filters": {
    "date_range": {"relative": "today"},
    "conditions": [
      {"field": "涨跌停标识", "operator": "=", "value": "U"},
      {"field": "封单金额", "operator": ">", "value": 100000000}
    ]
  },
  "sort": [{"field": "封单金额", "order": "desc"}]
}
```

用户: "今天有哪些股票跌停了？"
回复:
```json
{
  "query_type": "list",
  "table": "hq_stk_limit_list_d",
  "filters": {
    "date_range": {"relative": "today"},
    "conditions": [
      {"field": "涨跌停标识", "operator": "=", "value": "D"}
    ]
  },
  "sort": [{"field": "成交额", "order": "desc"}],
  "pagination": {"page": 1, "page_size": 20}
}
```

用户: "今天的涨跌停数据"
回复:
```json
{
  "query_type": "list",
  "table": "hq_stk_limit_list_d",
  "filters": {
    "date_range": {"relative": "today"}
  },
  "pagination": {"page": 1, "page_size": 20}
}
```

## 重要提醒

1. **涨跌停过滤**: 这张表包含涨停和跌停数据，必须根据用户问题自动添加limit_l条件
   - 问涨停相关 → 添加 `{"field": "涨跌停标识", "operator": "=", "value": "U"}`
   - 问跌停相关 → 添加 `{"field": "涨跌停标识", "operator": "=", "value": "D"}`
   - 问炸板相关 → 添加 `{"field": "涨跌停标识", "operator": "=", "value": "Z"}`
   - 用户没有明确说明 → 不添加limit_l条件

2. 字段名必须使用中文显示名称（如"封单金额"而不是"fd_amount"）
3. 日期可以使用relative字段：today, yesterday, last_week, last_month
4. 对于统计查询，必须包含aggregation配置
5. 数值字段（如金额）使用原始数字，不需要单位转换
6. 只返回JSON格式的QuerySpec，不要包含其他文字说明
"""

# ============== 路由定义 ==============

@app.route('/')
def home():
    return jsonify({
        "message": "A股行情分析助手 API",
        "version": "2.0",
        "features": ["自然语言查询", "涨停板数据分析", "实时对话"]
    })

@app.route('/api/tables', methods=['GET'])
def list_tables():
    """列出所有可用的数据表"""
    tables = executor.list_available_tables()
    return jsonify({"tables": tables})

@app.route('/api/tables/<table_name>/schema', methods=['GET'])
def get_table_schema(table_name: str):
    """获取表结构"""
    schema = executor.get_table_schema(table_name)
    if not schema:
        return jsonify({"error": f"表 '{table_name}' 不存在"}), 404
    return jsonify(schema)

@app.route('/api/query', methods=['POST'])
def execute_query():
    """
    执行NL2SQL查询

    前端需要先调用LLM获取QuerySpec，然后调用此接口执行
    """
    data = request.json
    query_spec_data = data.get('query_spec')

    if not query_spec_data:
        return jsonify({"error": "缺少query_spec参数"}), 400

    try:
        # 解析QuerySpec
        query_spec = QuerySpec.from_dict(query_spec_data)

        # 执行查询
        result = executor.execute_with_explanation(query_spec)

        return jsonify(result)

    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route('/api/chat/analyze', methods=['POST'])
def chat_analyze():
    """
    智能分析接口 - 集成NL2SQL的聊天接口

    这个接口会：
    1. 使用LLM理解用户意图并生成QuerySpec
    2. 执行数据库查询
    3. 使用LLM生成分析报告
    """
    data = request.json
    user_message = data.get('message', '').strip()

    if not user_message:
        return jsonify({"error": "消息不能为空"}), 400

    try:
        # 步骤1: 调用LLM生成QuerySpec
        print(f"\n{'='*60}")
        print(f"📝 用户问题: {user_message}")
        print(f"{'='*60}")

        query_spec_response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": STOCK_ANALYST_SYSTEM_PROMPT},
                {"role": "user", "content": user_message}
            ],
            temperature=0.1,  # 使用较低温度以获得更结构化的输出
            max_tokens=1500
        )

        response_text = query_spec_response.choices[0].message.content.strip()

        # 提取JSON（可能包含markdown代码块）
        if "```json" in response_text:
            response_text = response_text.split("```json")[1].split("```")[0].strip()
        elif "```" in response_text:
            response_text = response_text.split("```")[1].split("```")[0].strip()

        print(f"📋 LLM返回的QuerySpec:\n{response_text}")

        # 解析QuerySpec
        try:
            query_spec_data = json.loads(response_text)
            query_spec = QuerySpec.from_dict(query_spec_data)
        except json.JSONDecodeError:
            # 如果无法解析为QuerySpec，可能是普通对话
            print("⚠️  无法解析为QuerySpec，作为普通对话处理")
            return jsonify({
                "type": "chat",
                "message": response_text
            })

        # 步骤2: 执行查询
        query_result = executor.execute_with_explanation(query_spec)
        print(f"🔍 生成的SQL:\n{query_result.get('sql', 'N/A')}")
        print(f"📊 查询结果: {query_result.get('total', 0)} 条记录")

        if not query_result["success"]:
            return jsonify({
                "type": "error",
                "message": f"查询失败: {query_result['error']}"
            })

        # 步骤3: 生成分析报告
        analysis_prompt = f"""
基于以下查询结果，生成一份简洁的分析报告：

用户问题: {user_message}

查询结果:
{json.dumps(query_result['data'][:10], ensure_ascii=False, indent=2)}

查询说明: {query_result.get('explanation', '')}

请生成一份包含以下内容的分析报告：
1. 数据概览
2. 关键发现（2-3点）
3. 简短结论

要求：简洁专业，不超过200字。
"""

        analysis_response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": "你是一个专业的A股分析师，擅长数据分析和趋势解读。"},
                {"role": "user", "content": analysis_prompt}
            ],
            temperature=0.7,
            max_tokens=500
        )

        analysis_report = analysis_response.choices[0].message.content

        # 返回完整结果
        return jsonify({
            "type": "query_result",
            "query_spec": query_spec_data,
            "data": query_result["data"],
            "total": query_result["total"],
            "columns": query_result["columns"],
            "sql": query_result["sql"],
            "explanation": query_result.get("explanation", ""),
            "analysis": analysis_report
        })

    except Exception as e:
        print(f"Error in chat_analyze: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": f"分析失败: {str(e)}"}), 500

@app.route('/api/chat/vanna', methods=['POST'])
def chat_vanna():
    """
    基于 Vanna AI 的 NL2SQL 聊天接口

    这个接口使用 Vanna 框架：
    1. 直接从自然语言生成 SQL
    2. 执行查询
    3. 返回结果
    """
    import time
    data = request.json
    user_message = data.get('message', '').strip()

    if not user_message:
        return jsonify({"error": "消息不能为空"}), 400

    try:
        start_time = time.time()

        print(f"\n{'='*60}")
        print(f"📝 [VANNA] 用户问题: {user_message}")
        print(f"{'='*60}")

        # 使用 Vanna 进行 NL2SQL 查询
        result = nl2sql_query(user_message)

        elapsed_time = time.time() - start_time

        print(f"🔍 [VANNA] 生成的SQL:\n{result.get('sql', 'N/A')}")
        print(f"📊 [VANNA] 查询结果: {result.get('row_count', 0)} 条记录")
        print(f"⏱️  [VANNA] 总耗时: {elapsed_time:.2f}秒")
        print(f"{'='*60}\n")

        # 生成分析报告
        analysis_prompt = f"""
基于以下查询结果，生成一份简洁的分析报告：

用户问题: {user_message}

查询结果:
{json.dumps(result['data'][:10], ensure_ascii=False, indent=2)}

SQL语句:
{result['sql']}

请生成一份包含以下内容的分析报告：
1. 数据概览
2. 关键发现（2-3点）
3. 简短结论

要求：简洁专业，不超过200字。
"""

        analysis_response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": "你是一个专业的A股分析师，擅长数据分析和趋势解读。"},
                {"role": "user", "content": analysis_prompt}
            ],
            temperature=0.7,
            max_tokens=500
        )

        analysis_report = analysis_response.choices[0].message.content

        # 返回完整结果（包含调试信息）
        return jsonify({
            "type": "vanna_query_result",
            "question": result["question"],
            "sql": result["sql"],
            "data": result["data"],
            "columns": result["columns"],
            "row_count": result["row_count"],
            "analysis": analysis_report,
            "debug": {
                "elapsed_time": f"{elapsed_time:.2f}秒",
                "sql_length": len(result["sql"]),
                "columns": result["columns"]
            }
        })

    except Exception as e:
        print(f"Error in chat_vanna: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": f"Vanna 查询失败: {str(e)}"}), 500

@app.route('/api/chat/stream', methods=['POST'])
def chat_stream():
    """流式聊天响应（兼容原版对话）"""
    data = request.json
    user_message = data.get('message', '').strip()
    conversation_id = data.get('conversation_id', 'default')

    if not user_message:
        return jsonify({"error": "消息不能为空"}), 400

    if conversation_id not in conversations:
        conversations[conversation_id] = []

    conversations[conversation_id].append({
        "role": "user",
        "content": user_message
    })

    def generate():
        try:
            stream = client.chat.completions.create(
                model="deepseek-chat",
                messages=[
                    {"role": "system", "content": STOCK_ANALYST_SYSTEM_PROMPT},
                    *conversations[conversation_id]
                ],
                temperature=0.7,
                max_tokens=2000,
                stream=True
            )

            full_response = ""
            for chunk in stream:
                if chunk.choices[0].delta.content:
                    content = chunk.choices[0].delta.content
                    full_response += content
                    yield f"data: {json.dumps({'content': content})}\n\n"

            # 保存完整回复到历史
            conversations[conversation_id].append({
                "role": "assistant",
                "content": full_response
            })

            yield f"data: {json.dumps({'done': True})}\n\n"

        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

    return Response(stream_with_context(generate()), mimetype='text/event-stream')

# ============== 对话管理接口（保留原版）=============

@app.route('/api/conversations/<conversation_id>', methods=['GET'])
def get_conversation(conversation_id):
    """获取对话历史"""
    if conversation_id in conversations:
        return jsonify({
            "conversation_id": conversation_id,
            "messages": conversations[conversation_id]
        })
    return jsonify({"conversation_id": conversation_id, "messages": []})

@app.route('/api/conversations/<conversation_id>', methods=['DELETE'])
def delete_conversation(conversation_id):
    """删除对话"""
    if conversation_id in conversations:
        del conversations[conversation_id]
        return jsonify({"message": "对话已删除"})
    return jsonify({"error": "对话不存在"}), 404

@app.route('/api/conversations', methods=['GET'])
def list_conversations():
    """列出所有对话"""
    conversation_list = []
    for conv_id, messages in conversations.items():
        title = messages[0]['content'][:50] if messages else "新对话"
        conversation_list.append({
            "id": conv_id,
            "title": title,
            "message_count": len(messages)
        })
    return jsonify({"conversations": conversation_list})

@app.route('/api/conversations/new', methods=['POST'])
def new_conversation():
    """创建新对话"""
    import uuid
    new_id = str(uuid.uuid4())
    conversations[new_id] = []
    return jsonify({"conversation_id": new_id})

if __name__ == '__main__':
    print("🚀 A股行情分析助手 API 正在启动...")
    print("📊 支持NL2SQL查询")
    print("📡 API地址: http://localhost:5001")

    # 测试数据库连接
    if executor.test_connection():
        print("✅ 数据库连接成功")
    else:
        print("⚠️ 数据库连接失败")

    app.run(debug=True, host='0.0.0.0', port=5001)
