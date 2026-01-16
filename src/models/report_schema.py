"""
完整报告数据模型
三层报告结构：Executive Summary + Detailed Analysis + Evidence Sources
"""

from pydantic import BaseModel, Field, validator
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum
from decimal import Decimal


class DocumentType(str, Enum):
    """文档类型"""
    EMPLOYMENT_CONTRACT = "employment_contract"
    SERVICE_AGREEMENT = "service_agreement"
    NDA = "nda"
    SALES_CONTRACT = "sales_contract"
    LEASE_AGREEMENT = "lease_agreement"
    INVESTMENT_AGREEMENT = "investment_agreement"
    PARTNERSHIP_AGREEMENT = "partnership_agreement"
    OTHER = "other"


class RiskLevel(str, Enum):
    """风险等级"""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


# ========== 第一层：执行摘要 ==========

class QuickRecommendation(BaseModel):
    """快速建议"""
    priority: RiskLevel = Field(..., description="优先级")
    action_item: str = Field(..., description="行动建议")
    urgency: str = Field(..., description="紧急程度：立即处理/建议尽快/可选")
    category: str = Field(default="general", description="建议类别")


class ExecutiveSummary(BaseModel):
    """
    执行摘要 - 面向高管/客户

    目标受众：企业高管、法务负责人、决策者
    内容特点：简洁明了、突出重点、可操作性强
    """

    # 基本信息
    document_type: DocumentType = Field(..., description="文档类型")
    document_title: str = Field(..., description="文档标题")
    analysis_date: datetime = Field(default_factory=datetime.now, description="分析日期")

    # 评分系统
    overall_rating: float = Field(
        ...,
        ge=0,
        le=10,
        description="综合评分 (0-10)"
    )
    rating_explanation: str = Field(
        ...,
        description="评分说明"
    )
    rating_breakdown: Optional[Dict[str, float]] = Field(
        default_factory=dict,
        description="评分细分 (如: {法律合规: 8.5, 风险控制: 7.0})"
    )

    # 风险概览
    risk_summary: Dict[RiskLevel, int] = Field(
        ...,
        description="各风险级别数量统计"
    )
    key_risks: List[str] = Field(
        ...,
        min_items=1,
        max_items=5,
        description="前 5 个关键风险点"
    )

    # 关键问题
    critical_issues: List[str] = Field(
        default_factory=list,
        max_items=3,
        description="必须立即处理的严重问题"
    )

    # 快速建议
    quick_recommendations: List[QuickRecommendation] = Field(
        ...,
        min_items=1,
        max_items=10,
        description="优先级排序的行动建议"
    )

    # 一句话总结
    one_sentence_summary: str = Field(
        ...,
        max_length=300,
        description="一句话总结文档核心发现"
    )

    # 联系信息
    reviewer_name: str = Field(default="AI 法律分析系统", description="审查者名称")
    reviewer_contact: Optional[str] = Field(None, description="审查者联系方式")

    @validator('risk_summary')
    def validate_risk_summary(cls, v):
        """验证风险摘要"""
        total = sum(v.values())
        if total == 0:
            raise ValueError("风险摘要不能全为 0")
        return v

    def to_markdown(self) -> str:
        """转换为 Markdown 格式"""
        md = f"""
# {self.document_title} - 执行摘要

## 评分概览
- **综合评分**: {self.overall_rating}/10
- **评分说明**: {self.rating_explanation}

### 评分细分
"""
        if self.rating_breakdown:
            for category, score in self.rating_breakdown.items():
                md += f"- **{category}**: {score}/10\n"

        md += f"""
## 风险分布
"""
        for level, count in self.risk_summary.items():
            md += f"- **{level.upper()}**: {count} 个\n"

        md += f"""
## 关键风险
"""
        for i, risk in enumerate(self.key_risks, 1):
            md += f"{i}. {risk}\n"

        if self.critical_issues:
            md += f"""
## ⚠️ 严重问题
"""
            for issue in self.critical_issues:
                md += f"- {issue}\n"

        md += f"""
## 快速建议
"""
        for i, rec in enumerate(self.quick_recommendations, 1):
            md += f"{i}. [{rec.priority.value.upper()}] {rec.action_item} - {rec.urgency}\n"

        md += f"""
## 总结
{self.one_sentence_summary}

---
*报告生成时间: {self.analysis_date.strftime('%Y-%m-%d %H:%M')}*
*审查者: {self.reviewer_name}*
"""
        return md


