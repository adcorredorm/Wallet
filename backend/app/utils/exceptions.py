"""
Custom exceptions for the application.

These exceptions provide semantic error handling across the application layers.
"""


class WalletException(Exception):
    """Base exception for all Wallet application errors."""

    def __init__(self, message: str, status_code: int = 500):
        """
        Initialize exception.

        Args:
            message: Error message
            status_code: HTTP status code for API responses
        """
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)


class NotFoundError(WalletException):
    """Exception raised when a requested resource is not found."""

    def __init__(self, resource: str, resource_id: str):
        """
        Initialize not found exception.

        Args:
            resource: Name of the resource (e.g., "Account", "Transaction")
            resource_id: ID of the resource that was not found
        """
        message = f"{resource} con ID {resource_id} no encontrado"
        super().__init__(message, status_code=404)


class ValidationError(WalletException):
    """Exception raised when validation fails."""

    def __init__(self, message: str):
        """
        Initialize validation exception.

        Args:
            message: Validation error message
        """
        super().__init__(message, status_code=400)


class BusinessRuleError(WalletException):
    """Exception raised when a business rule is violated."""

    def __init__(self, message: str):
        """
        Initialize business rule exception.

        Args:
            message: Business rule violation message
        """
        super().__init__(message, status_code=422)
