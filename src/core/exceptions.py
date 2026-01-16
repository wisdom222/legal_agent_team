"""
核心异常类
定义应用中所有异常类型和错误处理工具
"""

from typing import Optional, Dict, Any, List
from enum import Enum
from datetime import datetime


class ErrorCategory(str, Enum):
    """错误类别"""
    # 可重试错误
    RETRYABLE = "retryable"
    RATE_LIMIT = "rate_limit"
    TIMEOUT = "timeout"

    # 不可重试错误
    NON_RETRYABLE = "non_retryable"
    VALIDATION = "validation"

    # 降级错误
    DEGRADED = "degraded"

    # 系统错误
    SYSTEM = "system"


class ApplicationException(Exception):
    """
    应用异常基类

    所有自定义异常都应继承此类
    """

    def __init__(
        self,
        message: str,
        category: ErrorCategory,
        details: Optional[Dict[str, Any]] = None,
        original_error: Optional[Exception] = None,
        user_message: Optional[str] = None
    ):
        self.message = message
        self.category = category
        self.details = details or {}
        self.original_error = original_error
        self.user_message = user_message or self._generate_user_message()

        super().__init__(self.message)

    def _generate_user_message(self) -> str:
        """生成用户友好的错误消息"""
        messages = {
            ErrorCategory.RETRYABLE: "服务暂时不可用，请稍后重试",
            ErrorCategory.RATE_LIMIT: "请求过于频繁，请稍后重试",
            ErrorCategory.TIMEOUT: "处理超时，请重试或减少文档大小",
            ErrorCategory.NON_RETRYABLE: "处理失败，请检查输入",
            ErrorCategory.VALIDATION: "输入验证失败，请检查文件格式",
            ErrorCategory.DEGRADED: "使用简化模式完成处理",
            ErrorCategory.SYSTEM: "系统错误，请联系管理员"
        }
        return messages.get(self.category, "处理过程中发生错误")

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典（用于 API 响应）"""
        return {
            "error_type": self.__class__.__name__,
            "category": self.category.value,
            "message": self.message,
            "user_message": self.user_message,
            "details": self.details,
            "timestamp": datetime.now().isoformat()
        }

    def __str__(self) -> str:
        return f"[{self.category.value.upper()}] {self.message}"


# ========== 检索层异常 ==========

class RetrievalError(ApplicationException):
    """检索错误"""
    pass


class BM25IndexError(RetrievalError):
    """BM25 索引错误"""
    pass


class VectorSearchError(RetrievalError):
    """向量检索错误"""
    pass


class RerankerError(RetrievalError):
    """Reranker 错误"""
    pass


# ========== Agent 层异常 ==========

class AgentError(ApplicationException):
    """Agent 错误"""
    pass


class WriterAgentError(AgentError):
    """Writer Agent 错误"""
    pass


class ReviewerAgentError(AgentError):
    """Reviewer Agent 错误"""
    pass


class ArbitratorAgentError(AgentError):
    """Arbitrator Agent 错误"""
    pass


# ========== 文档处理异常 ==========

class DocumentProcessingError(ApplicationException):
    """文档处理错误"""
    pass


class DocumentParsingError(DocumentProcessingError):
    """文档解析错误"""
    pass


class DocumentValidationError(DocumentProcessingError):
    """文档验证错误"""
    pass


# ========== 报告生成异常 ==========

class ReportGenerationError(ApplicationException):
    """报告生成错误"""
    pass


class ReportExportError(ReportGenerationError):
    """报告导出错误"""
    pass


class ValidationError(ReportGenerationError):
    """数据验证错误"""
    pass


# ========== 错误处理器 ==========

class ErrorHandler:
    """
    错误处理器

    提供统一的错误处理逻辑：
    - 日志记录
    - 错误分类
    - 用户消息生成
    - 降级策略
    """

    def __init__(self, logger=None, enable_metrics: bool = False):
        """
        初始化错误处理器

        Args:
            logger: 日志记录器
            enable_metrics: 是否启用指标收集
        """
        self.logger = logger
        self.enable_metrics = enable_metrics

        # 错误统计
        self.error_counts: Dict[str, int] = {}
        self.last_errors: Dict[str, datetime] = {}

    def handle_error(
        self,
        error: Exception,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        处理错误并返回用户友好的响应

        Args:
            error: 异常对象
            context: 错误上下文

        Returns:
            用户响应字典
        """
        # 记录错误
        self._log_error(error, context)

        # 更新统计
        self._update_statistics(error)

        # 处理 ApplicationException
        if isinstance(error, ApplicationException):
            return self._handle_application_error(error, context)

        # 处理未知异常
        return self._handle_unknown_error(error, context)

    def _log_error(self, error: Exception, context: Dict[str, Any]):
        """记录错误日志"""
        if self.logger:
            operation = context.get("operation", "unknown")
            self.logger.error(
                f"Error in {operation}: {str(error)}",
                extra={
                    "error_type": type(error).__name__,
                    "context": context
                },
                exc_info=True
            )

    def _update_statistics(self, error: Exception):
        """更新错误统计"""
        error_type = type(error).__name__
        self.error_counts[error_type] = self.error_counts.get(error_type, 0) + 1
        self.last_errors[error_type] = datetime.now()

    def _handle_application_error(
        self,
        error: ApplicationException,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """处理应用异常"""
        response = error.to_dict()
        response["context"] = context

        # 根据错误类别返回不同响应
        if error.category == ErrorCategory.RETRYABLE:
            response["retry_after"] = self._calculate_retry_after(error)
        elif error.category == ErrorCategory.DEGRADED:
            response["fallback_used"] = True
            response["original_error"] = error.message

        return response

    def _handle_unknown_error(
        self,
        error: Exception,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """处理未知异常"""
        return {
            "error_type": "UnknownError",
            "category": "system",
            "message": "系统发生未知错误",
            "user_message": "处理失败，请联系管理员",
            "details": {
                "original_error": str(error),
                "error_type": type(error).__name__
            },
            "context": context,
            "timestamp": datetime.now().isoformat()
        }

    def _calculate_retry_after(self, error: ApplicationException) -> int:
        """计算重试延迟时间（秒）"""
        # 基于错误类别和最近错误次数计算
        error_type = type(error).__name__
        error_count = self.error_counts.get(error_type, 0)

        # 指数退避
        base_delay = 1  # 秒
        max_delay = 60   # 秒

        delay = min(base_delay * (2 ** min(error_count, 5)), max_delay)

        return int(delay)

    def get_statistics(self) -> Dict[str, Any]:
        """获取错误统计"""
        return {
            "error_counts": self.error_counts.copy(),
            "last_errors": {
                k: v.isoformat()
                for k, v in self.last_errors.items()
            },
            "total_errors": sum(self.error_counts.values())
        }


# ========== 装饰器 ==========

def handle_errors(
    error_handler: ErrorHandler,
    reraise: bool = False,
    user_message: Optional[str] = None
):
    """
    错误处理装饰器

    Args:
        error_handler: 错误处理器实例
        reraise: 是否重新抛出异常
        user_message: 自定义用户消息
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                # 构建上下文
                context = {
                    "function": func.__name__,
                    "args": str(args)[:100],
                    "kwargs": str(kwargs)[:100]
                }

                # 处理错误
                result = error_handler.handle_error(e, context)

                # 是否重新抛出
                if reraise:
                    raise

                # 返回用户友好的响应
                return result

        return wrapper
    return decorator


def safe_run(
    fallback_value: Any = None,
    log_exception: bool = True
):
    """
    安全运行装饰器

    Args:
        fallback_value: 异常时的返回值
        log_exception: 是否记录异常
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                if log_exception:
                    import logging
                    logging.error(
                        f"Error in {func.__name__}: {str(e)}",
                        exc_info=True
                    )

                return fallback_value

        return wrapper
    return decorator


# ========== 工具函数 ==========

def create_error_response(
    message: str,
    category: ErrorCategory = ErrorCategory.SYSTEM,
    details: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    创建错误响应

    Args:
        message: 错误消息
        category: 错误类别
        details: 错误详情

    Returns:
        错误响应字典
    """
    error = ApplicationException(
        message=message,
        category=category,
        details=details
    )

    return error.to_dict()


def is_retryable_error(error: Exception) -> bool:
    """
    判断是否为可重试错误

    Args:
        error: 异常对象

    Returns:
        是否可重试
    """
    if isinstance(error, ApplicationException):
        return error.category in [
            ErrorCategory.RETRYABLE,
            ErrorCategory.RATE_LIMIT,
            ErrorCategory.TIMEOUT
        ]

    return False
