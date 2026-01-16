"""
Reviewer Agent 基类
定义审查者的通用接口和功能
"""

import time
from typing import List, Dict, Any
from datetime import datetime
from abc import ABC, abstractmethod

try:
    from agno import Agent
    from agno.models.openai import OpenAIChat
    AGNO_AVAILABLE = True
except ImportError:
    AGNO_AVAILABLE = False

from ..models.review_models import (
    ReviewFeedback,
    ReviewIssue,
    ReviewerType,
    SeverityLevel,
    IssueCategory,
    IssueLocation,
    generate_issue_id
)
from ..models.search_models import SearchContext


class BaseReviewerAgent(ABC):
    """
    Reviewer Agent 基类

    所有具体审查者（Legal, Risk, Format, Business）都应继承此类
    """

    def __init__(
        self,
        reviewer_type: ReviewerType,
        reviewer_name: str,
        model_name: str = "gpt-4o",
        api_key: str = None
    ):
        """
        初始化 Reviewer Agent

        Args:
            reviewer_type: 审查者类型
            reviewer_name: 审查者名称
            model_name: OpenAI 模型名称
            api_key: OpenAI API 密钥
        """
        if not AGNO_AVAILABLE:
            raise ImportError("Agno 包未安装。请运行: pip install agno")

        self.reviewer_type = reviewer_type
        self.reviewer_name = reviewer_name
        self.model_name = model_name

        # 创建 Agno Agent
        self.agent = Agent(
            name=reviewer_name,
            role=self._get_role(),
            model=OpenAIChat(id=model_name, api_key=api_key),
            instructions=self._get_instructions(),
            show_tool_calls=True,
            markdown=True
        )

    @abstractmethod
    def _get_role(self) -> str:
        """获取角色描述（子类实现）"""
        pass

    @abstractmethod
    def _get_instructions(self) -> List[str]:
        """获取审查指令（子类实现）"""
        pass

    @abstractmethod
    def _get_review_focus(self) -> List[str]:
        """获取审查重点（子类实现）"""
        pass

    async def review(
        self,
        draft: Any,
        document: Dict[str, Any],
        search_context: SearchContext
    ) -> ReviewFeedback:
        """
        执行审查

        Args:
            draft: 草稿报告
            document: 原始文档
            search_context: 检索上下文

        Returns:
            ReviewFeedback 对象
        """
        start_time = time.time()

        # 构建审查提示词
        prompt = self._build_review_prompt(draft, document, search_context)

        # 调用 Agent 审查
        try:
            response = await self.agent.arun(prompt)

            # 解析响应
            issues = self._parse_issues(response.get("issues", []))

            feedback = ReviewFeedback(
                reviewer_type=self.reviewer_type,
                reviewer_name=self.reviewer_name,
                issues=issues,
                overall_rating=response.get("rating", 7.0),
                rating_explanation=response.get("rating_explanation", ""),
                summary=response.get("summary", ""),
                key_findings=response.get("key_findings", []),
                confidence=response.get("confidence", 0.8),
                uncertainty_sources=response.get("uncertainties", []),
                review_timestamp=datetime.now(),
                review_duration_seconds=time.time() - start_time
            )

            return feedback

        except Exception as e:
            print(f"⚠️ {self.reviewer_name} 审查失败: {e}")
            # 返回空反馈
            return self._create_empty_feedback(start_time)

    def _build_review_prompt(
        self,
        draft: Any,
        document: Dict[str, Any],
        search_context: SearchContext
    ) -> str:
        """构建审查提示词"""
        prompt = f"""
# {self.reviewer_name} 审查任务

## 你的角色
{self._get_role()}

## 审查重点
{chr(10).join(f"- {focus}" for focus in self._get_review_focus())}

## 文档信息
- 文档 ID: {document.get('id', '')}
- 文档标题: {document.get('title', '')}
- 文档类型: {document.get('type', '')}

## 草稿内容
{self._format_draft(draft)}

## 检索到的相关知识
{search_context.to_string()}

## 审查要求
请基于你的专业视角，对文档进行全面审查，重点关注上述审查重点。

请以 JSON 格式返回，包含以下字段：
- issues: 发现的问题列表（每个问题包含 title, description, severity, category, location, suggested_fix）
- rating: 综合评分 (0-10)
- rating_explanation: 评分说明
- summary: 审查总结
- key_findings: 关键发现列表 (3-5条)
- confidence: 置信度 (0-1)
- uncertainties: 不确定性来源列表
"""
        return prompt

    def _format_draft(self, draft: Any) -> str:
        """格式化草稿内容"""
        if hasattr(draft, 'content_summary'):
            return f"""
内容摘要:
{draft.content_summary}

关键条款:
{self._format_key_clauses(draft.key_clauses)}

初步评估:
{draft.initial_assessment}
"""
        else:
            return str(draft)

    def _format_key_clauses(self, clauses: List) -> str:
        """格式化关键条款"""
        if not clauses:
            return "无"
        formatted = []
        for i, clause in enumerate(clauses, 1):
            if isinstance(clause, dict):
                formatted.append(f"{i}. {clause.get('title', '')}: {clause.get('content', '')}")
            else:
                formatted.append(f"{i}. {clause}")
        return "\n".join(formatted)

    def _parse_issues(self, issues_data: List[Dict]) -> List[ReviewIssue]:
        """解析问题数据"""
        issues = []
        for issue_data in issues_data:
            try:
                location_data = issue_data.get("location", {})
                location = IssueLocation(
                    clause_id=location_data.get("clause_id"),
                    paragraph_index=location_data.get("paragraph_index"),
                    line_number=location_data.get("line_number"),
                    text_excerpt=location_data.get("text_excerpt", ""),
                    page_number=location_data.get("page_number")
                )

                issue = ReviewIssue(
                    issue_id=generate_issue_id(),
                    reviewer_type=self.reviewer_type,
                    severity=SeverityLevel(issue_data.get("severity", "medium")),
                    category=IssueCategory(issue_data.get("category", "other")),
                    title=issue_data.get("title", ""),
                    description=issue_data.get("description", ""),
                    location=location,
                    suggested_fix=issue_data.get("suggested_fix"),
                    legal_basis=issue_data.get("legal_basis", []),
                    impact_assessment=issue_data.get("impact_assessment"),
                    likelihood=issue_data.get("likelihood")
                )
                issues.append(issue)
            except Exception as e:
                print(f"⚠️ 解析问题失败: {e}")
                continue

        return issues

    def _create_empty_feedback(self, start_time: float) -> ReviewFeedback:
        """创建空反馈（降级）"""
        return ReviewFeedback(
            reviewer_type=self.reviewer_type,
            reviewer_name=self.reviewer_name,
            issues=[],
            overall_rating=5.0,
            rating_explanation="审查过程中遇到问题，无法完成审查",
            summary=f"{self.reviewer_name} 审查失败",
            key_findings=[],
            confidence=0.0,
            uncertainty_sources=["系统错误"],
            review_timestamp=datetime.now(),
            review_duration_seconds=time.time() - start_time
        )
