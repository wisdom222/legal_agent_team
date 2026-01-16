"""
Agent 审查数据模型
定义审查反馈、问题、仲裁结果等数据结构
"""

from pydantic import BaseModel, Field, validator
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum


class ReviewerType(str, Enum):
    """审查者类型"""
    LEGAL = "legal"
    RISK = "risk"
    FORMAT = "format"
    BUSINESS = "business"
    WRITER = "writer"
    ARBITRATOR = "arbitrator"


class SeverityLevel(str, Enum):
    """严重程度"""
    CRITICAL = "critical"  # 必须修正
    HIGH = "high"         # 强烈建议修正
    MEDIUM = "medium"     # 建议修正
    LOW = "low"           # 可选修正
    INFO = "info"         # 信息提示


class IssueCategory(str, Enum):
    """问题类别"""
    LEGAL_COMPLIANCE = "legal_compliance"       # 法律合规
    RISK_ASSESSMENT = "risk_assessment"         # 风险评估
    FORMAT_STANDARD = "format_standard"         # 格式规范
    BUSINESS_LOGIC = "business_logic"           # 商业逻辑
    CONTRACT_TERM = "contract_term"             # 合同条款
    JURISDICTION = "jurisdiction"               # 管辖权
    TERMINATION = "termination"                 # 终止条款
    LIABILITY = "liability"                     # 责任条款
    PAYMENT = "payment"                         # 支付条款
    CONFIDENTIALITY = "confidentiality"         # 保密条款
    OTHER = "other"                             # 其他


class IssueLocation(BaseModel):
    """问题位置"""
    clause_id: Optional[int] = Field(None, description="条款序号")
    paragraph_index: Optional[int] = Field(None, description="段落索引")
    line_number: Optional[int] = Field(None, description="行号")
    text_excerpt: str = Field(..., description="问题文本摘录")
    page_number: Optional[int] = Field(None, description="页码")

    @validator('text_excerpt')
    def validate_excerpt_length(cls, v):
        """验证摘录长度"""
        if len(v) > 500:
            raise ValueError("文本摘录过长，最多 500 字符")
        return v


class LegalBasis(BaseModel):
    """法条依据"""
    article: str = Field(..., description="法条编号，如：第10条")
    law_name: str = Field(..., description="法律名称")
    full_citation: str = Field(..., description="完整引用")
    relevance_explanation: str = Field(..., description="相关性说明")
    url: Optional[str] = Field(None, description="法条链接（如有）")

    def __str__(self) -> str:
        return f"{self.law_name} {self.article}"


class ReviewIssue(BaseModel):
    """审查发现的问题"""
    issue_id: str = Field(..., description="问题唯一标识")
    reviewer_type: ReviewerType = Field(..., description="审查者类型")
    severity: SeverityLevel = Field(..., description="严重程度")
    category: IssueCategory = Field(..., description="问题类别")
    title: str = Field(..., description="问题标题")
    description: str = Field(..., description="问题描述")

    # 位置信息
    location: IssueLocation = Field(..., description="问题位置")

    # 建议和依据
    suggested_fix: Optional[str] = Field(None, description="建议修正方案")
    legal_basis: Optional[List[LegalBasis]] = Field(
        default_factory=list,
        description="法条依据"
    )

    # 影响评估
    impact_assessment: Optional[str] = Field(None, description="影响评估")
    likelihood: Optional[str] = Field(None, description="发生可能性")

    # 元数据
    created_at: datetime = Field(default_factory=datetime.now)
    resolved: bool = Field(default=False, description="是否已解决")
    resolution_note: Optional[str] = Field(None, description="解决说明")

    class Config:
        use_enum_values = True


class ReviewFeedback(BaseModel):
    """单个 Reviewer 的反馈"""
    reviewer_type: ReviewerType = Field(..., description="审查者类型")
    reviewer_name: str = Field(..., description="审查者名称")
    reviewer_version: str = Field(default="1.0", description="审查者版本")

    # 问题列表
    issues: List[ReviewIssue] = Field(
        default_factory=list,
        description="发现的问题列表"
    )

    # 整体评估
    overall_rating: float = Field(
        ...,
        ge=0,
        le=10,
        description="综合评分 (0-10)"
    )
    rating_explanation: str = Field(..., description="评分说明")

    # 审查总结
    summary: str = Field(..., description="审查总结")
    key_findings: List[str] = Field(
        default_factory=list,
        description="关键发现"
    )

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

    # 元数据
    review_timestamp: datetime = Field(default_factory=datetime.now)
    review_duration_seconds: float = Field(..., description="审查耗时（秒）")

    # 统计信息
    issue_count_by_severity: Dict[SeverityLevel, int] = Field(
        default_factory=dict,
        description="各级别问题数量"
    )

    @validator('issue_count_by_severity', always=True)
    def calculate_issue_counts(cls, v, values):
        """自动计算各级别问题数量"""
        if 'issues' in values:
            counts = {}
            for issue in values['issues']:
                severity = issue.severity
                counts[severity] = counts.get(severity, 0) + 1
            return counts
        return v

    class Config:
        use_enum_values = True


