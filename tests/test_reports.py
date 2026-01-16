"""
报告层单元测试
测试报告 Schema、导出器和 UI 组件
"""

import pytest
from datetime import datetime
from pathlib import Path
import tempfile
import json

from src.models.report_schema import (
    ExecutiveSummary,
    DetailedAnalysis,
    ClauseAnalysis,
    ComplianceChecklist,
    LegalDocumentReport,
    DocumentType,
    RiskLevel,
    QuickRecommendation
)
from src.reports.exporter import (
    JSONExporter,
    MarkdownExporter,
    PDFExporter,
    DOCXExporter,
    ReportExporter
)


# ======== Fixtures ========

@pytest.fixture
def sample_executive_summary():
    """示例执行摘要"""
    return ExecutiveSummary(
        document_type=DocumentType.EMPLOYMENT_CONTRACT,
        document_title="劳动合同",
        overall_rating=7.5,
        rating_explanation="文档整体合规，但存在一些需要关注的风险点",
        rating_breakdown={
            "法律合规": 8.0,
            "风险控制": 7.0,
            "格式规范": 7.5
        },
        risk_summary={
            RiskLevel.CRITICAL: 1,
            RiskLevel.HIGH: 2,
            RiskLevel.MEDIUM: 3,
            RiskLevel.LOW: 1
        },
        key_risks=[
            "工资支付条款不够明确",
            "合同期限可能违反法律规定",
            "违约责任不对等"
        ],
        critical_issues=[
            "第3条违反劳动合同法第10条",
            "第8条违约金过高可能无效"
        ],
        quick_recommendations=[
            QuickRecommendation(
                priority=RiskLevel.CRITICAL,
                action_item="修正第3条合同期限条款",
                urgency="立即处理",
                category="legal_compliance"
            ),
            QuickRecommendation(
                priority=RiskLevel.HIGH,
                action_item="补充工资支付的具体时间和方式",
                urgency="建议尽快",
                category="payment"
            )
        ],
        one_sentence_summary="该劳动合同基本框架完整，但存在法律合规风险和条款不明确问题，需要修订。"
    )


@pytest.fixture
def sample_detailed_analysis():
    """示例详细分析"""
    return DetailedAnalysis(
        total_clauses=10,
        clauses_with_issues=4,
        compliance_rate=60.0,
        clause_breakdown=[
            ClauseAnalysis(
                clause_id=1,
                clause_title="合同期限",
                clause_text="本合同期限为三年",
                clause_type="期限条款",
                risk_level=RiskLevel.HIGH,
                risk_score=75.0,
                issues_identified=[
                    "合同期限可能过长",
                    "缺少试用期规定"
                ],
                suggestions=[
                    "考虑缩短合同期限",
                    "增加试用期条款"
                ],
                legal_basis=[],
                reviewer_comments={},
                impact_analysis="可能影响员工流动性"
            )
        ],
        compliance_checklist=[
            ComplianceChecklist(
                check_item="书面形式",
                is_compliant=True,
                explanation="合同采用书面形式，符合规定",
                reference="劳动合同法第10条"
            ),
            ComplianceChecklist(
                check_item="工资标准",
                is_compliant=False,
                explanation="未明确工资标准",
                reference="劳动合同法第17条",
                severity=RiskLevel.HIGH
            )
        ],
        jurisdiction_analysis=None,
        special_considerations=[
            "需要关注试用期规定",
            "注意解除合同条件"
        ],
        recommended_clauses=[]
    )


@pytest.fixture
def sample_report(sample_executive_summary, sample_detailed_analysis):
    """示例完整报告"""
    return LegalDocumentReport(
        document_id="doc_123",
        document_name="劳动合同_张三",
        analysis_metadata={
            "analyzer_version": "2.0",
            "analysis_type": "contract_review"
        },
        analysis_duration_seconds=120.5,
        executive_summary=sample_executive_summary,
        detailed_analysis=sample_detailed_analysis,
        evidence_sources=[],
        agent_reasoning_chain=[]
    )


