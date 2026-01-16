"""
Legal Reviewer Agent
法律合规审查员
"""
from .base_reviewer import BaseReviewerAgent
from ..models.review_models import ReviewerType, IssueCategory


class LegalReviewerAgent(BaseReviewerAgent):
    """
    Legal Reviewer - 法律合规审查员

    职责:
    1. 检查法条引用的准确性
    2. 验证管辖权和适用法律
    3. 识别潜在的法律风险
    4. 确保符合强制性法律规定

    优先级: 1 (最高)
    """

    def __init__(self, model_name: str = "gpt-4o", api_key: str = None):
        super().__init__(
            reviewer_type=ReviewerType.LEGAL,
            reviewer_name="LegalReviewer",
            model_name=model_name,
            api_key=api_key
        )

    def _get_role(self) -> str:
        return """你是一位资深的法律合规审查员。

你的职责是：
1. 检查所有法条引用的准确性和完整性
2. 验证管辖权条款和适用法律的合规性
3. 识别可能违反强制性法律规定的内容
4. 指出法律风险和不合规条款

请以严格的法治标准进行审查，任何法律合规性问题都应标记为 CRITICAL 级别。"""

    def _get_instructions(self) -> list:
        return [
            "你是法律文档分析团队的法律合规审查专家。",
            "你需要从法律角度严格审查文档。",
            "重点关注:",
            "  - 法条引用是否准确、完整",
            "  - 管辖权条款是否合规",
            "  - 是否存在法律风险",
            "  - 是否违反强制性法律规定",
            "",
            "严重程度判断标准:",
            "  - CRITICAL: 违反强制性法律，可能导致合同无效",
            "  - HIGH: 存在较大法律风险，可能引发纠纷",
            "  - MEDIUM: 法律表述不清晰或存在瑕疵",
            "  - LOW: 轻微的法律问题",
            "  - INFO: 法律提示信息"
        ]

    def _get_review_focus(self) -> list:
        return [
            "法条引用准确性（法律名称、条文编号是否正确）",
            "管辖权和适用法律是否符合规定",
            "是否存在违反强制性法律规定的条款",
            "法律风险评估（合同无效、违约责任等）",
            "法律术语使用是否准确",
            "法律逻辑是否严密"
        ]
