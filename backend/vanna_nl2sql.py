"""
基于 Vanna AI 的 NL2SQL 模块
使用 RAG 技术从自然语言生成 SQL 查询
"""
import vanna
from database.config import db_config
import pymysql
import openai


class StockVanna:
    """自定义 Vanna 类，用于股票数据查询"""

    def __init__(self, api_key, model='deepseek-chat'):
        """
        初始化 Vanna

        Args:
            api_key: DeepSeek API 密钥
            model: 使用的模型名称
        """
        # 保存配置
        self.api_key = api_key
        self.model = model
        self._is_trained = False
        self._ddl = []
        self._doc = []
        self._sql_pairs = []

        # 初始化数据库连接
        self.db_config = db_config

        # 初始化 OpenAI 客户端
        self.client = openai.OpenAI(
            api_key=api_key,
            base_url="https://api.deepseek.com"
        )

    def get_connection(self):
        """获取数据库连接"""
        return pymysql.connect(
            host=self.db_config.host,
            port=self.db_config.port,
            user=self.db_config.user,
            password=self.db_config.password,
            database=self.db_config.database,
            charset=self.db_config.charset,
            cursorclass=pymysql.cursors.DictCursor
        )

    def train(self, ddl=None, documentation=None, question=None, sql=None):
        """训练 Vanna"""
        if ddl:
            self._ddl.append(ddl)
        if documentation:
            self._doc.append(documentation)
        if question and sql:
            self._sql_pairs.append((question, sql))

    def train_with_ddl(self):
        """使用 DDL 训练 Vanna"""
        ddl_info = """
        -- 涨跌停板数据表
        CREATE TABLE hq_stk_limit_list_d (
            trade_date VARCHAR(8) COMMENT '交易日期',
            ts_code VARCHAR(10) COMMENT '股票代码',
            name VARCHAR(20) COMMENT '股票名称',
            industry VARCHAR(20) COMMENT '所属行业',
            close DECIMAL(10,2) COMMENT '收盘价',
            pct_chg DECIMAL(10,2) COMMENT '涨跌幅(%)',
            amount DECIMAL(20,2) COMMENT '成交额(元)',
            limit_amount DECIMAL(20,2) COMMENT '板上成交金额(元)',
            float_mv DECIMAL(20,2) COMMENT '流通市值(元)',
            total_mv DECIMAL(20,2) COMMENT '总市值(元)',
            turnover_ratio DECIMAL(10,2) COMMENT '换手率(%)',
            fd_amount DECIMAL(20,2) COMMENT '封单金额(元)',
            first_time VARCHAR(5) COMMENT '首次封板时间',
            last_time VARCHAR(5) COMMENT '最后封板时间',
            open_times INT COMMENT '炸板次数',
            up_stat VARCHAR(10) COMMENT '涨停统计(N/T T天有N次涨停)',
            limit_times INT COMMENT '连板数',
            limit_l VARCHAR(1) COMMENT '涨跌停标识(D=跌停, U=涨停, Z=炸板)',
            PRIMARY KEY (trade_date, ts_code)
        ) COMMENT='A股涨跌停板日线数据表';

        -- 重要字段说明
        -- limit_l: D表示跌停, U表示涨停, Z表示炸板
        -- fd_amount: 封单金额，以涨停价买入挂单的资金总量
        -- open_times: 炸板次数，涨停打开的次数；跌停时为开板次数
        -- limit_times: 连板数，连续涨停的天数
        """

        self.train(ddl=ddl_info)
        print("✅ DDL 训练完成")

    def train_with_documentation(self):
        """使用文档训练 Vanna"""
        documentation = """
        # 涨跌停板数据查询业务说明

        ## 表名: hq_stk_limit_list_d
        包含A股涨停、跌停、炸板股票的日线数据。

        ## 关键字段说明

        1. **limit_l (涨跌停标识)**: 最重要的过滤字段
           - 'U' = 涨停
           - 'D' = 跌停
           - 'Z' = 炸板（曾经涨停但打开）

        2. **trade_date (交易日期)**: 格式为 '20240101' 这样的字符串

        3. **fd_amount (封单金额)**: 以涨停价买入挂单的资金总量，单位元
           - 数值越大，封板越强
           - 跌停时无此数据

        4. **open_times (炸板次数)**: 涨停打开的次数
           - 0 表示一次封死，没有打开
           - 数值越大，封板越弱

        5. **limit_times (连板数)**: 连续涨停的天数
           - 1 表示首次涨停
           - 2 表示二连板，以此类推

        6. **industry (行业)**: 股票所属行业
           - 常见值: 半导体、金融、医药、房地产等

        ## 常见查询模式

        1. **查询某日的涨停股**: WHERE limit_l = 'U' AND trade_date = '20240101'
        2. **查询某日封单金额超1亿的涨停股**: WHERE limit_l = 'U' AND fd_amount > 100000000
        3. **统计某日各行业涨停数量**: GROUP BY industry WHERE limit_l = 'U'
        4. **查询连板股**: WHERE limit_times >= 2 AND limit_l = 'U'
        5. **查询一次封板的股票**: WHERE open_times = 0 AND limit_l = 'U'

        ## 注意事项
        - 金额字段单位是"元"，不是"万"或"亿"
        - 日期是字符串格式，需要用单引号
        - 查询涨停或跌停时，务必添加 limit_l 条件
        - 封单金额、板上成交金额等字段只在涨停时有数据
        """

        self.train(documentation=documentation)
        print("✅ 文档训练完成")

    def train_with_sql_pairs(self):
        """使用 SQL 对训练 Vanna"""
        sql_pairs = [
            ("今天有哪些股票涨停了？",
             """
             SELECT ts_code, name, industry, close, pct_chg, fd_amount, limit_times
             FROM hq_stk_limit_list_d
             WHERE limit_l = 'U'
             ORDER BY fd_amount DESC
             LIMIT 20
             """),

            ("统计今天各行业的涨停数量",
             """
             SELECT industry, COUNT(*) as 涨停数量, AVG(fd_amount) as 平均封单金额
             FROM hq_stk_limit_list_d
             WHERE limit_l = 'U'
             GROUP BY industry
             ORDER BY 涨停数量 DESC
             """),

            ("封单金额超过1亿的涨停股",
             """
             SELECT ts_code, name, industry, fd_amount, close, pct_chg, limit_times
             FROM hq_stk_limit_list_d
             WHERE limit_l = 'U' AND fd_amount > 100000000
             ORDER BY fd_amount DESC
             """),

            ("今天有哪些股票跌停了？",
             """
             SELECT ts_code, name, industry, close, pct_chg, amount, open_times
             FROM hq_stk_limit_list_d
             WHERE limit_l = 'D'
             ORDER BY amount DESC
             LIMIT 20
             """),

            ("查询二连板及以上的股票",
             """
             SELECT ts_code, name, industry, limit_times, fd_amount, close, pct_chg
             FROM hq_stk_limit_list_d
             WHERE limit_l = 'U' AND limit_times >= 2
             ORDER BY limit_times DESC, fd_amount DESC
             """),

            ("一次封死没有打开的涨停股",
             """
             SELECT ts_code, name, industry, fd_amount, close, pct_chg, first_time
             FROM hq_stk_limit_list_d
             WHERE limit_l = 'U' AND open_times = 0
             ORDER BY fd_amount DESC
             LIMIT 20
             """),

            ("半导体行业今天的涨停股",
             """
             SELECT ts_code, name, close, pct_chg, fd_amount, limit_times
             FROM hq_stk_limit_list_d
             WHERE limit_l = 'U' AND industry = '半导体'
             ORDER BY fd_amount DESC
             """),

            ("今天炸板的股票",
             """
             SELECT ts_code, name, industry, open_times, close, pct_chg
             FROM hq_stk_limit_list_d
             WHERE limit_l = 'Z'
             ORDER BY open_times DESC
             LIMIT 20
             """),
        ]

        for question, sql in sql_pairs:
            self.train(question=question, sql=sql)

        print("✅ SQL 对训练完成")

    def train_all(self):
        """执行所有训练"""
        print("🔧 开始训练 Vanna...")
        self.train_with_ddl()
        self.train_with_documentation()
        self.train_with_sql_pairs()
        self._is_trained = True
        print("✅ Vanna 训练完成！")

    def generate_sql(self, question: str) -> str:
        """
        从自然语言生成 SQL (使用 LLM)

        Args:
            question: 用户的自然语言问题

        Returns:
            生成的 SQL 查询语句
        """
        if not self._is_trained:
            print("⚠️  Vanna 尚未训练，自动开始训练...")
            self.train_all()

        print(f"\n[VANNA] 开始生成SQL...")
        print(f"[VANNA] 问题: {question}")

        # 构建提示词
        context_parts = []

        # 添加 DDL
        if self._ddl:
            context_parts.append("## 数据表结构\n" + "\n".join(self._ddl))

        # 添加文档
        if self._doc:
            context_parts.append("## 业务说明\n" + "\n".join(self._doc))

        # 添加示例
        if self._sql_pairs:
            examples = "\n".join([
                f"Q: {q}\nSQL: {s}\n"
                for q, s in self._sql_pairs[:5]  # 只使用前5个示例
            ])
            context_parts.append("## 查询示例\n" + examples)

        context = "\n\n".join(context_parts)

        prompt = f"""{context}

基于以上信息，将以下自然语言问题转换为SQL查询：

问题: {question}

请只返回SQL语句，不要包含任何解释或markdown标记。
"""

        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": "你是一个SQL专家。根据数据表结构和业务规则，将自然语言问题转换为准确的SQL查询。"
                },
                {"role": "user", "content": prompt}
            ],
            temperature=0.1,
            max_tokens=1000
        )

        sql = response.choices[0].message.content.strip()

        print(f"[VANNA] LLM原始返回:\n{sql}")

        # 清理可能的 markdown 标记
        if "```sql" in sql:
            sql = sql.split("```sql")[1].split("```")[0].strip()
        elif "```" in sql:
            sql = sql.split("```")[1].split("```")[0].strip()

        print(f"[VANNA] 清理后的SQL:\n{sql}\n")

        return sql

    def execute_sql(self, sql: str) -> list:
        """
        执行 SQL 查询并返回结果

        Args:
            sql: 要执行的 SQL 语句

        Returns:
            查询结果列表
        """
        import decimal

        def convert_decimal(obj):
            """转换 Decimal 为 float"""
            if isinstance(obj, decimal.Decimal):
                return float(obj)
            return obj

        conn = self.get_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute(sql)
                result = cursor.fetchall()

            # 转换 Decimal 类型
            converted_result = []
            for row in result:
                converted_row = {k: convert_decimal(v) for k, v in row.items()}
                converted_result.append(converted_row)

            return converted_result
        finally:
            conn.close()

    def ask_and_execute(self, question: str) -> dict:
        """
        从自然语言到执行结果的一站式查询

        Args:
            question: 用户的自然语言问题

        Returns:
            包含 SQL、结果和元数据的字典
        """
        # 生成 SQL
        sql = self.generate_sql(question)

        # 执行查询
        result = self.execute_sql(sql)

        # 获取列名
        columns = list(result[0].keys()) if result else []

        return {
            "question": question,
            "sql": sql,
            "data": result,
            "columns": columns,
            "row_count": len(result)
        }


# 创建全局 Vanna 实例
_vanna_instance = None


def get_vanna_instance():
    """获取 Vanna 单例实例"""
    global _vanna_instance
    if _vanna_instance is None:
        _vanna_instance = StockVanna(
            api_key="sk-d5723e824a8b421ba055a52e8effdafc",
            model="deepseek-chat"
        )
        # 自动训练
        _vanna_instance.train_all()
    return _vanna_instance


def nl2sql_query(question: str) -> dict:
    """
    NL2SQL 查询接口

    Args:
        question: 自然语言问题

    Returns:
        查询结果字典
    """
    # 获取 Vanna 单例实例（如果首次调用会自动初始化并训练）
    vanna = get_vanna_instance()
    # 调用 Vanna 生成 SQL 并执行查询，返回包含 SQL、数据、列名和行数的结果字典
    return vanna.ask_and_execute(question)