# ======== ExecutiveSummary 测试 ========

class TestExecutiveSummary:
    """ExecutiveSummary 测试"""

    def test_create_executive_summary(self, sample_executive_summary):
        """测试：创建执行摘要"""
        assert sample_executive_summary.document_type == DocumentType.EMPLOYMENT_CONTRACT
        assert sample_executive_summary.overall_rating == 7.5
        assert len(sample_executive_summary.key_risks) == 3
        assert len(sample_executive_summary.quick_recommendations) == 2

    def test_risk_summary_validation(self):
        """测试：风险摘要验证"""
        with pytest.raises(ValueError):
            ExecutiveSummary(
                document_type=DocumentType.EMPLOYMENT_CONTRACT,
                document_title="测试",
                overall_rating=5.0,
                rating_explanation="测试",
                risk_summary={},  # 空风险摘要应该失败
                key_risks=["测试风险"],
                quick_recommendations=[],
                one_sentence_summary="测试"
            )

    def test_to_markdown(self, sample_executive_summary):
        """测试：转换为 Markdown"""
        md = sample_executive_summary.to_markdown()

        assert "劳动合同" in md
        assert "7.5/10" in md
        assert "关键风险" in md
        assert "快速建议" in md

    def test_rating_breakdown(self, sample_executive_summary):
        """测试：评分细分"""
        breakdown = sample_executive_summary.rating_breakdown
        assert "法律合规" in breakdown
        assert breakdown["法律合规"] == 8.0


# ======== DetailedAnalysis 测试 ========

class TestDetailedAnalysis:
    """DetailedAnalysis 测试"""

    def test_create_detailed_analysis(self, sample_detailed_analysis):
        """测试：创建详细分析"""
        assert sample_detailed_analysis.total_clauses == 10
        assert sample_detailed_analysis.clauses_with_issues == 4
        assert sample_detailed_analysis.compliance_rate == 60.0
        assert len(sample_detailed_analysis.clause_breakdown) == 1
        assert len(sample_detailed_analysis.compliance_checklist) == 2

    def test_clause_analysis(self, sample_detailed_analysis):
        """测试：条款分析"""
        clause = sample_detailed_analysis.clause_breakdown[0]

        assert clause.clause_id == 1
        assert clause.clause_title == "合同期限"
        assert clause.risk_level == RiskLevel.HIGH
        assert clause.risk_score == 75.0
        assert len(clause.issues_identified) == 2
        assert len(clause.suggestions) == 2

    def test_compliance_checklist(self, sample_detailed_analysis):
        """测试：合规性检查清单"""
        checklist = sample_detailed_analysis.compliance_checklist

        compliant_items = [item for item in checklist if item.is_compliant]
        non_compliant_items = [item for item in checklist if not item.is_compliant]

        assert len(compliant_items) == 1
        assert len(non_compliant_items) == 1

        # 测试不合规项
        non_compliant = non_compliant_items[0]
        assert non_compliant.severity == RiskLevel.HIGH

    def test_to_markdown(self, sample_detailed_analysis):
        """测试：转换为 Markdown"""
        md = sample_detailed_analysis.to_markdown()

        assert "总条款数: 10" in md
        assert "有问题条款: 4" in md
        assert "合规率: 60.0%" in md
        assert "条款 1" in md


# ======== LegalDocumentReport 测试 ========

