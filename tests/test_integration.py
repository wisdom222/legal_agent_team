"""
集成测试
测试完整的端到端流程
"""

import pytest
import asyncio
from pathlib import Path
import tempfile

from src.config.app_config import get_app_config
from src.retrieval.bm25_indexer import BM25Indexer
from src.retrieval.rrf_fusion import RRFFusion
from src.orchestration.review_pipeline import create_review_pipeline
from src.models.report_schema import LegalDocumentReport
from src.core.exceptions import ErrorHandler, is_retryable_error


@pytest.mark.asyncio
async def test_end_to_end_search_flow():
    """测试：端到端检索流程"""
    # 1. 创建示例文档
    from src.models.search_models import Document

    documents = [
        Document(
            id="doc1",
            content="劳动合同法规定，用人单位应当与劳动者订立书面劳动合同",
            title="劳动合同法",
            type="law"
        ),
        Document(
            id="doc2",
            content="试用期工资不得低于本单位相同岗位最低档工资的百分之八十",
            title="试用期规定",
            type="law"
        )
    ]

    # 2. 构建 BM25 索引
    bm25 = BM25Indexer()
    bm25.index_documents(documents)

    # 3. 执行检索
    results, duration = bm25.search("劳动合同", top_k=2)

    # 4. 验证结果
    assert len(results) > 0
    assert duration >= 0


@pytest.mark.asyncio
async def test_rrf_fusion_flow():
    """测试：RRF 融合流程"""
    from src.models.search_models import SearchResult, RetrievalMethod

    # 创建两路结果
    bm25_results = [
        SearchResult(doc_id="doc1", score=0.9, retrieval_method=RetrievalMethod.BM25),
        SearchResult(doc_id="doc2", score=0.8, retrieval_method=RetrievalMethod.BM25),
    ]

    vector_results = [
        SearchResult(doc_id="doc2", score=0.95, retrieval_method=RetrievalMethod.VECTOR),
        SearchResult(doc_id="doc3", score=0.85, retrieval_method=RetrievalMethod.VECTOR),
    ]

    # RRF 融合
    rrf = RRFFusion(k=60)
    fused_results, duration = rrf.fuse_two(bm25_results, vector_results, top_k=3)

    # 验证
    assert len(fused_results) > 0
    assert duration >= 0


@pytest.mark.asyncio
async def test_error_handling_flow():
    """测试：错误处理流程"""
    handler = ErrorHandler()

    # 测试可重试错误
    try:
        raise RuntimeError("Temporary failure")
    except Exception as e:
        response = handler.handle_error(e, {"operation": "test"})

        assert response["category"] in ["system", "retryable"]
        assert "user_message" in response


@pytest.mark.asyncio
async def test_config_loading():
    """测试：配置加载"""
    # 注意：这需要 .env 文件
    config = get_app_config()

    assert config is not None
    assert hasattr(config, "hybrid_search")
    assert hasattr(config, "agent")


@pytest.mark.asyncio
async def test_report_export_flow():
    """测试：报告导出流程"""
    from src.reports.exporter import ReportExporter

    # 创建简化报告
    from src.models.report_schema import (
        ExecutiveSummary,
        DetailedAnalysis,
        DocumentType,
        RiskLevel
    )

    summary = ExecutiveSummary(
        document_type=DocumentType.EMPLOYMENT_CONTRACT,
        document_title="测试合同",
        overall_rating=7.5,
        rating_explanation="测试",
        risk_summary={RiskLevel.LOW: 1},
        key_risks=["测试风险"],
        quick_recommendations=[],
        one_sentence_summary="测试"
    )

    analysis = DetailedAnalysis(
        total_clauses=1,
        clauses_with_issues=0,
        compliance_rate=100.0,
        clause_breakdown=[],
        compliance_checklist=[]
    )

    report = LegalDocumentReport(
        document_id="test",
        document_name="测试",
        analysis_metadata={},
        analysis_duration_seconds=10.0,
        executive_summary=summary,
        detailed_analysis=analysis,
        evidence_sources=[],
        agent_reasoning_chain=[]
    )

    # 导出测试
    with tempfile.TemporaryDirectory() as tmpdir:
        exporter = ReportExporter(tmpdir)
        results = exporter.export(
            report=report,
            formats=["json", "md"],
            filename="test_integration"
        )

        assert "json" in results
        assert "md" in results


def test_project_structure():
    """测试：项目结构完整性"""
    # 检查关键目录是否存在
    key_dirs = [
        "src/models",
        "src/retrieval",
        "src/agents",
        "src/orchestration",
        "src/reports",
        "src/core",
        "src/ui",
        "src/config",
        "tests",
        "docs"
    ]

    for dir_path in key_dirs:
        assert Path(dir_path).exists(), f"目录不存在: {dir_path}"

    # 检查关键文件是否存在
    key_files = [
        "requirements.txt",
        "README.md",
        ".gitignore",
        "docker-compose.yml",
        "Dockerfile"
    ]

    for file_path in key_files:
        assert Path(file_path).exists(), f"文件不存在: {file_path}"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