# ========== 第二层：详细分析 ==========

class LegalBasis(BaseModel):
    """法条依据"""
    article: str = Field(..., description="法条编号，如：第10条")
    law_name: str = Field(..., description="法律名称")
    full_citation: str = Field(..., description="完整引用")
    relevance_explanation: str = Field(..., description="相关性说明")
    url: Optional[str] = Field(None, description="法条链接（如有）")

    def __str__(self) -> str:
        return f"{self.law_name} {self.article}"


class ClauseAnalysis(BaseModel):
    """
    条款详细分析

    面向受众：律师、法务人员
    内容特点：详细、专业、有法理依据
    """

    clause_id: int = Field(..., ge=1, description="条款序号")
    clause_title: Optional[str] = Field(None, description="条款标题")
    clause_text: str = Field(..., description="条款原文或摘要")
    clause_type: str = Field(..., description="条款类型：责任/义务/权利/终止等")

    # 风险评估
    risk_level: RiskLevel = Field(..., description="风险等级")
    risk_score: float = Field(
        ...,
        ge=0,
        le=100,
        description="风险分数 (0-100)"
    )

    # 问题与建议
    issues_identified: List[str] = Field(
        default_factory=list,
        description="识别出的问题列表"
    )
    suggestions: List[str] = Field(
        default_factory=list,
        description="改进建议"
    )

    # 法律依据
    legal_basis: List[LegalBasis] = Field(
        default_factory=list,
        description="相关法条引用"
    )

    # 审查者意见
    reviewer_comments: Dict[str, str] = Field(
        default_factory=dict,
        description="各审查者的意见"
    )

    # 影响分析
    impact_analysis: Optional[str] = Field(
        None,
        description="影响分析"
    )


class ComplianceChecklist(BaseModel):
    """合规性检查清单"""
    check_item: str = Field(..., description="检查项名称")
    is_compliant: bool = Field(..., description="是否合规")
    explanation: str = Field(..., description="说明")
    reference: Optional[str] = Field(None, description="参考依据")
    severity: Optional[RiskLevel] = Field(None, description="不合规的严重程度")


class JurisdictionAnalysis(BaseModel):
    """管辖权分析"""
    applicable_law: str = Field(..., description="适用法律")
    jurisdiction: str = Field(..., description="管辖法院/仲裁机构")
    governing_language: str = Field(..., description="主导语言")
    cross_border_considerations: Optional[List[str]] = Field(
        None,
        description="跨境考虑因素（如适用）"
    )
    legal_framework: Optional[str] = Field(None, description="法律框架描述")


class DetailedAnalysis(BaseModel):
    """
    详细分析 - 面向律师/法务

    目标受众：法务人员、律师、合规官
    内容特点：详细、专业、有法律依据、可操作
    """

    # 统计信息
    total_clauses: int = Field(..., description="分析的总条款数")
    clauses_with_issues: int = Field(..., description="有问题的条款数")
    compliance_rate: float = Field(
        ...,
        ge=0,
        le=100,
        description="合规率 (%)"
    )

    # 条款分析
    clause_breakdown: List[ClauseAnalysis] = Field(
        ...,
        description="逐条分析结果"
    )

    # 合规性检查
    compliance_checklist: List[ComplianceChecklist] = Field(
        ...,
        description="合规性检查清单"
    )

    # 管辖权分析
    jurisdiction_analysis: Optional[JurisdictionAnalysis] = Field(
        None,
        description="管辖权分析"
    )

    # 特殊关注事项
    special_considerations: List[str] = Field(
        default_factory=list,
        description="需要特别关注的事项"
    )

    # 条款修改建议
    recommended_clauses: List[Dict[str, str]] = Field(
        default_factory=list,
        description="建议新增或修改的条款"
    )

    # 分析方法论
    methodology: Optional[str] = Field(
        None,
        description="分析方法说明"
    )

    def to_markdown(self) -> str:
        """转换为 Markdown 格式"""
        md = f"""
# 详细分析

## 概览
- **总条款数**: {self.total_clauses}
- **有问题条款**: {self.clauses_with_issues}
- **合规率**: {self.compliance_rate:.1f}%

## 条款分析
"""
        for clause in self.clause_breakdown:
            md += f"""
### 条款 {clause.clause_id}. {clause.clause_title or ''}

**类型**: {clause.clause_type}
**风险等级**: {clause.risk_level.value}
**风险分数**: {clause.risk_score}/100

**内容**:
{clause.clause_text}

"""
            if clause.issues_identified:
                md += "**问题**:\n"
                for issue in clause.issues_identified:
                    md += f"- {issue}\n"
                md += "\n"

            if clause.suggestions:
                md += "**建议**:\n"
                for suggestion in clause.suggestions:
                    md += f"- {suggestion}\n"
                md += "\n"

            if clause.legal_basis:
                md += "**法律依据**:\n"
                for basis in clause.legal_basis:
                    md += f"- {basis}\n"
                md += "\n"

        if self.compliance_checklist:
            md += """
## 合规性检查清单
"""
            for item in self.compliance_checklist:
                status = "✅ 合规" if item.is_compliant else f"❌ 不合规 - {item.severity.value if item.severity else ''}"
                md += f"- [{status}] {item.check_item}: {item.explanation}\n"

        if self.jurisdiction_analysis:
            md += f"""
## 管辖权分析
- **适用法律**: {self.jurisdiction_analysis.applicable_law}
- **管辖机构**: {self.jurisdiction_analysis.jurisdiction}
- **主导语言**: {self.jurisdiction_analysis.governing_language}
"""

        return md


