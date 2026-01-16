# AI 法律文档分析助手 - 架构增强设计文档

**项目**: DL_Project2 - AI 法律文档分析助手
**日期**: 2026-01-15
**版本**: 1.0
**状态**: 设计阶段

---

## 📋 目录

1. [设计概述](#设计概述)
2. [系统架构](#系统架构)
3. [Hybrid Search + Reranker](#hybrid-search--reranker)
4. [Reviewer 机制](#reviewer-机制)
5. [结构化输出](#结构化输出)
6. [数据流与集成](#数据流与集成)
7. [错误处理与测试](#错误处理与测试)
8. [实施计划](#实施计划)

---

## 设计概述

### 背景

当前 AI 法律文档分析助手基于 Agno 多智能体框架和 Qdrant 向量数据库，能够执行基础的文档分析功能。为提升检索质量、分析深度和输出规范性，提出三大架构改进目标。

### 改进目标

| # | 目标 | 问题描述 | 解决方案 |
|---|------|---------|---------|
| 1 | **检索增强** | 纯向量检索无法精确匹配关键词，相关性不足 | Hybrid Search (BM25 + 向量) + Reranker |
| 2 | **审查机制** | 单 Agent 分析缺乏多维度验证 | 并行 Reviewer 机制 + 仲裁者 |
| 3 | **输出规范化** | 自由文本输出无法直接用于业务场景 | Pydantic 结构化输出 + 可导出报告 |

### 预期收益

- **检索质量提升**: 相关性提升 30-50%，精确匹配召回率提升 40%
- **分析全面性**: 多维度问题检出率提升 60%
- **输出一致性**: 100% 符合规范，可直接用于业务场景

---

## 系统架构

### 整体架构图

```
┌─────────────────────────────────────────────────────────────┐
│                     Streamlit UI Layer                      │
│              (文档上传、结果展示、报告导出)                    │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                   Orchestration Layer                        │
│  ┌──────────────┐  ┌──────────────────┐  ┌──────────────┐  │
│  │ Hybrid Query │→ │ Agent Team Lead  │→ │ Report       │  │
│  │ Engine       │  │ (Agno Framework) │  │ Generator    │  │
│  └──────────────┘  └──────────────────┘  └──────────────┘  │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                    Intelligence Layer                        │
│  ┌──────────────────────────────────────────────────────┐  │
│  │              Knowledge & Memory System                │  │
│  │  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌────────────┐  │  │
│  │  │ BM25    │ │ Qdrant  │ │Reranker │ │ Structured │  │  │
│  │  │ Indexer │ │ Vector  │ │  API    │ │  Output    │  │  │
│  │  └─────────┘ └─────────┘ └─────────┘ └────────────┘  │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │            Multi-Agent Review System                  │  │
│  │  ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐ ┌──────────┐  │  │
│  │  │Writer│ │Legal │ │Risk  │ │Format│ │Arbitrator│  │  │
│  │  │Agent │ │Review│ │Review│ │Review│ │  Agent   │  │  │
│  │  └──────┘ └──────┘ └──────┘ └──────┘ └──────────┘  │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

### 核心组件

1. **Hybrid Query Engine**: 混合检索引擎，整合 BM25、向量检索和 Reranker
2. **Agent Team Lead**: 基于 Agno 框架的多智能体编排器
3. **Multi-Agent Review System**: 并行审查系统（Writer + 4 Reviewers + Arbitrator）
4. **Report Generator**: 结构化报告生成器（支持 JSON/PDF/DOCX 导出）

---

## Hybrid Search + Reranker

### 架构设计

```
User Query
     ↓
Query Preprocessing (分词 + 嵌入)
     ↓                ↓
┌─────────────┐   ┌─────────────┐
│   BM25      │   │   Qdrant    │
│   Search    │   │   Search    │
│  (关键词)   │   │  (向量)     │
└─────────────┘   └─────────────┘
     ↓                ↓
  Top-K(50)        Top-K(50)
     └────────┬────────┘
              ↓
      RRF Fusion (合并去重)
              ↓
         Top-K(20)
              ↓
      Reranker (Cohere/Jina API)
              ↓
         Top-K(10)
              ↓
      返回给 Agent Team
```

### 核心组件

#### 1. BM25 Indexer

使用 `rank_bm25` 库实现关键词索引：

```python
class BM25Indexer:
    def __init__(self, k1=1.5, b=0.75):
        self.k1 = k1  # 词频饱和度
        self.b = b    # 文档长度归一化
        self.bm25 = None

    def index_documents(self, documents: List[Document]):
        """使用 jieba 分词构建索引"""
        self.corpus = [jieba.cut(doc.content) for doc in documents]
        self.bm25 = BM25Okapi(self.corpus, k1=self.k1, b=self.b)

    def search(self, query: str, top_k: int = 50) -> List[SearchResult]:
        """关键词检索"""
        query_tokens = jieba.cut(query)
        scores = self.bm25.get_scores(query_tokens)
        return top_k_results(scores, top_k)
```

#### 2. RRF Fusion

Reciprocal Rank Fusion 融合器：

```python
class RRFFusion:
    def __init__(self, k: int = 60):
        self.k = k  # 平滑参数

    def fuse(self, bm25_results, vector_results, top_k: int = 20):
        """
        RRF 公式: score(d) = Σ 1 / (k + rank(d))
        """
        scores = {}
        for doc_id in all_doc_ids:
            score = 0
            if doc_id in bm25_ranks:
                score += 1 / (self.k + bm25_ranks[doc_id])
            if doc_id in vector_ranks:
                score += 1 / (self.k + vector_ranks[doc_id])
            scores[doc_id] = score
        return sorted_results(scores, top_k)
```

#### 3. Reranker Client

云端 Reranker 集成：

```python
class RerankerClient:
    def __init__(self, provider: str = "cohere"):
        if provider == "cohere":
            self.client = cohere.Client(api_key)

    def rerank(self, query: str, documents: List[SearchResult], top_k: int = 10):
        response = self.client.rerank(
            model="rerank-v3.5",
            query=query,
            documents=[d.content for d in documents],
            top_n=top_k
        )
        return [SearchResult(...) for r in response.results]
```

### 配置参数

| 参数 | 默认值 | 说明 |
|-----|-------|------|
| `bm25_k1` | 1.5 | 词频饱和度控制 |
| `bm25_b` | 0.75 | 文档长度归一化 |
| `rrf_k` | 60 | RRF 平滑参数 |
| `retrieval_k` | 50 | 初始检索数量 |
| `fusion_k` | 20 | 融合后数量 |
| `rerank_k` | 10 | 重排后数量 |

### 降级策略

- **双路容错**: BM25 或向量任一失败时，使用另一路结果
- **Reranker 超时**: 10 秒超时后直接使用融合结果
- **缓存**: Redis 缓存高频查询的 Reranker 结果

---

## Reviewer 机制

### 工作流程

```
文档输入
     ↓
┌─────────────────────────────────────────┐
│  Phase 1: Draft Generation              │
│  Writer Agent 生成初步分析               │
└─────────────────────────────────────────┘
     ↓
┌─────────────────────────────────────────┐
│  Phase 2: Parallel Review               │
│  ┌────────┐ ┌────────┐ ┌────────┐      │
│  │  Legal │ │  Risk  │ │ Format │      │
│  │Reviewer│ │Reviewer│ │Reviewer│      │
│  └────────┘ └────────┘ └────────┘      │
└─────────────────────────────────────────┘
     ↓
┌─────────────────────────────────────────┐
│  Phase 3: Arbitration                   │
│  Arbitrator Agent 解决冲突               │
└─────────────────────────────────────────┘
     ↓
┌─────────────────────────────────────────┐
│  Phase 4: Revision                      │
│  Writer Agent 根据反馈修正               │
└─────────────────────────────────────────┘
     ↓
最终报告
```

### Reviewer 角色定义

| Reviewer | 角色 | 审查重点 | 优先级 |
|---------|------|---------|--------|
| **Legal Reviewer** | 法律合规审查员 | 法条引用准确性、管辖权、合规性 | 1 (最高) |
| **Risk Reviewer** | 风险评估审查员 | 不公平条款、潜在纠纷、风险评估 | 2 |
| **Format Reviewer** | 格式规范审查员 | 文档结构、术语一致性、格式规范 | 4 (最低) |
| **Business Reviewer** | 商业逻辑审查员 | 交易合理性、商业条款公平性 | 3 |
| **Arbitrator** | 审查仲裁者 | 冲突解决、优先级判断 | 超级 |

### 冲突解决规则

```
优先级原则:
1. CRITICAL 级别问题必须修正
2. 法律合规 > 风险控制 > 商业逻辑 > 格式规范
3. 多个 Reviewer 标记的同一问题优先级提升
4. 无法自动解决的冲突标记为"需人工确认"
```

### 数据模型

```python
class ReviewIssue(BaseModel):
    issue_id: str
    reviewer_type: ReviewerType
    severity: SeverityLevel  # CRITICAL/HIGH/MEDIUM/LOW/INFO
    description: str
    location: IssueLocation
    suggested_fix: Optional[str]
    legal_basis: Optional[str]

class ReviewFeedback(BaseModel):
    reviewer_type: ReviewerType
    issues: List[ReviewIssue]
    overall_rating: float  # 0-10
    summary: str
    confidence: float  # 0-1

class ConsolidatedFeedback(BaseModel):
    prioritized_issues: List[ReviewIssue]
    conflicts_resolved: List[ConflictResolution]
    revision_instructions: str
```

### 并行执行

```python
async def execute_parallel_review(document, draft_report):
    """并行执行所有 Reviewer"""
    review_tasks = [
        legal_reviewer.run(draft_report),
        risk_reviewer.run(draft_report),
        format_reviewer.run(draft_report),
        business_reviewer.run(draft_report)
    ]
    reviews = await asyncio.gather(*review_tasks)

    # 仲裁
    feedback = await arbitrator.run(reviews)

    # 修正
    final_report = await writer.revise(draft_report, feedback)

    return final_report
```

---

## 结构化输出

### 三层报告结构

```
LegalDocumentReport
├── 元数据 (Metadata)
│   ├── document_id, document_name
│   ├── analysis_timestamp, analysis_version
│   └── analysis_duration_seconds
│
├── 第一层: ExecutiveSummary (执行摘要)
│   ├── document_type, overall_rating
│   ├── risk_summary (各风险级别数量)
│   ├── key_risks (前 5 个关键风险)
│   ├── critical_issues (必须处理的严重问题)
│   └── quick_recommendations (优先级排序的建议)
│
├── 第二层: DetailedAnalysis (详细分析)
│   ├── clauses_analyzed, compliance_rate
│   ├── clause_breakdown (逐条分析)
│   ├── compliance_checklist (合规清单)
│   └── jurisdiction_analysis (管辖权分析)
│
└── 第三层: EvidenceSources (证据来源)
    ├── evidence_and_reasoning (按类型分组)
    └── agent_reasoning_chain (所有 Agent 推理链)
```

### Pydantic Schema

```python
class ExecutiveSummary(BaseModel):
    """执行摘要 - 面向高管/客户"""
    document_type: DocumentType
    overall_rating: float = Field(..., ge=0, le=10)
    risk_summary: Dict[RiskLevel, int]
    key_risks: List[str] = Field(max_items=5)
    critical_issues: List[str] = Field(max_items=3)
    quick_recommendations: List[QuickRecommendation]
    one_sentence_summary: str = Field(max_length=200)

class ClauseAnalysis(BaseModel):
    """条款详细分析"""
    clause_id: int
    clause_text: str
    risk_level: RiskLevel
    risk_score: float = Field(..., ge=0, le=100)
    issues_identified: List[str]
    suggestions: List[str]
    legal_basis: List[LegalBasis]

class DetailedAnalysis(BaseModel):
    """详细分析 - 面向律师/法务"""
    total_clauses: int
    clauses_with_issues: int
    compliance_rate: float
    clause_breakdown: List[ClauseAnalysis]
    compliance_checklist: List[ComplianceChecklist]
    jurisdiction_analysis: Optional[JurisdictionAnalysis]

class LegalDocumentReport(BaseModel):
    """完整法律文档分析报告"""
    document_id: str
    document_name: str
    analysis_timestamp: datetime
    analysis_version: str = "1.0"
    analysis_duration_seconds: float

    executive_summary: ExecutiveSummary
    detailed_analysis: DetailedAnalysis
    evidence_and_reasoning: Dict[str, List[EvidenceSource]]
    agent_reasoning_chain: List[AgentReasoning]
```

### Agno Response Model 集成

```python
class WriterAgent:
    def __init__(self):
        self.agent = Agent(
            name="WriterAgent",
            model=OpenAIChat(id="gpt-4o"),
            response_model=LegalDocumentReport,  # 强制结构化输出
            instructions=[
                "严格按照 Pydantic Schema 格式输出",
                "确保所有必填字段都有值"
            ]
        )

    async def analyze(self, document, context) -> LegalDocumentReport:
        report: LegalDocumentReport = await self.agent.arun(
            f"分析文档: {document.content}"
        )
        return report  # 自动验证 Schema
```

### 报告导出

支持三种导出格式：

| 格式 | 用途 | 实现方式 |
|-----|------|---------|
| **JSON** | 原始数据、系统集成 | Pydantic `.json()` |
| **PDF** | 专业报告、存档 | WeasyPrint/ReportLab |
| **DOCX** | 可编辑文档 | python-docx |

---

## 数据流与集成

### 端到端流程

```
用户上传文档
     ↓
文档解析 (PDF/DOCX → Document)
     ↓
查询生成 (规则模板 + LLM 生成)
     ↓
混合检索 (BM25 + Vector → RRF → Reranker)
     ↓
Agent 分析 (Writer → Reviewers → Arbitrator → Revision)
     ↓
报告生成 (Executive + Detailed + Evidence)
     ↓
导出展示 (JSON/PDF/DOCX + Streamlit UI)
```

### 编排器设计

```python
class DocumentAnalysisOrchestrator:
    async def analyze_document(self, file, analysis_type):
        # Stage 1: 文档预处理
        document = await self._parse_document(file)

        # Stage 2: 查询生成
        queries = await self._generate_queries(document, analysis_type)

        # Stage 3: 混合检索
        contexts = [await self.hybrid_search.search(q) for q in queries]
        merged_context = self._merge_contexts(contexts)

        # Stage 4: Agent 分析
        report = await self.agent_pipeline.execute(document, merged_context)

        # Stage 5: 报告生成
        report.analysis_duration_seconds = time.time() - start_time

        # Stage 6: 缓存结果
        await self._cache_result(document, report)

        return report
```

### 配置管理

```python
# config/.env
QDRANT_URL=http://localhost:6333
COHERE_API_KEY=xxx
OPENAI_API_KEY=xxx
REDIS_URL=redis://localhost:6379

# config/settings.py
class HybridSearchConfig(BaseSettings):
    bm25_k1: float = 1.5
    rrf_k: int = 60
    reranker_provider: str = "cohere"
    reranker_model: str = "rerank-v3.5"
```

---

## 错误处理与测试

### 错误分类

| 类别 | 处理策略 | 示例 |
|-----|---------|------|
| **RETRYABLE** | 指数退避重试 | API 临时故障 |
| **RATE_LIMIT** | 等待后重试 | API 限流 |
| **TIMEOUT** | 降级方案 | Reranker 超时 → 使用融合结果 |
| **DEGRADED** | 返回降级结果 | 单路检索失败 → 使用另一路 |
| **NON_RETRYABLE** | 返回错误 | Schema 验证失败 |

### 降级策略

1. **检索降级**:
   - BM25 失败 → 仅向量检索
   - 向量检索失败 → 仅 BM25
   - Reranker 超时 → 使用 RRF 融合结果

2. **分析降级**:
   - Reviewer 失败 → 记录警告，继续其他 Reviewer
   - 仲裁失败 → 使用简单优先级规则
   - 超时 → 返回当前草稿 + 警告

### 测试策略

| 测试类型 | 覆盖率目标 | 关键场景 |
|---------|----------|---------|
| **单元测试** | 85%+ | BM25、RRF、Reranker、Schema 验证 |
| **集成测试** | 75%+ | 完整分析流程、缓存、导出 |
| **端到端测试** | 70%+ | 多文档并发、性能测试 |

### 监控指标

```python
# Prometheus 指标
retrieval_requests_total{method, status}
retrieval_duration_seconds{method}
agent_execution_duration_seconds{agent_name, stage}
report_generation_duration_seconds
active_analyses
```

---

## 实施计划

### Phase 1: 基础设施 (Week 1-2)

- [ ] 搭建 BM25 索引系统
- [ ] 实现 RRF 融合器
- [ ] 集成 Cohere Reranker API
- [ ] 编写检索层单元测试

### Phase 2: Agent Pipeline (Week 3-4)

- [ ] 实现并行 Reviewer 系统
- [ ] 开发 Arbitrator Agent
- [ ] 实现 Draft-Critique-Revise 流程
- [ ] 编写 Agent 层测试

### Phase 3: 结构化输出 (Week 5-6)

- [ ] 定义完整 Pydantic Schema
- [ ] 集成 Agno Response Model
- [ ] 实现报告导出器 (JSON/PDF/DOCX)
- [ ] 更新 Streamlit UI

### Phase 4: 集成与优化 (Week 7-8)

- [ ] 实现编排器
- [ ] 添加错误处理和降级策略
- [ ] 集成监控和日志
- [ ] 性能优化和压力测试

### 验收标准

| 目标 | 验收标准 | 测量方式 |
|-----|---------|---------|
| **检索质量** | 相关性提升 30%+ | 人工评估 100 个查询 |
| **分析全面性** | 多维度检出率提升 60% | 测试集对比 |
| **输出一致性** | 100% 符合 Schema | 自动化测试 |
| **系统稳定性** | 99% 可用性 | 监控数据 |

---

## 附录

### 技术栈总结

| 组件 | 技术 |
|-----|------|
| **检索** | rank_bm25, Qdrant, Cohere Reranker |
| **Agent 框架** | Agno, OpenAI GPT-4o |
| **数据验证** | Pydantic v2 |
| **文档处理** | pdfplumber, python-docx |
| **报告生成** | WeasyPrint, python-docx |
| **缓存** | Redis |
| **监控** | Prometheus |

### 参考资源

- [RRF 论文](https://plg.uwaterloo.ca/~gvcormac/cormacksigir09-rrf.pdf)
- [Cohere Rerank API](https://docs.cohere.com/reference/rerank)
- [Agno Response Models](https://github.com/pydantic/agno)
- [Pydantic v2 文档](https://docs.pydantic.dev/latest/)

---

**文档版本**: 1.0
**最后更新**: 2026-01-15
**状态**: ✅ 设计完成，待实施
