[根目录](CLAUDE.md) > **ai_legal_team_cn.py**

---

# 主应用模块：ai_legal_team_cn.py

---

## 变更记录 (Changelog)

### 2026-01-15 19:03:51
- 初始化模块文档
- 完成代码架构分析

---

## 模块职责

这是 AI 法律文档分析助手的核心应用文件，负责：
- Streamlit Web 界面的构建与交互
- 文档上传与处理流程管理
- 向量数据库（Qdrant）的初始化与连接
- AI 智能体团队的创建与协调
- 多维度法律分析功能的实现

---

## 入口与启动

### 主函数
```python
def main():
    st.set_page_config(page_title="法律文档分析助手", layout="wide")
    init_session_state()
    # ... UI 构建
```

### 启动命令
```bash
streamlit run ai_legal_team_cn.py
```

### 会话初始化流程
```python
init_session_state() → 初始化所有 session_state 变量
  ├─ openai_api_key
  ├─ qdrant_api_key
  ├─ qdrant_url
  ├─ vector_db
  ├─ legal_team
  ├─ knowledge_base
  └─ processed_files (跟踪已处理文档，避免重复处理)
```

---

## 对外接口

### 1. 文档处理接口

```python
process_document(uploaded_file, vector_db: Qdrant) -> Knowledge
```

**功能**：将上传的 PDF 文档处理为向量嵌入并存入 Qdrant

**参数**：
- `uploaded_file`: Streamlit UploadedFile 对象
- `vector_db`: 已初始化的 Qdrant 实例

**返回**：Knowledge 对象（包含文档向量知识库）

**处理流程**：
1. 保存文件到临时目录
2. 使用 Knowledge 加载文档内容
3. 调用 OpenAI Embeddings 创建向量
4. 存储到 Qdrant 集合 `legal_documents`
5. 清理临时文件

### 2. 向量数据库初始化

```python
init_qdrant() -> Optional[Qdrant]
```

**功能**：初始化 Qdrant 向量数据库连接

**配置**：
- 集合名称：`COLLECTION_NAME = "legal_documents"`
- 嵌入模型：`text-embedding-3-small`
- API 端点：`https://api.zhizengzeng.com/v1`

### 3. AI 团队接口

应用通过 Streamlit UI 暴露以下分析类型：

| 分析类型 | 调用的智能体 | 输出格式 |
|---------|-------------|---------|
| 合同审查 | 合同分析师 | 3 个标签页：分析结果、关键点、建议 |
| 法律研究 | 法律研究员 | 同上 |
| 风险评估 | 合同分析师 + 法律策略师 | 同上 |
| 合规性检查 | 全部智能体 | 同上 |
| 自定义查询 | 全部智能体 | 同上 |

---

## 关键依赖与配置

### 依赖项

```python
# 核心框架
import streamlit as st
from agno.agent import Agent
from agno.team import Team
from agno.knowledge.knowledge import Knowledge
from agno.vectordb.qdrant import Qdrant
from agno.tools.duckduckgo import DuckDuckGoTools
from agno.models.openai import OpenAIChat
from agno.knowledge.embedder.openai import OpenAIEmbedder

# 标准库
import tempfile
import os
```

### 环境变量与配置

| 配置项 | 来源 | 说明 |
|-------|------|------|
| `OPENAI_BASE_URL` | 硬编码 | `"https://api.zhizengzeng.com/v1"` |
| `COLLECTION_NAME` | 硬编码 | `"legal_documents"` |
| `OPENAI_API_KEY` | Session State | 用户在侧边栏输入 |
| `QDRANT_API_KEY` | Session State | 用户在侧边栏输入 |
| `QDRANT_URL` | Session State | 用户在侧边栏输入 |

### AI 模型配置

| 组件 | 模型 ID | 用途 |
|-----|---------|------|
| LLM | `gpt-4.1` | 所有智能体的主语言模型 |
| Embeddings | `text-embedding-3-small` | 文档向量化 |

---

## 数据模型

### 会话状态结构

```python
st.session_state = {
    # API 配置
    "openai_api_key": str | None,
    "qdrant_api_key": str | None,
    "qdrant_url": str | None,

    # 核心对象
    "vector_db": Qdrant | None,
    "knowledge_base": Knowledge | None,
    "legal_team": Team | None,

    # 文档跟踪
    "processed_files": Set[str]  # 已处理文件名集合
}
```

