// API配置
const API_BASE_URL = 'http://localhost:5001/api';

// 应用状态
let currentConversationId = null;
let conversations = [];

// DOM元素
const chatMessages = document.getElementById('chatMessages');
const messageInput = document.getElementById('messageInput');
const sendBtn = document.getElementById('sendBtn');
const newChatBtn = document.getElementById('newChatBtn');
const conversationsList = document.getElementById('conversationsList');
const menuToggle = document.getElementById('menuToggle');
const sidebar = document.getElementById('sidebar');

// 初始化
document.addEventListener('DOMContentLoaded', () => {
    initApp();
});

async function initApp() {
    // 加载对话列表
    await loadConversations();

    // 创建新对话
    await createNewConversation();

    // 设置事件监听
    setupEventListeners();
}

function setupEventListeners() {
    // 发送消息
    sendBtn.addEventListener('click', sendMessage);
    messageInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    });

    // 输入框自动调整高度
    messageInput.addEventListener('input', () => {
        messageInput.style.height = 'auto';
        messageInput.style.height = Math.min(messageInput.scrollHeight, 200) + 'px';
        sendBtn.disabled = !messageInput.value.trim();
    });

    // 新建对话
    newChatBtn.addEventListener('click', async () => {
        await createNewConversation();
    });

    // 移动端菜单切换
    menuToggle.addEventListener('click', () => {
        sidebar.classList.toggle('open');
    });

    // 点击主内容区关闭侧边栏（移动端）
    document.querySelector('.main-content').addEventListener('click', () => {
        if (window.innerWidth <= 768) {
            sidebar.classList.remove('open');
        }
    });
}

async function loadConversations() {
    try {
        const response = await fetch(`${API_BASE_URL}/conversations`);
        const data = await response.json();
        conversations = data.conversations || [];
        renderConversationsList();
    } catch (error) {
        console.error('加载对话列表失败:', error);
    }
}

function renderConversationsList() {
    conversationsList.innerHTML = '';

    if (conversations.length === 0) {
        conversationsList.innerHTML = '<p style="text-align: center; color: var(--text-secondary); padding: 20px;">暂无对话</p>';
        return;
    }

    conversations.forEach(conv => {
        const item = document.createElement('div');
        item.className = `conversation-item${conv.id === currentConversationId ? ' active' : ''}`;
        item.innerHTML = `
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor">
                <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
            </svg>
            <span class="conversation-title">${escapeHtml(conv.title)}</span>
            <button class="delete-btn" onclick="deleteConversation('${conv.id}', event)">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor">
                    <path d="M18 6L6 18M6 6l12 12" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                </svg>
            </button>
        `;
        item.addEventListener('click', (e) => {
            if (!e.target.closest('.delete-btn')) {
                loadConversation(conv.id);
            }
        });
        conversationsList.appendChild(item);
    });
}

async function createNewConversation() {
    try {
        const response = await fetch(`${API_BASE_URL}/conversations/new`, {
            method: 'POST'
        });
        const data = await response.json();
        currentConversationId = data.conversation_id;

        // 清空聊天区域
        chatMessages.innerHTML = `
            <div class="welcome-screen">
                <div class="welcome-icon">
                    <svg width="64" height="64" viewBox="0 0 24 24" fill="none" stroke="currentColor">
                        <path d="M12 2L2 7l10 5 10-5-10-5z" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                        <path d="M2 17l10 5 10-5" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                        <path d="M2 12l10 5 10-5" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                    </svg>
                </div>
                <h1>欢迎使用A股行情分析助手</h1>
                <p>我可以帮你查询和分析涨停板数据</p>
                <p class="examples">试试问："今天有哪些股票涨停了？"</p>
            </div>
        `;

        // 重新加载对话列表
        await loadConversations();

        // 移动端关闭侧边栏
        if (window.innerWidth <= 768) {
            sidebar.classList.remove('open');
        }
    } catch (error) {
        console.error('创建新对话失败:', error);
    }
}

async function loadConversation(conversationId) {
    try {
        const response = await fetch(`${API_BASE_URL}/conversations/${conversationId}`);
        const data = await response.json();
        currentConversationId = conversationId;

        // 渲染消息
        chatMessages.innerHTML = '';
        if (data.messages.length === 0) {
            chatMessages.innerHTML = `
                <div class="welcome-screen">
                    <div class="welcome-icon">
                        <svg width="64" height="64" viewBox="0 0 24 24" fill="none" stroke="currentColor">
                            <path d="M12 2L2 7l10 5 10-5-10-5z" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                        </svg>
                    </div>
                    <h1>A股行情分析助手</h1>
                    <p>有什么可以帮助您的吗？</p>
                </div>
            `;
        } else {
            data.messages.forEach(msg => {
                appendMessage(msg.role, msg.content);
            });
        }

        // 更新对话列表选中状态
        renderConversationsList();

        // 移动端关闭侧边栏
        if (window.innerWidth <= 768) {
            sidebar.classList.remove('open');
        }
    } catch (error) {
        console.error('加载对话失败:', error);
    }
}

