"""
应用配置管理
使用 Pydantic Settings 加载环境变量
"""

from pydantic_settings import BaseSettings
from typing import Optional, List
from functools import lru_cache


class HybridSearchConfig(BaseSettings):
    """混合检索配置"""

    # BM25 配置
    bm25_k1: float = 1.5
    bm25_b: float = 0.75
    bm25_enable_jieba: bool = True

    # RRF 配置
    rrf_k: int = 60

    # 检索数量配置
    retrieval_k: int = 50
    fusion_k: int = 20
    rerank_k: int = 10

    class Config:
        env_file = "config/.env"
        env_prefix = "HYBRID_"


class RerankerConfig(BaseSettings):
    """Reranker 配置"""

    # 提供商选择
    provider: str = "cohere"  # "cohere" or "jina"

    # API 配置
    api_key: Optional[str] = None
    model: Optional[str] = None

    # 性能配置
    timeout: float = 30.0
    enable: bool = True

    class Config:
        env_file = "config/.env"
        env_prefix = "RERANKER_"


class OpenAIConfig(BaseSettings):
    """OpenAI 配置"""

    api_key: str
    embedding_model: str = "text-embedding-3-small"
    chat_model: str = "gpt-4o"

    class Config:
        env_file = "config/.env"
        env_prefix = "OPENAI_"


class QdrantConfig(BaseSettings):
    """Qdrant 向量数据库配置"""

    url: str = "http://localhost:6333"
    api_key: Optional[str] = None
    collection_name: str = "legal_docs"

    # 向量配置
    vector_size: int = 1536
    distance: str = "Cosine"

    class Config:
        env_file = "config/.env"
        env_prefix = "QDRANT_"


class RedisConfig(BaseSettings):
    """Redis 缓存配置"""

    url: str = "redis://localhost:6379"
    password: Optional[str] = None
    db: int = 0

    # 缓存配置
    ttl: int = 3600  # 1 hour
    enabled: bool = True

    class Config:
        env_file = "config/.env"
        env_prefix = "REDIS_"


class AgentConfig(BaseSettings):
    """Agent 配置"""

    # 并行审查配置
    enable_parallel_review: bool = True
    max_review_rounds: int = 2

    # Reviewer 配置
    enabled_reviewers: List[str] = [
        "legal_reviewer",
        "risk_reviewer",
        "format_reviewer",
        "business_reviewer"
    ]

    # 仲裁配置
    enable_arbitrator: bool = True
    auto_resolve_conflicts: bool = True

    class Config:
        env_file = "config/.env"
        env_prefix = "AGENT_"


class AppConfig(BaseSettings):
    """应用配置"""

    # 服务器配置
    host: str = "localhost"
    port: int = 8501

    # 日志配置
    log_level: str = "INFO"

    # 监控配置
    enable_metrics: bool = True

    class Config:
        env_file = "config/.env"
        env_prefix = "APP_"


class Settings:
    """全局配置单例"""

    def __init__(self):
        self.hybrid_search = HybridSearchConfig()
        self.reranker = RerankerConfig()
        self.openai = OpenAIConfig()
        self.qdrant = QdrantConfig()
        self.redis = RedisConfig()
        self.agent = AgentConfig()
        self.app = AppConfig()

    def validate(self) -> bool:
        """验证配置"""
        errors = []

        # 验证必需的 API Keys
        if not self.openai.api_key:
            errors.append("OPENAI_API_KEY is required")

        if self.reranker.enable and not self.reranker.api_key:
            errors.append("RERANKER_API_KEY is required when reranker is enabled")

        if errors:
            print("❌ 配置验证失败:")
            for error in errors:
                print(f"   - {error}")
            return False

        return True

    def print_config(self):
        """打印配置信息"""
        print("=" * 50)
        print("📋 应用配置")
        print("=" * 50)
        print(f"Hybrid Search:")
        print(f"  - BM25 k1: {self.hybrid_search.bm25_k1}")
        print(f"  - RRF k: {self.hybrid_search.rrf_k}")
        print(f"  - Retrieval K: {self.hybrid_search.retrieval_k}")
        print(f"  - Fusion K: {self.hybrid_search.fusion_k}")
        print(f"  - Rerank K: {self.hybrid_search.rerank_k}")
        print(f"\nReranker:")
        print(f"  - Provider: {self.reranker.provider}")
        print(f"  - Enabled: {self.reranker.enable}")
        print(f"\nOpenAI:")
        print(f"  - Embedding Model: {self.openai.embedding_model}")
        print(f"  - Chat Model: {self.openai.chat_model}")
        print(f"\nQdrant:")
        print(f"  - URL: {self.qdrant.url}")
        print(f"  - Collection: {self.qdrant.collection_name}")
        print(f"\nAgent:")
        print(f"  - Parallel Review: {self.agent.enable_parallel_review}")
        print(f"  - Max Rounds: {self.agent.max_review_rounds}")
        print("=" * 50)


@lru_cache()
def get_settings() -> Settings:
    """
    获取全局配置单例

    Returns:
        Settings 实例
    """
    return Settings()
