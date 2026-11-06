"""Application error type, turned into JSON by the app's error handlers."""


class RotatorError(Exception):
    """Domain error with an HTTP status code (default 400)."""

    def __init__(self, message: str, status: int = 400):
        super().__init__(message)
        self.message = message
        self.status = status
