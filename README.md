# DeepSeek Chat - AI智能对话助手

一个简洁优雅的ChatGPT风格AI对话应用，使用DeepSeek API提供智能对话功能。

## 功能特性

- 🎨 ChatGPT风格界面设计
- 💬 实时流式对话响应
- 📝 多对话管理（新建、切换、删除）
- 📱 响应式设计，支持移动端
- 💾 对话历史记录
- 🎯 Markdown格式支持
- 💻 代码语法高亮

## 技术栈

**后端:**
- Python 3.8+
- Flask - Web框架
- OpenAI SDK - DeepSeek API集成

**前端:**
- HTML5/CSS3
- JavaScript (Vanilla)
- Marked.js - Markdown解析
- Highlight.js - 代码高亮

## 项目结构

```
stock-talk/
├── backend/
│   ├── app.py              # Flask后端服务
│   └── requirements.txt    # Python依赖
├── frontend/
│   ├── index.html          # 主页面
│   ├── style.css           # 样式文件
│   └── app.js              # 前端逻辑
└── README.md               # 项目说明
```

## 安装与运行

### 1. 安装后端依赖

```bash
cd backend
pip install -r requirements.txt
```

### 2. 启动后端服务

```bash
python app.py
```

后端服务将在 `http://localhost:5000` 启动

### 3. 打开前端页面

在浏览器中直接打开 `frontend/index.html` 文件

或者使用简单的HTTP服务器:

```bash
cd frontend
python -m http.server 8000
```

然后访问 `http://localhost:8000`

## 使用说明

1. **开始对话**: 在输入框中输入消息，按Enter或点击发送按钮
2. **新建对话**: 点击左侧边栏的"新建对话"按钮
3. **切换对话**: 点击左侧边栏的对话列表项
4. **删除对话**: 鼠标悬停在对话列表项上，点击删除按钮
5. **移动端**: 点击左上角菜单按钮打开/关闭侧边栏

## API接口

### POST /api/chat
发送消息并获取回复（非流式）

**请求:**
```json
{
  "message": "你好",
  "conversation_id": "uuid"
}
```

**响应:**
```json
{
  "message": "你好！有什么可以帮助你的吗？",
  "conversation_id": "uuid"
}
```

### POST /api/chat/stream
流式发送消息并获取回复（推荐）

**请求:**
```json
{
  "message": "你好",
  "conversation_id": "uuid"
}
```

**响应:** Server-Sent Events (SSE)

### GET /api/conversations
获取所有对话列表

### GET /api/conversations/{conversation_id}
获取指定对话的历史记录

### DELETE /api/conversations/{conversation_id}
删除指定对话

### POST /api/conversations/new
创建新对话

## 配置说明

DeepSeek API密钥已配置在 `backend/app.py` 中:

```python
client = openai.OpenAI(
    api_key="sk-d5723e824a8b421ba055a52e8effdafc",
    base_url="https://api.deepseek.com"
)
```

**⚠️ 注意:** 生产环境中应该使用环境变量存储API密钥

## 特性说明

### 对话历史
- 所有对话历史保存在后端内存中
- 重启服务后会清空历史记录
- 生产环境建议使用数据库持久化

### 流式响应
- 支持Server-Sent Events (SSE)
- 实时显示AI回复内容
- 提供更好的用户体验

### 代码高亮
- 自动识别编程语言
- 支持多种语言语法高亮
- GitHub Dark主题

## 浏览器兼容性

- Chrome 90+
- Firefox 88+
- Safari 14+
- Edge 90+

## 开发建议

### 生产环境部署

1. **使用环境变量管理API密钥**
```python
import os
client = openai.OpenAI(
    api_key=os.getenv('DEEPSEEK_API_KEY'),
    base_url="https://api.deepseek.com"
)
```

2. **使用数据库持久化对话**
- SQLite/PostgreSQL存储对话历史
- Redis缓存会话信息

3. **添加用户认证**
- JWT token认证
- 用户登录注册功能

4. **部署到生产服务器**
- 使用Nginx作为反向代理
- Gunicorn/uWSGI运行Flask应用
- Docker容器化部署

## 许可证

MIT License

## 贡献

欢迎提交Issue和Pull Request！

## 联系方式

如有问题，请提交Issue。
