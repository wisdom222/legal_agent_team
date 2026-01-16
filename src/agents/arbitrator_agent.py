"""
Arbitrator Agent
审查仲裁者 - 协调多个 Reviewer 的意见冲突
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
    ReviewFeedback,
    ReviewIssue,
    ConflictResolution,
    ConsolidatedFeedback,
    ReviewerType,
    SeverityLevel,
    generate_conflict_id,
    prioritize_issues
)


class ArbitratorAgent:
    """
    Arbitrator Agent - 审查仲裁者

    职责:
    1. 收集并分析所有 Reviewer 的反馈
    2. 根据优先级规则解决意见冲突
    3. 整合生成清晰的修订指导
    4. 确保关键问题不被忽略

    优先级规则:
    - CRITICAL 级别问题必须修正
    - 法律合规 > 风险控制 > 商业逻辑 > 格式规范
    - 多个 Reviewer 标记的同一问题优先级提升
    """

    def __init__(
        self,
        model_name: str = "gpt-4o",
        api_key: str = None
    ):
        """
        初始化 Arbitrator Agent

        Args:
            model_name: OpenAI 模型名称
            api_key: OpenAI API 密钥
        """
        if not AGNO_AVAILABLE:
            raise ImportError("Agno 包未安装。请运行: pip install agno")

        self.model_name = model_name

        # 创建 Agno Agent
        self.agent = Agent(
            name="ArbitratorAgent",
            role="审查仲裁者",
            model=OpenAIChat(id=model_name, api_key=api_key),
            instructions=self._get_instructions(),
            show_tool_calls=True,
            markdown=True
        )

        # 优先级权重
        self.reviewer_priority = {
            ReviewerType.LEGAL: 1,     # 最高优先级
            ReviewerType.RISK: 2,
            ReviewerType.BUSINESS: 3,
            ReviewerType.FORMAT: 4      # 最低优先级
        }

        # 严重程度权重
        self.severity_priority = {
            SeverityLevel.CRITICAL: 0,
            SeverityLevel.HIGH: 1,
            SeverityLevel.MEDIUM: 2,
            SeverityLevel.LOW: 3,
            SeverityLevel.INFO: 4
        }

    def _get_instructions(self) -> List[str]:
        """获取 Agent 指令"""
        return [
            "你是法律文档分析团队的审查仲裁者。",
            "你的职责是协调多个审查者的意见，解决冲突，生成最终的修订指导。",
            "",
            "优先级原则:",
            "1. CRITICAL 级别问题必须修正",
            "2. 法律合规 > 风险控制 > 商业逻辑 > 格式规范",
            "3. 多个审查者标记的同一问题优先级提升",
            "4. 无法自动解决的冲突标记为'需人工确认'",
            "",
            "你需要:",
            "- 仔细分析所有审查者的反馈",
            "- 识别和处理意见冲突",
            "- 按优先级排序所有问题",
            "- 生成清晰可执行的修订指导"
        ]

    async def arbitrate(
        self,
        draft: Any,
        review_feedbacks: List[ReviewFeedback],
        document: Dict[str, Any]
    ) -> ConsolidatedFeedback:
        """
        执行仲裁

        Args:
            draft: 草稿报告
            review_feedbacks: 所有 Reviewer 的反馈
            document: 原始文档

        Returns:
            ConsolidatedFeedback 对象
        """
        start_time = time.time()

        # 1. 收集所有问题
        all_issues = self._collect_all_issues(review_feedbacks)

        # 2. 识别冲突
        conflicts = self._identify_conflicts(all_issues)

        # 3. 解决冲突
        resolved_conflicts = await self._resolve_conflicts(
            conflicts,
            draft,
            document
        )

        # 4. 优先级排序
        prioritized_issues = prioritize_issues(all_issues)

        # 5. 生成修订指导
        revision_instructions = await self._generate_revision_instructions(
            prioritized_issues,
            resolved_conflicts,
            draft
        )

        # 6. 提取优先级行动
        priority_actions = self._extract_priority_actions(prioritized_issues)

        # 构建整合反馈
        arbitration_id = f"arb_{uuid.uuid4().hex[:8]}"

        consolidated_feedback = ConsolidatedFeedback(
            arbitration_id=arbitration_id,
            arbitration_timestamp=datetime.now(),
            prioritized_issues=prioritized_issues,
            conflicts_resolved=resolved_conflicts,
            revision_instructions=revision_instructions,
            priority_actions=priority_actions,
            estimated_revision_rounds=self._estimate_rounds(prioritized_issues),
            revision_focus_areas=self._extract_focus_areas(prioritized_issues),
            all_reviewer_feedback=review_feedbacks,
            arbitration_duration_seconds=time.time() - start_time
        )

        return consolidated_feedback

    def _collect_all_issues(
        self,
        feedbacks: List[ReviewFeedback]
    ) -> List[ReviewIssue]:
        """收集所有问题"""
        all_issues = []
        for feedback in feedbacks:
            all_issues.extend(feedback.issues)
        return all_issues

    def _identify_conflicts(
        self,
        issues: List[ReviewIssue]
    ) -> List[Dict[str, Any]]:
        """识别冲突"""
        # 按位置分组问题
        issues_by_location: Dict[str, List[ReviewIssue]] = {}

        for issue in issues:
            location_key = f"{issue.location.clause_id}_{issue.location.paragraph_index}"
            if location_key not in issues_by_location:
                issues_by_location[location_key] = []
            issues_by_location[location_key].append(issue)

        # 识别冲突（同一位置有不同 Reviewer 标记的问题）
        conflicts = []
        for location, location_issues in issues_by_location.items():
            if len(location_issues) > 1:
                # 检查是否有不同类型的 Reviewer
                reviewer_types = {issue.reviewer_type for issue in location_issues}
                if len(reviewer_types) > 1:
                    conflicts.append({
                        "location": location,
                        "issues": location_issues,
                        "reviewer_types": reviewer_types
                    })

        return conflicts

    async def _resolve_conflicts(
        self,
        conflicts: List[Dict[str, Any]],
        draft: Any,
        document: Dict[str, Any]
    ) -> List[ConflictResolution]:
        """解决冲突"""
        resolved = []

        for conflict_data in conflicts:
            location = conflict_data["location"]
            issues = conflict_data["issues"]
            reviewer_types = conflict_data["reviewer_types"]

            # 根据优先级规则解决
            priority_reviewer = min(
                reviewer_types,
                key=lambda rt: self.reviewer_priority.get(rt, 99)
            )

            # 选择优先级最高的问题
            priority_issue = min(
                issues,
                key=lambda i: (
                    self.severity_priority.get(i.severity, 99),
                    self.reviewer_priority.get(i.reviewer_type, 99)
                )
            )

            resolution = ConflictResolution(
                conflict_id=generate_conflict_id(),
                conflict_description=f"位置 {location} 存在多个审查者意见",
                involved_reviewers=list(reviewer_types),
                conflicting_issues=[issue.issue_id for issue in issues],
                resolution_strategy=f"prioritize_{priority_reviewer.value}",
                final_decision=f"采纳 {priority_reviewer.value} 的意见: {priority_issue.title}",
                rationale=f"根据优先级规则，{priority_reviewer.value} 的意见优先",
                priority=self.severity_priority.get(priority_issue.severity, 5),
                requires_human_review=self._requires_human_review(issues)
            )

            resolved.append(resolution)

        return resolved

    def _requires_human_review(self, issues: List[ReviewIssue]) -> bool:
        """判断是否需要人工复核"""
        # 如果有 CRITICAL 级别问题且意见分歧严重
        critical_issues = [i for i in issues if i.severity == SeverityLevel.CRITICAL]
        if len(critical_issues) > 1:
            return True

        # 如果有多个不同类型的高优先级 Reviewer 意见冲突
        high_priority_reviewers = {
            i.reviewer_type for i in issues
            if self.reviewer_priority.get(i.reviewer_type, 99) <= 2
            and i.severity in [SeverityLevel.CRITICAL, SeverityLevel.HIGH]
        }
        if len(high_priority_reviewers) > 1:
            return True

        return False

    async def _generate_revision_instructions(
        self,
        prioritized_issues: List[ReviewIssue],
        resolved_conflicts: List[ConflictResolution],
        draft: Any
    ) -> str:
        """生成修订指导"""
        # 构建提示词
        critical_issues = [i for i in prioritized_issues if i.severity == SeverityLevel.CRITICAL]
        high_issues = [i for i in prioritized_issues if i.severity == SeverityLevel.HIGH]

        prompt = f"""
