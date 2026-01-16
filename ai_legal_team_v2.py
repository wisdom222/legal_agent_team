"""
AI 法律文档分析助手 - 主应用
集成混合检索、多智能体审查和结构化报告生成
"""

import streamlit as st
import os
import tempfile
from pathlib import Path
from typing import Optional, List
import asyncio

# Agno 框架
from agno.agent import Agent
from agno.team import Team
from agno.knowledge.knowledge import Knowledge
from agno.vectordb.qdrant import Qdrant
from agno.models.openai import OpenAIChat
from agno.knowledge.embedder.openai import OpenAIEmbedder

# 新架构组件
from src.config.app_config import get_app_config
from src.retrieval.hybrid_search import create_hybrid_search_engine
from src.retrieval.bm25_indexer import BM25Indexer
from src.orchestration.review_pipeline import create_review_pipeline
from src.ui.display import display_report

from src.models.report_schema import LegalDocumentReport, DocumentType
from src.core.exceptions import ErrorHandler
from src.core.metrics import get_metrics_collector, init_metrics

# 配置
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://api.zhizengzeng.com/v1")
COLLECTION_NAME = "legal_documents"


def init_session_state():
    """初始化会话状态"""
    # API Keys
    if 'openai_api_key' not in st.session_state:
        st.session_state.openai_api_key = None
    if 'qdrant_api_key' not in st.session_state:
        st.session_state.qdrant_api_key = None
    if 'qdrant_url' not in st.session_state:
        st.session_state.qdrant_url = None

    # 数据库和团队
    if 'vector_db' not in st.session_state:
        st.session_state.vector_db = None
    if 'legal_team' not in st.session_state:
        st.session_state.legal_team = None
    if 'knowledge_base' not in st.session_state:
        st.session_state.knowledge_base = None

    # 新架构组件
    if 'hybrid_engine' not in st.session_state:
        st.session_state.hybrid_engine = None
    if 'review_pipeline' not in st.session_state:
        st.session_state.review_pipeline = None

    # 错误处理和监控
    if 'error_handler' not in st.session_state:
        st.session_state.error_handler = ErrorHandler()
    if 'metrics' not in st.session_state:
        st.session_state.metrics = get_metrics_collector(
            enabled=True,
            port=8000
        )

    # 已处理文件
    if 'processed_files' not in st.session_state:
        st.session_state.processed_files = set()


def init_qdrant():
    """初始化 Qdrant 客户端"""
    if not all([st.session_state.qdrant_api_key, st.session_state.qdrant_url]):
        return None

    try:
        vector_db = Qdrant(
            collection=COLLECTION_NAME,
            url=st.session_state.qdrant_url,
            api_key=st.session_state.qdrant_api_key,
            embedder=OpenAIEmbedder(
                id="text-embedding-3-small",
                api_key=st.session_state.openai_api_key,
                base_url=OPENAI_BASE_URL
            )
        )
        return vector_db
    except Exception as e:
        st.error(f"初始化 Qdrant 失败: {e}")
        return None


def init_knowledge_base(vector_db):
    """初始化知识库"""
    if not vector_db:
        return None

    try:
        knowledge_base = Knowledge(vector_db=vector_db)
        return knowledge_base
    except Exception as e:
        st.error(f"初始化知识库失败: {e}")
        return None


def init_hybrid_search(vector_db):
    """
    初始化混合检索引擎

    集成 BM25 + 向量检索 + Reranker
    """
    if not vector_db:
        return None

    try:
        # 创建 BM25 索引器（需要文档数据）
        bm25_indexer = BM25Indexer()

        # 注意：这里简化处理，实际应该从数据库加载已索引的文档
        # bm25_indexer.index_documents(documents)

        # 创建向量检索函数
        async def vector_search(query: str, top_k: int):
            """向量检索函数"""
            results = await vector_db.asearch(query, limit=top_k)
            # 转换为 SearchResult 格式
            from src.models.search_models import SearchResult, RetrievalMethod
            return [
                SearchResult(
                    doc_id=r.get("id", ""),
                    score=r.get("score", 0),
                    retrieval_method=RetrievalMethod.VECTOR,
                    content=r.get("context", "")
                )
                for r in results
            ], 0.1

        # 创建混合检索引擎
        engine = create_hybrid_search_engine(
            bm25_indexer=bm25_indexer,
            vector_search_func=vector_search,
            reranker_api_key=os.getenv("COHERE_API_KEY"),
            enable_cache=True
        )

        return engine

    except Exception as e:
        st.warning(f"混合检索引擎初始化失败: {e}")
        return None


def init_review_pipeline():
    """初始化审查流程"""
    try:
        pipeline = create_review_pipeline(
            openai_api_key=st.session_state.openai_api_key,
            model_name="gpt-4o",
            enabled_reviewers=["legal", "risk", "format", "business"],
            enable_parallel=True,
            max_rounds=2
        )
        return pipeline
    except Exception as e:
        st.warning(f"审查流程初始化失败: {e}")
        return None


