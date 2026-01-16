"""
RRF (Reciprocal Rank Fusion) 融合器
使用 RRF 算法合并多个排序列表
"""

from typing import List, Dict, Tuple
import time

from ..models.search_models import SearchResult, RetrievalMethod


class RRFFusion:
    """
    Reciprocal Rank Fusion 融合器

    RRF 是一种简单但强大的多路检索结果融合算法，
    无需调参，鲁棒性强，广泛应用于工业界。

    RRF 公式:
        score(d) = Σ 1 / (k + rank(d))

    其中:
        - k 是平滑参数 (默认 60)
        - rank(d) 是文档 d 在某个排序列表中的排名

    参数:
        k: 平滑参数 (默认 60)
           - 控制低排名文档的贡献度
           - 工业界标准值: 60
           - 较小的 k 会更重视低排名结果

    参考:
        Cormack, G. V., Clarke, C. L., & Buettcher, S. (2009).
        Reciprocal rank fusion outperforms condorcet and individual
        rank learning methods. SIGIR'09.
    """

    def __init__(self, k: int = 60):
        """
        初始化 RRF 融合器

        Args:
            k: 平滑参数
        """
        self.k = k

    def fuse(
        self,
        results_list: List[List[SearchResult]],
        top_k: int = 20
    ) -> Tuple[List[SearchResult], float]:
        """
        融合多个排序列表

        Args:
            results_list: 多个排序列表
                         例如: [bm25_results, vector_results]
            top_k: 返回前 K 个结果

        Returns:
            (融合后的结果列表, 耗时秒数)
        """
        start_time = time.time()

        # 构建排名映射
        rank_maps: List[Dict[str, int]] = []

        for results in results_list:
            rank_map = {}
            for rank, result in enumerate(results, start=1):
                rank_map[result.doc_id] = rank
            rank_maps.append(rank_map)

        # 收集所有文档 ID
        all_doc_ids = set()
        for rank_map in rank_maps:
            all_doc_ids.update(rank_map.keys())

        # 计算融合分数
        fusion_scores: Dict[str, float] = {}

        for doc_id in all_doc_ids:
            score = 0.0
            contribution_count = 0

            # 累加所有排序列表的贡献
            for rank_map in rank_maps:
                if doc_id in rank_map:
                    rank = rank_map[doc_id]
                    score += 1 / (self.k + rank)
                    contribution_count += 1

            # 只保留至少出现在一个列表中的文档
            if contribution_count > 0:
                fusion_scores[doc_id] = score

        # 按分数排序
        sorted_docs = sorted(
            fusion_scores.items(),
            key=lambda x: x[1],
            reverse=True
        )[:top_k]

        # 构建结果
        fused_results = []
        for rank, (doc_id, score) in enumerate(sorted_docs, start=1):
            # 从第一个可用列表中获取文档信息
            doc_info = None
            for results in results_list:
                for result in results:
                    if result.doc_id == doc_id:
                        doc_info = result
                        break
                if doc_info:
                    break

            if doc_info:
                fused_results.append(
                    SearchResult(
                        doc_id=doc_id,
                        score=score,
                        retrieval_method=RetrievalMethod.RRF_FUSION,
                        content=doc_info.content,
                        title=doc_info.title,
                        metadata=doc_info.metadata,
                        original_rank=rank
                    )
                )

        duration = time.time() - start_time

        return fused_results, duration

    def fuse_two(
        self,
        results_a: List[SearchResult],
        results_b: List[SearchResult],
        top_k: int = 20
    ) -> Tuple[List[SearchResult], float]:
        """
        融合两个排序列表（便捷方法）

        Args:
            results_a: 第一个排序列表 (如 BM25 结果)
            results_b: 第二个排序列表 (如向量检索结果)
            top_k: 返回前 K 个结果

        Returns:
            (融合后的结果列表, 耗时秒数)
        """
        return self.fuse([results_a, results_b], top_k)

    def get_fusion_info(
        self,
        results_a: List[SearchResult],
        results_b: List[SearchResult],
        fused_results: List[SearchResult]
    ) -> Dict[str, any]:
        """
        获取融合统计信息

        Args:
            results_a: 第一个排序列表
            results_b: 第二个排序列表
            fused_results: 融合后的结果

        Returns:
            统计信息字典
        """
        a_ids = {r.doc_id for r in results_a}
        b_ids = {r.doc_id for r in results_b}
        fused_ids = {r.doc_id for r in fused_results}

        return {
            "rrf_k": self.k,
            "results_a_count": len(results_a),
            "results_b_count": len(results_b),
            "fused_count": len(fused_results),
            "overlap": len(a_ids & b_ids),  # 交集数量
            "unique_to_a": len(a_ids - b_ids),  # 仅在 A 中
            "unique_to_b": len(b_ids - a_ids),  # 仅在 B 中
            "fusion_coverage": len(fused_ids) / max(len(a_ids | b_ids), 1)
        }


# 工厂函数
def create_rrf_fusion(k: int = 60) -> RRFFusion:
    """
    创建 RRF 融合器

    Args:
        k: 平滑参数

    Returns:
        RRFFusion 实例
    """
    return RRFFusion(k=k)
