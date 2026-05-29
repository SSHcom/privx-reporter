import logging

logger = logging.getLogger(__name__)


class ReportError(Exception):
    """Base exception for report-related errors."""

    def __init__(self, message: str, usage: str | None = None, prefix_usage: bool = True) -> None:
        self.message = message
        self.usage = usage
        self.prefix_usage = prefix_usage
        super().__init__(self.message)


class ConfigError(ReportError):
    """Exception for configuration-related errors."""

    pass


class ValidationError(ReportError):
    """Exception for validation-related errors."""

    pass


def handle_error(user_message: str, log_message: str | None = None) -> str:
    logger.error(user_message)
    if log_message:
        logger.error(log_message)

    return user_message