async function deleteConversation(conversationId, event) {
    event.stopPropagation();

    if (!confirm('确定要删除这个对话吗？')) {
        return;
    }

    try {
        await fetch(`${API_BASE_URL}/conversations/${conversationId}`, {
            method: 'DELETE'
        });

        // 如果删除的是当前对话，创建新对话
        if (conversationId === currentConversationId) {
            await createNewConversation();
        } else {
            await loadConversations();
        }
    } catch (error) {
        console.error('删除对话失败:', error);
    }
}

async function sendMessage() {
    const message = messageInput.value.trim();
    if (!message || !currentConversationId) return;

    // 清空输入框
    messageInput.value = '';
    messageInput.style.height = 'auto';
    sendBtn.disabled = true;

    // 移除欢迎屏幕
    const welcomeScreen = chatMessages.querySelector('.welcome-screen');
    if (welcomeScreen) {
        welcomeScreen.remove();
    }

    // 显示用户消息
    appendMessage('user', message);

    // 添加加载指示器
    const loadingDiv = document.createElement('div');
    loadingDiv.className = 'message assistant';
    loadingDiv.innerHTML = `
        <div class="message-content">
            <div class="message-avatar">AI</div>
            <div class="typing-indicator">
                <span></span>
                <span></span>
                <span></span>
            </div>
        </div>
    `;
    chatMessages.appendChild(loadingDiv);
    scrollToBottom();

    try {
        // 使用 Vanna NL2SQL 接口
        const response = await fetch(`${API_BASE_URL}/chat/vanna`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                message: message
            })
        });

        // 移除加载指示器
        loadingDiv.remove();

        const result = await response.json();

        if (result.error) {
            // 显示错误
            appendErrorMessage(result.error);
            return;
        }

        if (result.type === 'vanna_query_result') {
            // 显示 Vanna 查询结果
            appendVannaQueryResult(result);
        } else if (result.type === 'query_result') {
            // 显示查询结果
            appendQueryResult(result);
        } else if (result.type === 'chat') {
            // 显示普通回复
            appendMessage('assistant', result.message);
        } else if (result.type === 'error') {
            appendErrorMessage(result.message);
        }

    } catch (error) {
        console.error('发送消息失败:', error);
        loadingDiv.remove();

        // 显示错误消息
        appendErrorMessage("网络错误，请检查后端服务是否正常运行。");
    }
}