# ========== 第三层：证据来源 ==========

class SourceType(str, Enum):
    """来源类型"""
    KNOWLEDGE_BASE = "knowledge_base"
    LEGAL_DATABASE = "legal_database"
    CASE_LAW = "case_law"
    USER_INPUT = "user_input"
    AGENT_REASONING = "agent_reasoning"
    INTERNAL = "internal"


class EvidenceSource(BaseModel):
    """证据来源"""
    source_type: SourceType = Field(..., description="来源类型")
    source_id: str = Field(..., description="来源唯一标识")
    content: str = Field(..., description="来源内容")
    relevance_score: float = Field(
        ...,
        ge=0,
        le=1,
        description="相关性分数"
    )
    timestamp: datetime = Field(default_factory=datetime.now)

    # 检索元数据
    retrieval_method: str = Field(..., description="检索方法：bm25/vector/rerank")
    original_rank: int = Field(..., description="原始排名")

    # 可验证性
    url: Optional[str] = Field(None, description="来源 URL（如适用）")
    citation: Optional[str] = Field(None, description="学术引用格式")
    metadata: Optional[Dict[str, Any]] = Field(
        default_factory=dict,
        description="额外元数据"
    )


class AgentReasoning(BaseModel):
    """Agent 推理链"""
    agent_name: str = Field(..., description="Agent 名称")
    agent_role: str = Field(..., description="Agent 角色")

    # 推理过程
    reasoning_process: str = Field(..., description="推理过程说明")
    key_facts: List[str] = Field(..., description="关键事实提取")
    logic_chain: List[str] = Field(..., description="逻辑链条")

    # 置信度
    confidence: float = Field(
        ...,
        ge=0,
        le=1,
        description="置信度"
    )
    uncertainty_sources: List[str] = Field(
        default_factory=list,
        description="不确定性来源"
    )

    # 依据
    sources_used: List[EvidenceSource] = Field(
        ...,
        description="使用的证据来源"
    )

    # 元数据
    timestamp: datetime = Field(default_factory=datetime.now)
    processing_duration_seconds: float = Field(
        ...,
        description="处理耗时（秒）"
    )


# ========== 完整报告 ==========

