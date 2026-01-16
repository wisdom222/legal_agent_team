"""
混合检索引擎
编排 BM25、向量检索和 Reranker 的完整检索流程
"""

import asyncio
from typing import List, Optional, Tuple
import time

from .bm25_indexer import BM25Indexer
from .rrf_fusion import RRFFusion
from .reranker import RerankerClient, RerankerFallback
from ..models.search_models import (
    SearchResult,
    SearchContext,
    SearchStatistics,
    RetrievalMethod,
    Document
)


class HybridSearchEngine:
    """
    混合检索引擎

    完整的检索流程:
    1. 并行执行 BM25 和向量检索
    2. 使用 RRF 算法融合双路结果
    3. 调用 Reranker API 精排
    4. 返回最终结果

    支持降级策略:
    - 单路检索失败时，使用另一路结果
    - Reranker 超时时，使用融合结果

    参数:
        bm25_indexer: BM25 索引器
        vector_search_func: 向量检索函数
        rrf_fusion: RRF 融合器
        reranker: Reranker 客户端（可选）
        enable_cache: 是否启用缓存
    """

    def __init__(
        self,
        bm25_indexer: BM25Indexer,
        vector_search_func: callable,
        rrf_fusion: Optional[RRFFusion] = None,
        reranker: Optional[RerankerClient] = None,
        enable_cache: bool = False
    ):
        self.bm25 = bm25_indexer
        self.vector_search = vector_search_func
        self.rrf = rrf_fusion or RRFFusion()
        self.reranker = reranker
        self.enable_cache = enable_cache

        # 缓存（简单内存缓存，生产环境建议使用 Redis）
        self._cache = {}

    async def search(
        self,
        query: str,
        retrieval_k: int = 50,
        fusion_k: int = 20,
        rerank_k: int = 10,
        enable_reranker: bool = True
    ) -> SearchContext:
        """
        执行完整的混合检索流程

        Args:
            query: 用户查询
            retrieval_k: 初始检索数量（每路）
            fusion_k: 融合后数量
            rerank_k: 重排后数量
            enable_reranker: 是否启用 Reranker

        Returns:
            SearchContext 对象
        """
        start_time = time.time()

        # 检查缓存
        cache_key = f"{query}:{retrieval_k}:{fusion_k}:{rerank_k}"
        if self.enable_cache and cache_key in self._cache:
            print(f"✅ 缓存命中: {query}")
            return self._cache[cache_key]

        # 统计信息
        stats = SearchStatistics(
            total_retrieved=0,
            duration_ms=0,
            cache_hit=False
        )

        # ========== Phase 1: 并行双路检索 ==========
        print(f"🔍 执行双路检索: {query}")

        bm25_results, bm25_duration = await self._safe_bm25_search(
            query,
            top_k=retrieval_k
        )
        stats.bm25_count = len(bm25_results)
        stats.bm25_duration_ms = bm25_duration * 1000

        vector_results, vector_duration = await self._safe_vector_search(
            query,
            top_k=retrieval_k
        )
        stats.vector_count = len(vector_results)
        stats.vector_duration_ms = vector_duration * 1000

        # ========== Phase 2: 检查是否完全失败 ==========
        if not bm25_results and not vector_results:
            print("⚠️ 所有检索路径均失败")
            stats.total_retrieved = 0
            stats.duration_ms = (time.time() - start_time) * 1000
            return SearchContext(
                query=query,
                results=[],
                statistics=stats,
                retrieval_k=retrieval_k,
                fusion_k=fusion_k,
                rerank_k=rerank_k
            )

        # ========== Phase 3: 降级处理 ==========
        if not bm25_results or not vector_results:
            method = "vector" if vector_results else "bm25"
            print(f"⚠️ 降级：仅使用 {method} 检索")

            final_results = vector_results if vector_results else bm25_results
            final_results = final_results[:rerank_k]

            stats.total_retrieved = len(final_results)
            stats.duration_ms = (time.time() - start_time) * 1000

            context = SearchContext(
                query=query,
                results=final_results,
                statistics=stats,
                retrieval_k=retrieval_k,
                fusion_k=fusion_k,
                rerank_k=rerank_k
            )

            # 缓存结果
            if self.enable_cache:
                self._cache[cache_key] = context

            return context

        # ========== Phase 4: RRF 融合 ==========
        print(f"🔗 RRF 融合: {len(bm25_results)} + {len(vector_results)}")

        fused_results, fusion_duration = self.rrf.fuse_two(
            bm25_results,
            vector_results,
            top_k=fusion_k
        )
        stats.fused_count = len(fused_results)
        stats.fusion_duration_ms = fusion_duration * 1000

        # ========== Phase 5: Reranker 精排 ==========
        if enable_reranker and self.reranker:
            print(f"🎯 Reranker 精排: {len(fused_results)} 个结果")

            final_results, rerank_duration = await self.reranker.rerank(
                query=query,
                documents=fused_results,
                top_k=rerank_k
            )
            stats.reranked_count = len(final_results)
            stats.rerank_duration_ms = rerank_duration * 1000
        else:
            print("⏭️  跳过 Reranker")
            final_results = fused_results[:rerank_k]
            stats.reranked_count = len(final_results)

        # ========== Phase 6: 构建上下文 ==========
        stats.total_retrieved = len(final_results)
        stats.duration_ms = (time.time() - start_time) * 1000

        context = SearchContext(
            query=query,
            results=final_results,
            statistics=stats,
            retrieval_k=retrieval_k,
            fusion_k=fusion_k,
            rerank_k=rerank_k
        )

        # 缓存结果
        if self.enable_cache:
            self._cache[cache_key] = context

        print(f"✅ 检索完成: {len(final_results)} 个结果, "
              f"耗时 {stats.duration_ms:.0f}ms")

        return context

    async def _safe_bm25_search(
        self,
        query: str,
        top_k: int
    ) -> Tuple[List[SearchResult], float]:
        """安全的 BM25 检索（带错误处理）"""
        try:
            return self.bm25.search(query, top_k=top_k)
        except Exception as e:
            print(f"⚠️ BM25 检索失败: {e}")
            return [], 0.0

    async def _safe_vector_search(
        self,
        query: str,
        top_k: int
    ) -> Tuple[List[SearchResult], float]:
        """安全的向量检索（带错误处理）"""
        try:
            return await self.vector_search(query, top_k)
        except Exception as e:
            print(f"⚠️ 向量检索失败: {e}")
            return [], 0.0

    def clear_cache(self):
        """清空缓存"""
        self._cache.clear()
        print("✅ 缓存已清空")

    def get_engine_info(self) -> dict:
        """获取引擎信息"""
        return {
            "bm25_indexed": self.bm25.get_index_info()["indexed"],
            "bm25_documents": self.bm25.get_index_info()["document_count"],
            "rrf_k": self.rrf.k,
            "reranker_enabled": self.reranker is not None,
            "reranker_info": self.reranker.get_reranker_info() if self.reranker else None,
            "cache_enabled": self.enable_cache,
            "cache_size": len(self._cache)
        }


# 工厂函数
def create_hybrid_search_engine(
    bm25_indexer: BM25Indexer,
    vector_search_func: callable,
    rrf_k: int = 60,
    reranker_provider: Optional[str] = None,
    reranker_api_key: Optional[str] = None,
    enable_cache: bool = False
) -> HybridSearchEngine:
    """
    创建混合检索引擎

    Args:
        bm25_indexer: BM25 索引器
        vector_search_func: 向量检索函数
        rrf_k: RRF 平滑参数
        reranker_provider: Reranker 提供商（"cohere" 或 "jina"）
        reranker_api_key: Reranker API 密钥
        enable_cache: 是否启用缓存

    Returns:
        HybridSearchEngine 实例
    """
    # 创建 RRF 融合器
    rrf = RRFFusion(k=rrf_k)

    # 创建 Reranker（可选）
    reranker = None
    if reranker_provider and reranker_api_key:
        reranker = RerankerClient(
            provider=reranker_provider,
            api_key=reranker_api_key
        )

    # 创建引擎
    return HybridSearchEngine(
        bm25_indexer=bm25_indexer,
        vector_search_func=vector_search_func,
        rrf_fusion=rrf,
        reranker=reranker,
        enable_cache=enable_cache
    )