### 分析配置结构

```python
analysis_configs = {
    "分析类型名称": {
        "query": str,           # 预定义的提示词
        "agents": List[str],    # 参与的智能体名称列表
        "description": str      # 描述文本
    }
}
```

### Agent 配置结构

```python
Agent(
    name=str,              # 智能体名称
    role=str,              # 角色定位
    model=OpenAIChat,      # LLM 模型
    tools=List,            # 工具列表（如 DuckDuckGoTools）
    knowledge=Knowledge,   # 共享知识库
    search_knowledge=bool, # 是否启用知识库搜索
    instructions=List[str],# 行为指导
    debug_mode=bool,       # 调试模式
    markdown=bool          # Markdown 输出
)
```

---

## 测试与质量

### 当前状态
❌ **无测试覆盖**

### 建议测试策略

#### 单元测试（使用 pytest）

```python
# tests/test_ai_legal_team.py

def test_init_session_state():
    """测试会话状态初始化"""
    # 模拟 Streamlit session_state
    # 验证所有变量被正确初始化

def test_init_qdrant_success():
    """测试 Qdrant 成功初始化"""
    # Mock Qdrant 连接
    # 验证返回正确的 Qdrant 实例

def test_init_qdrant_missing_credentials():
    """测试缺少凭证时的行为"""
    # 验证返回 None
    # 验证错误消息显示

def test_process_document_success():
    """测试文档处理成功流程"""
    # Mock 临时文件创建
    # Mock Knowledge.add_content
    # 验证知识库返回

def test_process_document_no_api_key():
    """测试缺少 API 密钥时的异常处理"""
    # 验证抛出 ValueError

def test_agent_team_initialization():
    """测试 AI 团队初始化"""
    # 验证 Team 对象创建
    # 验证包含 3 个成员 Agent
    # 验证共享知识库
```

#### 集成测试

```python
def test_full_document_upload_workflow():
    """完整文档上传流程测试"""
    # 1. 初始化 session_state
    # 2. 配置 API 密钥
    # 3. 上传测试 PDF
    # 4. 验证文档处理
    # 5. 验证团队初始化
    # 6. 执行分析
    # 7. 验证输出格式
```

#### UI 测试（使用 Streamlit Testing）

```python
def test_ui_rendering():
    """测试 UI 元素渲染"""
    # 验证侧边栏元素
    # 验证主内容区
    # 验证文件上传器
    # 验证分析选择器

def test_analysis_flow():
    """测试分析流程"""
    # 模拟用户选择分析类型
    # 点击"开始分析"按钮
    # 验证结果标签页显示
```

### 代码质量工具

建议添加：
- **Black**：代码格式化
- **Flake8**：代码风格检查
- **MyPy**：类型检查（需先添加类型注解）
- **Pylint**：代码质量分析

---

## 常见问题 (FAQ)

### Q1: 为什么文档上传后会卡住？
**A**: 检查以下事项：
- OpenAI API Key 是否有效
- Qdrant 连接是否成功
- 网络是否可以访问 `api.zhizengzeng.com`
- PDF 文件是否损坏或过大

### Q2: 如何添加新的分析类型？
**A**: 在 `analysis_configs` 字典中添加新条目：
```python
"新分析类型": {
    "query": "分析提示词",
    "agents": ["智能体1", "智能体2"],
    "description": "描述文本"
}
```

### Q3: 如何修改 AI 智能体的行为？
**A**: 编辑 Agent 实例的 `instructions` 参数：
```python
legal_researcher = Agent(
    instructions=[
        "新指令1",
        "新指令2"
    ]
)
```

### Q4: 支持哪些文档格式？
**A**: 当前仅支持 PDF（`type=['pdf']`）。要支持更多格式，需修改 `st.file_uploader` 的 `type` 参数并确保 Knowledge 类能处理这些格式。

### Q5: 如何更换向量数据库？
**A**: 替换 `Qdrant` 为 Agno 支持的其他向量数据库（如 PgVector、Chroma 等），并修改 `init_qdrant()` 函数。

### Q6: 文档处理失败但未显示错误？
**A**: 检查浏览器控制台和 Streamlit 终端输出。启用 `debug_mode=True` 查看详细日志。

---

## 代码结构分析

### 文件组织（400 行）

