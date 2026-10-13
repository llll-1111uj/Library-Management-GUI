"""Domain and application errors with GUI-stable messages."""


class AuthError(Exception):
    """Raised when registration or login validation fails."""

    def __init__(self, message: str):
        super().__init__(message)
        self.message = message
