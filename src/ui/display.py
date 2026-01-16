"""
Streamlit UI 组件
用于展示法律文档分析报告
"""

import streamlit as st
from typing import Optional
import io

from ..models.report_schema import (
    LegalDocumentReport,
    ExecutiveSummary,
    DetailedAnalysis
)
from ..reports.exporter import ReportExporter


class ReportDisplay:
    """
    报告展示组件

    提供多种展示方式：
    - 执行摘要视图
    - 详细分析视图
    - 完整报告视图
    - 下载功能
    """

    def __init__(self, report: LegalDocumentReport):
        """
        初始化展示组件

        Args:
            report: 报告对象
        """
        self.report = report
        self.exporter = ReportExporter()

    def display_full_report(self):
        """展示完整报告"""
        # 标签页
        tab1, tab2, tab3, tab4 = st.tabs([
            "📊 执行摘要",
            "📋 详细分析",
            "🔍 证据来源",
            "💾 导出报告"
        ])

        with tab1:
            self.display_executive_summary()

        with tab2:
            self.display_detailed_analysis()

        with tab3:
            self.display_evidence_sources()

        with tab4:
            self.display_export_options()

    def display_executive_summary(self):
        """展示执行摘要"""
        summary: ExecutiveSummary = self.report.executive_summary

        # 文档信息
        st.metric(
            label="综合评分",
            value=f"{summary.overall_rating}/10",
            delta=None,
            help="基于法律合规性、风险控制、格式规范等多个维度综合评估"
        )

        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric(
                "文档类型",
                summary.document_type.value,
                help="文档的法律类型分类"
            )
        with col2:
            st.metric(
                "分析时间",
                summary.analysis_date.strftime("%Y-%m-%d %H:%M"),
                help="报告生成时间"
            )
        with col3:
            total_issues = sum(summary.risk_summary.values())
            st.metric(
                "发现问题",
                total_issues,
                help="各类风险等级问题总数"
            )

        st.divider()

        # 风险分布
        st.subheader("📈 风险分布")

        # 风险统计可视化
        risk_cols = st.columns(len(summary.risk_summary)))
        for i, (level, count) in enumerate(summary.risk_summary.items()):
            with risk_cols[i]:
                color = self._get_risk_color(level)
                st.markdown(
                    f"<div style='text-align: center; "
                    f"background-color: {color}; padding: 10px; "
                    f"border-radius: 5px; color: white;'>"
                    f"<strong>{level.value.upper()}</strong><br>"
                    f"<span style='font-size: 24px;'>{count}</span>"
                    f"</div>",
                    unsafe_allow_html=True
                )

        st.divider()

        # 关键风险
        st.subheader("⚠️ 关键风险")
        for i, risk in enumerate(summary.key_risks, 1):
            st.markdown(f"{i}. {risk}")

        # 严重问题
        if summary.critical_issues:
            st.subheader("🚨 严重问题（需立即处理）")
            for issue in summary.critical_issues:
                st.error(issue)

        # 快速建议
        st.subheader("💡 快速建议")
        for i, rec in enumerate(summary.quick_recommendations, 1):
            priority_icon = self._get_priority_icon(rec.priority)
            st.markdown(
                f"{priority_icon} **{rec.action_item}**\n"
                f"*{rec.urgency}*"
            )
            st.markdown("---")

        # 一句话总结
        st.info(f"**总结**: {summary.one_sentence_summary}")

    def display_detailed_analysis(self):
        """展示详细分析"""
        analysis: DetailedAnalysis = self.report.detailed_analysis

        # 概览统计
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("总条款数", analysis.total_clauses)
        with col2:
            st.metric("有问题条款", analysis.clauses_with_issues)
        with col3:
            # 合规率进度条
            compliance_rate = analysis.compliance_rate
            st.metric("合规率", f"{compliance_rate:.1f}%")

            # 进度条可视化
            st.progress(compliance_rate / 100)

        st.divider()

        # 条款分析
        st.subheader("📝 条款详细分析")

        for clause in analysis.clause_breakdown:
            with st.expander(
                f"条款 {clause.clause_id}: {clause.clause_title or clause.clause_type}",
                expanded=clause.risk_level.value in ["critical", "high"]
            ):
                # 风险等级标签
                risk_color = self._get_risk_color(clause.risk_level)
                st.markdown(
                    f"<span style='background-color: {risk_color}; "
                    f"padding: 4px 8px; border-radius: 4px; "
                    f"color: white;'>{clause.risk_level.value.upper()}</span> "
                    f"风险分数: **{clause.risk_score:.1f}/100**",
                    unsafe_allow_html=True
                )

                st.markdown(f"**内容**: {clause.clause_text}")

                # 问题
                if clause.issues_identified:
                    st.markdown("**问题**:")
                    for issue in clause.issues_identified:
                        st.markdown(f"- ⚠️ {issue}")

                # 建议
                if clause.suggestions:
                    st.markdown("**建议**:")
                    for suggestion in clause.suggestions:
                        st.markdown(f"- 💡 {suggestion}")

                # 法律依据
                if clause.legal_basis:
                    st.markdown("**法律依据**:")
                    for basis in clause.legal_basis:
                        st.markdown(f"- 📜 {basis}")

                # 审查者意见
                if clause.reviewer_comments:
                    st.markdown("**审查者意见**:")
                    for reviewer, comment in clause.reviewer_comments.items():
                        st.markdown(f"- **{reviewer}**: {comment}")

        # 合规性检查清单
        if analysis.compliance_checklist:
            st.subheader("✅ 合规性检查清单")

            for item in analysis.compliance_checklist:
                icon = "✅" if item.is_compliant else "❌"
                status_color = "green" if item.is_compliant else "red"

                st.markdown(
                    f"<span style='color: {status_color};'>"
                    f"{icon} **{item.check_item}**"
                    f"</span>: {item.explanation}",
                    unsafe_allow_html=True
                )

                if not item.is_compliant and item.severity:
                    st.caption(f"严重程度: {item.severity.value}")

        # 管辖权分析
        if analysis.jurisdiction_analysis:
            st.subheader("⚖️ 管辖权分析")
            ja = analysis.jurisdiction_analysis

            st.markdown(f"- **适用法律**: {ja.applicable_law}")
            st.markdown(f"- **管辖机构**: {ja.jurisdiction}")
            st.markdown(f"- **主导语言**: {ja.governing_language}")

            if ja.cross_border_considerations:
                st.markdown("**跨境考虑**:")
                for consideration in ja.cross_border_considerations:
                    st.markdown(f"- {consideration}")

    def display_evidence_sources(self):
        """展示证据来源"""
        st.subheader("📚 证据来源")

        # 统计信息
        source_types = {}
        for source in self.report.evidence_sources:
            source_types[source.source_type.value] = \
                source_types.get(source.source_type.value, 0) + 1

        if source_types:
            st.write("**来源统计**:")
            for source_type, count in source_types.items():
                st.markdown(f"- {source_type}: {count} 个")

        st.divider()

        # 证据列表
        tab1, tab2 = st.tabs(["来源列表", "Agent 推理链"])

        with tab1:
            for i, source in enumerate(self.report.evidence_sources, 1):
                type_icon = self._get_source_type_icon(source.source_type.value)

                with st.expander(
                    f"{type_icon} {source.source_type.value} "
                    f"(相关性: {source.relevance_score:.2f})"
                ):
                    st.markdown(f"**内容**: {source.content}")
                    st.caption(f"检索方法: {source.retrieval_method}")
                    st.caption(f"原始排名: {source.original_rank}")

                    if source.url:
                        st.markdown(f"[查看来源]({source.url})")

        with tab2:
            for reasoning in self.report.agent_reasoning_chain:
                with st.expander(
                    f"🤖 {reasoning.agent_name} "
                    f"(置信度: {reasoning.confidence:.2f})"
                ):
                    st.markdown(f"**角色**: {reasoning.agent_role}")

                    # 置信度进度条
                    st.progress(reasoning.confidence)
                    st.caption(f"耗时: {reasoning.processing_duration_seconds:.2f}s")

                    st.markdown("**推理过程**:")
                    st.markdown(reasoning.reasoning_process)

                    st.markdown("**关键事实**:")
                    for fact in reasoning.key_facts:
                        st.markdown(f"- {fact}")

                    if reasoning.uncertainty_sources:
                        st.markdown("**不确定性**:")
                        for source in reasoning.uncertainty_sources:
                            st.markdown(f"- ⚠️ {source}")

    def display_export_options(self):
        """展示导出选项"""
        st.subheader("📥 导出报告")

        # 格式选择
        col1, col2 = st.columns(2)

        with col1:
            st.write("**选择格式**:")
            export_formats = st.multiselect(
                "导出格式",
                ["json", "md", "pdf", "docx"],
                default=["json", "md"],
                help="选择要导出的文件格式"
            )

        with col2:
            st.write("**文件名**:")
            filename = st.text_input(
                "文件名（不含扩展名）",
                value=self.report.document_name,
                help="留空则使用默认文件名"
            )

        # 导出按钮
        if st.button("🚀 生成报告", type="primary"):
            if export_formats:
                with st.spinner("正在生成报告..."):
                    results = self.exporter.export(
                        report=self.report,
                        formats=export_formats,
                        filename=filename if filename else None
                    )

                # 显示结果
                st.success("报告生成完成！")

                for fmt, filepath in results.items():
                    if filepath:
                        st.info(f"✅ {fmt.upper()}: `{filepath}`")

                        # 提供下载链接
                        with open(filepath, 'rb') as f:
                            st.download_button(
                                label=f"⬇️ 下载 {fmt.upper()}",
                                data=f,
                                file_name=filepath,
                                mime=self._get_mime_type(fmt),
                                key=f"download_{fmt}"
                            )
            else:
                st.warning("请至少选择一种格式")

        # 报告元信息
        st.divider()
        st.subheader("📋 报告信息")

        st.json({
            "document_name": self.report.document_name,
            "analysis_version": self.report.analysis_version,
            "analysis_timestamp": self.report.analysis_timestamp.isoformat(),
            "analysis_duration": f"{self.report.analysis_duration_seconds:.2f}s",
            "export_formats": list(self.report.export_config.keys())
        })

    @staticmethod
    def _get_risk_color(level) -> str:
        """获取风险等级对应的颜色"""
        colors = {
            "critical": "#e74c3c",  # 红色
            "high": "#e67e22",      # 橙色
            "medium": "#f39c12",    # 黄色
            "low": "#27ae60",       # 绿色
            "info": "#3498db"       # 蓝色
        }
        return colors.get(level.value if hasattr(level, 'value') else level, "#95a5a6")

    @staticmethod
    def _get_priority_icon(priority) -> str:
        """获取优先级图标"""
        icons = {
            "critical": "🔴",
            "high": "🟠",
            "medium": "🟡",
            "low": "🟢",
            "info": "🔵"
        }
        return icons.get(priority.value if hasattr(priority, 'value') else priority, "⚪")

    @staticmethod
    def _get_source_type_icon(source_type: str) -> str:
        """获取来源类型图标"""
        icons = {
            "knowledge_base": "📚",
            "legal_database": "⚖️",
            "case_law": "📜",
            "user_input": "👤",
            "agent_reasoning": "🤖",
            "internal": "📋"
        }
        return icons.get(source_type, "📄")

    @staticmethod
    def _get_mime_type(fmt: str) -> str:
        """获取 MIME 类型"""
        mimes = {
            "json": "application/json",
            "md": "text/markdown",
            "pdf": "application/pdf",
            "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        }
        return mimes.get(fmt, "application/octet-stream")


# 便捷函数
def display_report(report: LegalDocumentReport):
    """
    展示报告（便捷函数）

    Args:
        report: 报告对象
    """
    display = ReportDisplay(report)
    display.display_full_report()


def display_executive_summary_only(report: LegalDocumentReport):
    """
    仅展示执行摘要

    Args:
        report: 报告对象
    """
    display = ReportDisplay(report)
    display.display_executive_summary()


def display_detailed_analysis_only(report: LegalDocumentReport):
    """
    仅展示详细分析

    Args:
        report: 报告对象
    """
    display = ReportDisplay(report)
    display.display_detailed_analysis()