class LegalDocumentReport(BaseModel):
    """
    完整法律文档分析报告

    三层结构:
    1. Executive Summary - 执行摘要（高管视角）
    2. Detailed Analysis - 详细分析（律师视角）
    3. Evidence Sources - 证据来源（审计视角）
    """

    # ========== 元数据 ==========
    report_metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="报告元数据"
    )

    document_id: str = Field(..., description="文档唯一标识")
    document_name: str = Field(..., description="文档名称")
    document_hash: Optional[str] = Field(None, description="文档哈希（用于完整性验证）")

    analysis_metadata: Dict[str, Any] = Field(
        ...,
        description="分析元数据"
    )
    analysis_timestamp: datetime = Field(default_factory=datetime.now, description="分析时间戳")
    analysis_version: str = Field(default="2.0", description="分析版本号")
    analysis_duration_seconds: float = Field(
        ...,
        description="分析耗时（秒）"
    )

    # ========== 三层结构 ==========
    executive_summary: ExecutiveSummary = Field(
        ...,
        description="执行摘要"
    )
    detailed_analysis: DetailedAnalysis = Field(
        ...,
        description="详细分析"
    )

    # ========== 证据与推理 ==========
    evidence_sources: List[EvidenceSource] = Field(
        ...,
        description="证据来源列表"
    )
    agent_reasoning_chain: List[AgentReasoning] = Field(
        ...,
        description="所有 Agent 的推理链"
    )

    # ========== 导出配置 ==========
    export_config: Dict[str, Any] = Field(
        default_factory=dict,
        description="导出配置"
    )

    # ========== 验证器 ==========
    @validator('analysis_duration_seconds')
    def validate_duration(cls, v):
        """验证分析时长"""
        if v <= 0:
            raise ValueError("分析时长必须大于 0")
        if v > 3600:  # 超过 1 小时
            raise ValueError("分析时长异常，超过 1 小时")
        return v

    # ========== 导出方法 ==========
    def to_json(self, indent: int = 2, ensure_ascii: bool = False) -> str:
        """
        导出为 JSON

        Args:
            indent: 缩进空格数
            ensure_ascii: 是否确保 ASCII 编码

        Returns:
            JSON 字符串
        """
        import json
        from .encoders import datetime_encoder

        return json.dumps(
            self.dict(),
            indent=indent,
            ensure_ascii=ensure_ascii,
            default=datetime_encoder
        )

    def get_executive_summary_markdown(self) -> str:
        """获取执行摘要的 Markdown 格式"""
        return self.executive_summary.to_markdown()

    def get_detailed_analysis_markdown(self) -> str:
        """获取详细分析的 Markdown 格式"""
        return self.detailed_analysis.to_markdown()

    def get_full_markdown(self) -> str:
        """获取完整报告的 Markdown 格式"""
        md = f"""# {self.document_name} - 法律分析报告

生成时间: {self.analysis_timestamp.strftime('%Y-%m-%d %H:%M:%S')}
分析版本: {self.analysis_version}
分析耗时: {self.analysis_duration_seconds:.2f} 秒

---

{self.get_executive_summary_markdown()}

---

{self.get_detailed_analysis_markdown()}

---

## 证据来源

"""
        for source in self.evidence_sources:
            md += f"- **[{source.source_type.value}]** {source.content} (相关性: {source.relevance_score:.2f})\n"

        md += "\n## Agent 推理链\n\n"

        for reasoning in self.agent_reasoning_chain:
            md += f"""
### {reasoning.agent_name} ({reasoning.agent_role})

**置信度**: {reasoning.confidence:.2f}
**耗时**: {reasoning.processing_duration_seconds:.2f}s

**推理过程**:
{reasoning.reasoning_process}

**关键事实**:
"""
            for fact in reasoning.key_facts:
                md += f"- {fact}\n"

            md += "\n"

        return md

    def get_summary_dict(self) -> Dict[str, Any]:
        """获取报告摘要字典（用于快速预览）"""
        return {
            "document_name": self.document_name,
            "document_type": self.executive_summary.document_type.value,
            "overall_rating": self.executive_summary.overall_rating,
            "total_clauses": self.detailed_analysis.total_clauses,
            "clauses_with_issues": self.detailed_analysis.clauses_with_issues,
            "compliance_rate": self.detailed_analysis.compliance_rate,
            "critical_issues_count": self.executive_summary.risk_summary.get(RiskLevel.CRITICAL, 0),
            "high_issues_count": self.executive_summary.risk_summary.get(RiskLevel.HIGH, 0),
            "analysis_duration": self.analysis_duration_seconds,
            "analysis_timestamp": self.analysis_timestamp.isoformat()
        }


# 辅助函数
def datetime_encoder(obj):
    """datetime JSON 编码器"""
    if isinstance(obj, datetime):
        return obj.isoformat()
    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")