class ConflictResolution(BaseModel):
    """冲突解决方案"""
    conflict_id: str = Field(..., description="冲突唯一标识")
    conflict_description: str = Field(..., description="冲突描述")

    # 涉及的审查者
    involved_reviewers: List[ReviewerType] = Field(
        ...,
        description="涉及冲突的审查者"
    )

    # 冲突的议题
    conflicting_issues: List[str] = Field(
        ...,
        description="冲突的问题 ID 列表"
    )

    # 解决策略
    resolution_strategy: str = Field(
        ...,
        description="解决策略: prioritize_legal/merge/escalate/keep_both"
    )

    # 最终决策
    final_decision: str = Field(..., description="最终决策说明")
    rationale: str = Field(..., description="决策理由")

    # 优先级
    priority: int = Field(..., ge=1, le=10, description="优先级 (1-10)")

    # 元数据
    resolved_at: datetime = Field(default_factory=datetime.now)
    requires_human_review: bool = Field(default=False, description="是否需要人工复核")

    class Config:
        use_enum_values = True


class ConsolidatedFeedback(BaseModel):
    """整合后的反馈（来自 Arbitrator）"""
    arbitration_id: str = Field(..., description="仲裁唯一标识")
    arbitration_timestamp: datetime = Field(default_factory=datetime.now)

    # 优先级排序后的问题
    prioritized_issues: List[ReviewIssue] = Field(
        ...,
        description="按优先级排序的问题列表"
    )

    # 冲突解决
    conflicts_resolved: List[ConflictResolution] = Field(
        default_factory=list,
        description="已解决的冲突列表"
    )

    # 修订指导
    revision_instructions: str = Field(..., description="修订指导")
    priority_actions: List[str] = Field(
        ...,
        description="优先级行动列表"
    )

    # 迭代建议
    estimated_revision_rounds: int = Field(
        default=1,
        ge=1,
        le=2,
        description="建议修订轮数"
    )
    revision_focus_areas: List[str] = Field(
        default_factory=list,
        description="修订重点关注领域"
    )

    # 元数据
    all_reviewer_feedback: List[ReviewFeedback] = Field(
        ...,
        description="所有审查者的原始反馈"
    )
    arbitration_duration_seconds: float = Field(
        ...,
        description="仲裁耗时（秒）"
    )

    class Config:
        use_enum_values = True


class DraftReport(BaseModel):
    """草稿报告（来自 Writer Agent）"""
    draft_id: str = Field(..., description="草稿唯一标识")
    document_id: str = Field(..., description="文档 ID")
    document_title: str = Field(..., description="文档标题")

    # 草稿内容
    content_summary: str = Field(..., description="内容摘要")
    key_clauses: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="关键条款分析"
    )

    # 初步评估
    initial_assessment: str = Field(..., description="初步评估")
    risk_indicators: List[str] = Field(
        default_factory=list,
        description="风险指标"
    )

    # 元数据
    created_at: datetime = Field(default_factory=datetime.now)
    writer_version: str = Field(default="1.0", description="Writer 版本")
    generation_duration_seconds: float = Field(
        ...,
        description="生成耗时（秒）"
    )


class FinalReport(BaseModel):
    """最终报告（经过审查和修订）"""
    report_id: str = Field(..., description="报告唯一标识")
    draft_id: str = Field(..., description="源草稿 ID")
    document_id: str = Field(..., description="文档 ID")

    # 报告版本
    version: str = Field(default="1.0", description="报告版本")
    revision_round: int = Field(default=1, ge=1, description="修订轮数")

    # 整合的反馈
    consolidated_feedback: ConsolidatedFeedback = Field(
        ...,
        description="整合后的反馈"
    )

    # 最终内容
    executive_summary: str = Field(..., description="执行摘要")
    detailed_analysis: Dict[str, Any] = Field(
        ...,
        description="详细分析"
    )
    recommendations: List[str] = Field(
        ...,
        description="建议列表"
    )

    # 元数据
    finalized_at: datetime = Field(default_factory=datetime.now)
    total_duration_seconds: float = Field(
        ...,
        description="总耗时（秒）"
    )

    # 质量指标
    issue_resolution_rate: float = Field(
        ...,
        ge=0,
        le=1,
        description="问题解决率"
    )
    reviewer_agreement_score: float = Field(
        ...,
        ge=0,
        le=1,
        description="审查者一致性分数"
    )


class AgentContext(BaseModel):
    """Agent 上下文"""
    document: Dict[str, Any] = Field(..., description="文档信息")
    search_context: Dict[str, Any] = Field(..., description="检索上下文")
    analysis_type: str = Field(..., description="分析类型")
    agent_config: Dict[str, Any] = Field(
        default_factory=dict,
        description="Agent 配置"
    )

    # 历史信息
    previous_feedback: Optional[List[ReviewFeedback]] = Field(
        None,
        description="之前的反馈（用于修订）"
    )
    revision_round: int = Field(default=1, description="当前修订轮数")


# 工具函数
def generate_issue_id() -> str:
    """生成问题 ID"""
    import uuid
    return f"issue_{uuid.uuid4().hex[:8]}"


def generate_conflict_id() -> str:
    """生成冲突 ID"""
    import uuid
    return f"conflict_{uuid.uuid4().hex[:8]}"


def prioritize_issues(issues: List[ReviewIssue]) -> List[ReviewIssue]:
    """
    按优先级排序问题

    排序规则:
    1. 严重程度: CRITICAL > HIGH > MEDIUM > LOW > INFO
    2. 同级别按类别排序
    """
    severity_order = {
        SeverityLevel.CRITICAL: 0,
        SeverityLevel.HIGH: 1,
        SeverityLevel.MEDIUM: 2,
        SeverityLevel.LOW: 3,
        SeverityLevel.INFO: 4
    }

    return sorted(
        issues,
        key=lambda x: (
            severity_order.get(x.severity, 99),
            x.category.value
        )
    )
