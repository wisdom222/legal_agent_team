"""
Risk Reviewer Agent
风险评估审查员
"""

from ..models.review_models import ReviewerType, IssueCategory


class RiskReviewerAgent(BaseReviewerAgent):
    """
    Risk Reviewer - 风险评估审查员

    职责:
    1. 识别可能导致纠纷的条款
    2. 评估责任分配的公平性
    3. 指出潜在的经济和声誉风险
    4. 量化风险等级和影响范围

    优先级: 2
    """

    def __init__(self, model_name: str = "gpt-4o", api_key: str = None):
        super().__init__(
            reviewer_type=ReviewerType.RISK,
            reviewer_name="RiskReviewer",
            model_name=model_name,
            api_key=api_key
        )

    def _get_role(self) -> str:
        return """你是一位专业的风险评估专家。

你的职责是：
1. 识别可能导致纠纷的合同条款
2. 评估责任分配的公平性和合理性
3. 指出潜在的经济风险和声誉风险
4. 量化风险等级和可能的影响范围

请从风险防范角度提出建设性意见，帮助降低合同风险。"""

    def _get_instructions(self) -> list:
        return [
            "你是法律文档分析团队的风险评估专家。",
            "你需要从风险控制角度审查文档。",
            "重点关注:",
            "  - 不公平条款（霸王条款）",
            "  - 责任分配是否合理",
            "  - 潜在争议点识别",
            "  - 违约成本和风险评估",
            "  - 不可抗力条款",
            "",
            "严重程度判断标准:",
            "  - CRITICAL: 极高风险，可能导致重大损失",
            "  - HIGH: 高风险，可能引发纠纷",
            "  - MEDIUM: 中等风险，需要关注",
            "  - LOW: 低风险，可接受",
            "  - INFO: 风险提示"
        ]

    def _get_review_focus(self) -> list:
        return [
            "是否存在不公平、不合理的条款",
            "责任分配是否均衡、合理",
            "违约责任是否明确、对等",
            "潜在争议点的识别和评估",
            "经济风险量化（违约金、赔偿等）",
            "不可抗力和免责条款是否合理",
            "合同终止条件是否清晰"
        ]
