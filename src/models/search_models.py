"""
检索层数据模型
定义搜索结果、上下文和相关数据结构
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum


class RetrievalMethod(str, Enum):
    """检索方法"""
    BM25 = "bm25"
    VECTOR = "vector"
    RRF_FUSION = "rrf_fusion"
    RERANK_COHERE = "cohere_rerank"
    RERANK_JINA = "jina_rerank"


class SearchResult(BaseModel):
    """单个搜索结果"""
    doc_id: str = Field(..., description="文档唯一标识")
    score: float = Field(..., ge=0, description="相关性分数")
    retrieval_method: RetrievalMethod = Field(
        ...,
        description="检索方法"
    )

    # 内容信息
    content: Optional[str] = Field(None, description="文档内容")
    title: Optional[str] = Field(None, description="文档标题")
    metadata: Optional[Dict[str, Any]] = Field(
        default_factory=dict,
        description="额外元数据"
    )

    # 检索元数据
    original_rank: Optional[int] = Field(None, description="原始排名")
    timestamp: datetime = Field(default_factory=datetime.now)

    class Config:
        use_enum_values = True


class SearchStatistics(BaseModel):
    """检索统计信息"""
    total_retrieved: int = Field(..., description="检索到的总结果数")
    bm25_count: int = Field(default=0, description="BM25 检索结果数")
    vector_count: int = Field(default=0, description="向量检索结果数")
    fused_count: int = Field(default=0, description="融合后结果数")
    reranked_count: int = Field(default=0, description="重排后结果数")

    duration_ms: float = Field(..., description="总耗时（毫秒）")
    bm25_duration_ms: float = Field(default=0, description="BM25 耗时")
    vector_duration_ms: float = Field(default=0, description="向量检索耗时")
    fusion_duration_ms: float = Field(default=0, description="融合耗时")
    rerank_duration_ms: float = Field(default=0, description="重排耗时")

    cache_hit: bool = Field(default=False, description="是否命中缓存")

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "total_retrieved": self.total_retrieved,
            "bm25_count": self.bm25_count,
            "vector_count": self.vector_count,
            "fused_count": self.fused_count,
            "reranked_count": self.reranked_count,
            "duration_ms": self.duration_ms,
            "cache_hit": self.cache_hit
        }


class SearchContext(BaseModel):
    """搜索上下文 - 包含所有检索结果和统计信息"""
    query: str = Field(..., description="搜索查询")
    results: List[SearchResult] = Field(
        default_factory=list,
        description="搜索结果列表"
    )
    statistics: SearchStatistics = Field(..., description="检索统计信息")

    # 检索参数
    retrieval_k: int = Field(default=50, description="初始检索数量")
    fusion_k: int = Field(default=20, description="融合后数量")
    rerank_k: int = Field(default=10, description="重排后数量")

    @property
    def top_results(self, limit: int = 5) -> List[SearchResult]:
        """获取前 N 个结果"""
        return self.results[:limit]

    @property
    def has_results(self) -> bool:
        """是否有结果"""
        return len(self.results) > 0

    def get_result_by_id(self, doc_id: str) -> Optional[SearchResult]:
        """根据文档 ID 获取结果"""
        for result in self.results:
            if result.doc_id == doc_id:
                return result
        return None

    def to_string(self) -> str:
        """转换为字符串（用于 Agent 提示）"""
        if not self.has_results:
            return f"未找到与查询 '{self.query}' 相关的结果。"

        output = [
            f"查询: {self.query}",
            f"找到 {len(self.results)} 个相关结果：\n"
        ]

        for i, result in enumerate(self.results, 1):
            output.append(
                f"{i}. [分数: {result.score:.3f}] "
                f"{result.title or result.doc_id}\n"
                f"   {result.content[:200]}..."
            )

        return "\n".join(output)


class Query(BaseModel):
    """搜索查询"""
    text: str = Field(..., description="查询文本")
    embedding: Optional[List[float]] = Field(None, description="查询向量")
    weight: float = Field(default=1.0, ge=0, le=1, description="查询权重")
    metadata: Optional[Dict[str, Any]] = Field(
        default_factory=dict,
        description="查询元数据"
    )


class Document(BaseModel):
    """文档模型"""
    id: str = Field(..., description="文档唯一标识")
    content: str = Field(..., description="文档内容")
    title: Optional[str] = Field(None, description="文档标题")
    type: Optional[str] = Field(None, description="文档类型")

    metadata: Optional[Dict[str, Any]] = Field(
        default_factory=dict,
        description="文档元数据"
    )
    created_at: datetime = Field(default_factory=datetime.now)

    def get_snippet(self, max_length: int = 200) -> str:
        """获取内容片段"""
        if len(self.content) <= max_length:
            return self.content
        return self.content[:max_length] + "..."
