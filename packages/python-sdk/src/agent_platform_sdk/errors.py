class AgentPlatformError(RuntimeError):
    """Structured error returned by the Agent Tool Platform."""

    def __init__(self, message: str, *, code: str, status_code: int) -> None:
        super().__init__(message)
        self.code = code
        self.status_code = status_code
