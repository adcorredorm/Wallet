"""
Account service containing business logic for account operations.
"""

from uuid import UUID
from decimal import Decimal

from app.models import Account
from app.repositories import AccountRepository
from app.utils.exceptions import NotFoundError, BusinessRuleError


class AccountService:
    """Service for account business logic."""

    def __init__(self):
        """Initialize account service with repository."""
        self.repository = AccountRepository()

    def get_all(self, include_archived: bool = False) -> list[Account]:
        """
        Get all accounts, optionally including archived ones.

        Args:
            include_archived: Whether to include inactive accounts

        Returns:
            List of accounts
        """
        if include_archived:
            return self.repository.get_all()
        return self.repository.get_all_active()

    def get_by_id(self, account_id: UUID) -> Account:
        """
        Get an account by ID.

        Args:
            account_id: Account UUID

        Returns:
            Account instance

        Raises:
            NotFoundError: If account not found
        """
        return self.repository.get_by_id_or_fail(account_id)

    def get_with_balance(self, account_id: UUID) -> tuple[Account, Decimal]:
        """
        Get an account with its calculated balance.

        Args:
            account_id: Account UUID

        Returns:
            Tuple of (account instance, balance)

        Raises:
            NotFoundError: If account not found
        """
        account = self.repository.get_by_id_or_fail(account_id)
        balance = self.repository.calculate_balance(account_id)
        return account, balance

    def get_all_with_balances(
        self, include_archived: bool = False
    ) -> list[tuple[Account, Decimal]]:
        """
        Get all accounts with their calculated balances.

        Args:
            include_archived: Whether to include inactive accounts

        Returns:
            List of tuples (account, balance)
        """
        accounts = self.get_all(include_archived=include_archived)
        return [
            (account, self.repository.calculate_balance(account.id))
            for account in accounts
        ]

    def create(
        self,
        nombre: str,
        tipo: str,
        divisa: str,
        descripcion: str | None = None,
        tags: list[str] | None = None,
        client_id: str | None = None,
    ) -> Account:
        """
        Create a new account.

        If client_id is provided and a record with that key already exists in
        the database the existing account is returned immediately without
        inserting a duplicate row (offline-first idempotency).

        Args:
            nombre: Account name
            tipo: Account type
            divisa: Currency code (ISO 4217)
            descripcion: Optional description
            tags: Optional list of tags
            client_id: Optional client-generated idempotency key

        Returns:
            Created or pre-existing account instance
        """
        from app.models.account import AccountType

        if client_id:
            existing = self.repository.get_by_client_id(client_id)
            if existing:
                return existing

        return self.repository.create(
            nombre=nombre,
            tipo=AccountType(tipo),
            divisa=divisa.upper(),
            descripcion=descripcion,
            tags=tags or [],
            client_id=client_id,
        )

    def update(
        self,
        account_id: UUID,
        nombre: str | None = None,
        tipo: str | None = None,
        divisa: str | None = None,
        descripcion: str | None = None,
        tags: list[str] | None = None,
        activa: bool | None = None,
    ) -> Account:
        """
        Update an existing account.

        Args:
            account_id: Account UUID
            nombre: New account name
            tipo: New account type
            divisa: New currency code
            descripcion: New description
            tags: New tags list
            activa: New active status

        Returns:
            Updated account instance

        Raises:
            NotFoundError: If account not found
        """
        from app.models.account import AccountType

        account = self.repository.get_by_id_or_fail(account_id)

        update_data = {}
        if nombre is not None:
            update_data["nombre"] = nombre
        if tipo is not None:
            update_data["tipo"] = AccountType(tipo)
        if divisa is not None:
            update_data["divisa"] = divisa.upper()
        if descripcion is not None:
            update_data["descripcion"] = descripcion
        if tags is not None:
            update_data["tags"] = tags
        if activa is not None:
            update_data["activa"] = activa

        return self.repository.update(account, **update_data)

    def archive(self, account_id: UUID) -> Account:
        """
        Archive an account (soft delete).

        Args:
            account_id: Account UUID

        Returns:
            Archived account instance

        Raises:
            NotFoundError: If account not found
        """
        return self.repository.soft_delete(account_id)

    def delete(self, account_id: UUID) -> None:
        """
        Permanently delete an account.

        Args:
            account_id: Account UUID

        Raises:
            NotFoundError: If account not found
            BusinessRuleError: If account has transactions or transfers
        """
        account = self.repository.get_by_id_or_fail(account_id)

        # Check if account has transactions
        if account.transacciones.count() > 0:
            raise BusinessRuleError(
                "No se puede eliminar una cuenta con transacciones. "
                "Use archivar en su lugar."
            )

        # Check if account has transfers
        if (
            account.transferencias_origen.count() > 0
            or account.transferencias_destino.count() > 0
        ):
            raise BusinessRuleError(
                "No se puede eliminar una cuenta con transferencias. "
                "Use archivar en su lugar."
            )

        self.repository.delete(account)

    def get_balance(self, account_id: UUID) -> Decimal:
        """
        Get calculated balance for an account.

        Args:
            account_id: Account UUID

        Returns:
            Account balance

        Raises:
            NotFoundError: If account not found
        """
        # Verify account exists
        self.repository.get_by_id_or_fail(account_id)
        return self.repository.calculate_balance(account_id)
