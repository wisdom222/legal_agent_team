"""
Review Pipeline
编排 Writer、Reviewers 和 Arbitrator 的完整审查流程
"""

import asyncio
import time
from typing import List, Dict, Any, Optional

from ..agents.writer_agent import WriterAgent
from ..agents.legal_reviewer import LegalReviewerAgent
from ..agents.risk_reviewer import RiskReviewerAgent
from ..agents.format_reviewer import FormatReviewerAgent
from ..agents.business_reviewer import BusinessReviewerAgent
from ..agents.arbitrator_agent import ArbitratorAgent

from ..models.review_models import (
    ReviewFeedback,
    ReviewerType,
    ConsolidatedFeedback,
    DraftReport,
    FinalReport
)
from ..models.search_models import SearchContext, Document


class ReviewPipeline:
    """
    Review Pipeline - 审查流程编排器

    完整的审查流程:
    1. Writer Agent 生成草稿
    2. 并行执行所有 Reviewer 审查
    3. Arbitrator Agent 仲裁并生成整合反馈
    4. Writer Agent 根据反馈修订草稿
    5. 可选：第二轮审查

    支持配置:
    - 选择性启用 Reviewer
    - 控制审查轮数
    - 并行或串行执行
    """

    def __init__(
        self,
        writer_agent: WriterAgent,
        reviewers: Dict[ReviewerType, Any],
        arbitrator: ArbitratorAgent,
        enable_parallel: bool = True,
        max_rounds: int = 2
    ):
        """
        初始化 Review Pipeline

        Args:
            writer_agent: Writer Agent
            reviewers: Reviewer 字典
            arbitrator: Arbitrator Agent
            enable_parallel: 是否启用并行审查
            max_rounds: 最大审查轮数
        """
        self.writer = writer_agent
        self.reviewers = reviewers
        self.arbitrator = arbitrator
        self.enable_parallel = enable_parallel
        self.max_rounds = max_rounds

    async def execute(
        self,
        document: Dict[str, Any],
        search_context: SearchContext,
        analysis_type: str = "contract_review"
    ) -> FinalReport:
        """
        执行完整的审查流程

        Args:
            document: 文档信息
            search_context: 检索上下文
            analysis_type: 分析类型

        Returns:
            FinalReport 对象
        """
        total_start_time = time.time()

        # ========== Phase 1: Writer 生成草稿 ==========
        print("📝 Phase 1: Writer Agent 生成草稿...")
        draft = await self.writer.generate_draft(
            document=document,
            search_context=search_context,
            analysis_type=analysis_type
        )
        print(f"✅ 草稿生成完成: {draft.draft_id}")

        # 执行审查迭代
        current_round = 1
        final_report = None

        while current_round <= self.max_rounds:
            print(f"\n🔄 审查轮次: {current_round}/{self.max_rounds}")

            # ========== Phase 2: 并行审查 ==========
            print("🔍 Phase 2: 并行审查中...")
            review_feedbacks = await self._execute_parallel_review(
                draft=draft,
                document=document,
                search_context=search_context
            )

            # ========== Phase 3: 仲裁 ==========
            print("⚖️  Phase 3: 仲裁中...")
            consolidated_feedback = await self.arbitrator.arbitrate(
                draft=draft,
                review_feedbacks=review_feedbacks,
                document=document
            )

            print(f"✅ 仲裁完成: {len(consolidated_feedback.prioritized_issues)} 个问题")

            # ========== Phase 4: 修订 ==========
            print("✏️  Phase 4: 修订草稿...")
            final_report = await self.writer.revise_draft(
                draft=draft,
                feedback=consolidated_feedback,
                search_context=search_context
            )

            # 检查是否需要第二轮
            if current_round < self.max_rounds:
                # 如果没有 CRITICAL 或 HIGH 问题，可以提前结束
                critical_count = sum(
                    1 for i in consolidated_feedback.prioritized_issues
                    if i.severity.value in ["critical", "high"]
                )

                if critical_count == 0:
                    print("✅ 所有问题已解决，无需第二轮审查")
                    break

                # 更新 draft 用于下一轮（使用修订后的报告）
                # 在实际实现中，这里应该从 final_report 中提取新的 draft
                current_round += 1
            else:
                break

        total_duration = time.time() - total_start_time
        print(f"\n🎉 审查流程完成! 总耗时: {total_duration:.2f}s")

        return final_report

    async def _execute_parallel_review(
        self,
        draft: DraftReport,
        document: Dict[str, Any],
        search_context: SearchContext
    ) -> List[ReviewFeedback]:
        """
        执行并行审查

        Args:
            draft: 草稿报告
            document: 原始文档
            search_context: 检索上下文

        Returns:
            所有 Reviewer 的反馈列表
        """
        if self.enable_parallel:
            # 并行执行所有 Reviewer
            review_tasks = [
                reviewer.review(
                    draft=draft,
                    document=document,
                    search_context=search_context
                )
                for reviewer in self.reviewers.values()
            ]

            feedbacks = await asyncio.gather(*review_tasks, return_exceptions=True)

            # 处理异常
            valid_feedbacks = []
            for i, feedback in enumerate(feedbacks):
                if isinstance(feedback, Exception):
                    print(f"⚠️ Reviewer {i} 失败: {feedback}")
                    # 创建空反馈
                    reviewer_type = list(self.reviewers.keys())[i]
                    valid_feedbacks.append(self._create_empty_feedback(reviewer_type))
                else:
                    valid_feedbacks.append(feedback)

            return valid_feedbacks
        else:
            # 串行执行
            feedbacks = []
            for reviewer in self.reviewers.values():
                feedback = await reviewer.review(
                    draft=draft,
                    document=document,
                    search_context=search_context
                )
                feedbacks.append(feedback)

            return feedbacks

    def _create_empty_feedback(
        self,
        reviewer_type: ReviewerType
    ) -> ReviewFeedback:
        """创建空反馈（降级）"""
        from ..models.review_models import ReviewFeedback
        from datetime import datetime

        return ReviewFeedback(
            reviewer_type=reviewer_type,
            reviewer_name=f"{reviewer.value}_reviewer",
            issues=[],
            overall_rating=5.0,
            rating_explanation="审查失败",
            summary="审查过程中遇到问题",
            key_findings=[],
            confidence=0.0,
            uncertainty_sources=["系统错误"],
            review_timestamp=datetime.now(),
            review_duration_seconds=0.0
        )

    def get_pipeline_info(self) -> Dict[str, Any]:
        """获取 Pipeline 信息"""
        return {
            "enabled_reviewers": list(self.reviewers.keys()),
            "enable_parallel": self.enable_parallel,
            "max_rounds": self.max_rounds,
            "writer_model": self.writer.model_name,
            "arbitrator_model": self.arbitrator.model_name
        }


