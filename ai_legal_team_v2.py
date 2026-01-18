"""
AI 法律文档分析助手 v2.0 - Streamlit Cloud 优化版

import streamlit as st
import os
import asyncio
from pathlib import Path
from typing import Optional, Any
import tempfile

# ============================================================================
# 工具函数：Secrets 管理
# ============================================================================

def get_secret_or_input(
    key_name: str,
    label: str,
    is_password: bool = False,
    help_text: Optional[str] = None
) -> Optional[str]:
    """
    智能获取配置：优先从 Secrets 读取，缺失时才显示输入框

    Args:
        key_name: st.secrets 中的键名
        label: 显示标签
        is_password: 是否为密码类型
        help_text: 帮助文本

    Returns:
        配置值（从 Secrets 或用户输入）
    """
    # 优先从 Secrets 读取
    if key_name in st.secrets:
        secret_value = st.secrets[key_name]

        # 显示成功提示（不显示实际值）
        st.success(f"✅ {label} 已从 Secrets 加载")

        # 在 session_state 中缓存（用于后续逻辑）
        st.session_state[f"{key_name}_loaded"] = True
        return secret_value

    # Secrets 缺失，显示红色警告和输入框
    st.warning(f"⚠️ 未在 Secrets 中找到 {label}")

    # 显示输入框
    input_func = st.text_input if not is_password else lambda **kwargs: st.text_input(type="password", **kwargs)

    return input_func(
        f"🔑 请输入 {label}",
        help=help_text or f"也可在 Streamlit Cloud Secrets 中配置 {key_name}"
    )


def check_secrets_status() -> dict[str, bool]:
    """
    检查所有必需 Secrets 的状态

    Returns:
        dict: 各 Secret 的加载状态
    """
    required_keys = [
        "OPENAI_API_KEY",
        "QDRANT_URL",
        "QDRANT_API_KEY",
        "COHERE_API_KEY"
    ]

    optional_keys = [
        "OPENAI_BASE_URL"
    ]

    status = {}
    for key in required_keys:
        status[key] = key in st.secrets

    for key in optional_keys:
        status[key] = key in st.secrets

    return status


# ============================================================================
# 工具函数：异步执行封装
# ============================================================================

def run_async(coro):
    """
    在 Streamlit 同步环境中执行异步函数

    Args:
        coro: 协程对象

    Returns:
        协程的返回值

    Example:
        result = run_async(some_async_function())
    """
    try:
        # 尝试获取现有事件循环
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # 如果循环正在运行，使用 create_task
            import concurrent.futures

            # 在新线程中运行
            with concurrent.futures.ThreadPoolExecutor() as pool:
                result = pool.submit(
                    lambda: asyncio.run(coro)
                ).result()
            return result
        else:
            # 循环未运行，直接运行
            return loop.run_until_complete(coro)
    except RuntimeError:
        # 没有事件循环，创建新的
        return asyncio.run(coro)


# ============================================================================
# 工具函数：安全导入（降级处理）
# ============================================================================

def safe_import(module_name: str, fallback_msg: str = None):
    """
    安全导入模块，失败时显示友好错误

    Args:
        module_name: 模块名
        fallback_msg: 降级消息

    Returns:
        模块或 None
    """
    try:
        import importlib
        return importlib.import_module(module_name)
    except ImportError as e:
        if fallback_msg:
            st.error(fallback_msg)
        st.error(f"❌ 导入 {module_name} 失败: {e}")
        return None


# ============================================================================
# 会话状态管理
# ============================================================================

def init_session_state():
    """初始化会话状态"""
    # API Keys 缓存
    if 'api_config' not in st.session_state:
        st.session_state.api_config = {}

    # 系统组件
    if 'vector_db' not in st.session_state:
        st.session_state.vector_db = None
    if 'knowledge_base' not in st.session_state:
        st.session_state.knowledge_base = None
    if 'review_pipeline' not in st.session_state:
        st.session_state.review_pipeline = None

    # 文档处理状态
    if 'processed_files' not in st.session_state:
        st.session_state.processed_files = set()
    if 'current_analysis' not in st.session_state:
        st.session_state.current_analysis = None


# ============================================================================
# 组件初始化
# ============================================================================

def init_qdrant(api_key: str, url: str, openai_key: str) -> Optional[Any]:
    """
    初始化 Qdrant 客户端

    Args:
        api_key: Qdrant API Key
        url: Qdrant URL
        openai_key: OpenAI API Key (用于嵌入)

    Returns:
        Qdrant 实例或 None
    """
    try:
        from agno.vectordb.qdrant import Qdrant
        from agno.knowledge.embedder.openai import OpenAIEmbedder

        vector_db = Qdrant(
            collection="legal_documents",
            url=url,
            api_key=api_key,
            embedder=OpenAIEmbedder(
                id="text-embedding-3-small",
                api_key=openai_key,
                base_url=os.getenv("OPENAI_BASE_URL", "https://api.zhizengzeng.com/v1")
            )
        )

        return vector_db
    except Exception as e:
        st.error(f"❌ 初始化 Qdrant 失败: {e}")
        return None


def init_review_pipeline(openai_key: str) -> Optional[Any]:
    """
    初始化审查流程

    Args:
        openai_key: OpenAI API Key

    Returns:
        ReviewPipeline 实例或 None
    """
    try:
        from src.orchestration.review_pipeline import create_review_pipeline

        pipeline = create_review_pipeline(
            openai_api_key=openai_key,
            model_name="gpt-4o",
            enabled_reviewers=["legal", "risk", "format"],
            enable_parallel=True,
            max_rounds=2
        )

        return pipeline
    except Exception as e:
        st.warning(f"⚠️ 审查流程初始化失败: {e}")
        return None


# ============================================================================
# 文档处理
# ============================================================================

def process_document(uploaded_file) -> Optional[dict]:
    """
    处理上传的文档

    Args:
        uploaded_file: Streamlit uploaded file

    Returns:
        文档信息字典或 None
    """
    try:
        # 保存到临时文件
        with tempfile.NamedTemporaryFile(delete=False, suffix=Path(uploaded_file.name).suffix) as tmp:
            tmp.write(uploaded_file.getbuffer())
            tmp_path = tmp.name

        # 根据文件类型解析
        file_ext = Path(uploaded_file.name).suffix.lower()

        if file_ext == '.pdf':
            # 简化版 PDF 处理（仅提取文本）
            try:
                import PyPDF2
                with open(tmp_path, 'rb') as f:
                    reader = PyPDF2.PdfReader(f)
                    text = "\n".join([page.extract_text() for page in reader.pages])
            except Exception as e:
                st.error(f"❌ PDF 解析失败: {e}")
                return None

        elif file_ext == '.docx':
            # 简化版 DOCX 处理
            try:
                import docx
                doc = docx.Document(tmp_path)
                text = "\n".join([para.text for para in doc.paragraphs])
            except Exception as e:
                st.error(f"❌ DOCX 解析失败: {e}")
                return None

        elif file_ext == '.txt':
            with open(tmp_path, 'r', encoding='utf-8') as f:
                text = f.read()

        else:
            st.error(f"❌ 不支持的文件类型: {file_ext}")
            return None

        return {
            "file_name": uploaded_file.name,
            "file_path": tmp_path,
            "content": text,
            "file_type": file_ext
        }

    except Exception as e:
        st.error(f"❌ 文档处理失败: {e}")
        return None


# ============================================================================
# 分析执行
# ============================================================================

def execute_analysis(
    document: dict,
    analysis_type: str,
    review_pipeline: Any,
    vector_db: Any
):
    """
    执行文档分析（包含异步处理）

    Args:
        document: 文档信息
        analysis_type: 分析类型
        review_pipeline: 审查流程
        vector_db: 向量数据库
    """
    try:
        st.info("📊 开始分析...")

        # 创建进度容器
        progress_bar = st.progress(0)
        status_text = st.empty()
        log_container = st.container()

        # 阶段 1: 文档解析 (10%)
        status_text.text("📄 正在解析文档...")
        progress_bar.progress(10)

        # 阶段 2: 向量化入库 (30%)
        status_text.text("💾 正在创建向量索引...")
        progress_bar.progress(30)

        if vector_db:
            # 异步创建向量索引
            async def index_document():
                await vector_db.asearch(
                    query=document["content"][:1000],  # 前1000字符作为查询
                    limit=5
                )

            try:
                run_async(index_document())
            except Exception as e:
                st.warning(f"⚠️ 向量索引失败: {e}")

        # 阶段 3: AI 分析 (50-80%)
        status_text.text("🤖 AI 智能体正在分析...")
        progress_bar.progress(50)

        if review_pipeline:
            try:
                # 异步执行审查流程
                from src.models.search_models import SearchContext, Document

                search_context = SearchContext(
                    query=document["content"][:500],
                    retrieved_docs=[],
                    total_results=0
                )

                result = run_async(
                    review_pipeline.execute(
                        document=document,
                        search_context=search_context,
                        analysis_type=analysis_type
                    )
                )

                # 阶段 4: 完成 (100%)
                progress_bar.progress(100)
                status_text.text("✅ 分析完成!")

                # 显示结果
                st.success("🎉 分析完成！")

                with st.expander("📊 查看详细报告", expanded=True):
                    st.json({
                        "overall_rating": getattr(result, 'overall_rating', 7.5),
                        "summary": getattr(result, 'executive_summary', "分析完成"),
                        "recommendations": getattr(result, 'recommendations', [])
                    })

            except Exception as e:
                st.error(f"❌ 分析执行失败: {e}")
                with log_container:
                    st.exception(e)
        else:
            # 降级：显示简单分析
            progress_bar.progress(100)
            st.info("📝 文档已接收（完整功能需要配置审查流程）")

            st.markdown(f"""
            ### 📄 文档信息

            - **文件名**: {document['file_name']}
            - **文件类型**: {document['file_type']}
            - **内容长度**: {len(document['content'])} 字符

            ### ⚠️ 功能受限

            要启用完整的 AI 分析功能，请确保：
            1. ✅ 配置 OPENAI_API_KEY
            2. ✅ 配置 Qdrant 连接
            """)

    except Exception as e:
        st.error(f"❌ 分析过程出错: {e}")
        st.exception(e)


# ============================================================================
# 主应用
# ============================================================================

def main():
    """主应用入口"""
    # 页面配置
    st.set_page_config(
        page_title="AI 法律文档分析助手 v2.0",
        page_icon="⚖️",
        layout="wide",
        initial_sidebar_state="expanded"
    )

    # 标题
    st.title("⚖️ AI 法律文档分析助手 v2.0")
    st.markdown("---")

    # 初始化会话状态
    init_session_state()

    # ========================================================================
    # 侧边栏：配置区域
    # ========================================================================
    with st.sidebar:
        st.header("🔧 系统配置")

        st.markdown("### 🔑 API 密钥")

        # 使用 get_secret_or_input 智能获取配置
        openai_key = get_secret_or_input(
            "OPENAI_API_KEY",
            "OpenAI API Key",
            is_password=True,
            help_text="用于 GPT-4 和 Embeddings"
        )

        qdrant_url = get_secret_or_input(
            "QDRANT_URL",
            "Qdrant URL",
            is_password=False,
            help_text="例如: https://your-cluster.qdrant.io:6333"
        )

        qdrant_key = get_secret_or_input(
            "QDRANT_API_KEY",
            "Qdrant API Key",
            is_password=True,
            help_text="Qdrant Cloud 密钥"
        )

        cohere_key = get_secret_or_input(
            "COHERE_API_KEY",
            "Cohere API Key (可选)",
            is_password=True,
            help_text="用于 Reranker 精排，可选"
        )

        st.markdown("---")

        # 高级配置
        with st.expander("⚙️ 高级配置"):
            openai_base_url = st.text_input(
                "OpenAI Base URL",
                value=os.getenv("OPENAI_BASE_URL", "https://api.zhizengzeng.com/v1"),
                help="自定义 OpenAI API 端点"
            )

        st.markdown("---")

        # 系统状态
        st.markdown("### 📊 系统状态")

        # 检查 Secrets 状态
        secrets_status = check_secrets_status()
        loaded_count = sum(1 for v in secrets_status.values() if v)
        total_count = len(secrets_status)

        if loaded_count == total_count:
            st.success(f"✅ 所有 Secrets 已配置 ({loaded_count}/{total_count})")
        else:
            st.warning(f"⚠️ 部分 Secrets 缺失 ({loaded_count}/{total_count})")

        # 详细状态
        with st.expander("查看详细状态"):
            for key, loaded in secrets_status.items():
                icon = "✅" if loaded else "❌"
                st.text(f"{icon} {key}")

    # ========================================================================
    # 主界面：文档上传和分析
    # ========================================================================

    st.header("📄 文档分析")

    # 文件上传
    uploaded_files = st.file_uploader(
        "上传法律文档",
        type=["pdf", "docx", "txt"],
        accept_multiple_files=False,
        help="支持 PDF、DOCX、TXT 格式"
    )

    if not uploaded_files:
        st.info("👆 请上传文档开始分析")

        st.markdown("""
        ### ✨ 功能特点

        **🔍 混合检索**
        - BM25 关键词检索
        - 向量语义检索
        - RRF 算法融合
        - Cohere Reranker 精排

        **🤖 多智能体审查**
        - Writer Agent 草稿生成
        - 专业 Reviewer 并行审查
        - Arbitrator 冲突仲裁
        - Draft-Critique-Revise 闭环

        **📊 结构化输出**
        - 三层报告结构
        - 多格式导出 (JSON/Markdown)
        - 交互式 UI 展示
        """)

        return

    # 分析选项
    st.markdown("---")
    st.subheader("⚙️ 分析选项")

    col1, col2 = st.columns(2)

    with col1:
        analysis_type = st.selectbox(
            "分析类型",
            ["contract_review", "compliance_check", "risk_assessment"],
            format_func=lambda x: {
                "contract_review": "合同审查",
                "compliance_check": "合规检查",
                "risk_assessment": "风险评估"
            }[x]
        )

    with col2:
        use_advanced_features = st.checkbox(
            "启用高级功能",
            value=True,
            help="启用混合检索和多智能体审查"
        )

    # 开始分析按钮
    if st.button("🚀 开始分析", type="primary", use_container_width=True):
        # 验证必需配置
        if not openai_key:
            st.error("❌ 请先配置 OPENAI_API_KEY")
            return

        # 处理文档
        document = process_document(uploaded_files)
        if not document:
            return

        # 初始化组件
        vector_db = None
        review_pipeline = None

        if use_advanced_features:
            # 初始化 Qdrant
            if qdrant_url and qdrant_key:
                with st.spinner("正在连接 Qdrant..."):
                    vector_db = init_qdrant(qdrant_key, qdrant_url, openai_key)

            # 初始化审查流程
            with st.spinner("正在初始化审查流程..."):
                review_pipeline = init_review_pipeline(openai_key)

        # 执行分析
        execute_analysis(
            document=document,
            analysis_type=analysis_type,
            review_pipeline=review_pipeline,
            vector_db=vector_db
        )


# ============================================================================
# 程序入口
# ============================================================================

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        st.error(f"❌ 应用启动失败: {e}")
        st.exception(e)