class TestLegalDocumentReport:
    """LegalDocumentReport 测试"""

    def test_create_report(self, sample_report):
        """测试：创建报告"""
        assert sample_report.document_id == "doc_123"
        assert sample_report.document_name == "劳动合同_张三"
        assert sample_report.analysis_version == "2.0"
        assert sample_report.analysis_duration_seconds == 120.5

    def test_duration_validation(self):
        """测试：时长验证"""
        # 正常时长
        report = LegalDocumentReport(
            document_id="doc1",
            document_name="测试",
            analysis_metadata={},
            analysis_duration_seconds=100,
            executive_summary=ExecutiveSummary(
                document_type=DocumentType.OTHER,
                document_title="测试",
                overall_rating=5.0,
                rating_explanation="测试",
                risk_summary={RiskLevel.LOW: 1},
                key_risks=[],
                quick_recommendations=[],
                one_sentence_summary="测试"
            ),
            detailed_analysis=DetailedAnalysis(
                total_clauses=1,
                clauses_with_issues=0,
                compliance_rate=100.0,
                clause_breakdown=[],
                compliance_checklist=[]
            ),
            evidence_sources=[],
            agent_reasoning_chain=[]
        )
        assert report.analysis_duration_seconds == 100

        # 时长过短
        with pytest.raises(ValueError):
            LegalDocumentReport(
                document_id="doc1",
                document_name="测试",
                analysis_metadata={},
                analysis_duration_seconds=0,  # 无效
                executive_summary=ExecutiveSummary(
                    document_type=DocumentType.OTHER,
                    document_title="测试",
                    overall_rating=5.0,
                    rating_explanation="测试",
                    risk_summary={RiskLevel.LOW: 1},
                    key_risks=[],
                    quick_recommendations=[],
                    one_sentence_summary="测试"
                ),
                detailed_analysis=DetailedAnalysis(
                    total_clauses=1,
                    clauses_with_issues=0,
                    compliance_rate=100.0,
                    clause_breakdown=[],
                    compliance_checklist=[]
                ),
                evidence_sources=[],
                agent_reasoning_chain=[]
            )

    def test_to_json(self, sample_report):
        """测试：转换为 JSON"""
        json_str = sample_report.to_json()

        assert isinstance(json_str, str)
        assert "劳动合同_张三" in json_str

        # 验证可以解析回来
        data = json.loads(json_str)
        assert data["document_name"] == "劳动合同_张三"

    def test_get_summary_dict(self, sample_report):
        """测试：获取摘要字典"""
        summary = sample_report.get_summary_dict()

        assert summary["document_name"] == "劳动合同_张三"
        assert summary["overall_rating"] == 7.5
        assert summary["total_clauses"] == 10
        assert summary["clauses_with_issues"] == 4
        assert summary["compliance_rate"] == 60.0


# ======== 导出器测试 ========

class TestJSONExporter:
    """JSON 导出器测试"""

    def test_export_json(self, sample_report):
        """测试：导出 JSON"""
        with tempfile.TemporaryDirectory() as tmpdir:
            exporter = JSONExporter(tmpdir)
            filepath = exporter.export(sample_report, "test_report")

            # 验证文件存在
            assert Path(filepath).exists()
            assert filepath.endswith(".json")

            # 验证内容
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
                assert data["document_name"] == "劳动合同_张三"


class TestMarkdownExporter:
    """Markdown 导出器测试"""

    def test_export_markdown(self, sample_report):
        """测试：导出 Markdown"""
        with tempfile.TemporaryDirectory() as tmpdir:
            exporter = MarkdownExporter(tmpdir)
            filepath = exporter.export(sample_report, "test_report")

            # 验证文件存在
            assert Path(filepath).exists()
            assert filepath.endswith(".md")

            # 验证内容
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
                assert "# 劳动合同_张三 - 法律分析报告" in content
                assert "执行摘要" in content


class TestReportExporter:
    """ReportExporter 测试"""

    def test_export_multiple_formats(self, sample_report):
        """测试：导出多种格式"""
        with tempfile.TemporaryDirectory() as tmpdir:
            exporter = ReportExporter(tmpdir)

            results = exporter.export(
                report=sample_report,
                formats=["json", "md"],
                filename="test"
            )

            assert "json" in results
            assert "md" in results
            assert Path(results["json"]).exists()
            assert Path(results["md"]).exists()

    def test_export_all(self, sample_report):
        """测试：导出所有格式"""
        with tempfile.TemporaryDirectory() as tmpdir:
            exporter = ReportExporter(tmpdir)

            results = exporter.export_all(sample_report, "test_all")

            # 应该至少有 json 和 md（其他可能因依赖问题降级）
            assert "json" in results
            assert "md" in results


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
