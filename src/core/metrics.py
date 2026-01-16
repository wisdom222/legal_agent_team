"""
监控指标模块
使用 Prometheus 收集和暴露应用指标
"""

import time
from functools import wraps
from typing import Callable, Optional, Dict, Any
from datetime import datetime

try:
    from prometheus_client import Counter, Histogram, Gauge, start_http_server, CollectorRegistry, REGISTRY
    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False
    print("⚠️ prometheus_client 未安装，监控功能将不可用")


class MetricsCollector:
    """
    指标收集器

    收集以下类型的指标:
    - Counter: 计数器（只增不减）
    - Histogram: 直方图（分布统计）
    - Gauge: 仪表盘（可增可减）
    """

    def __init__(
        self,
        enabled: bool = True,
        port: Optional[int] = None
    ):
        """
        初始化指标收集器

        Args:
            enabled: 是否启用监控
            port: Prometheus 指标端口
        """
        if not PROMETHEUS_AVAILABLE:
            self.enabled = False
            return

        self.enabled = enabled
        self.port = port

        if self.enabled:
            # 创建指标
            self._init_metrics()

            # 启动 HTTP 服务器
            if port:
                try:
                    start_http_server(port)
                    print(f"✅ Prometheus 指标服务器启动在端口 {port}")
                except Exception as e:
                    print(f"⚠️ 无法启动 Prometheus 服务器: {e}")

    def _init_metrics(self):
        """初始化所有指标"""
        # 检索指标
        self.retrieval_requests = Counter(
            'retrieval_requests_total',
            'Total retrieval requests',
            ['method', 'status']
        )

        self.retrieval_duration = Histogram(
            'retrieval_duration_seconds',
            'Retrieval duration',
            ['method'],
            buckets=[0.01, 0.05, 0.1, 0.5, 1.0, 2.0, 5.0, 10.0]
        )

        # Agent 指标
        self.agent_requests = Counter(
            'agent_requests_total',
            'Total agent requests',
            ['agent_name', 'stage', 'status']
        )

        self.agent_duration = Histogram(
            'agent_execution_duration_seconds',
            'Agent execution duration',
            ['agent_name', 'stage'],
            buckets=[0.5, 1.0, 2.0, 5.0, 10.0, 20.0, 30.0, 60.0]
        )

        # 报告指标
        self.report_generation_duration = Histogram(
            'report_generation_duration_seconds',
            'Report generation duration',
            buckets=[0.5, 1.0, 2.0, 5.0, 10.0, 20.0]
        )

        self.reports_generated = Counter(
            'reports_generated_total',
            'Total reports generated',
            ['format', 'status']
        )

        # 系统指标
        self.active_analyses = Gauge(
            'active_analyses',
            'Number of active document analyses'
        )

        self.error_count = Counter(
            'errors_total',
            'Total errors',
            ['error_type', 'category']
        )

        # 缓存指标
        self.cache_hits = Counter(
            'cache_hits_total',
            'Total cache hits',
            ['cache_type']
        )

        self.cache_misses = Counter(
            'cache_misses_total',
            'Total cache misses',
            ['cache_type']
        )

    # ========== 装饰器 ==========

    def track_retrieval(
        self,
        method: str = "unknown"
    ):
        """
        检索跟踪装饰器

        Args:
            method: 检索方法名称
        """
        if not self.enabled:
            def decorator(func):
                return func
            return decorator

        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            status = "success"

            try:
                result = func(*args, **kwargs)
                return result

            except Exception as e:
                status = "error"
                self.error_count.labels(
                    error_type=type(e).__name__,
                    category="retrieval"
                ).inc()
                raise

            finally:
                duration = time.time() - start_time
                self.retrieval_requests.labels(
                    method=method,
                    status=status
                ).inc()
                self.retrieval_duration.labels(
                    method=method
                ).observe(duration)

        return wrapper

    def track_agent(
        self,
        agent_name: str,
        stage: str = "unknown"
    ):
        """
        Agent 跟踪装饰器

        Args:
            agent_name: Agent 名称
            stage: 执行阶段
        """
        if not self.enabled:
            def decorator(func):
                return func
            return decorator

        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            status = "success"

            try:
                result = func(*args, **kwargs)
                return result

            except Exception as e:
                status = "error"
                self.error_count.labels(
                    error_type=type(e).__name__,
                    category="agent"
                ).inc()
                raise

            finally:
                duration = time.time() - start_time
                self.agent_requests.labels(
                    agent_name=agent_name,
                    stage=stage,
                    status=status
                ).inc()
                self.agent_duration.labels(
                    agent_name=agent_name,
                    stage=stage
                ).observe(duration)

        return wrapper

    def track_report_generation(
        self,
        format: str = "json"
    ):
        """
        报告生成跟踪装饰器

        Args:
            format: 报告格式
        """
        if not self.enabled:
            def decorator(func):
                return func
            return decorator

        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            status = "success"

            try:
                result = func(*args, **kwargs)
                return result

            except Exception as e:
                status = "error"
                self.error_count.labels(
                    error_type=type(e).__name__,
                    category="report_generation"
                ).inc()
                raise

            finally:
                duration = time.time() - start_time
                self.reports_generated.labels(
                    format=format,
                    status=status
                ).inc()
                self.report_generation_duration.observe(duration)

        return wrapper

    # ========== 手动指标记录 ==========

    def increment_active_analyses(self, delta: int = 1):
        """增加/减少活跃分析数"""
        if self.enabled:
            current = self.active_analyses._value.get()
            self.active_analyses.set(current + delta)

    def record_cache_hit(self, cache_type: str = "default"):
        """记录缓存命中"""
        if self.enabled:
            self.cache_hits.labels(cache_type=cache_type).inc()

    def record_cache_miss(self, cache_type: str = "default"):
        """记录缓存未命中"""
        if self.enabled:
            self.cache_misses.labels(cache_type=cache_type).inc()

    def get_metrics_summary(self) -> Dict[str, Any]:
        """获取指标摘要"""
        if not self.enabled:
            return {"enabled": False}

        summary = {
            "enabled": True,
            "timestamp": datetime.now().isoformat()
        }

        # 添加计数器值
        try:
            summary["retrieval_requests"] = self.retrieval_requests._value.get()
            summary["agent_requests"] = self.agent_requests._value.get()
            summary["reports_generated"] = self.reports_generated._value.get()
            summary["error_count"] = self.error_count._value.get()
            summary["cache_hits"] = self.cache_hits._value.get()
            summary["cache_misses"] = self.cache_misses._value.get()
        except Exception as e:
            summary["error"] = str(e)

        return summary


