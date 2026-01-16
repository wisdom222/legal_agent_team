"""
Reranker 客户端
集成 Cohere/Jina Reranker API 进行结果重排序
"""

import asyncio
from typing import List, Optional, Literal
import time

try:
    import cohere
    COHERE_AVAILABLE = True
except ImportError:
    COHERE_AVAILABLE = False

from ..models.search_models import (
    SearchResult,
    RetrievalMethod
)


class RerankerClient:
    """
    Reranker 客户端

    支持多个 Reranker 提供商:
    - Cohere Rerank API
    - Jina Reranker API

    Reranker 能够基于查询上下文对检索结果进行精排，
    通常比简单的向量相似度更准确。

    参数:
        provider: 提供商名称 ("cohere" 或 "jina")
        api_key: API 密钥
        model: 模型名称
        timeout: 请求超时时间（秒）
    """

    def __init__(
        self,
        provider: Literal["cohere", "jina"] = "cohere",
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        timeout: float = 30.0
    ):
        self.provider = provider
        self.timeout = timeout

        if provider == "cohere":
            if not COHERE_AVAILABLE:
                raise ImportError(
                    "cohere 包未安装。请运行: pip install cohere"
                )
            if not api_key:
                raise ValueError("Cohere API key is required")

            self.client = cohere.Client(api_key=api_key)
            self.model = model or "rerank-v3.5"

        elif provider == "jina":
            # Jina 客户端配置
            if not api_key:
                raise ValueError("Jina API key is required")

            self.api_key = api_key
            self.model = model or "jina-reranker-v1-base-en"
            self.base_url = "https://api.jina.ai/v1/rerank"

        else:
            raise ValueError(f"Unsupported provider: {provider}")

    async def rerank(
        self,
        query: str,
        documents: List[SearchResult],
        top_k: int = 10
    ) -> Tuple[List[SearchResult], float]:
        """
        使用 Reranker API 重新排序

        Args:
            query: 用户查询
            documents: 待重排的文档列表
            top_k: 返回前 K 个结果

        Returns:
            (重排后的结果列表, 耗时秒数)
        """
        start_time = time.time()

        try:
            # 使用超时控制
            if self.provider == "cohere":
                results = await asyncio.wait_for(
                    self._rerank_cohere(query, documents, top_k),
                    timeout=self.timeout
                )
            elif self.provider == "jina":
                results = await asyncio.wait_for(
                    self._rerank_jina(query, documents, top_k),
                    timeout=self.timeout
                )
            else:
                raise ValueError(f"Unsupported provider: {self.provider}")

            duration = time.time() - start_time
            return results, duration

        except asyncio.TimeoutError:
            print(f"⚠️ Reranker 超时 ({self.timeout}s)，返回原始结果")
            duration = time.time() - start_time
            return documents[:top_k], duration

        except Exception as e:
            print(f"⚠️ Reranker 失败: {e}，返回原始结果")
            duration = time.time() - start_time
            return documents[:top_k], duration

    async def _rerank_cohere(
        self,
        query: str,
        documents: List[SearchResult],
        top_k: int
    ) -> List[SearchResult]:
        """使用 Cohere API 重排"""
        # 准备文档内容
        doc_texts = [d.content or d.title or d.doc_id for d in documents]

        # 调用 Cohere API
        response = self.client.rerank(
            model=self.model,
            query=query,
            documents=doc_texts,
            top_n=top_k,
            return_documents=False
        )

        # 构建结果
        reranked_results = []
        for r in response.results:
            original_doc = documents[r.index]
            reranked_results.append(
                SearchResult(
                    doc_id=original_doc.doc_id,
                    score=r.relevance_score,
                    retrieval_method=RetrievalMethod.RERANK_COHERE,
                    content=original_doc.content,
                    title=original_doc.title,
                    metadata={
                        **original_doc.metadata,
                        "rerank_index": r.index,
                        "reranked": True
                    },
                    original_rank=r.index + 1
                )
            )

        return reranked_results

    async def _rerank_jina(
        self,
        query: str,
        documents: List[SearchResult],
        top_k: int
    ) -> List[SearchResult]:
        """使用 Jina API 重排"""
        import httpx

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }

        data = {
            "model": self.model,
            "query": query,
            "documents": [
                {"text": d.content or d.title or d.doc_id}
                for d in documents
            ],
            "top_n": top_k
        }

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                self.base_url,
                headers=headers,
                json=data
            )
            response.raise_for_status()
            result = response.json()

        # 构建结果
        reranked_results = []
        for r in result.get("results", []):
            original_doc = documents[r["index"]]
            reranked_results.append(
                SearchResult(
                    doc_id=original_doc.doc_id,
                    score=r["relevance_score"],
                    retrieval_method=RetrievalMethod.RERANK_JINA,
                    content=original_doc.content,
                    title=original_doc.title,
                    metadata={
                        **original_doc.metadata,
                        "rerank_index": r["index"],
                        "reranked": True
                    },
                    original_rank=r["index"] + 1
                )
            )

        return reranked_results

    def get_reranker_info(self) -> dict:
        """获取 Reranker 信息"""
        return {
            "provider": self.provider,
            "model": self.model,
            "timeout": self.timeout,
            "available": COHERE_AVAILABLE if self.provider == "cohere" else True
        }


# 工厂函数
def create_reranker(
    provider: Literal["cohere", "jina"] = "cohere",
    api_key: Optional[str] = None,
    model: Optional[str] = None,
    timeout: float = 30.0
) -> RerankerClient:
    """
    创建 Reranker 客户端

    Args:
        provider: 提供商名称
        api_key: API 密钥
        model: 模型名称
        timeout: 请求超时时间

    Returns:
        RerankerClient 实例
    """
    return RerankerClient(
        provider=provider,
        api_key=api_key,
        model=model,
        timeout=timeout
    )


# 降级策略
class RerankerFallback:
    """
    Reranker 降级策略

    当 Reranker API 不可用时，提供简单的降级方案：
    - 直接返回原始结果（按原始分数排序）
    """

    @staticmethod
    async def fallback(
        documents: List[SearchResult],
        top_k: int
    ) -> Tuple[List[SearchResult], float]:
        """
        降级方案：直接返回原始结果

        Args:
            documents: 原始文档列表
            top_k: 返回前 K 个结果

        Returns:
            (结果列表, 0 耗时)
        """
        start_time = time.time()

        # 按原始分数排序
        sorted_docs = sorted(
            documents,
            key=lambda x: x.score,
            reverse=True
        )[:top_k]

        # 更新 retrieval_method 标记为降级
        results = []
        for doc in sorted_docs:
            results.append(
                SearchResult(
                    doc_id=doc.doc_id,
                    score=doc.score,
                    retrieval_method=doc.retrieval_method,
                    content=doc.content,
                    title=doc.title,
                    metadata={
                        **doc.metadata,
                        "reranked": False,
                        "fallback": True
                    },
                    original_rank=doc.original_rank
                )
            )

        duration = time.time() - start_time
        return results, duration