# 工厂函数
def create_review_pipeline(
    openai_api_key: str,
    model_name: str = "gpt-4o",
    enabled_reviewers: List[str] = None,
    enable_parallel: bool = True,
    max_rounds: int = 2
) -> ReviewPipeline:
    """
    创建 Review Pipeline

    Args:
        openai_api_key: OpenAI API 密钥
        model_name: OpenAI 模型名称
        enabled_reviewers: 启用的 Reviewer 列表
        enable_parallel: 是否启用并行审查
        max_rounds: 最大审查轮数

    Returns:
        ReviewPipeline 实例
    """
    # 创建 Writer Agent
    writer = WriterAgent(model_name=model_name, api_key=openai_api_key)

    # 创建 Reviewers
    if enabled_reviewers is None:
        enabled_reviewers = ["legal", "risk", "format", "business"]

    reviewers = {}

    if "legal" in enabled_reviewers:
        reviewers[ReviewerType.LEGAL] = LegalReviewerAgent(
            model_name=model_name,
            api_key=openai_api_key
        )

    if "risk" in enabled_reviewers:
        reviewers[ReviewerType.RISK] = RiskReviewerAgent(
            model_name=model_name,
            api_key=openai_api_key
        )

    if "format" in enabled_reviewers:
        reviewers[ReviewerType.FORMAT] = FormatReviewerAgent(
            model_name=model_name,
            api_key=openai_api_key
        )

    if "business" in enabled_reviewers:
        reviewers[ReviewerType.BUSINESS] = BusinessReviewerAgent(
            model_name=model_name,
            api_key=openai_api_key
        )

    # 创建 Arbitrator
    arbitrator = ArbitratorAgent(
        model_name=model_name,
        api_key=openai_api_key
    )

    # 创建 Pipeline
    return ReviewPipeline(
        writer_agent=writer,
        reviewers=reviewers,
        arbitrator=arbitrator,
        enable_parallel=enable_parallel,
        max_rounds=max_rounds
    )
