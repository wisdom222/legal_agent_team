"""
Business Reviewer Agent
商业逻辑审查员
"""
from .base_reviewer import BaseReviewerAgent
from ..models.review_models import ReviewerType, IssueCategory


class BusinessReviewerAgent(BaseReviewerAgent):
    """
    Business Reviewer - 商业逻辑审查员

    职责:
    1. 评估交易条款的商业合理性
    2. 判断是否符合市场惯例
    3. 识别可能影响商业目标的风险
    4. 提出平衡各方利益的建议

    优先级: 3
    """

    def __init__(self, model_name: str = "gpt-4o", api_key: str = None):
        super().__init__(
            reviewer_type=ReviewerType.BUSINESS,
            reviewer_name="BusinessReviewer",
            model_name=model_name,
            api_key=api_key
        )

    def _get_role(self) -> str:
        return """你是一位经验丰富的商业顾问。

你的职责是：
1. 评估交易条款的商业合理性和可行性
2. 判断条款是否符合市场惯例和行业规范
3. 识别可能影响商业目标和可持续性的风险
4. 提出平衡各方利益的改进建议

请从商业成功和可持续性角度提出建议。"""

    def _get_instructions(self) -> list:
        return [
            "你是法律文档分析团队的商业顾问。",
            "你需要从商业可行性和合理性角度审查。",
            "重点关注:",
            "  - 交易条款是否公平合理",
            "  - 是否符合市场惯例",
            "  - 商业目标是否清晰可达",
            "  - 是否存在商业陷阱",
            "  - 条款对业务运营的影响",
            "",
            "严重程度判断标准:",
            "  - CRITICAL: 严重影响商业可行性",
            "  - HIGH: 显著偏离市场惯例",
            "  - MEDIUM: 商业条款不够优化",
            "  - LOW: 轻微商业问题",
            "  - INFO: 商业优化建议"
        ]

    def _get_review_focus(self) -> list:
        return [
            "价格和付款条款是否合理",
            "交货和服务条款是否明确",
            "违约责任是否对等、公平",
            "合同期限和终止条件是否合理",
            "保密条款是否符合商业需求",
            "知识产权条款是否清晰",
            "是否存在限制竞争的不合理条款",
            "整体交易结构是否平衡"
        ]
