# AI 法律文档分析助手 - 功能增强设计文档

**项目**: DL_Project2
**日期**: 2026-01-15
**版本**: 2.1
**状态**: ✅ 设计完成，待实施

---

## 📋 目录

1. [设计概述](#设计概述)
2. [Streamlit Cloud 部署适配](#streamlit-cloud-部署适配)
3. [历史记录存储方案](#历史记录存储方案)
4. [历史对比功能架构](#历史对比功能架构)
5. [可视化图表系统](#可视化图表系统)
6. [实时进度系统](#实时进度系统)
7. [响应式 UI 设计](#响应式-ui-设计)
8. [实施计划](#实施计划)

---

## 设计概述

### 背景

基于已完成的 AI 法律文档分析助手 v2.0，本次功能增强聚焦于三个核心方向：

1. **云端部署** - 部署到 Streamlit Cloud，便于展示和分享
2. **历史对比** - 实现版本对比和横向对比功能
3. **用户体验** - 实时进度、可视化图表、移动端适配

### 改进目标

| # | 目标 | 用户价值 |
|---|------|---------|
| 1 | **Streamlit Cloud 部署** | 随时随地访问，轻松展示成果 |
| 2 | **历史记录对比** | 追踪文档演变，发现风险变化 |
| 3 | **可视化图表** | 直观理解分析结果，洞察趋势 |
| 4 | **实时进度反馈** | 了解处理状态，减少等待焦虑 |
| 5 | **移动端适配** | 手机上也能使用，随时随地分析 |

### 技术选型总结

| 组件 | 技术选择 | 说明 |
|-----|---------|------|
| **部署平台** | Streamlit Cloud | 免费托管，零配置部署 |
| **向量数据库** | Qdrant Cloud | 托管服务，无需维护 |
| **存储** | 本地文件系统 | Streamlit Cloud 持久化目录 |
| **可视化** | Plotly | 交互式图表，支持移动端 |
| **进度展示** | st.status | 可折叠的详细步骤 |
| **响应式** | CSS Media Query | 原生支持，无需额外库 |

---

## Streamlit Cloud 部署适配

### 核心挑战

Streamlit Cloud 有几个关键限制需要解决：

1. **无状态性**：每次部署都是新环境，本地文件系统在重启后会清空
2. **资源限制**：免费版 1GB 内存，需要优化内存使用
3. **外部服务**：需要公网可访问的 Qdrant 实例
4. **环境变量**：通过 Streamlit Cloud Secrets 管理

### 架构调整

```
Streamlit Cloud (app.streamlit.app)
    ↓
Qdrant Cloud (cloud.qdrant.io)
    ↓
[可选] Redis Cloud (redis.com)
```

### 文件结构调整

```
DL_Project2/
├── .streamlit/
│   ├── config.toml           # Streamlit 配置
│   └── secrets.toml.example  # 密钥模板（不提交真实密钥）
├── deployments/
│   ├── streamlit/            # Streamlit Cloud 部署文件
│   │   ├── packages.txt      # 系统依赖
│   │   ├── requirements.txt  # 精简的 Python 依赖
│   │   └── run.sh            # 启动脚本
│   └── qdrant/               # Qdrant 配置
│       └── cloud_setup.md    # Qdrant Cloud 设置指南
├── src/storage/              # 新增：存储层
│   ├── history_manager.py    # 历史记录管理
│   ├── cache_manager.py      # 缓存管理
│   └── persistence.py        # 持久化抽象
└── ai_legal_team_cloud.py    # Streamlit Cloud 专用入口
```

### 精简依赖策略

**保留的核心依赖**：

```txt
# requirements.txt for Streamlit Cloud
streamlit>=1.28.0
agno>=0.1.0
pydantic>=2.0.0
rank-bm25>=0.2.2
jieba>=0.42.1
qdrant-client>=1.7.0
openai>=1.0.0
cohere>=4.0.0
plotly>=5.18.0
pypdf>=3.17.0
python-docx>=1.1.0
```

**移除的重量级依赖**：
- `pdfplumber` → 使用 `pypdf`（更轻量）
- `weasyprint` → Cloud 版禁用 PDF 导出
- `redis` → 可选，本地开发用

### 配置管理

**环境变量配置**：

```python
# src/config/qdrant_cloud.py
from pydantic_settings import BaseSettings

class QdrantCloudConfig(BaseSettings):
    """Qdrant Cloud 配置"""
    url: str
    api_key: str
    collection: str = "legal_documents_v2"

    class Config:
        env_prefix = "QDRANT_"

# 使用
config = QdrantCloudConfig()
# 从 st.secrets 读取
qdrant_config = QdrantCloudConfig(
    url=st.secrets["QDRANT_URL"],
    api_key=st.secrets["QDRANT_API_KEY"]
)
```

---

## 历史记录存储方案

### 存储架构

```
~/.streamlit/
├── cache/                      # Streamlit 自动缓存
└── mount_data/                 # 持久化存储目录
    ├── analysis_history/       # 分析历史记录
    │   ├── 2026-01-15/
    │   │   ├── analysis_{timestamp}.json.gz
    │   │   └── metadata.json
    │   └── index.json          # 全局索引
    ├── bm25_index/             # BM25 索引文件
    │   └── legal_docs.pkl
    └── uploads/                # 临时上传文件
        └── {session_id}/
```

### 分层存储策略

| 层级 | 存储位置 | 保留策略 | 用途 |
|-----|---------|---------|------|
| **热数据** | `st.session_state` | 当前会话 | 快速访问 |
| **温数据** | `mount_data/analysis_history/7days/` | 7天 | 频繁访问 |
| **冷数据** | `mount_data/analysis_history/archive/` | 30天 | 偶尔访问 |

### 数据模型

**1. 分析记录元数据**：

```python
from pydantic import BaseModel, Field
from datetime import datetime
from uuid import uuid4
from enum import Enum

class DocumentType(str, Enum):
    """文档类型"""
    EMPLOYMENT_CONTRACT = "劳动合同"
    SERVICE_AGREEMENT = "服务协议"
    SALES_CONTRACT = "销售合同"
    NDA = "保密协议"
    OTHER = "其他"

class AnalysisMetadata(BaseModel):
    """单次分析的元数据"""
    analysis_id: str = Field(default_factory=lambda: uuid4().hex)
    timestamp: datetime
    document_name: str
    document_type: DocumentType
    file_hash: str              # MD5 哈希，用于版本识别
    analysis_type: str          # contract_review / compliance_check
    overall_rating: float
    total_risks: int

    # 版本关联
    document_version_id: Optional[str] = None  # 同一文档的不同版本
    parent_analysis_id: Optional[str] = None   # 父分析ID（用于对比）

    # 性能指标
    duration_seconds: float

    # 存储路径
    report_path: str
    document_path: Optional[str] = None
```

**2. 历史索引**：

```python
class HistoryIndex(BaseModel):
    """全局历史索引"""
    total_analyses: int
    analyses: List[AnalysisMetadata]
    documents: Dict[str, List[str]]  # document_hash -> [analysis_ids]
    tags: Dict[str, List[str]]       # 标签索引
```

### 存储管理器实现

```python
import gzip
import json
from pathlib import Path
from typing import List, Optional
from datetime import datetime, timedelta

class HistoryManager:
    """历史记录管理器"""

    def __init__(self, base_path: str = "./mount_data"):
        self.base_path = Path(base_path)
        self.history_dir = self.base_path / "analysis_history"
        self.index_path = self.history_dir / "index.json"

        # 确保目录存在
        self.history_dir.mkdir(parents=True, exist_ok=True)

    async def save_analysis(
        self,
        report: LegalDocumentReport,
        document: Optional[Document] = None
    ) -> AnalysisMetadata:
        """保存分析记录"""
        # 1. 生成元数据
        metadata = self._create_metadata(report, document)

        # 2. 保存报告（压缩）
        date_dir = self.history_dir / metadata.timestamp.strftime("%Y-%m-%d")
        date_dir.mkdir(parents=True, exist_ok=True)

        report_path = date_dir / f"analysis_{metadata.timestamp.timestamp()}.json.gz"
        self._save_compressed_json(report, report_path)

        metadata.report_path = str(report_path)

        # 3. 更新索引
        self._update_index(metadata)

        return metadata

    def _save_compressed_json(self, data: BaseModel, path: Path):
        """保存压缩的 JSON"""
        with gzip.open(path, 'wt', encoding='utf-8') as f:
            f.write(data.model_dump_json(indent=2))

    async def _load_report(self, analysis_id: str) -> LegalDocumentReport:
        """加载分析报告"""
        metadata = self._load_metadata(analysis_id)
        if not metadata:
            raise ValueError(f"Analysis not found: {analysis_id}")

        with gzip.open(metadata.report_path, 'rt', encoding='utf-8') as f:
            data = json.load(f)

        return LegalDocumentReport(**data)

    def get_history(
        self,
        limit: int = 50,
        document_type: Optional[DocumentType] = None
    ) -> List[AnalysisMetadata]:
        """获取历史记录"""
        index = self._load_index()
        results = index.analyses

        if document_type:
            results = [r for r in results if r.document_type == document_type]

        return sorted(results, key=lambda x: x.timestamp, reverse=True)[:limit]

    def _load_index(self) -> HistoryIndex:
        """加载索引"""
        if not self.index_path.exists():
            return HistoryIndex(total_analyses=0, analyses=[], documents={}, tags={})

        with open(self.index_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        return HistoryIndex(**data)

    def _update_index(self, metadata: AnalysisMetadata):
        """更新索引"""
        index = self._load_index()

        # 添加到分析列表
        index.analyses.append(metadata)
        index.total_analyses += 1

        # 更新文档索引
        if metadata.file_hash not in index.documents:
            index.documents[metadata.file_hash] = []
        index.documents[metadata.file_hash].append(metadata.analysis_id)

        # 保存索引
        with open(self.index_path, 'w', encoding='utf-8') as f:
            f.write(index.model_dump_json(indent=2))
```

---

## 历史对比功能架构

### 功能架构

```
┌─────────────────────────────────────────────────────────┐
│              对比功能入口 (UI Layer)                     │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐ │
│  │ 历史记录浏览 │→ │ 版本对比     │→ │ 横向对比     │ │
│  └──────────────┘  └──────────────┘  └──────────────┘ │
└─────────────────────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────┐
│            对比引擎 (Comparison Engine)                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐ │
│  │Version       │  │ Document     │  │ Trend        │ │
│  │Comparator    │  │ Comparator   │  │ Analyzer     │ │
│  └──────────────┘  └──────────────┘  └──────────────┘ │
└─────────────────────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────┐
│            可视化展示 (Visualization)                    │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐ │
│  │ 差异高亮     │  │ 对比表格     │  │ 变化图表     │ │
│  └──────────────┘  └──────────────┘  └──────────────┘ │
└─────────────────────────────────────────────────────────┘
```

### 版本对比器

```python
class VersionComparator:
    """同一文档不同版本的对比"""

    def compare(
        self,
        before: LegalDocumentReport,
        after: LegalDocumentReport
    ) -> VersionComparison:
        """对比两个版本"""
        return VersionComparison(
            metadata=ComparisonMetadata(
                before_date=before.analysis_timestamp,
                after_date=after.analysis_timestamp,
                before_version=before.analysis_version,
                after_version=after.analysis_version
            ),
            # 评分变化
            rating_change=self._compare_rating(before, after),
            # 风险变化
            risk_changes=self._compare_risks(before, after),
            # 条款变化
            clause_changes=self._compare_clauses(before, after),
            # 合规变化
            compliance_changes=self._compare_compliance(before, after),
            # 差异摘要
            summary=self._generate_summary(before, after)
        )

    def _compare_risks(
        self,
        before: LegalDocumentReport,
        after: LegalDocumentReport
    ) -> RiskChanges:
        """对比风险变化"""
        before_risks = set(before.executive_summary.key_risks)
        after_risks = set(after.executive_summary.key_risks)

        return RiskChanges(
            resolved=list(before_risks - after_risks),  # 已解决
            new=list(after_risks - before_risks),        # 新增
            unchanged=list(before_risks & after_risks),  # 未变化
            severity_changes=self._compare_severity(before, after)
        )
```

### UI 交互设计

**历史记录页面**：

```python
def show_history_page():
    """历史记录浏览页面"""
    st.title("📚 分析历史")

    # 筛选器
    col1, col2, col3 = st.columns(3)
    with col1:
        doc_type_filter = st.selectbox("文档类型", ["全部", "劳动合同", "服务协议"])
    with col2:
        date_range = st.date_input("日期范围")
    with col3:
        sort_by = st.selectbox("排序", ["最新", "评分", "风险数量"])

    # 历史记录列表
    history = st.session_state.history_manager.get_history(limit=100)

    for item in history:
        with st.expander(
            f"{item.document_name} - {item.timestamp.strftime('%Y-%m-%d %H:%M')}",
            expanded=False
        ):
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("评分", f"{item.overall_rating:.1f}")
            col2.metric("风险数", item.total_risks)
            col3.metric("耗时", f"{item.duration_seconds:.1f}s")

            with col4:
                if st.button("查看", key=f"view_{item.analysis_id}"):
                    st.session_state.selected_analysis = item.analysis_id
                    st.rerun()

                if st.button("对比", key=f"compare_{item.analysis_id}"):
                    st.session_state.compare_mode = True
                    st.session_state.compare_base = item.analysis_id
                    st.rerun()
```

---

## 可视化图表系统

### 图表架构

```
src/visualization/
├── charts/                  # 图表组件
│   ├── risk_charts.py       # 风险分析图表
│   ├── compliance_charts.py # 合规性图表
│   ├── performance_charts.py # 性能监控图表
│   └── comparison_charts.py  # 对比图表
├── components/              # UI 组件
│   ├── dashboard.py         # 仪表板组件
│   ├── metric_card.py       # 指标卡片
│   └── chart_container.py   # 图表容器
└── themes/                  # 主题配置
    └── color_schemes.py     # 配色方案
```

### 风险分析图表

**1. 风险分布饼图**：

```python
import plotly.graph_objects as go

def create_risk_distribution_pie(risk_summary: Dict[RiskLevel, int]) -> go.Figure:
    """创建风险分布饼图"""
    colors = {
        RiskLevel.CRITICAL: "#DC2626",  # 红色
        RiskLevel.HIGH: "#F97316",      # 橙色
        RiskLevel.MEDIUM: "#EAB308",    # 黄色
        RiskLevel.LOW: "#22C55E",       # 绿色
        RiskLevel.INFO: "#3B82F6",      # 蓝色
    }

    labels = [level.value for level in risk_summary.keys()]
    values = list(risk_summary.values())
    color_list = [colors[level] for level in risk_summary.keys()]

    fig = go.Figure(data=[go.Pie(
        labels=labels,
        values=values,
        marker=dict(colors=color_list),
        textinfo='percent+label',
        hole=0.3,
        hovertemplate='<b>%{label}</b><br>数量: %{value}<br>占比: %{percent}<extra></extra>'
    )])

    fig.update_layout(
        title="风险等级分布",
        showlegend=True,
        height=400
    )

    return fig
```

**2. 风险趋势折线图**：

```python
def create_risk_trend_line(history: List[AnalysisMetadata]) -> go.Figure:
    """创建风险趋势图"""
    daily_stats = defaultdict(lambda: {"rating": [], "risks": []})

    for item in history:
        date_key = item.timestamp.strftime("%Y-%m-%d")
        daily_stats[date_key]["rating"].append(item.overall_rating)
        daily_stats[date_key]["risks"].append(item.total_risks)

    dates = sorted(daily_stats.keys())
    avg_ratings = [np.mean(daily_stats[d]["rating"]) for d in dates]
    avg_risks = [np.mean(daily_stats[d]["risks"]) for d in dates]

    fig = go.Figure()

    # 评分趋势
    fig.add_trace(go.Scatter(
        x=dates,
        y=avg_ratings,
        mode='lines+markers',
        name='平均评分',
        line=dict(color='#3B82F6', width=3),
        hovertemplate='<b>%{x}</b><br>评分: %{y:.2f}<extra></extra>'
    ))

    # 风险数量趋势
    fig.add_trace(go.Scatter(
        x=dates,
        y=avg_risks,
        mode='lines+markers',
        name='平均风险数',
        line=dict(color='#EF4444', width=3),
        yaxis='y2',
        hovertemplate='<b>%{x}</b><br>风险数: %{y:.0f}<extra></extra>'
    ))

    fig.update_layout(
        title="评分与风险趋势",
        yaxis2=dict(
            title="风险数量",
            overlaying='y',
            side='right'
        ),
        hovermode='x unified',
        height=400
    )

    return fig
```

### 合规性仪表板

```python
def create_compliance_gauge(compliance_rate: float) -> go.Figure:
    """创建合规率仪表盘"""
    fig = go.Figure(go.Indicator(
        mode="gauge+number+delta",
        value=compliance_rate,
        domain={'x': [0, 1], 'y': [0, 1]},
        title={'text': "合规率 (%)"},
        delta={'reference': 80},
        gauge={
            'axis': {'range': [None, 100]},
            'bar': {'color': "#3B82F6"},
            'steps': [
                {'range': [0, 60], 'color': "#FEE2E2"},
                {'range': [60, 80], 'color': "#FEF3C7"},
                {'range': [80, 100], 'color': "#D1FAE5"}
            ],
            'threshold': {
                'line': {'color': "red", 'width': 4},
                'thickness': 0.75,
                'value': 80
            }
        }
    ))

    fig.update_layout(height=300)
    return fig
```

---

## 实时进度系统

### 进度追踪器

```python
from enum import Enum
from dataclasses import dataclass
from typing import Dict, List, Optional
import time

class StageStatus(Enum):
    """阶段状态"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"

@dataclass
class StageProgress:
    """单个阶段的进度信息"""
    stage_id: str
    stage_name: str
    status: StageStatus
    progress: float = 0.0
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    error: Optional[str] = None
    details: List[str] = None
    sub_stages: Dict[str, 'StageProgress'] = None

    @property
    def duration(self) -> Optional[float]:
        """阶段耗时"""
        if self.start_time and self.end_time:
            return self.end_time - self.start_time
        return None

class ProgressTracker:
    """进度追踪器"""

    def __init__(self, total_stages: int):
        self.total_stages = total_stages
        self.stages: Dict[str, StageProgress] = {}
        self.current_stage: Optional[str] = None
        self.overall_progress: float = 0.0

    def add_stage(self, stage_id: str, stage_name: str, parent_id: Optional[str] = None):
        """添加阶段"""
        stage = StageProgress(
            stage_id=stage_id,
            stage_name=stage_name,
            status=StageStatus.PENDING,
            details=[]
        )
        self.stages[stage_id] = stage
        return stage

    def start_stage(self, stage_id: str):
        """开始阶段"""
        if stage_id in self.stages:
            self.stages[stage_id].status = StageStatus.IN_PROGRESS
            self.stages[stage_id].start_time = time.time()
            self.current_stage = stage_id

    def update_progress(self, stage_id: str, progress: float, detail: Optional[str] = None):
        """更新进度"""
        if stage_id in self.stages:
            self.stages[stage_id].progress = progress
            if detail:
                if self.stages[stage_id].details is None:
                    self.stages[stage_id].details = []
                self.stages[stage_id].details.append(detail)

    def complete_stage(self, stage_id: str, final_details: Optional[List[str]] = None):
        """完成阶段"""
        if stage_id in self.stages:
            self.stages[stage_id].status = StageStatus.COMPLETED
            self.stages[stage_id].progress = 100.0
            self.stages[stage_id].end_time = time.time()
```

### Streamlit 进度渲染器

```python
class ProgressRenderer:
    """Streamlit 进度渲染器"""

    STATUS_ICONS = {
        StageStatus.PENDING: "⏸️",
        StageStatus.IN_PROGRESS: "⏳",
        StageStatus.COMPLETED: "✅",
        StageStatus.FAILED: "❌",
        StageStatus.SKIPPED: "⏭️"
    }

    def __init__(self, tracker: ProgressTracker):
        self.tracker = tracker

    def render_stages(self):
        """渲染所有阶段"""
        for stage in self.tracker.stages.values():
            self._render_stage(stage, level=0)

    def _render_stage(self, stage: StageProgress, level: int = 0):
        """渲染单个阶段"""
        icon = self.STATUS_ICONS[stage.status]

        if stage.status == StageStatus.IN_PROGRESS:
            # 使用 st.status 展开详细步骤
            with st.status(
                f"{icon} {stage.stage_name}",
                state="running",
                expanded=True
            ):
                if stage.progress > 0:
                    st.progress(stage.progress / 100)

                if stage.details:
                    with st.expander("📋 详细信息"):
                        for detail in stage.details:
                            st.text(f"  • {detail}")

        elif stage.status == StageStatus.COMPLETED:
            duration_str = f" ({stage.duration:.1f}s)" if stage.duration else ""
            st.success(f"{icon} {stage.stage_name}{duration_str}")
```

---

## 响应式 UI 设计

### 响应式容器

```python
class ResponsiveContainer:
    """响应式容器组件"""

    BREAKPOINTS = {
        'mobile': 768,
        'tablet': 1024,
        'desktop': 1440
    }

    @staticmethod
    def get_device_type() -> str:
        """检测设备类型"""
        try:
            screen_width = st.session_state.get('screen_width', 1024)

            if screen_width < ResponsiveContainer.BREAKPOINTS['mobile']:
                return 'mobile'
            elif screen_width < ResponsiveContainer.BREAKPOINTS['tablet']:
                return 'tablet'
            else:
                return 'desktop'
        except:
            return 'desktop'

    @staticmethod
    def render_layout(content_func: Callable):
        """渲染响应式布局"""
        device = ResponsiveContainer.get_device_type()

        if device == 'mobile':
            ResponsiveContainer._render_mobile_layout(content_func)
        elif device == 'tablet':
            ResponsiveContainer._render_tablet_layout(content_func)
        else:
            ResponsiveContainer._render_desktop_layout(content_func)

    @staticmethod
    def _render_mobile_layout(content_func: Callable):
        """移动端布局"""
        # 汉堡菜单按钮
        col1, col2 = st.columns([1, 5])
        with col1:
            if st.button("☰"):
                st.session_state.show_sidebar = not st.session_state.get('show_sidebar', False)
        with col2:
            st.title("⚖️ 法律助手")

        # 主内容
        content_func()
```

### 移动端优化 CSS

```css
/* 移动端优化 */
@media (max-width: 768px) {
    /* 增大按钮尺寸 */
    .stButton > button {
        width: 100%;
        padding: 0.75rem 1rem;
        font-size: 1rem;
    }

    /* 优化输入框 */
    .stTextInput > div > div > input,
    .stSelectbox > div > div > select {
        font-size: 16px; /* 防止 iOS 自动缩放 */
    }

    /* 减小边距 */
    .block-container {
        padding: 1rem;
    }

    /* 隐藏侧边栏 */
    [data-testid="stSidebar"] {
        display: none;
    }
}

/* 触摸设备优化 */
@media (hover: none) and (pointer: coarse) {
    /* 增大所有可点击元素 */
    button, a, input, select {
        min-height: 44px;
        min-width: 44px;
    }
}
```

---

## 实施计划

### Phase 1: Streamlit Cloud 部署 (Week 1-2)

**任务清单**：

- [ ] 创建 Qdrant Cloud 账户和集群
- [ ] 配置 Streamlit Cloud Secrets
- [ ] 创建 `src/storage/` 存储层模块
- [ ] 实现精简的 `requirements.txt`
- [ ] 创建 `.streamlit/config.toml`
- [ ] 编写部署文档
- [ ] 测试部署流程
- [ ] 优化内存使用

**验收标准**：
- ✅ 应用成功部署到 Streamlit Cloud
- ✅ Qdrant Cloud 连接正常
- ✅ 文件上传和分析功能正常
- ✅ 内存使用 < 1GB

### Phase 2: 历史记录功能 (Week 2-3)

**任务清单**：

- [ ] 实现 `HistoryManager` 类
- [ ] 实现分析记录保存/加载
- [ ] 创建历史记录浏览页面
- [ ] 实现历史记录筛选和排序
- [ ] 添加历史记录删除功能
- [ ] 测试数据持久化
- [ ] 编写单元测试

**验收标准**：
- ✅ 分析结果自动保存
- ✅ 历史记录正确显示
- ✅ 筛选和排序功能正常
- ✅ 数据在重启后保留

### Phase 3: 对比功能 (Week 3-4)

**任务清单**：

- [ ] 实现 `VersionComparator`
- [ ] 实现 `DocumentComparator`
- [ ] 创建版本对比页面
- [ ] 创建横向对比页面
- [ ] 实现差异高亮显示
- [ ] 添加对比图表
- [ ] 编写单元测试

**验收标准**：
- ✅ 版本对比功能正常
- ✅ 横向对比支持 2-5 个文档
- ✅ 差异显示清晰直观
- ✅ 对比结果可导出

### Phase 4: 可视化图表 (Week 4-5)

**任务清单**：

- [ ] 实现风险分析图表
- [ ] 实现合规性仪表板
- [ ] 实现性能监控图表
- [ ] 创建综合仪表板页面
- [ ] 优化图表移动端显示
- [ ] 添加图表交互功能
- [ ] 编写单元测试

**验收标准**：
- ✅ 所有图表正确渲染
- ✅ 图表支持交互
- ✅ 移动端显示正常
- ✅ 图表加载速度 < 2s

### Phase 5: 实时进度 (Week 5-6)

**任务清单**：

- [ ] 实现 `ProgressTracker` 类
- [ ] 实现 `ProgressRenderer` 类
- [ ] 集成到分析流程
- [ ] 添加进度装饰器
- [ ] 优化进度刷新频率
- [ ] 测试长时间运行场景
- [ ] 编写单元测试

**验收标准**：
- ✅ 进度实时更新
- ✅ 详细步骤可展开
- ✅ 错误正确显示
- ✅ 不影响分析性能

### Phase 6: 响应式 UI (Week 6-7)

**任务清单**：

- [ ] 实现 `ResponsiveContainer` 类
- [ ] 实现设备类型检测
- [ ] 创建移动端布局
- [ ] 注入响应式 CSS
- [ ] 优化触摸交互
- [ ] 测试各种设备
- [ ] 编写单元测试

**验收标准**：
- ✅ 移动端布局正常
- ✅ 平板端布局正常
- ✅ 桌面端布局正常
- ✅ 触摸交互流畅

### 总体验收标准

| 目标 | 验收标准 | 测量方式 |
|-----|---------|---------|
| **部署成功** | Streamlit Cloud 可访问 | URL 访问测试 |
| **历史功能** | 100% 分析结果可保存 | 自动化测试 |
| **对比功能** | 支持 5 种对比类型 | 功能测试 |
| **可视化** | 10+ 图表类型 | 统计测试 |
| **进度显示** | 实时延迟 < 500ms | 性能测试 |
| **响应式** | 3 种设备适配 | 兼容性测试 |

---

## 附录

### 技术栈总结

| 类别 | 技术 |
|-----|------|
| **部署** | Streamlit Cloud, Docker |
| **数据库** | Qdrant Cloud, JSON 文件 |
| **可视化** | Plotly, Streamlit |
| **存储** | gzip, pickle |
| **UI** | CSS Media Query, JavaScript |

### 参考资源

- [Streamlit Cloud 文档](https://docs.streamlit.io/streamlit-cloud)
- [Qdrant Cloud 文档](https://qdrant.tech/documentation/cloud/)
- [Plotly Python 文档](https://plotly.com/python/)
- [响应式设计指南](https://web.dev/responsive-web-design-basics/)

---

**文档版本**: 1.0
**最后更新**: 2026-01-15
**状态**: ✅ 设计完成，待实施

**下一步**: 询问用户是否准备开始实施？
