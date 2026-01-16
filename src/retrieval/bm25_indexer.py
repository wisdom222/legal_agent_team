"""
BM25 索引器
基于 rank_bm25 库实现关键词检索
"""

import jieba
import numpy as np
from typing import List, Optional, Dict, Tuple
from rank_bm25 import BM25Okapi
import time

from ..models.search_models import (
    Document,
    SearchResult,
    RetrievalMethod
)


class BM25Indexer:
    """
    BM25 关键词索引管理器

    使用 BM25 算法进行关键词检索，特别适用于精确匹配法条编号、
    专有名词等向量检索难以覆盖的场景。

    参数:
        k1: 控制词频饱和度 (默认 1.5)
             - 较高的 k1 值会让词频对分数的影响更大
             - 推荐范围: 1.2 - 2.0
        b: 控制文档长度归一化 (默认 0.75)
           - b 值越大，长文档的惩罚越严重
           - 推荐范围: 0.5 - 0.8
    """

    def __init__(
        self,
        k1: float = 1.5,
        b: float = 0.75,
        enable_jieba: bool = True
    ):
        self.k1 = k1
        self.b = b
        self.enable_jieba = enable_jieba

        # BM25 索引
        self.bm25: Optional[BM25Okapi] = None

        # 文档存储
        self.documents: Dict[str, Document] = {}
        self.corpus: List[List[str]] = []
        self.doc_ids: List[str] = []

        # 索引状态
        self._indexed: bool = False

    def _tokenize(self, text: str) -> List[str]:
        """
        中文分词

        Args:
            text: 待分词文本

        Returns:
            分词结果列表
        """
        if self.enable_jieba:
            # 使用 jieba 分词
            return list(jieba.cut(text))
        else:
            # 简单空格分词
            return text.split()

    def index_documents(self, documents: List[Document]) -> None:
        """
        构建 BM25 索引

        Args:
            documents: 文档列表
        """
        start_time = time.time()

        # 存储文档
        for doc in documents:
            self.documents[doc.id] = doc

        # 构建语料库
        self.corpus = [
            self._tokenize(doc.content)
            for doc in documents
        ]
        self.doc_ids = [doc.id for doc in documents]

        # 创建 BM25 索引
        self.bm25 = BM25Okapi(
            self.corpus,
            k1=self.k1,
            b=self.b,
            epsilon=0.25
        )

        self._indexed = True

        duration = time.time() - start_time
        print(f"✅ BM25 索引构建完成: {len(documents)} 个文档, 耗时 {duration:.2f}s")

    def search(
        self,
        query: str,
        top_k: int = 50,
        min_score: float = 0.0
    ) -> Tuple[List[SearchResult], float]:
        """
        关键词检索

        Args:
            query: 查询文本
            top_k: 返回前 K 个结果
            min_score: 最小分数阈值

        Returns:
            (搜索结果列表, 耗时秒数)
        """
        if not self._indexed:
            raise RuntimeError("BM25 索引未构建，请先调用 index_documents()")

        start_time = time.time()

        # 分词
        query_tokens = self._tokenize(query)

        # 计算分数
        scores = self.bm25.get_scores(query_tokens)

        # 获取 Top-K 结果
        top_indices = np.argsort(scores)[::-1][:top_k]

        # 构建结果
        results = []
        for idx in top_indices:
            score = float(scores[idx])

            # 过滤低分结果
            if score < min_score:
                continue

            doc_id = self.doc_ids[idx]
            document = self.documents[doc_id]

            results.append(
                SearchResult(
                    doc_id=doc_id,
                    score=score,
                    retrieval_method=RetrievalMethod.BM25,
                    content=document.content,
                    title=document.title,
                    metadata=document.metadata,
                    original_rank=len(results) + 1
                )
            )

        duration = time.time() - start_time

        return results, duration

    def get_document(self, doc_id: str) -> Optional[Document]:
        """
        获取文档

        Args:
            doc_id: 文档 ID

        Returns:
            文档对象，不存在返回 None
        """
        return self.documents.get(doc_id)

    def get_index_info(self) -> Dict[str, any]:
        """
        获取索引信息

        Returns:
            索引信息字典
        """
        return {
            "indexed": self._indexed,
            "document_count": len(self.documents),
            "k1": self.k1,
            "b": self.b,
            "enable_jieba": self.enable_jieba
        }

    def save_index(self, filepath: str) -> None:
        """
        保存索引到文件

        Args:
            filepath: 保存路径
        """
        import pickle

        index_data = {
            "bm25": self.bm25,
            "documents": self.documents,
            "corpus": self.corpus,
            "doc_ids": self.doc_ids,
            "k1": self.k1,
            "b": self.b,
            "enable_jieba": self.enable_jieba
        }

        with open(filepath, 'wb') as f:
            pickle.dump(index_data, f)

        print(f"✅ BM25 索引已保存到: {filepath}")

    def load_index(self, filepath: str) -> None:
        """
        从文件加载索引

        Args:
            filepath: 索引文件路径
        """
        import pickle

        with open(filepath, 'rb') as f:
            index_data = pickle.load(f)

        self.bm25 = index_data["bm25"]
        self.documents = index_data["documents"]
        self.corpus = index_data["corpus"]
        self.doc_ids = index_data["doc_ids"]
        self.k1 = index_data["k1"]
        self.b = index_data["b"]
        self.enable_jieba = index_data["enable_jieba"]
        self._indexed = True

        print(f"✅ BM25 索引已加载: {len(self.documents)} 个文档")


# 工厂函数
def create_bm25_indexer(
    k1: float = 1.5,
    b: float = 0.75,
    enable_jieba: bool = True
) -> BM25Indexer:
    """
    创建 BM25 索引器

    Args:
        k1: BM25 k1 参数
        b: BM25 b 参数
        enable_jieba: 是否启用 jieba 分词

    Returns:
        BM25Indexer 实例
    """
    return BM25Indexer(
        k1=k1,
        b=b,
        enable_jieba=enable_jieba
    )
