class AuthError(Exception):
    """Base class for authentication errors."""
    pass

class InvalidCredentialsError(AuthError):
    """Raised when authentication fails due to incorrect credentials."""
    pass

class UserNotFoundError(AuthError):
    """Raised when a user is not found."""
    pass

class UserInactiveError(AuthError):
    """Raised when an operation is attempted on an inactive user."""
    pass

class EmailAlreadyExistsError(AuthError):
    """Raised when trying to register with an existing email."""
    pass

class InvalidTokenError(AuthError):
    """Raised when a token is invalid (format, signature, claims)."""
    pass

class TokenExpiredError(AuthError):
    """Raised when a token has expired."""
    pass
