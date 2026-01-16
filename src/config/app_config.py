"""
应用配置管理
整合所有配置模块并提供统一接口
"""

from .settings import Settings, get_settings


class AppConfig:
    """
    应用配置

    提供统一的配置访问接口
    """

    def __init__(self):
        """初始化配置"""
        self.settings = get_settings()

    def validate_all(self) -> bool:
        """验证所有配置"""
        return self.settings.validate()

    def print_config(self):
        """打印配置信息"""
        self.settings.print_config()

    # 检索配置
    @property
    def hybrid_search(self):
        return self.settings.hybrid_search

    @property
    def reranker(self):
        return self.settings.reranker

    @property
    def qdrant(self):
        return self.settings.qdrant

    @property
    def redis(self):
        return self.settings.redis

    # Agent 配置
    @property
    def agent(self):
        return self.settings.agent

    # 应用配置
    @property
    def app(self):
        return self.settings.app

    # OpenAI 配置
    @property
    def openai(self):
        return self.settings.openai


# 全局实例
_app_config: AppConfig = None


def get_app_config() -> AppConfig:
    """
    获取全局应用配置

    Returns:
        AppConfig 实例
    """
    global _app_config

    if _app_config is None:
        _app_config = AppConfig()

    return _app_config