# 修订指导生成任务

## 草稿信息
- 草稿 ID: {draft.draft_id if hasattr(draft, 'draft_id') else 'N/A'}

## 问题统计
- 总问题数: {len(prioritized_issues)}
- CRITICAL: {len(critical_issues)}
- HIGH: {len(high_issues)}

## 关键问题
{self._format_critical_issues(critical_issues[:5])}

## 冲突解决
{len(resolved_conflicts)} 个冲突已解决

## 任务要求
请基于以上信息，生成清晰、可执行的修订指导。

修订指导应包含:
1. 总体修订策略
2. 重点修改方向
3. 优先级顺序
4. 注意事项

请以简洁、专业的语言撰写。
"""

        try:
            response = await self.agent.arun(prompt)
            return response.get("instructions", "请根据优先级问题列表进行修订")
        except Exception as e:
            print(f"⚠️ 生成修订指导失败: {e}")
            return self._create_fallback_instructions(prioritized_issues)

    def _format_critical_issues(self, issues: List[ReviewIssue]) -> str:
        """格式化关键问题"""
        if not issues:
            return "无关键问题"

        formatted = []
        for issue in issues:
            formatted.append(
                f"- **[{issue.severity.value.upper()}]** {issue.title}\n"
                f"  {issue.description}"
            )
        return "\n".join(formatted)

    def _create_fallback_instructions(
        self,
        issues: List[ReviewIssue]
    ) -> str:
        """创建降级修订指导"""
        critical = [i for i in issues if i.severity == SeverityLevel.CRITICAL]
        high = [i for i in issues if i.severity == SeverityLevel.HIGH]

        instructions = ["请按以下优先级修订文档："]

        if critical:
            instructions.append("\n**紧急处理（CRITICAL）：**")
            for issue in critical[:5]:
                instructions.append(f"- {issue.title}: {issue.description}")

        if high:
            instructions.append("\n**重要处理（HIGH）：**")
            for issue in high[:5]:
                instructions.append(f"- {issue.title}: {issue.description}")

        return "\n".join(instructions)

    def _extract_priority_actions(
        self,
        issues: List[ReviewIssue]
    ) -> List[str]:
        """提取优先级行动"""
        actions = []

        # 提取 CRITICAL 和 HIGH 级别的建议修正
        for issue in issues:
            if issue.severity in [SeverityLevel.CRITICAL, SeverityLevel.HIGH]:
                if issue.suggested_fix:
                    actions.append(f"[{issue.severity.value.upper()}] {issue.suggested_fix}")
                else:
                    actions.append(f"[{issue.severity.value.upper()}] 修正: {issue.title}")

        return actions[:10]  # 最多 10 条

    def _estimate_rounds(self, issues: List[ReviewIssue]) -> int:
        """估计修订轮数"""
        critical_count = sum(1 for i in issues if i.severity == SeverityLevel.CRITICAL)
        high_count = sum(1 for i in issues if i.severity == SeverityLevel.HIGH)

        if critical_count > 0:
            return 2
        elif high_count > 5:
            return 2
        else:
            return 1

    def _extract_focus_areas(self, issues: List[ReviewIssue]) -> List[str]:
        """提取重点关注领域"""
        # 按类别统计
        category_count: Dict[str, int] = {}
        for issue in issues:
            if issue.severity in [SeverityLevel.CRITICAL, SeverityLevel.HIGH]:
                category = issue.category.value
                category_count[category] = category_count.get(category, 0) + 1

        # 返回问题最多的 3 个类别
        sorted_categories = sorted(
            category_count.items(),
            key=lambda x: x[1],
            reverse=True
        )[:3]

        return [cat for cat, _ in sorted_categories]


# 工厂函数
def create_arbitrator_agent(
    model_name: str = "gpt-4o",
    api_key: str = None
) -> ArbitratorAgent:
    """
    创建 Arbitrator Agent

    Args:
        model_name: OpenAI 模型名称
        api_key: OpenAI API 密钥

    Returns:
        ArbitratorAgent 实例
    """
    return ArbitratorAgent(
        model_name=model_name,
        api_key=api_key
    )
