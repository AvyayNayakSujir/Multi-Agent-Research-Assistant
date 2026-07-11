class AppBaseException(Exception):
    """Base exception class for all application errors.

    Carries a human-readable message and an associated HTTP status code.
    """

    def __init__(self, message: str, status_code: int = 500):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


class AgentTimeoutError(AppBaseException):
    """Raised when the execution of an agent workflow exceeds the maximum allowed time limit."""

    def __init__(
        self,
        message: str = "Agent workflow execution timed out",
        status_code: int = 504,
    ):
        super().__init__(message, status_code)


class ToolExecutionError(AppBaseException):
    """Raised when an external tool (e.g., Tavily search, scraper services) fails to execute."""

    def __init__(self, message: str = "Tool execution failed", status_code: int = 502):
        super().__init__(message, status_code)


class MaxIterationsExceededError(AppBaseException):
    """Raised when critique-to-writer feedback loops exceed maximum allowed iterations.

    Note: The application workflow might later return a best-effort draft instead of raising,
    but this exception class is defined here for completeness.
    """

    def __init__(
        self,
        message: str = "Maximum critique iterations exceeded",
        status_code: int = 422,
    ):
        super().__init__(message, status_code)


class UnauthorizedError(AppBaseException):
    """Raised when API key verification fails."""

    def __init__(
        self, message: str = "Invalid or missing API key", status_code: int = 401
    ):
        super().__init__(message, status_code)
