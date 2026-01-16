"""
Writer Agent
负责生成文档分析的初步草稿
"""

import time
import uuid
from typing import List, Dict, Any
from datetime import datetime

try:
    from agno import Agent
    from agno.models.openai import OpenAIChat
    AGNO_AVAILABLE = True
except ImportError:
    AGNO_AVAILABLE = False

from ..models.review_models import (
    DraftReport,
    FinalReport,
    AgentContext,
    generate_issue_id
)
from ..models.search_models import SearchContext


class WriterAgent:
    """
    Writer Agent - 文档分析草稿生成专家

    职责:
    1. 分析文档内容
    2. 基于检索结果生成初步分析
    3. 识别关键条款和风险点
    4. 生成结构化草稿报告

    支持:
    - 草稿生成 (generate_draft)
    - 草稿修订 (revise_draft)
    """

    def __init__(
        self,
        model_name: str = "gpt-4o",
        api_key: str = None,
        enable_structured_output: bool = True
    ):
        """
        初始化 Writer Agent

        Args:
            model_name: OpenAI 模型名称
            api_key: OpenAI API 密钥
            enable_structured_output: 是否启用结构化输出
        """
        if not AGNO_AVAILABLE:
            raise ImportError("Agno 包未安装。请运行: pip install agno")

        self.model_name = model_name
        self.enable_structured_output = enable_structured_output

        # 创建 Agno Agent
        self.agent = Agent(
            name="WriterAgent",
            role="法律文档分析草稿专家",
            model=OpenAIChat(id=model_name, api_key=api_key),
            instructions=self._get_instructions(),
            show_tool_calls=True,
            markdown=True
        )

    def _get_instructions(self) -> List[str]:
        """获取 Agent 指令"""
        return [
            "你是法律文档分析团队的起草专家。",
            "你的职责是基于检索到的知识库信息，对文档进行初步分析。",
            "你需要:",
            "1. 仔细阅读文档内容",
            "2. 理解文档的性质和目的",
            "3. 识别关键条款和重要内容",
            "4. 指出潜在的风险点",
            "5. 生成结构化的分析草稿",
            "",
            "重要原则:",
            "- 客观中立，基于事实",
            "- 不做最终判断，仅提出初步看法",
            "- 标注不确定的地方",
            "- 为后续审查者提供清晰的上下文"
        ]

    async def generate_draft(
        self,
        document: Dict[str, Any],
        search_context: SearchContext,
        analysis_type: str = "contract_review"
    ) -> DraftReport:
        """
        生成文档分析草稿

        Args:
            document: 文档信息（包含 id, title, content 等）
            search_context: 检索上下文
            analysis_type: 分析类型

        Returns:
            DraftReport 对象
        """
        start_time = time.time()

        # 构建提示词
        prompt = self._build_draft_prompt(
            document,
            search_context,
            analysis_type
        )

        # 调用 Agent 生成草稿
        try:
            response = await self.agent.arun(prompt)

            # 解析响应
            draft_id = f"draft_{uuid.uuid4().hex[:8]}"

            draft = DraftReport(
                draft_id=draft_id,
                document_id=document.get("id", ""),
                document_title=document.get("title", ""),
                content_summary=response.get("summary", ""),
                key_clauses=response.get("key_clauses", []),
                initial_assessment=response.get("assessment", ""),
                risk_indicators=response.get("risks", []),
                created_at=datetime.now(),
                generation_duration_seconds=time.time() - start_time
            )

            return draft

        except Exception as e:
            print(f"⚠️ Writer Agent 生成草稿失败: {e}")
            # 返回简化版草稿
            return self._create_fallback_draft(
                document,
                search_context,
                start_time
            )

    async def revise_draft(
        self,
        draft: DraftReport,
        feedback: Any,  # ConsolidatedFeedback
        search_context: SearchContext
    ) -> FinalReport:
        """
        根据反馈修订草稿

        Args:
            draft: 原始草稿
            feedback: 整合后的反馈
            search_context: 检索上下文

        Returns:
            FinalReport 对象
        """
        start_time = time.time()

        # 构建修订提示词
        prompt = self._build_revision_prompt(draft, feedback)

        # 调用 Agent 修订
        try:
            response = await self.agent.arun(prompt)

            # 构建最终报告
            report_id = f"report_{uuid.uuid4().hex[:8]}"

            final_report = FinalReport(
                report_id=report_id,
                draft_id=draft.draft_id,
                document_id=draft.document_id,
                version="1.0",
                revision_round=1,
                consolidated_feedback=feedback,
                executive_summary=response.get("summary", ""),
                detailed_analysis=response.get("analysis", {}),
                recommendations=response.get("recommendations", []),
                finalized_at=datetime.now(),
                total_duration_seconds=time.time() - start_time,
                issue_resolution_rate=self._calculate_resolution_rate(feedback),
                reviewer_agreement_score=self._calculate_agreement_score(feedback)
            )

            return final_report

        except Exception as e:
            print(f"⚠️ Writer Agent 修订失败: {e}")
            # 返回简化版报告
            return self._create_fallback_report(
                draft,
                feedback,
                start_time
            )

    def _build_draft_prompt(
        self,
        document: Dict[str, Any],
        search_context: SearchContext,
        analysis_type: str
    ) -> str:
        """构建草稿生成提示词"""
        prompt = f"""
# 文档分析任务

## 文档信息
- 文档 ID: {document.get('id', '')}
- 文档标题: {document.get('title', '')}
- 文档类型: {document.get('type', '')}
- 分析类型: {analysis_type}

## 文档内容
{document.get('content', '')[:3000]}...

## 检索到的相关知识
{search_context.to_string()}

## 任务要求
请基于以上信息，生成一份文档分析草稿，包含以下内容：

1. **内容摘要** (summary): 简明扼要地概括文档核心内容
2. **关键条款** (key_clauses): 列出3-5个最重要的条款，每个包含:
   - 条款序号/标题
   - 条款内容摘要
   - 初步评估

3. **初步评估** (assessment):
   - 文档整体质量评价
   - 主要特点和亮点
   - 潜在的关注点

4. **风险指标** (risks): 列出3-5个潜在风险点或需要注意的方面

请以 JSON 格式返回，包含上述字段。
"""
        return prompt

    def _build_revision_prompt(
        self,
        draft: DraftReport,
        feedback: Any
    ) -> str:
        """构建修订提示词"""
        prompt = f"""
# 草稿修订任务

## 原始草稿
- 草稿 ID: {draft.draft_id}
- 内容摘要: {draft.content_summary}
- 初步评估: {draft.initial_assessment}

## 审查反馈
共有 {len(feedback.prioritized_issues)} 个问题需要处理

### 优先级问题
{self._format_issues(feedback.prioritized_issues[:5])}

### 修订指导
{feedback.revision_instructions}

### 优先级行动
{chr(10).join(f"- {action}" for action in feedback.priority_actions)}

## 任务要求
请基于以上反馈，修订草稿并生成最终报告，包含：

1. **执行摘要** (summary): 面向高管的简洁总结
2. **详细分析** (analysis):
   - 逐条分析关键条款
   - 问题整改情况
   - 风险评估结果
3. **建议** (recommendations): 3-5条可执行的建议

请以 JSON 格式返回。
"""
        return prompt

    def _format_issues(self, issues: List) -> str:
        """格式化问题列表"""
        formatted = []
        for issue in issues:
            formatted.append(
                f"- **[{issue.severity.value}]** {issue.title}: {issue.description}"
            )
        return "\n".join(formatted)

    def _calculate_resolution_rate(self, feedback: Any) -> float:
        """计算问题解决率"""
        if not feedback.prioritized_issues:
            return 1.0

        resolved_count = sum(1 for issue in feedback.prioritized_issues if issue.resolved)
        return resolved_count / len(feedback.prioritized_issues)

    def _calculate_agreement_score(self, feedback: Any) -> float:
        """计算审查者一致性分数"""
        # 简化实现：基于冲突解决情况
        if not feedback.conflicts_resolved:
            return 1.0

        # 冲突越少，一致性越高
        return max(0.0, 1.0 - len(feedback.conflicts_resolved) * 0.1)

    def _create_fallback_draft(
        self,
        document: Dict[str, Any],
        search_context: SearchContext,
        start_time: float
    ) -> DraftReport:
        """创建降级草稿"""
        draft_id = f"draft_fallback_{uuid.uuid4().hex[:8]}"

        return DraftReport(
            draft_id=draft_id,
            document_id=document.get("id", ""),
            document_title=document.get("title", ""),
            content_summary=f"对《{document.get('title', '')》的初步分析",
            key_clauses=[],
            initial_assessment="草稿生成遇到问题，使用简化版本",
            risk_indicators=[],
            created_at=datetime.now(),
            generation_duration_seconds=time.time() - start_time
        )

    def _create_fallback_report(
        self,
        draft: DraftReport,
        feedback: Any,
        start_time: float
    ) -> FinalReport:
        """创建降级报告"""
        report_id = f"report_fallback_{uuid.uuid4().hex[:8]}"

        return FinalReport(
            report_id=report_id,
            draft_id=draft.draft_id,
            document_id=draft.document_id,
            version="1.0",
            revision_round=1,
            consolidated_feedback=feedback,
            executive_summary=draft.content_summary,
            detailed_analysis={},
            recommendations=[],
            finalized_at=datetime.now(),
            total_duration_seconds=time.time() - start_time,
            issue_resolution_rate=0.0,
            reviewer_agreement_score=0.5
        )


# 工厂函数
def create_writer_agent(
    model_name: str = "gpt-4o",
    api_key: str = None,
    enable_structured_output: bool = True
) -> WriterAgent:
    """
    创建 Writer Agent

    Args:
        model_name: OpenAI 模型名称
        api_key: OpenAI API 密钥
        enable_structured_output: 是否启用结构化输出

    Returns:
        WriterAgent 实例
    """
    return WriterAgent(
        model_name=model_name,
        api_key=api_key,
        enable_structured_output=enable_structured_output
    )