function appendMessage(role, content) {
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${role}`;

    const avatar = role === 'user' ? 'U' : 'AI';

    messageDiv.innerHTML = `
        <div class="message-content">
            <div class="message-avatar">${avatar}</div>
            <div class="message-text">${marked.parse(content)}</div>
        </div>
    `;

    chatMessages.appendChild(messageDiv);

    // 高亮代码块
    messageDiv.querySelectorAll('pre code').forEach((block) => {
        hljs.highlightElement(block);
    });

    scrollToBottom();
}

function appendQueryResult(result) {
    // 1. 先显示分析报告
    if (result.analysis) {
        const analysisDiv = document.createElement('div');
        analysisDiv.className = 'message assistant';
        analysisDiv.innerHTML = `
            <div class="message-content">
                <div class="message-avatar">AI</div>
                <div class="message-text">
                    <div class="analysis-report">${marked.parse(result.analysis)}</div>
                </div>
            </div>
        `;
        chatMessages.appendChild(analysisDiv);
    }

    // 2. 显示数据表格
    if (result.data && result.data.length > 0) {
        const tableDiv = document.createElement('div');
        tableDiv.className = 'message assistant';

        let tableHTML = `
            <div class="message-content">
                <div class="message-avatar">AI</div>
                <div class="message-text">
                    <div class="query-result">
                        <div class="result-header">
                            <h3>📊 查询结果</h3>
                            <span class="result-count">共 ${result.total} 条记录</span>
                        </div>
                        <div class="table-container">
                            <table class="data-table">
                                <thead>
                                    <tr>
        `;

        // 表头
        result.columns.forEach(col => {
            tableHTML += `<th>${col}</th>`;
        });
        tableHTML += `</tr></thead><tbody>`;

        // 表数据（最多显示50条）
        const displayData = result.data.slice(0, 50);
        displayData.forEach(row => {
            tableHTML += `<tr>`;
            result.columns.forEach(col => {
                tableHTML += `<td>${formatCellValue(row[col])}</td>`;
            });
            tableHTML += `</tr>`;
        });

        tableHTML += `
                                </tbody>
                            </table>
                        </div>
        `;

        // 如果有更多数据
        if (result.total > 50) {
            tableHTML += `<p class="table-footer">仅显示前50条，共${result.total}条记录</p>`;
        }

        // SQL预览（可折叠）
        tableHTML += `
            <details class="sql-preview">
                <summary>查看SQL语句</summary>
                <pre><code>${escapeHtml(result.sql)}</code></pre>
            </details>
        `;

        tableHTML += `</div></div></div>`;

        tableDiv.innerHTML = tableHTML;
        chatMessages.appendChild(tableDiv);

        // 高亮SQL代码
        tableDiv.querySelectorAll('pre code').forEach((block) => {
            hljs.highlightElement(block);
        });
    }

    scrollToBottom();
}

function appendVannaQueryResult(result) {
    // 1. 先显示调试信息面板
    if (result.debug) {
        const debugDiv = document.createElement('div');
        debugDiv.className = 'message assistant';
        debugDiv.innerHTML = `
            <div class="message-content">
                <div class="message-avatar">🔍</div>
                <div class="message-text">
                    <div class="debug-panel">
                        <details open>
                            <summary style="cursor: pointer; font-weight: bold; color: #4CAF50;">
                                🔧 调试信息
                            </summary>
                            <div class="debug-info" style="margin-top: 10px; padding: 10px; background: #f5f5f5; border-radius: 5px; font-size: 12px;">
                                <p><strong>⏱️ 总耗时:</strong> ${result.debug.elapsed_time}</p>
                                <p><strong>📏 SQL长度:</strong> ${result.debug.sql_length} 字符</p>
                                <p><strong>📋 查询列:</strong> ${result.debug.columns.join(', ')}</p>
                                <p><strong>📊 返回行数:</strong> ${result.row_count} 条</p>
                            </div>
                        </details>
                    </div>
                </div>
            </div>
        `;
        chatMessages.appendChild(debugDiv);
    }

    // 2. 显示 SQL 语句（突出显示）
    const sqlDiv = document.createElement('div');
    sqlDiv.className = 'message assistant';
    sqlDiv.innerHTML = `
        <div class="message-content">
            <div class="message-avatar">SQL</div>
            <div class="message-text">
                <div class="sql-highlight">
                    <p style="margin-bottom: 5px; font-weight: bold; color: #2196F3;">🔍 Vanna 生成的 SQL:</p>
                    <pre><code class="language-sql">${escapeHtml(result.sql)}</code></pre>
                </div>
            </div>
        </div>
    `;
    chatMessages.appendChild(sqlDiv);

    // 高亮SQL代码
    sqlDiv.querySelectorAll('pre code').forEach((block) => {
        hljs.highlightElement(block);
    });

    // 3. 显示分析报告
    if (result.analysis) {
        const analysisDiv = document.createElement('div');
        analysisDiv.className = 'message assistant';
        analysisDiv.innerHTML = `
            <div class="message-content">
                <div class="message-avatar">AI</div>
                <div class="message-text">
                    <div class="analysis-report">${marked.parse(result.analysis)}</div>
                </div>
            </div>
        `;
        chatMessages.appendChild(analysisDiv);
    }

    // 4. 显示数据表格
    if (result.data && result.data.length > 0) {
        const tableDiv = document.createElement('div');
        tableDiv.className = 'message assistant';

        let tableHTML = `
            <div class="message-content">
                <div class="message-avatar">📊</div>
                <div class="message-text">
                    <div class="query-result">
                        <div class="result-header">
                            <h3>查询结果</h3>
                            <span class="result-count">共 ${result.row_count} 条记录</span>
                        </div>
                        <div class="table-container">
                            <table class="data-table">
                                <thead>
                                    <tr>
        `;

        // 表头
        result.columns.forEach(col => {
            tableHTML += `<th>${col}</th>`;
        });
        tableHTML += `</tr></thead><tbody>`;

        // 表数据（最多显示50条）
        const displayData = result.data.slice(0, 50);
        displayData.forEach(row => {
            tableHTML += `<tr>`;
            result.columns.forEach(col => {
                tableHTML += `<td>${formatCellValue(row[col])}</td>`;
            });
            tableHTML += `</tr>`;
        });

        tableHTML += `
                                </tbody>
                            </table>
                        </div>
        `;

        // 如果有更多数据
        if (result.row_count > 50) {
            tableHTML += `<p class="table-footer">仅显示前50条，共${result.row_count}条记录</p>`;
        }

        tableHTML += `</div></div></div>`;

        tableDiv.innerHTML = tableHTML;
        chatMessages.appendChild(tableDiv);
    }

    scrollToBottom();
}

function appendErrorMessage(errorMsg) {
    const errorDiv = document.createElement('div');
    errorDiv.className = 'message assistant';
    errorDiv.innerHTML = `
        <div class="message-content">
            <div class="message-avatar">AI</div>
            <div class="message-text" style="color: #ff6b6b;">
                <strong>❌ 错误</strong><br/>
                ${escapeHtml(errorMsg)}
            </div>
        </div>
    `;
    chatMessages.appendChild(errorDiv);
    scrollToBottom();
}

function formatCellValue(value) {
    if (value === null || value === undefined) {
        return '-';
    }

    // 如果是数字，尝试格式化
    if (typeof value === 'number') {
        // 大数字格式化（亿、万）
        if (Math.abs(value) >= 100000000) {
            return (value / 100000000).toFixed(2) + '亿';
        } else if (Math.abs(value) >= 10000) {
            return (value / 10000).toFixed(2) + '万';
        } else if (value % 1 !== 0) {
            // 小数保留2位
            return value.toFixed(2);
        }
    }

    return String(value);
}

function scrollToBottom() {
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}
