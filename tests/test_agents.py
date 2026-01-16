"""
Agent 层单元测试
测试 Writer, Reviewers, Arbitrator 和 Pipeline
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime

from src.agents.writer_agent import WriterAgent
from src.agents.legal_reviewer import LegalReviewerAgent
from src.agents.risk_reviewer import RiskReviewerAgent
from src.agents.format_reviewer import FormatReviewerAgent
from src.agents.business_reviewer import BusinessReviewerAgent
from src.agents.arbitrator_agent import ArbitratorAgent
from src.orchestration.review_pipeline import ReviewPipeline, create_review_pipeline

from src.models.review_models import (
    ReviewFeedback,
    ReviewIssue,
    ReviewerType,
    SeverityLevel,
    IssueCategory,
    IssueLocation,
    DraftReport,
    ConsolidatedFeedback
)
from src.models.search_models import SearchContext, SearchResult, RetrievalMethod


# ======== Fixtures ========

@pytest.fixture
def sample_document():
    """示例文档"""
    return {
        "id": "doc1",
        "title": "劳动合同",
        "type": "劳动合同",
        "content": "甲方：XXX公司\n乙方：张三\n\n第一条 合同期限\n本合同期限为三年..."
    }


@pytest.fixture
def sample_search_context():
    """示例检索上下文"""
    results = [
        SearchResult(
            doc_id="law1",
            score=0.9,
            retrieval_method=RetrievalMethod.BM25,
            content="劳动合同法第10条规定...",
            title="劳动合同法"
        )
    ]

    return SearchContext(
        query="劳动合同法",
        results=results,
        statistics=Mock(total_retrieved=1, duration_ms=100)
    )


@pytest.fixture
def sample_draft():
    """示例草稿"""
    return DraftReport(
        draft_id="draft_123",
        document_id="doc1",
        document_title="劳动合同",
        content_summary="这是一份劳动合同的初步分析",
        key_clauses=[],
        initial_assessment="文档结构完整",
        risk_indicators=["需要关注工资条款"],
        generation_duration_seconds=5.0
    )


@pytest.fixture
def sample_review_feedback():
    """示例审查反馈"""
    return ReviewFeedback(
        reviewer_type=ReviewerType.LEGAL,
        reviewer_name="LegalReviewer",
        issues=[
            ReviewIssue(
                issue_id="issue_1",
                reviewer_type=ReviewerType.LEGAL,
                severity=SeverityLevel.HIGH,
                category=IssueCategory.LEGAL_COMPLIANCE,
                title="法条引用不准确",
                description="第3条引用的法条编号有误",
                location=IssueLocation(
                    clause_id=3,
                    text_excerpt="根据劳动法第X条规定"
                ),
                suggested_fix="更正为劳动合同法第10条"
            )
        ],
        overall_rating=7.5,
        rating_explanation="整体合规，但有小问题",
        summary="文档基本合规，需要修正部分法条引用",
        key_findings=["法条引用问题"],
        confidence=0.9,
        uncertainty_sources=[],
        review_timestamp=datetime.now(),
        review_duration_seconds=10.0
    )


# ======== Writer Agent 测试 ========

class TestWriterAgent:
    """Writer Agent 测试"""

    @pytest.mark.asyncio
    async def test_generate_draft_success(self, sample_document, sample_search_context):
        """测试：成功生成草稿"""
        # Mock Agent
        with patch('src.agents.writer_agent.AGNO_AVAILABLE', True):
            with patch('src.agents.writer_agent.Agent') as mock_agent_class:
                mock_agent = Mock()
                mock_agent.arun = AsyncMock(return_value={
                    "summary": "测试摘要",
                    "key_clauses": [],
                    "assessment": "测试评估",
                    "risks": []
                })
                mock_agent_class.return_value = mock_agent

                writer = WriterAgent(api_key="test-key")
                draft = await writer.generate_draft(
                    document=sample_document,
                    search_context=sample_search_context
                )

                assert draft.document_id == "doc1"
                assert draft.content_summary == "测试摘要"

    @pytest.mark.asyncio
    async def test_generate_draft_fallback(self, sample_document, sample_search_context):
        """测试：降级处理"""
        with patch('src.agents.writer_agent.AGNO_AVAILABLE', True):
            with patch('src.agents.writer_agent.Agent') as mock_agent_class:
                mock_agent = Mock()
                mock_agent.arun = AsyncMock(side_effect=Exception("API Error"))
                mock_agent_class.return_value = mock_agent

                writer = WriterAgent(api_key="test-key")
                draft = await writer.generate_draft(
                    document=sample_document,
                    search_context=sample_search_context
                )

                # 应该返回降级草稿
                assert "fallback" in draft.draft_id


# ======== Reviewer Agent 测试 ========

class TestLegalReviewerAgent:
    """Legal Reviewer Agent 测试"""

    @pytest.mark.asyncio
    async def test_review_success(self, sample_draft, sample_document, sample_search_context):
        """测试：成功审查"""
        with patch('src.agents.reviewer_agent.AGNO_AVAILABLE', True):
            with patch('src.agents.reviewer_agent.Agent') as mock_agent_class:
                mock_agent = Mock()
                mock_agent.arun = AsyncMock(return_value={
                    "issues": [
                        {
                            "title": "测试问题",
                            "description": "这是一个测试问题",
                            "severity": "high",
                            "category": "legal_compliance",
                            "location": {
                                "clause_id": 1,
                                "text_excerpt": "测试文本"
                            },
                            "suggested_fix": "建议修正"
                        }
                    ],
                    "rating": 8.0,
                    "rating_explanation": "测试评分说明",
                    "summary": "测试总结",
                    "key_findings": ["发现1", "发现2"],
                    "confidence": 0.9,
                    "uncertainties": []
                })
                mock_agent_class.return_value = mock_agent

                reviewer = LegalReviewerAgent(api_key="test-key")
                feedback = await reviewer.review(
                    draft=sample_draft,
                    document=sample_document,
                    search_context=sample_search_context
                )

                assert feedback.reviewer_type == ReviewerType.LEGAL
                assert len(feedback.issues) == 1
                assert feedback.overall_rating == 8.0

    def test_get_role(self):
        """测试：获取角色"""
        with patch('src.agents.reviewer_agent.AGNO_AVAILABLE', True):
            reviewer = LegalReviewerAgent(api_key="test-key")
            role = reviewer._get_role()
            assert "法律合规审查员" in role

    def test_get_instructions(self):
        """测试：获取指令"""
        with patch('src.agents.reviewer_agent.AGNO_AVAILABLE', True):
            reviewer = LegalReviewerAgent(api_key="test-key")
            instructions = reviewer._get_instructions()
            assert isinstance(instructions, list)
            assert len(instructions) > 0

    def test_get_review_focus(self):
        """测试：获取审查重点"""
        with patch('src.agents.reviewer_agent.AGNO_AVAILABLE', True):
            reviewer = LegalReviewerAgent(api_key="test-key")
            focus = reviewer._get_review_focus()
            assert isinstance(focus, list)
            assert len(focus) > 0


class TestRiskReviewerAgent:
    """Risk Reviewer Agent 测试"""

    def test_reviewer_type(self):
        """测试：审查者类型"""
        with patch('src.agents.reviewer_agent.AGNO_AVAILABLE', True):
            reviewer = RiskReviewerAgent(api_key="test-key")
            assert reviewer.reviewer_type == ReviewerType.RISK


class TestFormatReviewerAgent:
    """Format Reviewer Agent 测试"""

    def test_reviewer_type(self):
        """测试：审查者类型"""
        with patch('src.agents.reviewer_agent.AGNO_AVAILABLE', True):
            reviewer = FormatReviewerAgent(api_key="test-key")
            assert reviewer.reviewer_type == ReviewerType.FORMAT


class TestBusinessReviewerAgent:
    """Business Reviewer Agent 测试"""

    def test_reviewer_type(self):
        """测试：审查者类型"""
        with patch('src.agents.reviewer_agent.AGNO_AVAILABLE', True):
            reviewer = BusinessReviewerAgent(api_key="test-key")
            assert reviewer.reviewer_type == ReviewerType.BUSINESS


# ======== Arbitrator Agent 测试 ========

class TestArbitratorAgent:
    """Arbitrator Agent 测试"""

    @pytest.mark.asyncio
    async def test_arbitrate_no_conflicts(self, sample_draft, sample_review_feedback):
        """测试：无冲突仲裁"""
        with patch('src.agents.arbitrator_agent.AGNO_AVAILABLE', True):
            arbitrator = ArbitratorAgent(api_key="test-key")

            feedbacks = [sample_review_feedback]

            # Mock Agent
            with patch.object(arbitrator.agent, 'arun') as mock_arun:
                mock_arun.return_value = {
                    "instructions": "请根据问题列表进行修订"
                }

                result = await arbitrator.arbitrate(
                    draft=sample_draft,
                    review_feedbacks=feedbacks,
                    document=sample_document()
                )

                assert isinstance(result, ConsolidatedFeedback)
                assert len(result.prioritized_issues) > 0

    def test_reviewer_priority(self):
        """测试：审查者优先级"""
        with patch('src.agents.arbitrator_agent.AGNO_AVAILABLE', True):
            arbitrator = ArbitratorAgent(api_key="test-key")

            assert arbitrator.reviewer_priority[ReviewerType.LEGAL] == 1
            assert arbitrator.reviewer_priority[ReviewerType.RISK] == 2
            assert arbitrator.reviewer_priority[ReviewerType.BUSINESS] == 3
            assert arbitrator.reviewer_priority[ReviewerType.FORMAT] == 4

    def test_severity_priority(self):
        """测试：严重程度优先级"""
        with patch('src.agents.arbitrator_agent.AGNO_AVAILABLE', True):
            arbitrator = ArbitratorAgent(api_key="test-key")

            assert arbitrator.severity_priority[SeverityLevel.CRITICAL] == 0
            assert arbitrator.severity_priority[SeverityLevel.HIGH] == 1
            assert arbitrator.severity_priority[SeverityLevel.MEDIUM] == 2


# ======== Review Pipeline 测试 ========

class TestReviewPipeline:
    """Review Pipeline 测试"""

    @pytest.fixture
    def mock_pipeline(self):
        """Mock Pipeline"""
        # Mock Writer
        mock_writer = Mock(spec=WriterAgent)
        mock_writer.generate_draft = AsyncMock(return_value=Mock(
            draft_id="draft_123",
            document_id="doc1",
            document_title="测试文档",
            content_summary="测试摘要",
            key_clauses=[],
            initial_assessment="测试评估",
            risk_indicators=[]
        ))
        mock_writer.revise_draft = AsyncMock(return_value=Mock(
            report_id="report_123",
            draft_id="draft_123",
            document_id="doc1",
            version="1.0",
            revision_round=1,
            consolidated_feedback=Mock(prioritized_issues=[]),
            executive_summary="执行摘要",
            detailed_analysis={},
            recommendations=[],
            issue_resolution_rate=1.0,
            reviewer_agreement_score=1.0
        ))

        # Mock Reviewers
        mock_reviewers = {
            ReviewerType.LEGAL: Mock(spec=LegalReviewerAgent),
            ReviewerType.RISK: Mock(spec=RiskReviewerAgent),
        }

        for reviewer in mock_reviewers.values():
            reviewer.review = AsyncMock(return_value=Mock(
                reviewer_type=ReviewerType.LEGAL,
                issues=[],
                overall_rating=8.0,
                rating_explanation="",
                summary="",
                key_findings=[],
                confidence=0.9,
                uncertainty_sources=[],
                review_timestamp=datetime.now(),
                review_duration_seconds=5.0
            ))

        # Mock Arbitrator
        mock_arbitrator = Mock(spec=ArbitratorAgent)
        mock_arbitrator.arbitrate = AsyncMock(return_value=Mock(
            arbitration_id="arb_123",
            prioritized_issues=[],
            conflicts_resolved=[],
            revision_instructions="修订指导",
            priority_actions=[],
            estimated_revision_rounds=1,
            revision_focus_areas=[],
            all_reviewer_feedback=[],
            arbitration_duration_seconds=2.0
        ))

        return ReviewPipeline(
            writer_agent=mock_writer,
            reviewers=mock_reviewers,
            arbitrator=mock_arbitrator,
            enable_parallel=True,
            max_rounds=1
        )

    @pytest.mark.asyncio
    async def test_execute_success(self, mock_pipeline, sample_document, sample_search_context):
        """测试：成功执行流程"""
        result = await mock_pipeline.execute(
            document=sample_document,
            search_context=sample_search_context
        )

        # 验证调用
        mock_pipeline.writer.generate_draft.assert_called_once()
        assert len(mock_pipeline.reviewers) == 2
        mock_pipeline.arbitrator.arbitrate.assert_called_once()
        mock_pipeline.writer.revise_draft.assert_called_once()

    def test_get_pipeline_info(self, mock_pipeline):
        """测试：获取 Pipeline 信息"""
        info = mock_pipeline.get_pipeline_info()

        assert "enabled_reviewers" in info
        assert "enable_parallel" in info
        assert info["enable_parallel"] is True
        assert info["max_rounds"] == 1


# ======== 集成测试 ========

class TestAgentIntegration:
    """集成测试"""

    @pytest.mark.asyncio
    async def test_end_to_end_review(self, sample_document, sample_search_context):
        """测试：端到端审查流程（简化版）"""
        # 注意：这需要真实的 API key，通常在集成测试中使用
        # 这里仅展示测试结构

        # Mock 所有 Agent
        with patch('src.agents.writer_agent.AGNO_AVAILABLE', True), \
             patch('src.agents.reviewer_agent.AGNO_AVAILABLE', True), \
             patch('src.agents.arbitrator_agent.AGNO_AVAILABLE', True):

            # 创建 Mock 响应
            mock_draft_response = {
                "summary": "测试摘要",
                "key_clauses": [],
                "assessment": "测试评估",
                "risks": []
            }

            mock_review_response = {
                "issues": [],
                "rating": 8.0,
                "rating_explanation": "评分说明",
                "summary": "审查总结",
                "key_findings": [],
                "confidence": 0.9,
                "uncertainties": []
            }

            mock_arbitrate_response = {
                "instructions": "修订指导"
            }

            # 由于需要 Mock 多个 Agent，这里简化处理
            # 实际测试中应该使用更完整的 Mock 设置


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