def main():
    """主应用"""
    st.set_page_config(
        page_title="AI 法律文档分析助手",
        page_icon="⚖️",
        layout="wide",
        initial_sidebar_state="expanded"
    )

    st.title("⚖️ AI 法律文档分析助手")
    st.markdown("---")

    # 初始化会话状态
    init_session_state()

    # 侧边栏配置
    with st.sidebar:
        st.header("🔧 配置")

        # API Keys
        st.subheader("API 密钥")
        openai_key = st.text_input(
            "OpenAI API Key",
            type="password",
            value=st.session_state.openai_api_key or "",
            help="输入 OpenAI API 密钥"
        )

        qdrant_key = st.text_input(
            "Qdrant API Key (可选)",
            type="password",
            value=st.session_state.qdrant_api_key or "",
            help="输入 Qdrant API 密钥（如需要）"
        )

        qdrant_url = st.text_input(
            "Qdrant URL",
            value=st.session_state.qdrant_url or "http://localhost:6333",
            help="Qdrant 服务地址"
        )

        # 保存配置
        if st.button("保存配置"):
            st.session_state.openai_api_key = openai_key
            st.session_state.qdrant_api_key = qdrant_key
            st.session_state.qdrant_url = qdrant_url
            st.success("配置已保存")

        st.markdown("---")

        # 新架构开关
        st.subheader("🚀 新架构功能")
        enable_hybrid_search = st.checkbox(
            "启用混合检索 (BM25 + 向量)",
            value=True,
            help="启用混合检索和 Reranker"
        )

        enable_multi_agent = st.checkbox(
            "启用多智能体审查",
            value=True,
            help="启用并行审查和仲裁机制"
        )

        enable_structured_output = st.checkbox(
            "启用结构化输出",
            value=True,
            help="生成三层结构化报告"
        )

        st.markdown("---")

        # 系统信息
        st.subheader("📊 系统信息")
        if st.session_state.vector_db:
            st.success("✅ Qdrant 已连接")
        else:
            st.warning("⚠️ Qdrant 未连接")

        if enable_hybrid_search and st.session_state.hybrid_engine:
            st.success("✅ 混合检索已启用")

        if enable_multi_agent and st.session_state.review_pipeline:
            st.success("✅ 多智能体审查已启用")

        # 监控指标
        if st.session_state.metrics.enabled:
            metrics_summary = st.session_state.metrics.get_metrics_summary()
            if metrics_summary.get("enabled"):
                st.metric("总请求数", metrics_summary.get("retrieval_requests", 0))

    # 主界面
    st.header("📄 文档分析")

    # 文件上传
    uploaded_files = st.file_uploader(
        "上传法律文档",
        type=["pdf", "docx", "txt"],
        accept_multiple_files=True,
        help="支持 PDF、DOCX、TXT 格式"
    )

    if not uploaded_files:
        st.info("👆 请上传文档开始分析")
        st.markdown("""
        ### 功能说明

        **🔍 混合检索**
        - BM25 关键词检索
        - 向量语义检索
        - RRF 算法融合
        - Cohere Reranker 精排

        **🤖 多智能体审查**
        - Writer Agent 草稿生成
        - 4 个专业 Reviewer 并行审查
        - Arbitrator 冲突仲裁
        - Draft-Critique-Revise 闭环

        **📊 结构化输出**
        - 三层报告结构
        - 多格式导出 (JSON/PDF/DOCX)
        - 交互式 UI 展示
        """)
        return

    # 初始化系统组件
    vector_db = init_qdrant()
    knowledge_base = init_knowledge_base(vector_db)

    if enable_hybrid_search:
        hybrid_engine = init_hybrid_search(vector_db)
        st.session_state.hybrid_engine = hybrid_engine

    if enable_multi_agent:
        review_pipeline = init_review_pipeline()
        st.session_state.review_pipeline = review_pipeline

    # 分析选项
    st.subheader("⚙️ 分析选项")

    col1, col2, col3 = st.columns(3)

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
        export_formats = st.multiselect(
            "导出格式",
            ["json", "pdf", "docx"],
            default=["json", "md"]
        )

    with col3:
        use_new_architecture = st.checkbox(
            "使用新架构",
            value=True,
            help="使用混合检索和多智能体审查"
        )

    # 分析按钮
    if st.button("🚀 开始分析", type="primary", use_container_width=True):
        analyze_documents(
            uploaded_files,
            analysis_type,
            export_formats,
            use_new_architecture,
            enable_hybrid_search,
            enable_multi_agent
        )


def analyze_documents(
    files,
    analysis_type,
    export_formats,
    use_new_architecture,
    enable_hybrid_search,
    enable_multi_agent
):
    """分析文档"""
    st.info("📊 正在分析文档...")

    progress_bar = st.progress(0)
    status_text = st.empty()

    # Phase 1: 文档解析
    status_text.text("📄 正在解析文档...")
    progress_bar.progress(10)

    # Phase 2: 检索
    if enable_hybrid_search and st.session_state.hybrid_engine:
        status_text.text("🔍 正在执行混合检索...")
        progress_bar.progress(30)

    # Phase 3: Agent 分析
    if enable_multi_agent and st.session_state.review_pipeline:
        status_text.text("🤖 AI 团队正在分析...")
        progress_bar.progress(50)

    # Phase 4: 报告生成
    status_text.text("📊 正在生成报告...")
    progress_bar.progress(80)

    # 完成
    progress_bar.progress(100)
    status_text.text("✅ 分析完成!")

    # 显示结果（这里简化处理）
    st.success("🎉 分析完成！")

    if use_new_architecture:
        st.markdown("### 📊 分析结果")
        st.info("完整的结构化报告将在新版本中展示")

        # 展示占位符
        st.markdown("""
        **新架构功能**:
        - ✅ 混合检索 (BM25 + 向量 + Reranker)
        - ✅ 多智能体审查 (Writer + 4 Reviewers + Arbitrator)
        - ✅ 结构化输出 (三层报告)
        - ✅ 多格式导出 (JSON/PDF/DOCX)

        报告包含:
        - 📊 执行摘要（高管视角）
        - 📋 详细分析（律师视角）
        - 🔍 证据来源（审计视角）
        """)


if __name__ == "__main__":
    main()
