"""
Format Reviewer Agent
格式规范审查员
"""

from ..models.review_models import ReviewerType, IssueCategory


class FormatReviewerAgent(BaseReviewerAgent):
    """
    Format Reviewer - 格式规范审查员

    职责:
    1. 确保文档结构完整、层次清晰
    2. 检查术语使用的一致性
    3. 验证编号、日期、格式的规范性
    4. 发现文字错误和语法问题

    优先级: 4 (最低)
    """

    def __init__(self, model_name: str = "gpt-4o", api_key: str = None):
        super().__init__(
            reviewer_type=ReviewerType.FORMAT,
            reviewer_name="FormatReviewer",
            model_name=model_name,
            api_key=api_key
        )

    def _get_role(self) -> str:
        return """你是一位细致的格式审查专家。

你的职责是：
1. 确保文档结构完整、层次清晰、逻辑连贯
2. 检查术语使用的一致性和规范性
3. 验证编号、日期、签章等格式的规范性
4. 发现错别字、语法错误和标点符号问题

请以专业标准确保文档的规范性和可读性。"""

    def _get_instructions(self) -> list:
        return [
            "你是法律文档分析团队的格式规范专家。",
            "你需要从文档规范性和可读性角度审查。",
            "重点关注:",
            "  - 文档结构是否完整",
            "  - 术语使用是否一致",
            "  - 编号和格式是否规范",
            "  - 是否存在错别字或语法错误",
            "  - 标点符号使用是否正确",
            "",
            "严重程度判断标准:",
            "  - CRITICAL: 结构缺失导致理解困难",
            "  - HIGH: 严重格式错误影响专业性",
            "  - MEDIUM: 格式不一致或小错误",
            "  - LOW: 轻微格式问题",
            "  - INFO: 格式优化建议"
        ]

    def _get_review_focus(self) -> list:
        return [
            "文档结构是否完整（标题、条款、签署等）",
            "编号体系是否规范、连续",
            "日期格式是否统一、正确",
            "术语使用是否一致、准确",
            "是否存在错别字、语法错误",
            "标点符号使用是否规范",
            "段落划分是否合理",
            "签章栏是否齐全"
        ]