```python
# 1-12: 导入声明
# 13-31: 会话状态初始化
# 32-53: Qdrant 初始化
# 55-103: 文档处理
# 105-399: 主应用逻辑

主要部分：
├── 配置层（全局变量、常量）
├── 数据层（Qdrant、Knowledge）
├── 业务逻辑层（Agent Team、分析配置）
└── 表现层（Streamlit UI）
```

### 函数复杂度

| 函数 | 行数 | 复杂度 | 建议 |
|-----|------|--------|------|
| `main()` | ~295 | 高 | 拆分为多个 UI 组件函数 |
| `process_document()` | ~50 | 中 | 可接受，考虑添加重试逻辑 |
| `init_qdrant()` | ~20 | 低 | 结构清晰 |
| `init_session_state()` | ~20 | 低 | 简单初始化 |

---

## 重构建议

### 1. 模块化拆分

建议拆分为以下文件：

```
src/
├── config.py          # 配置常量
├── state.py           # 会话状态管理
├── vector_db.py       # Qdrant 初始化
├── document.py        # 文档处理逻辑
├── agents/
│   ├── __init__.py
│   ├── legal_researcher.py
│   ├── contract_analyst.py
│   └── legal_strategist.py
├── team.py            # AI 团队配置
├── analysis.py        # 分析类型配置
└── ui/
    ├── __init__.py
    ├── sidebar.py     # 侧边栏组件
    ├── main.py        # 主内容区
    └── results.py     # 结果展示
```

### 2. 配置外部化

创建 `.env.example`：
```env
OPENAI_API_KEY=your_key_here
OPENAI_BASE_URL=https://api.zhizengzeng.com/v1
QDRANT_URL=your_qdrant_url
QDRANT_API_KEY=your_qdrant_key
QDRANT_COLLECTION=legal_documents
```

使用 `python-dotenv` 加载：
```python
from dotenv import load_dotenv
load_dotenv()
```

### 3. 添加类型注解

```python
from typing import Optional
from streamlit.uploaded_file_manager import UploadedFile

def process_document(
    uploaded_file: UploadedFile,
    vector_db: Qdrant
) -> Optional[Knowledge]:
    ...
```

### 4. 错误处理增强

```python
# 定义自定义异常
class DocumentProcessingError(Exception):
    pass

class VectorDBError(Exception):
    pass

# 使用重试机制
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(stop=stop_after_attempt(3), wait=wait_exponential())
def init_qdrant() -> Optional[Qdrant]:
    ...
```

---

## 相关文件清单

### 本模块使用的外部文件
- 无（所有逻辑在单文件内）

### 建议添加的文件
- `requirements.txt` - Python 依赖声明
- `.env.example` - 环境变量示例
- `README.md` - 项目说明
- `tests/test_ai_legal_team.py` - 单元测试
- `.gitignore` - Git 忽略规则

### 依赖的配置文件
- `.spec-workflow/templates/` - 开发文档模板（不直接依赖）

---

## 性能考虑

### 潜在瓶颈
1. **文档嵌入**：大 PDF 文件向量化可能耗时较长
2. **API 调用**：每次分析需要多次 LLM 调用
3. **向量检索**：Qdrant 查询性能取决于集合大小

### 优化建议
1. 添加文档处理进度条（已有 `st.spinner`）
2. 实现结果缓存（避免重复分析）
3. 限制单次文档大小
4. 考虑异步处理大型文档

---

## 安全注意事项

### 当前问题
1. API 密钥仅存储在 Session State（刷新后丢失）
2. 无输入验证（文件大小、类型验证不严格）
3. 无用户认证（任何人都可访问）
4. 无速率限制（可能被滥用）

### 改进建议
1. 实现用户认证系统
2. 添加 API 密钥加密存储
3. 实现文件上传大小限制
4. 添加速率限制
5. 审计日志记录

---

## 扩展方向

### 功能扩展
- 支持更多文档格式（Word、TXT、图片 OCR）
- 多语言支持（英文法律文档）
- 文档对比功能（对比两个合同）
- 导出分析报告（PDF/Word）
- 历史记录保存

### 技术扩展
- 部署为云端服务（Streamlit Cloud/Docker）
- 添加数据库持久化（PostgreSQL/MongoDB）
- 实现批量文档处理
- 添加 REST API 接口
- 集成更多数据源（法律数据库、案例库）

---

**文档生成时间**: 2026-01-15 19:03:51
**最后更新**: 2026-01-15 19:03:51