# ========== 全局实例 ==========

_metrics_collector: Optional[MetricsCollector] = None


def get_metrics_collector(
    enabled: bool = True,
    port: Optional[int] = None
) -> MetricsCollector:
    """
    获取全局指标收集器

    Args:
        enabled: 是否启用监控
        port: Prometheus 端口

    Returns:
        MetricsCollector 实例
    """
    global _metrics_collector

    if _metrics_collector is None:
        _metrics_collector = MetricsCollector(
            enabled=enabled,
            port=port
        )

    return _metrics_collector


def init_metrics(
    enabled: bool = True,
    port: Optional[int] = 8000
):
    """
    初始化监控指标

    Args:
        enabled: 是否启用监控
        port: Prometheus 指标端口
    """
    global _metrics_collector
    _metrics_collector = MetricsCollector(
        enabled=enabled,
        port=port
    )


# ========== 便捷装饰器 ==========

def track_retrieval(method: str = "unknown"):
    """检索跟踪装饰器（便捷函数）"""
    collector = get_metrics_collector()
    return collector.track_retrieval(method)


def track_agent(agent_name: str, stage: str = "unknown"):
    """Agent 跟踪装饰器（便捷函数）"""
    collector = get_metrics_collector()
    return collector.track_agent(agent_name, stage)


def track_report_generation(format: str = "json"):
    """报告生成跟踪装饰器（便捷函数）"""
    collector = get_metrics_collector()
    return collector.track_report_generation(format)
