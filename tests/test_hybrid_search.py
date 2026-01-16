"""
检索层单元测试
测试 BM25、RRF、Reranker 和 Hybrid Search Engine
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch

from src.retrieval.bm25_indexer import BM25Indexer
from src.retrieval.rrf_fusion import RRFFusion
from src.retrieval.reranker import RerankerClient, RerankerFallback
from src.retrieval.hybrid_search import HybridSearchEngine
from src.models.search_models import (
    Document,
    SearchResult,
    RetrievalMethod
)


# ======== Fixtures ========

@pytest.fixture
def sample_documents():
    """示例文档集合"""
    return [
        Document(
            id="doc1",
            content="劳动合同法规定，用人单位应当与劳动者订立书面劳动合同",
            title="劳动合同法",
            type="law"
        ),
        Document(
            id="doc2",
            content="试用期工资不得低于本单位相同岗位最低档工资或者劳动合同约定工资的百分之八十",
            title="试用期规定",
            type="law"
        ),
        Document(
            id="doc3",
            content="劳动者提前三十日以书面形式通知用人单位，可以解除劳动合同",
            title="辞职流程",
            type="law"
        ),
        Document(
            id="doc4",
            content="用人单位违反本法规定未向劳动者出具解除或者终止劳动合同的书面证明",
            title="合同终止证明",
            type="law"
        ),
        Document(
            id="doc5",
            content="经济补偿按劳动者在本单位工作的年限，每满一年支付一个月工资的标准向劳动者支付",
            title="经济补偿",
            type="law"
        )
    ]


@pytest.fixture
def indexed_bm25(sample_documents):
    """已构建索引的 BM25 索引器"""
    bm25 = BM25Indexer()
    bm25.index_documents(sample_documents)
    return bm25


@pytest.fixture
def sample_search_results():
    """示例搜索结果"""
    return [
        SearchResult(
            doc_id="doc1",
            score=0.9,
            retrieval_method=RetrievalMethod.BM25,
            content="劳动合同法规定...",
            title="劳动合同法"
        ),
        SearchResult(
            doc_id="doc2",
            score=0.8,
            retrieval_method=RetrievalMethod.BM25,
            content="试用期工资...",
            title="试用期规定"
        ),
        SearchResult(
            doc_id="doc3",
            score=0.7,
            retrieval_method=RetrievalMethod.BM25,
            content="劳动者提前...",
            title="辞职流程"
        )
    ]


# ======== BM25 Indexer 测试 ========

class TestBM25Indexer:
    """BM25 索引器测试"""

    def test_index_documents(self, sample_documents):
        """测试：构建索引"""
        bm25 = BM25Indexer()
        bm25.index_documents(sample_documents)

        assert bm25._indexed is True
        assert len(bm25.documents) == 5
        assert len(bm25.corpus) == 5
        assert len(bm25.doc_ids) == 5

    def test_search(self, indexed_bm25):
        """测试：搜索"""
        results, duration = indexed_bm25.search("劳动合同", top_k=3)

        assert len(results) > 0
        assert duration >= 0
        assert all(r.score > 0 for r in results)
        assert all(r.retrieval_method == RetrievalMethod.BM25 for r in results)

    def test_search_empty_query(self, indexed_bm25):
        """测试：空查询"""
        results, duration = indexed_bm25.search("", top_k=3)
        # 应该返回结果（即使查询为空）

    def test_get_document(self, indexed_bm25, sample_documents):
        """测试：获取文档"""
        doc = indexed_bm25.get_document("doc1")
        assert doc is not None
        assert doc.id == "doc1"
        assert doc.title == "劳动合同法"

    def test_get_nonexistent_document(self, indexed_bm25):
        """测试：获取不存在的文档"""
        doc = indexed_bm25.get_document("nonexistent")
        assert doc is None

    def test_get_index_info(self, indexed_bm25):
        """测试：获取索引信息"""
        info = indexed_bm25.get_index_info()
        assert info["indexed"] is True
        assert info["document_count"] == 5
        assert "k1" in info
        assert "b" in info

    def test_search_without_index(self):
        """测试：未构建索引时搜索"""
        bm25 = BM25Indexer()
        with pytest.raises(RuntimeError):
            bm25.search("test")


# ======== RRF Fusion 测试 ========

class TestRRFFusion:
    """RRF 融合器测试"""

    @pytest.fixture
    def rrf(self):
        return RRFFusion(k=60)

    @pytest.fixture
    def bm25_results(self):
        """BM25 搜索结果"""
        return [
            SearchResult(doc_id="doc1", score=0.9, retrieval_method=RetrievalMethod.BM25),
            SearchResult(doc_id="doc2", score=0.8, retrieval_method=RetrievalMethod.BM25),
            SearchResult(doc_id="doc3", score=0.7, retrieval_method=RetrievalMethod.BM25),
            SearchResult(doc_id="doc4", score=0.6, retrieval_method=RetrievalMethod.BM25),
            SearchResult(doc_id="doc5", score=0.5, retrieval_method=RetrievalMethod.BM25),
        ]

    @pytest.fixture
    def vector_results(self):
        """向量搜索结果（不同顺序）"""
        return [
            SearchResult(doc_id="doc3", score=0.95, retrieval_method=RetrievalMethod.VECTOR),
            SearchResult(doc_id="doc1", score=0.85, retrieval_method=RetrievalMethod.VECTOR),
            SearchResult(doc_id="doc5", score=0.75, retrieval_method=RetrievalMethod.VECTOR),
            SearchResult(doc_id="doc2", score=0.65, retrieval_method=RetrievalMethod.VECTOR),
            SearchResult(doc_id="doc4", score=0.55, retrieval_method=RetrievalMethod.VECTOR),
        ]

    def test_fuse_two(self, rrf, bm25_results, vector_results):
        """测试：融合两个排序列表"""
        fused_results, duration = rrf.fuse_two(bm25_results, vector_results, top_k=5)

        assert len(fused_results) == 5
        assert duration >= 0
        assert all(r.retrieval_method == RetrievalMethod.RRF_FUSION for r in fused_results)

    def test_fuse_overlap_detection(self, rrf, bm25_results, vector_results):
        """测试：检测重叠文档"""
        fused_results, _ = rrf.fuse_two(bm25_results, vector_results, top_k=5)
        info = rrf.get_fusion_info(bm25_results, vector_results, fused_results)

        assert info["overlap"] == 5  # 所有文档都重叠
        assert info["unique_to_a"] == 0
        assert info["unique_to_b"] == 0

    def test_fuse_empty_lists(self, rrf):
        """测试：融合空列表"""
        results, _ = rrf.fuse_two([], [], top_k=5)
        assert len(results) == 0

    def test_fuse_one_empty_list(self, rrf, bm25_results):
        """测试：一个列表为空"""
        results, _ = rrf.fuse_two(bm25_results, [], top_k=5)
        assert len(results) == 5


# ======== Reranker Client 测试 ========

class TestRerankerClient:
    """Reranker 客户端测试"""

    def test_init_cohere(self):
        """测试：初始化 Cohere 客户端"""
        # 注意：这需要有效的 API key
        # reranker = RerankerClient(provider="cohere", api_key="test")
        # assert reranker.provider == "cohere"
        pass

    def test_init_invalid_provider(self):
        """测试：无效的提供商"""
        with pytest.raises(ValueError):
            RerankerClient(provider="invalid", api_key="test")

    def test_init_missing_api_key(self):
        """测试：缺少 API key"""
        with pytest.raises(ValueError):
            RerankerClient(provider="cohere", api_key=None)


class TestRerankerFallback:
    """Reranker 降级策略测试"""

    @pytest.fixture
    def sample_results(self):
        return [
            SearchResult(doc_id="doc1", score=0.9, retrieval_method=RetrievalMethod.BM25),
            SearchResult(doc_id="doc2", score=0.8, retrieval_method=RetrievalMethod.BM25),
            SearchResult(doc_id="doc3", score=0.7, retrieval_method=RetrievalMethod.BM25),
        ]

    @pytest.mark.asyncio
    async def test_fallback(self, sample_results):
        """测试：降级策略"""
        results, duration = await RerankerFallback.fallback(sample_results, top_k=2)

        assert len(results) == 2
        assert results[0].doc_id == "doc1"  # 最高分
        assert results[0].score == 0.9
        assert results[0].metadata.get("fallback") is True


# ======== Hybrid Search Engine 测试 ========

class TestHybridSearchEngine:
    """混合检索引擎测试"""

    @pytest.fixture
    def mock_vector_search(self):
        """Mock 向量检索函数"""
        async def mock_func(query, top_k):
            return [
                SearchResult(
                    doc_id=f"vec_doc_{i}",
                    score=0.9 - i * 0.1,
                    retrieval_method=RetrievalMethod.VECTOR
                )
                for i in range(top_k)
            ], 0.1
        return mock_func

    @pytest.fixture
    def hybrid_engine(self, indexed_bm25, mock_vector_search):
        """混合检索引擎"""
        return HybridSearchEngine(
            bm25_indexer=indexed_bm25,
            vector_search_func=mock_vector_search,
            enable_cache=False
        )

    @pytest.mark.asyncio
    async def test_search(self, hybrid_engine):
        """测试：完整检索流程"""
        context = await hybrid_engine.search(
            query="劳动合同",
            retrieval_k=10,
            fusion_k=5,
            rerank_k=3
        )

        assert context.query == "劳动合同"
        assert len(context.results) > 0
        assert context.statistics.total_retrieved > 0
        assert context.statistics.duration_ms > 0

    @pytest.mark.asyncio
    async def test_search_with_bm25_failure(self, hybrid_engine):
        """测试：BM25 失败时的降级"""
        # Mock BM25 失败
        with patch.object(hybrid_engine.bm25, 'search', side_effect=Exception("BM25 failed")):
            context = await hybrid_engine.search("test")

        # 应该降级到仅向量检索
        assert context.statistics.bm25_count == 0
        assert context.statistics.vector_count > 0
        assert len(context.results) > 0

    @pytest.mark.asyncio
    async def test_search_with_vector_failure(self, hybrid_engine):
        """测试：向量检索失败时的降级"""
        # Mock 向量检索失败
        async def failing_search(query, top_k):
            raise Exception("Vector search failed")

        hybrid_engine.vector_search = failing_search

        context = await hybrid_engine.search("test")

        # 应该降级到仅 BM25
        assert context.statistics.bm25_count > 0
        assert context.statistics.vector_count == 0
        assert len(context.results) > 0

    @pytest.mark.asyncio
    async def test_cache(self, hybrid_engine):
        """测试：缓存功能"""
        # 启用缓存
        hybrid_engine.enable_cache = True

        # 第一次检索
        context1 = await hybrid_engine.search("劳动合同")
        cache_size_before = len(hybrid_engine._cache)

        # 第二次检索（应该命中缓存）
        context2 = await hybrid_engine.search("劳动合同")

        assert context1.query == context2.query
        assert len(context1.results) == len(context2.results)
        assert len(hybrid_engine._cache) == cache_size_before

    def test_clear_cache(self, hybrid_engine):
        """测试：清空缓存"""
        hybrid_engine._cache["test"] = "value"
        assert len(hybrid_engine._cache) > 0

        hybrid_engine.clear_cache()
        assert len(hybrid_engine._cache) == 0

    def test_get_engine_info(self, hybrid_engine):
        """测试：获取引擎信息"""
        info = hybrid_engine.get_engine_info()

        assert "bm25_indexed" in info
        assert "rrf_k" in info
        assert "reranker_enabled" in info
        assert "cache_enabled" in info


# ======== 集成测试 ========

class TestHybridSearchIntegration:
    """集成测试"""

    @pytest.mark.asyncio
    async def test_end_to_end_search(self, sample_documents):
        """测试：端到端检索流程"""
        # 1. 构建 BM25 索引
        bm25 = BM25Indexer()
        bm25.index_documents(sample_documents)

        # 2. Mock 向量检索
        async def mock_vector_search(query, top_k):
            return [
                SearchResult(
                    doc_id=doc.id,
                    score=0.8,
                    retrieval_method=RetrievalMethod.VECTOR,
                    content=doc.content,
                    title=doc.title
                )
                for doc in sample_documents[:top_k]
            ], 0.1

        # 3. 创建引擎
        engine = HybridSearchEngine(
            bm25_indexer=bm25,
            vector_search_func=mock_vector_search,
            enable_cache=False
        )

        # 4. 执行检索
        context = await engine.search(
            query="劳动合同 试用期",
            retrieval_k=5,
            fusion_k=3,
            rerank_k=2
        )

        # 5. 验证结果
        assert context.query == "劳动合同 试用期"
        assert len(context.results) > 0
        assert context.statistics.total_retrieved > 0
        assert context.statistics.bm25_count > 0
        assert context.statistics.vector_count > 0
        assert context.statistics.fused_count > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
