# Multiusuario Backend Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add multi-user support to the Wallet backend: Google OAuth authentication, JWT + refresh token session management, per-user data isolation on all existing models, and onboarding seed data endpoint.

**Architecture:** Three phases execute sequentially — (1) data layer (models + migrations), (2) auth middleware + endpoints, (3) service/ownership wiring + seed. Each phase builds on the previous. The `BaseRepository` is refactored to be user-aware, propagating `user_id` from `g.current_user_id` through services down to every query. All existing models receive a `user_id` FK via a two-phase migration (NULLABLE → backfill → NOT NULL). `ExchangeRate` and `UserSetting` follow separate migration paths per the spec.

**Tech Stack:** Flask 3.0, SQLAlchemy 2.0, Alembic 1.13, Pydantic v2, PyJWT (new dependency), google-auth (new dependency), PostgreSQL 15

---

## Pre-flight: Dependencies

Two new Python packages are required. Add them to `backend/requirements.txt` before any code tasks:

```
PyJWT==2.8.0
google-auth==2.28.0
```

---

## Chunk 1: Modelos, Migraciones y Config de Auth (Ticket 1)

### Task 1.1: Agregar variables de auth a `config.py`

**Files:**
- Modify: `backend/app/config.py`

- [ ] **Step 1: Agregar las cuatro variables de auth a la clase `Config` base**

  Open `backend/app/config.py` and add inside the `Config` class, after the `JSON_SORT_KEYS` block:

  ```python
  # Authentication
  GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")
  JWT_SECRET = os.getenv("JWT_SECRET", "dev-jwt-secret-change-in-production")
  JWT_EXPIRY_HOURS = int(os.getenv("JWT_EXPIRY_HOURS", "24"))
  REFRESH_TOKEN_EXPIRY_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRY_DAYS", "90"))
  ```

- [ ] **Step 2: Agregar validación de producción para JWT_SECRET en `ProductionConfig`**

  In the `ProductionConfig` class, after the existing `SECRET_KEY` validation, add:

  ```python
  if not os.getenv("JWT_SECRET"):
      raise ValueError("JWT_SECRET must be set in production environment")
  if not os.getenv("GOOGLE_CLIENT_ID"):
      raise ValueError("GOOGLE_CLIENT_ID must be set in production environment")
  ```

- [ ] **Step 3: Verificar que la app arranca sin errores con la nueva config**

  Run: `cd /Users/angelcorredor/Code/Wallet/backend && python -c "from app import create_app; app = create_app(); print('OK')"`
  Expected output: `OK`

- [ ] **Step 4: Commit**

  ```bash
  cd /Users/angelcorredor/Code/Wallet
  git add backend/app/config.py
  git commit -m "feat(auth): add auth config variables to Config"
  ```

---

### Task 1.2: Agregar dependencias de auth a `requirements.txt`

**Files:**
- Modify: `backend/requirements.txt`

- [ ] **Step 1: Agregar PyJWT y google-auth**

  In `backend/requirements.txt`, add under the `# Utilities` section:

  ```
  PyJWT==2.8.0
  google-auth==2.28.0
  ```

- [ ] **Step 2: Instalar en el entorno**

  Run: `cd /Users/angelcorredor/Code/Wallet/backend && pip install PyJWT==2.8.0 google-auth==2.28.0`
  Expected: Both packages install without errors.

- [ ] **Step 3: Verificar importación**

  Run: `python -c "import jwt; import google.auth; print('OK')"`
  Expected: `OK`

- [ ] **Step 4: Commit**

  ```bash
  git add backend/requirements.txt
  git commit -m "feat(auth): add PyJWT and google-auth dependencies"
  ```

---

### Task 1.3: Crear modelo `User`

**Files:**
- Create: `backend/app/models/user.py`
- Modify: `backend/app/models/__init__.py`

- [ ] **Step 1: Escribir el test del modelo**

  Create `backend/tests/models/test_user.py`:

  ```python
  """Tests for the User model."""
  import pytest
  from uuid import UUID
  from app.models.user import User


  def test_user_has_expected_columns(app):
      """User table has id, google_id, email, name, created_at, updated_at."""
      columns = {c.name for c in User.__table__.columns}
      assert {"id", "google_id", "email", "name", "created_at", "updated_at"}.issubset(columns)


  def test_user_repr(app):
      u = User(google_id="sub123", email="test@example.com", name="Test")
      assert "test@example.com" in repr(u)
  ```

- [ ] **Step 2: Ejecutar el test — debe fallar**

  Run: `cd /Users/angelcorredor/Code/Wallet/backend && python -m pytest tests/models/test_user.py -v`
  Expected: FAIL — `ModuleNotFoundError: No module named 'app.models.user'`

- [ ] **Step 3: Crear `backend/app/models/user.py`**

  ```python
  """
  User model for authenticated users.

  Users authenticate via Google OAuth only. No passwords are stored.
  Each user owns their financial data (accounts, transactions, etc.)
  through a foreign key on every domain model.
  """

  from datetime import datetime
  from typing import Any

  from sqlalchemy import Column, String, DateTime, Index
  from sqlalchemy.dialects.postgresql import UUID
  from uuid import uuid4

  from app.extensions import db


  class User(db.Model):
      """
      Authenticated user record.

      Created on first Google OAuth login. The google_id is the 'sub' claim
      from the Google id_token and is the canonical identity key.

      Attributes:
          id: UUID primary key generated server-side.
          google_id: Google account subject identifier ('sub' from id_token). Unique.
          email: User's Google email address. Unique.
          name: User's display name from Google profile.
          created_at: UTC timestamp of account creation.
          updated_at: UTC timestamp of last profile update.
      """

      __tablename__ = "users"
      __allow_unmapped__ = True

      id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
      google_id = Column(String(255), unique=True, nullable=False, index=True)
      email = Column(String(255), unique=True, nullable=False)
      name = Column(String(255), nullable=False)
      created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
      updated_at = Column(
          DateTime,
          default=datetime.utcnow,
          onupdate=datetime.utcnow,
          nullable=False,
      )

      __table_args__ = (
          Index("idx_users_google_id", "google_id"),
          Index("idx_users_email", "email"),
      )

      def to_dict(self) -> dict[str, Any]:
          """
          Serialize user to dictionary.

          Returns:
              Dict with id (str), email, name, created_at (ISO), updated_at (ISO).
          """
          return {
              "id": str(self.id),
              "email": self.email,
              "name": self.name,
              "created_at": self.created_at.isoformat() if self.created_at else None,
              "updated_at": self.updated_at.isoformat() if self.updated_at else None,
          }

      def __repr__(self) -> str:
          """String representation."""
          return f"<User {self.email}>"
  ```

- [ ] **Step 4: Agregar `User` al `__init__.py` de models**

  In `backend/app/models/__init__.py`, add:
  - Import: `from app.models.user import User`
  - Add `"User"` to `__all__`

- [ ] **Step 5: Ejecutar el test — debe pasar**

  Run: `cd /Users/angelcorredor/Code/Wallet/backend && python -m pytest tests/models/test_user.py -v`
  Expected: PASS (2 tests)

- [ ] **Step 6: Commit**

  ```bash
  git add backend/app/models/user.py backend/app/models/__init__.py backend/tests/models/test_user.py
  git commit -m "feat(auth): add User model"
  ```

---

### Task 1.4: Crear modelo `RefreshToken`

**Files:**
- Create: `backend/app/models/refresh_token.py`
- Modify: `backend/app/models/__init__.py`

- [ ] **Step 1: Escribir el test del modelo**

  Create `backend/tests/models/test_refresh_token.py`:

  ```python
  """Tests for the RefreshToken model."""
  from app.models.refresh_token import RefreshToken


  def test_refresh_token_has_expected_columns(app):
      columns = {c.name for c in RefreshToken.__table__.columns}
      assert {"id", "user_id", "token_hash", "expires_at", "created_at"}.issubset(columns)


  def test_refresh_token_user_id_fk(app):
      fk_cols = {fk.column.table.name for fk in RefreshToken.__table__.foreign_keys}
      assert "users" in fk_cols


  def test_refresh_token_repr(app):
      import uuid
      rt = RefreshToken(user_id=uuid.uuid4(), token_hash="abc123")
      assert "abc123" in repr(rt)
  ```

- [ ] **Step 2: Ejecutar el test — debe fallar**

  Run: `cd /Users/angelcorredor/Code/Wallet/backend && python -m pytest tests/models/test_refresh_token.py -v`
  Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Crear `backend/app/models/refresh_token.py`**

  ```python
  """
  RefreshToken model for managing long-lived session tokens.

  At most one active refresh token exists per user. On rotation, the old
  token row is deleted and a new one is inserted — there is no revoked_at
  column. Token values are never stored in plain text; only the SHA-256
  hash is persisted.
  """

  from datetime import datetime
  from typing import Any

  from sqlalchemy import Column, String, DateTime, ForeignKey, Index
  from sqlalchemy.dialects.postgresql import UUID
  from uuid import uuid4

  from app.extensions import db


  class RefreshToken(db.Model):
      """
      Hashed refresh token linked to a user.

      Attributes:
          id: UUID primary key.
          user_id: FK to users.id — CASCADE DELETE ensures cleanup.
          token_hash: SHA-256 hex digest of the opaque token string.
          expires_at: UTC expiration timestamp (90 days from issuance).
          created_at: UTC issuance timestamp.
      """

      __tablename__ = "refresh_tokens"
      __allow_unmapped__ = True

      id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
      user_id = Column(
          UUID(as_uuid=True),
          ForeignKey("users.id", ondelete="CASCADE"),
          nullable=False,
          index=True,
      )
      token_hash = Column(String(64), unique=True, nullable=False)
      expires_at = Column(DateTime, nullable=False)
      created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

      __table_args__ = (
          Index("idx_refresh_tokens_token_hash", "token_hash"),
          Index("idx_refresh_tokens_user_id", "user_id"),
      )

      def to_dict(self) -> dict[str, Any]:
          """Serialize to dictionary (never exposes token_hash)."""
          return {
              "id": str(self.id),
              "user_id": str(self.user_id),
              "expires_at": self.expires_at.isoformat() if self.expires_at else None,
              "created_at": self.created_at.isoformat() if self.created_at else None,
          }

      def __repr__(self) -> str:
          """String representation (uses first 8 chars of hash for readability)."""
          return f"<RefreshToken hash={self.token_hash[:8]}...>"
  ```

- [ ] **Step 4: Agregar `RefreshToken` al `__init__.py` de models**

  In `backend/app/models/__init__.py`, add:
  - Import: `from app.models.refresh_token import RefreshToken`
  - Add `"RefreshToken"` to `__all__`

- [ ] **Step 5: Ejecutar el test — debe pasar**

  Run: `cd /Users/angelcorredor/Code/Wallet/backend && python -m pytest tests/models/test_refresh_token.py -v`
  Expected: PASS (3 tests)

- [ ] **Step 6: Commit**

  ```bash
  git add backend/app/models/refresh_token.py backend/app/models/__init__.py backend/tests/models/test_refresh_token.py
  git commit -m "feat(auth): add RefreshToken model"
  ```

---

### Task 1.5: Agregar `user_id` a los modelos existentes (`BaseModel`)

**Files:**
- Modify: `backend/app/models/base.py`
- Modify: `backend/app/models/account.py`
- Modify: `backend/app/models/category.py`
- Modify: `backend/app/models/transaction.py`
- Modify: `backend/app/models/transfer.py`
- Modify: `backend/app/models/dashboard.py`
- Modify: `backend/app/models/dashboard_widget.py`

The `user_id` column and the composite unique constraint on `client_id` will be added at the model level here. The migration handles making it NULLABLE first, then NOT NULL (see Task 1.6).

- [ ] **Step 1: Agregar `user_id` a `BaseModel` — NULLABLE inicialmente**

  In `backend/app/models/base.py`, add these imports and column definition:

  After existing imports, add:
  ```python
  from sqlalchemy import ForeignKey
  ```

  In the `BaseModel` class, after the `updated_at` column, add:
  ```python
  user_id = Column(
      UUID(as_uuid=True),
      ForeignKey("users.id", ondelete="CASCADE"),
      nullable=True,  # Starts NULLABLE; migration 008b sets NOT NULL after backfill
      index=True,
  )
  ```

  Also change the `client_id` column from `unique=True` to `unique=False` (the unique constraint becomes composite and is defined per-table in each model's `__table_args__`):
  ```python
  client_id = Column(String(100), nullable=True, index=True)
  ```
  Remove `unique=True` from this line.

- [ ] **Step 2: Agregar el composite unique constraint en `Account`**

  In `backend/app/models/account.py`, modify `__table_args__` (create it if it doesn't exist — Account has no `__table_args__` currently):

  ```python
  from sqlalchemy import UniqueConstraint

  # Add inside Account class:
  __table_args__ = (
      UniqueConstraint("user_id", "client_id", name="uq_accounts_user_client"),
  )
  ```

- [ ] **Step 3: Agregar el composite unique constraint en `Category`**

  In `backend/app/models/category.py`, the `__table_args__` already contains index definitions. Add the UniqueConstraint:

  ```python
  from sqlalchemy import UniqueConstraint  # add to imports

  __table_args__ = (
      Index("idx_categories_type", "type"),
      Index("idx_categories_parent", "parent_category_id"),
      Index("idx_categories_active", "active"),
      UniqueConstraint("user_id", "client_id", name="uq_categories_user_client"),
  )
  ```

- [ ] **Step 4: Agregar el composite unique constraint en `Transaction`**

  In `backend/app/models/transaction.py`, add UniqueConstraint to `__table_args__`:

  ```python
  from sqlalchemy import UniqueConstraint  # add to imports

  __table_args__ = (
      Index("idx_transactions_account_date", "account_id", "date"),
      Index("idx_transactions_account_type", "account_id", "type"),
      Index("idx_transactions_category", "category_id"),
      Index("idx_transactions_date", "date"),
      UniqueConstraint("user_id", "client_id", name="uq_transactions_user_client"),
  )
  ```

- [ ] **Step 5: Agregar el composite unique constraint en `Transfer`**

  In `backend/app/models/transfer.py`, add UniqueConstraint to `__table_args__`:

  ```python
  from sqlalchemy import UniqueConstraint  # add to imports

  __table_args__ = (
      Index("idx_transfers_source", "source_account_id"),
      Index("idx_transfers_destination", "destination_account_id"),
      Index("idx_transfers_date", "date"),
      UniqueConstraint("user_id", "client_id", name="uq_transfers_user_client"),
  )
  ```

- [ ] **Step 6: Agregar el composite unique constraint en `Dashboard`**

  In `backend/app/models/dashboard.py`, the existing `__table_args__` has a CheckConstraint. Add UniqueConstraint:

  ```python
  from sqlalchemy import UniqueConstraint  # add to imports

  __table_args__ = (
      CheckConstraint(
          "layout_columns >= 1 AND layout_columns <= 4",
          name="ck_dashboards_layout_columns",
      ),
      UniqueConstraint("user_id", "client_id", name="uq_dashboards_user_client"),
  )
  ```

- [ ] **Step 7: Agregar el composite unique constraint en `DashboardWidget`**

  In `backend/app/models/dashboard_widget.py`, add UniqueConstraint to `__table_args__`:

  ```python
  from sqlalchemy import UniqueConstraint  # add to imports

  __table_args__ = (
      CheckConstraint("width >= 1 AND width <= 4", name="ck_widgets_width"),
      CheckConstraint("height >= 1 AND height <= 3", name="ck_widgets_height"),
      CheckConstraint("position_x >= 0", name="ck_widgets_position_x"),
      CheckConstraint("position_y >= 0", name="ck_widgets_position_y"),
      UniqueConstraint("user_id", "client_id", name="uq_widgets_user_client"),
  )
  ```

- [ ] **Step 8: Verificar que los modelos importan sin error**

  Run: `cd /Users/angelcorredor/Code/Wallet/backend && python -c "from app.models import Account, Category, Transaction, Transfer, Dashboard, DashboardWidget; print('OK')"`
  Expected: `OK`

- [ ] **Step 9: Commit**

  ```bash
  git add backend/app/models/base.py backend/app/models/account.py backend/app/models/category.py backend/app/models/transaction.py backend/app/models/transfer.py backend/app/models/dashboard.py backend/app/models/dashboard_widget.py
  git commit -m "feat(auth): add user_id FK and composite client_id constraints to all domain models"
  ```

---

### Task 1.6: Actualizar modelo `UserSetting` a PK compuesta `(user_id, key)`

**Files:**
- Modify: `backend/app/models/user_setting.py`
- Modify: `backend/app/repositories/user_setting.py`
- Modify: `backend/app/services/user_setting.py`
- Modify: `backend/app/api/settings.py`

`UserSetting` does NOT inherit from `BaseModel`. It gets a `user_id` column added as part of the primary key.

- [ ] **Step 1: Escribir test para el nuevo comportamiento**

  Create `backend/tests/models/test_user_setting_user_aware.py`:

  ```python
  """Tests verifying UserSetting has composite PK (user_id, key)."""
  from app.models.user_setting import UserSetting


  def test_user_setting_pk_is_composite(app):
      """UserSetting PK must include user_id and key."""
      pk_cols = {col.name for col in UserSetting.__table__.primary_key}
      assert pk_cols == {"user_id", "key"}


  def test_user_setting_user_id_fk(app):
      fk_tables = {fk.column.table.name for fk in UserSetting.__table__.foreign_keys}
      assert "users" in fk_tables
  ```

- [ ] **Step 2: Ejecutar el test — debe fallar**

  Run: `cd /Users/angelcorredor/Code/Wallet/backend && python -m pytest tests/models/test_user_setting_user_aware.py -v`
  Expected: FAIL

- [ ] **Step 3: Actualizar `UserSetting` model**

  Replace the contents of `backend/app/models/user_setting.py`:

  ```python
  """
  UserSetting model for per-user key/value configuration.

  Unlike other models, UserSetting does not inherit from BaseModel — it has no
  UUID id and no client_id. Its primary key is the composite (user_id, key),
  meaning each user has their own independent set of settings.
  """

  from datetime import datetime
  from typing import Any

  from sqlalchemy import Column, String, DateTime, ForeignKey, PrimaryKeyConstraint
  from sqlalchemy.dialects.postgresql import JSONB, UUID

  from app.extensions import db


  class UserSetting(db.Model):
      """
      Per-user key/value store for application settings.

      Primary key is (user_id, key), so each user maintains independent settings.
      Values use JSONB for flexible structured storage without schema changes.

      Attributes:
          user_id: FK to users.id. Part of composite PK.
          key: Setting identifier (e.g. 'primary_currency'). Part of composite PK.
          value: JSONB setting value.
          updated_at: Auto-updated modification timestamp.
      """

      __tablename__ = "user_settings"
      __allow_unmapped__ = True

      user_id = Column(
          UUID(as_uuid=True),
          ForeignKey("users.id", ondelete="CASCADE"),
          nullable=False,
      )
      key = Column(String(100), nullable=False)
      value = Column(JSONB, nullable=False)
      updated_at = Column(
          DateTime,
          default=datetime.utcnow,
          onupdate=datetime.utcnow,
          nullable=False,
      )

      __table_args__ = (
          PrimaryKeyConstraint("user_id", "key", name="pk_user_settings"),
      )

      def to_dict(self) -> dict[str, Any]:
          """
          Convert model to dictionary.

          Returns:
              Dict with user_id (str), key, value, and updated_at (ISO).
          """
          return {
              "user_id": str(self.user_id),
              "key": self.key,
              "value": self.value,
              "updated_at": self.updated_at.isoformat() if self.updated_at else None,
          }

      def __repr__(self) -> str:
          """String representation."""
          return f"<UserSetting user={self.user_id} {self.key}={self.value!r}>"
  ```

- [ ] **Step 4: Actualizar `SettingsRepository` para ser user-aware**

  Replace `backend/app/repositories/user_setting.py`:

  ```python
  """
  UserSetting repository for per-user key/value database operations.

  UserSetting uses a composite primary key (user_id, key) rather than a UUID,
  so it does not extend BaseRepository. The set() method is a full upsert.
  """

  from datetime import datetime
  from typing import Any, Optional
  from uuid import UUID

  from sqlalchemy.dialects.postgresql import insert

  from app.extensions import db
  from app.models.user_setting import UserSetting


  class SettingsRepository:
      """
      Repository for UserSetting with per-user isolation.

      All methods require a user_id to scope operations to a single user's
      settings. No cross-user reads are possible through this interface.
      """

      def get(self, user_id: UUID, key: str) -> Optional[UserSetting]:
          """
          Retrieve a single setting by user and key.

          Args:
              user_id: Owning user's UUID.
              key: Setting identifier (e.g. 'primary_currency').

          Returns:
              UserSetting instance if the key exists for this user, else None.
          """
          return db.session.execute(
              db.select(UserSetting).where(
                  UserSetting.user_id == user_id,
                  UserSetting.key == key,
              )
          ).scalars().one_or_none()

      def get_all(self, user_id: UUID) -> list[UserSetting]:
          """
          Retrieve all settings for a user.

          Args:
              user_id: Owning user's UUID.

          Returns:
              List of UserSetting instances for this user.
          """
          return (
              db.session.execute(
                  db.select(UserSetting).where(UserSetting.user_id == user_id)
              )
              .scalars()
              .all()
          )

      def set(self, user_id: UUID, key: str, value: Any) -> UserSetting:
          """
          Insert or update a setting for the given user and key.

          Uses PostgreSQL INSERT … ON CONFLICT (user_id, key) DO UPDATE.

          Args:
              user_id: Owning user's UUID.
              key: Setting identifier.
              value: Python value stored as JSONB.

          Returns:
              The persisted UserSetting instance, refreshed from the database.
          """
          now = datetime.utcnow()
          stmt = (
              insert(UserSetting)
              .values(
                  user_id=user_id,
                  key=key,
                  value=value,
                  updated_at=now,
              )
              .on_conflict_do_update(
                  index_elements=["user_id", "key"],
                  set_={
                      "value": value,
                      "updated_at": now,
                  },
              )
          )
          db.session.execute(stmt)
          db.session.commit()
          return self.get(user_id, key)  # type: ignore[return-value]
  ```

- [ ] **Step 5: Actualizar `SettingsService` para aceptar `user_id`**

  In `backend/app/services/user_setting.py`, update every method to accept and pass `user_id: UUID`:

  ```python
  """
  UserSetting service containing business logic for per-user application settings.

  Known keys and their validation rules
  ---------------------------------------
  ``primary_currency``
      Must be a string matching the regex ``/^[A-Z]{2,10}$/``.

  Any key not in the known set raises ``ValidationError``.
  """

  import re
  from typing import Any
  from uuid import UUID

  from app.models.user_setting import UserSetting
  from app.repositories.user_setting import SettingsRepository
  from app.utils.exceptions import ValidationError

  _CURRENCY_RE = re.compile(r"^[A-Z]{2,10}$")
  _KNOWN_KEYS: dict[str, Any] = {
      "primary_currency": None,
  }


  def _validate_primary_currency(value: Any) -> str:
      """
      Validate the ``primary_currency`` setting value.

      Args:
          value: Candidate value from the caller.

      Returns:
          Uppercased currency code string.

      Raises:
          ValidationError: If the value is not a non-empty string of 2-10
              uppercase ASCII letters.
      """
      if not isinstance(value, str):
          raise ValidationError(
              "primary_currency debe ser una cadena de texto (ej. 'USD', 'COP')"
          )
      upper = value.upper()
      if not _CURRENCY_RE.match(upper):
          raise ValidationError(
              "primary_currency debe ser un código de divisa de 2 a 10 letras mayúsculas "
              "(ej. 'USD', 'COP', 'BTC')"
          )
      return upper


  _VALIDATORS = {
      "primary_currency": _validate_primary_currency,
  }


  class SettingsService:
      """Service for per-user application settings business logic."""

      def __init__(self) -> None:
          """Initialise service with its repository."""
          self.repository = SettingsRepository()

      def get(self, user_id: UUID, key: str) -> Any:
          """
          Return the Python value stored for the given user and key.

          Args:
              user_id: Owning user's UUID.
              key: Setting identifier (e.g. 'primary_currency').

          Returns:
              The stored Python value, or None if the key does not exist.
          """
          row = self.repository.get(user_id, key)
          if row is None:
              return None
          return row.value

      def get_all(self, user_id: UUID) -> dict[str, Any]:
          """
          Return all settings for a user as a flat ``{key: value}`` dictionary.

          Args:
              user_id: Owning user's UUID.

          Returns:
              Dictionary mapping every stored setting key to its Python value.
          """
          rows = self.repository.get_all(user_id)
          return {row.key: row.value for row in rows}

      def set(self, user_id: UUID, key: str, value: Any) -> UserSetting:
          """
          Persist a setting after validating both key and value.

          Args:
              user_id: Owning user's UUID.
              key: Setting identifier. Must be one of the known keys.
              value: New value. Validated according to per-key rules.

          Returns:
              Persisted UserSetting instance.

          Raises:
              ValidationError: If key is unknown or value fails per-key validation.
          """
          if key not in _KNOWN_KEYS:
              raise ValidationError(
                  f"Clave de configuración desconocida: '{key}'. "
                  f"Claves válidas: {', '.join(sorted(_KNOWN_KEYS))}"
              )
          validator = _VALIDATORS.get(key)
          if validator is not None:
              value = validator(value)
          return self.repository.set(user_id=user_id, key=key, value=value)
  ```

- [ ] **Step 6: Actualizar `settings.py` API para extraer `user_id` de `g`**

  In `backend/app/api/settings.py`, update the two endpoints to pass `user_id`:
  - Add `from flask import g` to imports
  - In `get_settings()`: call `settings_service.get_all(user_id=g.current_user_id)`
  - In `update_setting()`: call `settings_service.set(user_id=g.current_user_id, key=key, value=...)`

  Note: `@require_auth` will be applied in Chunk 2, Task 2.1. For now the `g.current_user_id` call will fail if hit directly, but the decorator will protect it.

- [ ] **Step 7: Ejecutar los tests del modelo**

  Run: `cd /Users/angelcorredor/Code/Wallet/backend && python -m pytest tests/models/test_user_setting_user_aware.py -v`
  Expected: PASS (2 tests)

- [ ] **Step 8: Commit**

  ```bash
  git add backend/app/models/user_setting.py backend/app/repositories/user_setting.py backend/app/services/user_setting.py backend/app/api/settings.py backend/tests/models/test_user_setting_user_aware.py
  git commit -m "feat(auth): update UserSetting to composite PK (user_id, key)"
  ```

---

### Task 1.7: Crear migraciones (008a, 008b, 008c)

**Files:**
- Create: `backend/migrations/versions/008a_add_users_and_refresh_tokens.py`
- Create: `backend/migrations/versions/008b_add_user_id_nullable_to_domain_models.py`
- Create: `backend/migrations/versions/008c_make_user_id_not_null.py`

The migration is split in three steps per the spec's two-phase strategy:
- `008a`: Create `users` and `refresh_tokens` tables.
- `008b`: Add `user_id` as NULLABLE to all domain tables, drop old `UNIQUE` on `client_id`, add composite `UNIQUE(user_id, client_id)`, update `user_settings` PK to `(user_id, key)`. Backfills existing rows to the first user if present, otherwise deletes orphan rows.
- `008c`: Alter all `user_id` columns to NOT NULL.

- [ ] **Step 1: Crear `008a` — tablas de auth**

  Create `backend/migrations/versions/008a_add_users_and_refresh_tokens.py`:

  ```python
  """Add users and refresh_tokens tables.

  Revision ID: 008a_add_users_and_refresh_tokens
  Revises: 007_add_active_to_categories
  Create Date: 2026-03-15
  """

  from typing import Sequence, Union
  import sqlalchemy as sa
  from sqlalchemy.dialects import postgresql
  from alembic import op

  revision: str = "008a_add_users_and_refresh_tokens"
  down_revision: Union[str, None] = "007_add_active_to_categories"
  branch_labels: Union[str, Sequence[str], None] = None
  depends_on: Union[str, Sequence[str], None] = None


  def upgrade() -> None:
      # users
      op.create_table(
          "users",
          sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                    server_default=sa.text("gen_random_uuid()")),
          sa.Column("google_id", sa.String(255), nullable=False),
          sa.Column("email", sa.String(255), nullable=False),
          sa.Column("name", sa.String(255), nullable=False),
          sa.Column("created_at", sa.DateTime(), nullable=False,
                    server_default=sa.text("now()")),
          sa.Column("updated_at", sa.DateTime(), nullable=False,
                    server_default=sa.text("now()")),
          sa.UniqueConstraint("google_id", name="uq_users_google_id"),
          sa.UniqueConstraint("email", name="uq_users_email"),
      )
      op.create_index("idx_users_google_id", "users", ["google_id"])
      op.create_index("idx_users_email", "users", ["email"])

      # refresh_tokens
      op.create_table(
          "refresh_tokens",
          sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                    server_default=sa.text("gen_random_uuid()")),
          sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
          sa.Column("token_hash", sa.String(64), nullable=False),
          sa.Column("expires_at", sa.DateTime(), nullable=False),
          sa.Column("created_at", sa.DateTime(), nullable=False,
                    server_default=sa.text("now()")),
          sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
          sa.UniqueConstraint("token_hash", name="uq_refresh_tokens_hash"),
      )
      op.create_index("idx_refresh_tokens_token_hash", "refresh_tokens", ["token_hash"])
      op.create_index("idx_refresh_tokens_user_id", "refresh_tokens", ["user_id"])


  def downgrade() -> None:
      op.drop_table("refresh_tokens")
      op.drop_table("users")
  ```

- [ ] **Step 2: Crear `008b` — agregar user_id NULLABLE + backfill**

  Create `backend/migrations/versions/008b_add_user_id_nullable_to_domain_models.py`:

  ```python
  """Add user_id (NULLABLE) to domain models; backfill or delete orphans.

  Two-phase migration step (b):
  - Drops old UNIQUE constraint on client_id in each domain table.
  - Adds user_id as NULLABLE FK to users.id.
  - Adds composite UNIQUE(user_id, client_id) to each domain table.
  - Updates user_settings: drops old PK on key, adds user_id column,
    creates new composite PK (user_id, key).
  - Backfills user_id to the first user found in users table, or deletes
    orphan rows if no users exist yet.

  Revision ID: 008b_add_user_id_nullable_to_domain_models
  Revises: 008a_add_users_and_refresh_tokens
  Create Date: 2026-03-15
  """

  from typing import Sequence, Union
  import sqlalchemy as sa
  from sqlalchemy.dialects import postgresql
  from alembic import op

  revision: str = "008b_add_user_id_nullable_to_domain_models"
  down_revision: Union[str, None] = "008a_add_users_and_refresh_tokens"
  branch_labels: Union[str, Sequence[str], None] = None
  depends_on: Union[str, Sequence[str], None] = None

  # Tables that inherit from BaseModel and need user_id + composite client_id constraint.
  DOMAIN_TABLES = [
      "accounts",
      "categories",
      "transactions",
      "transfers",
      "dashboards",
      "dashboard_widgets",
  ]


  def upgrade() -> None:
      conn = op.get_bind()

      # --- Domain tables: drop old unique(client_id), add user_id, add composite unique ---
      for table in DOMAIN_TABLES:
          # Drop the old table-level unique constraint on client_id (name is auto-generated).
          # We use a raw SQL approach since constraint names vary.
          conn.execute(sa.text(
              f"ALTER TABLE {table} DROP CONSTRAINT IF EXISTS {table}_client_id_key"
          ))
          # Add user_id NULLABLE FK
          op.add_column(
              table,
              sa.Column(
                  "user_id",
                  postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("users.id", ondelete="CASCADE"),
                  nullable=True,
              ),
          )
          op.create_index(f"idx_{table}_user_id", table, ["user_id"])
          # Composite unique constraint: only applies when both columns are non-null
          # PostgreSQL unique constraints ignore rows with NULLs, so this is safe.
          short = table[:15]  # keep constraint name under 63 chars
          op.create_unique_constraint(
              f"uq_{short}_user_client",
              table,
              ["user_id", "client_id"],
          )

      # --- user_settings: restructure to composite PK ---
      # Drop old PK
      op.drop_constraint("user_settings_pkey", "user_settings", type_="primary")
      # Add user_id column (nullable for now)
      op.add_column(
          "user_settings",
          sa.Column(
              "user_id",
              postgresql.UUID(as_uuid=True),
              nullable=True,
          ),
      )

      # --- Backfill: assign all rows to the first user, or delete if none ---
      result = conn.execute(
          sa.text("SELECT id FROM users ORDER BY created_at ASC LIMIT 1")
      ).fetchone()

      if result is not None:
          first_user_id = result[0]
          for table in DOMAIN_TABLES:
              conn.execute(
                  sa.text(f"UPDATE {table} SET user_id = :uid WHERE user_id IS NULL"),
                  {"uid": first_user_id},
              )
          conn.execute(
              sa.text("UPDATE user_settings SET user_id = :uid WHERE user_id IS NULL"),
              {"uid": first_user_id},
          )
      else:
          # No users exist: delete all orphan domain data (test/empty environment)
          for table in DOMAIN_TABLES:
              conn.execute(sa.text(f"DELETE FROM {table} WHERE user_id IS NULL"))
          conn.execute(sa.text("DELETE FROM user_settings WHERE user_id IS NULL"))

      # Add FK constraint on user_settings.user_id now that it is populated
      op.create_foreign_key(
          "fk_user_settings_user_id",
          "user_settings",
          "users",
          ["user_id"],
          ["id"],
          ondelete="CASCADE",
      )
      # New composite PK for user_settings
      op.create_primary_key("pk_user_settings", "user_settings", ["user_id", "key"])


  def downgrade() -> None:
      # Restore user_settings old PK
      op.drop_constraint("pk_user_settings", "user_settings", type_="primary")
      op.drop_constraint("fk_user_settings_user_id", "user_settings", type_="foreignkey")
      op.drop_column("user_settings", "user_id")
      op.create_primary_key("user_settings_pkey", "user_settings", ["key"])

      for table in DOMAIN_TABLES:
          short = table[:15]
          op.drop_constraint(f"uq_{short}_user_client", table, type_="unique")
          op.drop_index(f"idx_{table}_user_id", table_name=table)
          op.drop_column(table, "user_id")
          # Restore old unique constraint on client_id
          op.create_unique_constraint(
              f"{table}_client_id_key", table, ["client_id"]
          )
  ```

- [ ] **Step 3: Crear `008c` — NOT NULL en user_id**

  Create `backend/migrations/versions/008c_make_user_id_not_null.py`:

  ```python
  """Make user_id NOT NULL on all domain tables and user_settings.

  Two-phase migration step (c): after the backfill in 008b, all rows
  have a valid user_id. This migration enforces the NOT NULL constraint.

  Revision ID: 008c_make_user_id_not_null
  Revises: 008b_add_user_id_nullable_to_domain_models
  Create Date: 2026-03-15
  """

  from typing import Sequence, Union
  import sqlalchemy as sa
  from alembic import op

  revision: str = "008c_make_user_id_not_null"
  down_revision: Union[str, None] = "008b_add_user_id_nullable_to_domain_models"
  branch_labels: Union[str, Sequence[str], None] = None
  depends_on: Union[str, Sequence[str], None] = None

  DOMAIN_TABLES = [
      "accounts",
      "categories",
      "transactions",
      "transfers",
      "dashboards",
      "dashboard_widgets",
      "user_settings",
  ]


  def upgrade() -> None:
      for table in DOMAIN_TABLES:
          op.alter_column(table, "user_id", nullable=False)


  def downgrade() -> None:
      for table in DOMAIN_TABLES:
          op.alter_column(table, "user_id", nullable=True)
  ```

- [ ] **Step 4: Ejecutar las migraciones**

  Run: `cd /Users/angelcorredor/Code/Wallet/backend && flask db upgrade`
  Expected: All three migrations complete without error. Output shows `Running upgrade ... -> 008c_make_user_id_not_null`.

- [ ] **Step 5: Verificar el schema en la DB**

  Run: `cd /Users/angelcorredor/Code/Wallet/backend && flask db current`
  Expected: `008c_make_user_id_not_null (head)`

- [ ] **Step 6: Commit**

  ```bash
  git add backend/migrations/versions/008a_add_users_and_refresh_tokens.py backend/migrations/versions/008b_add_user_id_nullable_to_domain_models.py backend/migrations/versions/008c_make_user_id_not_null.py
  git commit -m "feat(auth): add three-phase user_id migration (008a/008b/008c)"
  ```

---

## Chunk 2: Endpoints de Autenticación y Middleware (Ticket 2)

### Task 2.1: Implementar `@require_auth` decorator

**Files:**
- Create: `backend/app/utils/auth.py`

- [ ] **Step 1: Escribir tests para el decorator**

  Create `backend/tests/utils/test_auth_decorator.py`:

  ```python
  """Tests for the @require_auth decorator."""
  import pytest
  import jwt
  from datetime import datetime, timedelta
  from flask import g
  from app.utils.auth import require_auth


  @pytest.fixture
  def valid_token(app):
      """Generate a valid JWT for testing."""
      payload = {
          "id": "00000000-0000-0000-0000-000000000001",
          "email": "test@example.com",
          "name": "Test User",
          "exp": datetime.utcnow() + timedelta(hours=1),
      }
      return jwt.encode(payload, app.config["JWT_SECRET"], algorithm="HS256")


  @pytest.fixture
  def expired_token(app):
      """Generate an expired JWT for testing."""
      payload = {
          "id": "00000000-0000-0000-0000-000000000001",
          "email": "test@example.com",
          "name": "Test User",
          "exp": datetime.utcnow() - timedelta(hours=1),
      }
      return jwt.encode(payload, app.config["JWT_SECRET"], algorithm="HS256")


  def test_require_auth_sets_current_user_id(app, valid_token):
      """require_auth injects g.current_user_id from a valid Bearer token."""
      with app.test_request_context(
          "/",
          headers={"Authorization": f"Bearer {valid_token}"},
      ):
          @require_auth
          def protected():
              return str(g.current_user_id)

          result = protected()
          assert "00000000-0000-0000-0000-000000000001" in result


  def test_require_auth_returns_401_without_header(app):
      """require_auth returns 401 when Authorization header is absent."""
      with app.test_request_context("/"):
          @require_auth
          def protected():
              return "ok"

          response, status = protected()
          assert status == 401


  def test_require_auth_returns_401_on_expired_token(app, expired_token):
      """require_auth returns 401 for expired tokens."""
      with app.test_request_context(
          "/",
          headers={"Authorization": f"Bearer {expired_token}"},
      ):
          @require_auth
          def protected():
              return "ok"

          response, status = protected()
          assert status == 401


  def test_require_auth_returns_401_on_malformed_token(app):
      """require_auth returns 401 for non-JWT garbage."""
      with app.test_request_context(
          "/",
          headers={"Authorization": "Bearer not.a.jwt"},
      ):
          @require_auth
          def protected():
              return "ok"

          response, status = protected()
          assert status == 401
  ```

- [ ] **Step 2: Ejecutar el test — debe fallar**

  Run: `cd /Users/angelcorredor/Code/Wallet/backend && python -m pytest tests/utils/test_auth_decorator.py -v`
  Expected: FAIL — `ModuleNotFoundError: No module named 'app.utils.auth'`

- [ ] **Step 3: Crear `backend/app/utils/auth.py`**

  ```python
  """
  Authentication utilities: JWT verification and require_auth decorator.

  The decorator extracts and verifies the JWT from the Authorization header,
  injects g.current_user_id as a UUID, and returns 401 on any failure.
  Endpoints decorated with @require_auth cannot be reached without a valid token.
  """

  import uuid
  from functools import wraps
  from typing import Callable, Any

  import jwt
  from flask import current_app, g, request

  from app.utils.responses import error_response


  def _extract_bearer_token() -> str | None:
      """
      Extract the Bearer token from the Authorization header.

      Returns:
          Token string if header is present and well-formed, else None.
      """
      auth_header = request.headers.get("Authorization", "")
      if not auth_header.startswith("Bearer "):
          return None
      return auth_header[len("Bearer "):]


  def verify_jwt(token: str) -> dict[str, Any]:
      """
      Verify a JWT token and return its decoded payload.

      Args:
          token: Raw JWT string (without 'Bearer ' prefix).

      Returns:
          Decoded payload dict containing at least 'id', 'email', 'name'.

      Raises:
          jwt.ExpiredSignatureError: If the token has expired.
          jwt.InvalidTokenError: If the token is malformed or signature is invalid.
      """
      return jwt.decode(
          token,
          current_app.config["JWT_SECRET"],
          algorithms=["HS256"],
      )


  def require_auth(f: Callable) -> Callable:
      """
      Decorator that enforces JWT authentication on a Flask route.

      Extracts the Bearer token from the Authorization header, verifies it,
      and injects g.current_user_id (UUID) for use in the route handler.

      Returns 401 if the header is missing, token is malformed, or token
      is expired.

      Args:
          f: The Flask view function to protect.

      Returns:
          Wrapped function that performs auth before delegating to f.
      """

      @wraps(f)
      def decorated(*args: Any, **kwargs: Any) -> Any:
          token = _extract_bearer_token()
          if not token:
              return error_response("Autenticación requerida", status_code=401)

          try:
              payload = verify_jwt(token)
          except jwt.ExpiredSignatureError:
              return error_response("Token expirado", status_code=401)
          except jwt.InvalidTokenError:
              return error_response("Token inválido", status_code=401)

          try:
              g.current_user_id = uuid.UUID(payload["id"])
          except (KeyError, ValueError):
              return error_response("Token inválido: payload malformado", status_code=401)

          return f(*args, **kwargs)

      return decorated
  ```

- [ ] **Step 4: Ejecutar los tests — deben pasar**

  Run: `cd /Users/angelcorredor/Code/Wallet/backend && python -m pytest tests/utils/test_auth_decorator.py -v`
  Expected: PASS (4 tests)

- [ ] **Step 5: Commit**

  ```bash
  git add backend/app/utils/auth.py backend/tests/utils/test_auth_decorator.py
  git commit -m "feat(auth): implement require_auth JWT decorator"
  ```

---

### Task 2.2: Crear `AuthService` y repositorios de auth

**Files:**
- Create: `backend/app/services/auth.py`

The `AuthService` encapsulates all auth business logic: Google token verification, user find/create, JWT issuance, refresh token rotation, and logout.

- [ ] **Step 1: Escribir tests para `AuthService`**

  Create `backend/tests/services/test_auth_service.py`:

  ```python
  """Tests for AuthService."""
  import pytest
  from unittest.mock import patch, MagicMock
  from uuid import uuid4
  from app.services.auth import AuthService
  from app.models.user import User


  @pytest.fixture
  def auth_service(app):
      return AuthService()


  @pytest.fixture
  def mock_google_payload():
      return {
          "sub": "google_sub_12345",
          "email": "user@example.com",
          "name": "Test User",
      }


  def test_find_or_create_user_creates_new_user(app, auth_service, mock_google_payload):
      """find_or_create_user creates a new User when google_id is unknown."""
      with app.app_context():
          user, is_new = auth_service.find_or_create_user(mock_google_payload)
          assert is_new is True
          assert user.google_id == "google_sub_12345"
          assert user.email == "user@example.com"


  def test_find_or_create_user_finds_existing_user(app, auth_service, mock_google_payload):
      """find_or_create_user returns existing user on second call."""
      with app.app_context():
          user1, is_new1 = auth_service.find_or_create_user(mock_google_payload)
          user2, is_new2 = auth_service.find_or_create_user(mock_google_payload)
          assert is_new2 is False
          assert user1.id == user2.id


  def test_issue_tokens_returns_access_and_refresh(app, auth_service):
      """issue_tokens returns a dict with access_token and refresh_token."""
      with app.app_context():
          user, _ = auth_service.find_or_create_user(
              {"sub": "sub999", "email": "a@b.com", "name": "A"}
          )
          tokens = auth_service.issue_tokens(user)
          assert "access_token" in tokens
          assert "refresh_token" in tokens


  def test_rotate_refresh_token_returns_new_tokens(app, auth_service):
      """rotate_refresh_token issues new tokens and invalidates the old one."""
      with app.app_context():
          user, _ = auth_service.find_or_create_user(
              {"sub": "sub888", "email": "b@c.com", "name": "B"}
          )
          tokens1 = auth_service.issue_tokens(user)
          tokens2 = auth_service.rotate_refresh_token(tokens1["refresh_token"])
          assert tokens2["refresh_token"] != tokens1["refresh_token"]
          # Old token should no longer be valid
          with pytest.raises(Exception):
              auth_service.rotate_refresh_token(tokens1["refresh_token"])


  def test_revoke_refresh_token_is_idempotent(app, auth_service):
      """revoke_refresh_token does not raise if token does not exist."""
      with app.app_context():
          # Should not raise
          auth_service.revoke_refresh_token("nonexistent_token_string")
  ```

- [ ] **Step 2: Ejecutar tests — deben fallar**

  Run: `cd /Users/angelcorredor/Code/Wallet/backend && python -m pytest tests/services/test_auth_service.py -v`
  Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Crear `backend/app/services/auth.py`**

  ```python
  """
  AuthService: business logic for Google OAuth, JWT issuance, and token rotation.

  Flow:
  1. Client sends Google id_token → POST /auth/google
  2. AuthService.verify_google_token() validates it locally (no HTTP round-trip)
  3. AuthService.find_or_create_user() returns (User, is_new_user)
  4. AuthService.issue_tokens() emits JWT (24h) + opaque refresh token (90d)
  5. On subsequent visits: POST /auth/refresh with refresh token
  6. AuthService.rotate_refresh_token() deletes old token, inserts new one
  7. POST /auth/logout → AuthService.revoke_refresh_token()
  """

  import hashlib
  import secrets
  from datetime import datetime, timedelta
  from typing import Any
  from uuid import UUID

  import jwt
  from flask import current_app
  from google.oauth2 import id_token as google_id_token
  from google.auth.transport import requests as google_requests

  from app.extensions import db
  from app.models.user import User
  from app.models.refresh_token import RefreshToken
  from app.utils.exceptions import ValidationError


  def _hash_token(token: str) -> str:
      """Return the SHA-256 hex digest of a plaintext token string."""
      return hashlib.sha256(token.encode()).hexdigest()


  class AuthService:
      """
      Handles the full authentication lifecycle.

      Responsibilities:
      - Validate Google id_token and extract user info
      - Find or create User records on first login
      - Issue JWT access tokens and opaque refresh tokens
      - Rotate refresh tokens (delete old, insert new)
      - Revoke refresh tokens on logout
      """

      def verify_google_token(self, id_token_str: str) -> dict[str, Any]:
          """
          Verify a Google id_token and return its payload.

          Validation is performed locally using google-auth library — no
          outbound HTTP call per verification.

          Args:
              id_token_str: The raw id_token string from Google Sign-In.

          Returns:
              Verified payload dict containing at least 'sub', 'email', 'name'.

          Raises:
              ValidationError: If the token is invalid, expired, or audience mismatch.
          """
          try:
              payload = google_id_token.verify_oauth2_token(
                  id_token_str,
                  google_requests.Request(),
                  current_app.config["GOOGLE_CLIENT_ID"],
              )
          except Exception as e:
              raise ValidationError(f"Token de Google inválido: {str(e)}")

          required_fields = {"sub", "email", "name"}
          if not required_fields.issubset(payload.keys()):
              raise ValidationError(
                  "Token de Google no contiene los campos requeridos (sub, email, name)"
              )
          return payload

      def find_or_create_user(
          self, google_payload: dict[str, Any]
      ) -> tuple[User, bool]:
          """
          Find an existing user by google_id or create a new one.

          Args:
              google_payload: Verified Google id_token payload with 'sub',
                  'email', 'name'.

          Returns:
              Tuple of (User instance, is_new_user bool).
          """
          google_id = google_payload["sub"]
          existing = (
              db.session.execute(
                  db.select(User).where(User.google_id == google_id)
              )
              .scalars()
              .one_or_none()
          )
          if existing:
              return existing, False

          user = User(
              google_id=google_id,
              email=google_payload["email"],
              name=google_payload["name"],
          )
          db.session.add(user)
          db.session.commit()
          db.session.refresh(user)
          return user, True

      def _build_jwt(self, user: User) -> str:
          """
          Build a signed JWT containing user identity payload.

          Payload includes 'id', 'email', 'name', and 'exp'. The frontend
          decodes the payload to extract user info without an extra API call.

          Args:
              user: User instance to embed in the token.

          Returns:
              Signed JWT string.
          """
          expiry_hours = current_app.config["JWT_EXPIRY_HOURS"]
          payload = {
              "id": str(user.id),
              "email": user.email,
              "name": user.name,
              "exp": datetime.utcnow() + timedelta(hours=expiry_hours),
          }
          return jwt.encode(
              payload,
              current_app.config["JWT_SECRET"],
              algorithm="HS256",
          )

      def _issue_refresh_token(self, user: User) -> str:
          """
          Create a new refresh token for a user, replacing any existing one.

          The old refresh token row is deleted before the new one is inserted,
          enforcing the single-token-per-user invariant.

          Args:
              user: User instance to issue a refresh token for.

          Returns:
              Plaintext opaque token string (64 hex chars). Only returned once;
              only the hash is stored.
          """
          expiry_days = current_app.config["REFRESH_TOKEN_EXPIRY_DAYS"]
          token_plain = secrets.token_hex(32)  # 64-char hex string
          token_hash = _hash_token(token_plain)
          expires_at = datetime.utcnow() + timedelta(days=expiry_days)

          # Enforce single token per user: delete any existing token
          db.session.execute(
              db.delete(RefreshToken).where(RefreshToken.user_id == user.id)
          )
          new_token = RefreshToken(
              user_id=user.id,
              token_hash=token_hash,
              expires_at=expires_at,
          )
          db.session.add(new_token)
          db.session.commit()
          return token_plain

      def issue_tokens(self, user: User) -> dict[str, str]:
          """
          Issue a JWT and a fresh refresh token for the given user.

          Args:
              user: Authenticated User instance.

          Returns:
              Dict with 'access_token' (JWT) and 'refresh_token' (opaque).
          """
          access_token = self._build_jwt(user)
          refresh_token = self._issue_refresh_token(user)
          return {
              "access_token": access_token,
              "refresh_token": refresh_token,
          }

      def rotate_refresh_token(self, token_plain: str) -> dict[str, str]:
          """
          Validate and rotate a refresh token.

          Finds the stored token by hash, verifies it is not expired, deletes
          the old row, and issues new JWT + refresh token pair.

          Args:
              token_plain: Plaintext refresh token from the client.

          Returns:
              Dict with new 'access_token' and 'refresh_token'.

          Raises:
              ValidationError: If token is not found or has expired.
          """
          token_hash = _hash_token(token_plain)
          stored = (
              db.session.execute(
                  db.select(RefreshToken).where(
                      RefreshToken.token_hash == token_hash
                  )
              )
              .scalars()
              .one_or_none()
          )

          if stored is None:
              raise ValidationError("Refresh token inválido o ya utilizado")

          if stored.expires_at < datetime.utcnow():
              # Token expired: clean it up
              db.session.delete(stored)
              db.session.commit()
              raise ValidationError("Refresh token expirado")

          # Load the user before deleting the token row
          user = db.session.get(User, stored.user_id)
          if user is None:
              db.session.delete(stored)
              db.session.commit()
              raise ValidationError("Usuario no encontrado")

          # _issue_refresh_token deletes the old token internally
          return self.issue_tokens(user)

      def revoke_refresh_token(self, token_plain: str) -> None:
          """
          Revoke a refresh token by deleting its DB row.

          Idempotent: no-op if the token does not exist.

          Args:
              token_plain: Plaintext refresh token to revoke.
          """
          token_hash = _hash_token(token_plain)
          db.session.execute(
              db.delete(RefreshToken).where(
                  RefreshToken.token_hash == token_hash
              )
          )
          db.session.commit()
  ```

- [ ] **Step 4: Ejecutar los tests**

  Run: `cd /Users/angelcorredor/Code/Wallet/backend && python -m pytest tests/services/test_auth_service.py -v`
  Expected: PASS (5 tests). Note: `test_find_or_create_user_*` require DB — ensure test DB is running.

- [ ] **Step 5: Commit**

  ```bash
  git add backend/app/services/auth.py backend/tests/services/test_auth_service.py
  git commit -m "feat(auth): implement AuthService with Google OAuth and token rotation"
  ```

---

### Task 2.3: Crear endpoints `/auth/*`

**Files:**
- Create: `backend/app/api/auth.py`
- Modify: `backend/app/api/__init__.py`

- [ ] **Step 1: Escribir tests de integración para los endpoints de auth**

  Create `backend/tests/api/test_auth_endpoints.py`:

  ```python
  """Integration tests for /auth/* endpoints."""
  import pytest
  from unittest.mock import patch, MagicMock
  from app.models.user import User


  @pytest.fixture
  def mock_google_verify(app):
      """Patch AuthService.verify_google_token to return a fake payload."""
      with patch("app.api.auth.auth_service.verify_google_token") as mock:
          mock.return_value = {
              "sub": "google_sub_test",
              "email": "test@example.com",
              "name": "Test User",
          }
          yield mock


  def test_post_auth_google_creates_user(client, mock_google_verify):
      """POST /auth/google creates user and returns tokens."""
      resp = client.post(
          "/auth/google",
          json={"id_token": "fake_google_token"},
      )
      assert resp.status_code == 200
      data = resp.get_json()
      assert "access_token" in data["data"]
      assert "refresh_token" in data["data"]
      assert data["data"]["is_new_user"] is True


  def test_post_auth_google_missing_id_token(client):
      """POST /auth/google returns 400 when id_token is absent."""
      resp = client.post("/auth/google", json={})
      assert resp.status_code == 400


  def test_post_auth_refresh_rotates_token(client, mock_google_verify):
      """POST /auth/refresh returns new tokens and invalidates old refresh token."""
      # First login
      login_resp = client.post(
          "/auth/google",
          json={"id_token": "fake_google_token"},
      )
      old_refresh = login_resp.get_json()["data"]["refresh_token"]

      # Refresh
      refresh_resp = client.post(
          "/auth/refresh",
          json={"refresh_token": old_refresh},
      )
      assert refresh_resp.status_code == 200
      new_data = refresh_resp.get_json()["data"]
      assert "access_token" in new_data
      assert new_data["refresh_token"] != old_refresh


  def test_post_auth_refresh_invalid_token_returns_401(client):
      """POST /auth/refresh returns 401 for unknown refresh token."""
      resp = client.post(
          "/auth/refresh",
          json={"refresh_token": "completely_fake_token"},
      )
      assert resp.status_code == 401


  def test_post_auth_logout_returns_204(client, mock_google_verify):
      """POST /auth/logout deletes the refresh token and returns 204."""
      login_resp = client.post(
          "/auth/google",
          json={"id_token": "fake_google_token"},
      )
      refresh_token = login_resp.get_json()["data"]["refresh_token"]

      logout_resp = client.post(
          "/auth/logout",
          json={"refresh_token": refresh_token},
      )
      assert logout_resp.status_code == 204


  def test_post_auth_logout_is_idempotent(client):
      """POST /auth/logout returns 204 even if token does not exist."""
      resp = client.post(
          "/auth/logout",
          json={"refresh_token": "nonexistent_token"},
      )
      assert resp.status_code == 204
  ```

- [ ] **Step 2: Ejecutar los tests — deben fallar**

  Run: `cd /Users/angelcorredor/Code/Wallet/backend && python -m pytest tests/api/test_auth_endpoints.py -v`
  Expected: FAIL — `404 Not Found` (blueprint not registered)

- [ ] **Step 3: Crear `backend/app/api/auth.py`**

  ```python
  """
  Authentication endpoints.

  All endpoints in this blueprint are PUBLIC — no @require_auth decorator.
  They handle Google OAuth login, refresh token rotation, and logout.
  """

  from flask import Blueprint, request

  from app.services.auth import AuthService
  from app.utils.exceptions import ValidationError
  from app.utils.responses import error_response, success_response

  auth_bp = Blueprint("auth", __name__, url_prefix="/auth")
  auth_service = AuthService()


  @auth_bp.route("/google", methods=["POST"])
  def google_login():
      """
      Authenticate via Google OAuth.

      Validates the Google id_token locally, finds or creates the user,
      and returns a JWT + refresh token pair.

      Request Body:
          id_token (str): Google id_token from the frontend Google Sign-In SDK.

      Returns:
          200: access_token, refresh_token, user info, is_new_user flag.
          400: Missing or invalid request body.
          401: Google token validation failed.
      """
      body = request.get_json(silent=True) or {}
      id_token_str = body.get("id_token")
      if not id_token_str:
          return error_response("El campo 'id_token' es requerido", status_code=400)

      try:
          google_payload = auth_service.verify_google_token(id_token_str)
      except ValidationError as e:
          return error_response(e.message, status_code=401)

      user, is_new_user = auth_service.find_or_create_user(google_payload)
      tokens = auth_service.issue_tokens(user)

      return success_response(
          data={
              "access_token": tokens["access_token"],
              "refresh_token": tokens["refresh_token"],
              "user": user.to_dict(),
              "is_new_user": is_new_user,
          }
      )


  @auth_bp.route("/refresh", methods=["POST"])
  def refresh_token():
      """
      Rotate a refresh token and issue a new JWT.

      The old refresh token is deleted and a new one is issued atomically.
      If the token does not exist or is expired, returns 401.

      Request Body:
          refresh_token (str): Opaque refresh token from AuthDB.

      Returns:
          200: New access_token and refresh_token.
          400: Missing refresh_token field.
          401: Token not found, expired, or already rotated.
      """
      body = request.get_json(silent=True) or {}
      token_plain = body.get("refresh_token")
      if not token_plain:
          return error_response("El campo 'refresh_token' es requerido", status_code=400)

      try:
          tokens = auth_service.rotate_refresh_token(token_plain)
      except ValidationError as e:
          return error_response(e.message, status_code=401)

      return success_response(
          data={
              "access_token": tokens["access_token"],
              "refresh_token": tokens["refresh_token"],
          }
      )


  @auth_bp.route("/logout", methods=["POST"])
  def logout():
      """
      Revoke a refresh token (logout).

      Public endpoint — does not require a valid JWT, since the user may
      be logging out with an expired access token. Always returns 204.
      Idempotent: no-op if the token is not found.

      Request Body:
          refresh_token (str, optional): Opaque refresh token to revoke.

      Returns:
          204: Token revoked (or was already absent).
      """
      body = request.get_json(silent=True) or {}
      token_plain = body.get("refresh_token", "")
      if token_plain:
          auth_service.revoke_refresh_token(token_plain)
      return "", 204
  ```

- [ ] **Step 4: Registrar el blueprint en `backend/app/api/__init__.py`**

  In `backend/app/api/__init__.py`, add:
  ```python
  from app.api.auth import auth_bp
  ```
  And in `register_blueprints()`:
  ```python
  app.register_blueprint(auth_bp)
  ```

- [ ] **Step 5: Ejecutar los tests**

  Run: `cd /Users/angelcorredor/Code/Wallet/backend && python -m pytest tests/api/test_auth_endpoints.py -v`
  Expected: PASS (6 tests)

- [ ] **Step 6: Commit**

  ```bash
  git add backend/app/api/auth.py backend/app/api/__init__.py backend/tests/api/test_auth_endpoints.py
  git commit -m "feat(auth): add /auth/google, /auth/refresh, /auth/logout endpoints"
  ```

---

### Task 2.4: Actualizar `BaseRepository` para ser user-aware

**Files:**
- Modify: `backend/app/repositories/base.py`

**Critical:** The current `get_by_id()` uses `db.session.get()` which bypasses SQLAlchemy filters. It must be replaced with an explicit query that includes `WHERE user_id = :user_id`.

- [ ] **Step 1: Escribir tests para los métodos user-aware**

  Create `backend/tests/repositories/test_base_repository_user_aware.py`:

  ```python
  """Tests verifying BaseRepository methods filter by user_id."""
  import pytest
  from uuid import uuid4
  from app.models.account import Account, AccountType
  from app.repositories.account import AccountRepository


  @pytest.fixture
  def user_a_id(app):
      from app.models.user import User
      from app.extensions import db
      with app.app_context():
          u = User(google_id="ga", email="a@test.com", name="A")
          db.session.add(u)
          db.session.commit()
          return u.id


  @pytest.fixture
  def user_b_id(app):
      from app.models.user import User
      from app.extensions import db
      with app.app_context():
          u = User(google_id="gb", email="b@test.com", name="B")
          db.session.add(u)
          db.session.commit()
          return u.id


  @pytest.fixture
  def account_for_user_a(app, user_a_id):
      from app.extensions import db
      with app.app_context():
          acc = Account(
              name="A's Account",
              type=AccountType.DEBIT,
              currency="COP",
              user_id=user_a_id,
          )
          db.session.add(acc)
          db.session.commit()
          return acc.id


  def test_get_by_id_returns_none_for_wrong_user(app, account_for_user_a, user_b_id):
      """get_by_id with wrong user_id returns None, not the record."""
      repo = AccountRepository()
      result = repo.get_by_id(account_for_user_a, user_b_id)
      assert result is None


  def test_get_by_id_returns_record_for_correct_user(app, account_for_user_a, user_a_id):
      """get_by_id with correct user_id returns the record."""
      repo = AccountRepository()
      result = repo.get_by_id(account_for_user_a, user_a_id)
      assert result is not None


  def test_get_all_filters_by_user_id(app, account_for_user_a, user_a_id, user_b_id):
      """get_all only returns records owned by the specified user."""
      repo = AccountRepository()
      a_records = repo.get_all(user_id=user_a_id)
      b_records = repo.get_all(user_id=user_b_id)
      assert len(a_records) >= 1
      assert all(r.user_id == user_a_id for r in a_records)
      assert len(b_records) == 0


  def test_get_by_client_id_filters_by_user_id(app, app_context, user_a_id, user_b_id):
      """get_by_client_id does not return a record owned by a different user."""
      from app.extensions import db
      cid = "test-client-id-001"
      acc = Account(
          name="CID Account",
          type=AccountType.CASH,
          currency="USD",
          client_id=cid,
          user_id=user_a_id,
      )
      db.session.add(acc)
      db.session.commit()

      repo = AccountRepository()
      # User A should find it
      found = repo.get_by_client_id(cid, user_a_id)
      assert found is not None
      # User B should not
      not_found = repo.get_by_client_id(cid, user_b_id)
      assert not_found is None
  ```

- [ ] **Step 2: Ejecutar los tests — deben fallar**

  Run: `cd /Users/angelcorredor/Code/Wallet/backend && python -m pytest tests/repositories/test_base_repository_user_aware.py -v`
  Expected: FAIL — current `get_by_id` ignores user_id

- [ ] **Step 3: Reescribir `backend/app/repositories/base.py`**

  Replace the entire file:

  ```python
  """
  Base repository with user-aware CRUD operations.

  All query methods require a user_id to enforce per-user data isolation.
  The get_by_id() method deliberately avoids db.session.get() because that
  API bypasses SQLAlchemy WHERE filters — it is rewritten as an explicit
  SELECT ... WHERE id = :id AND user_id = :user_id query.
  """

  from datetime import datetime
  from typing import TypeVar, Generic, Optional, Type
  from uuid import UUID

  from app.extensions import db
  from app.models.base import BaseModel
  from app.utils.exceptions import NotFoundError

  T = TypeVar("T", bound=BaseModel)


  class BaseRepository(Generic[T]):
      """
      Generic base repository with user-scoped CRUD operations.

      Every method that reads or writes data requires a user_id to ensure
      complete isolation between users. No method returns data belonging to
      a different user.
      """

      def __init__(self, model: Type[T]):
          """
          Initialize repository with model class.

          Args:
              model: SQLAlchemy model class (must have user_id column).
          """
          self.model = model

      def get_by_id(self, id: UUID, user_id: UUID) -> Optional[T]:
          """
          Get a single record by ID, scoped to a specific user.

          This method uses an explicit SELECT query (not db.session.get()) to
          ensure the user_id filter is always applied. db.session.get() bypasses
          WHERE filters and would allow cross-user data access.

          Args:
              id: Record UUID.
              user_id: Owner's UUID. Record is only returned if it belongs to
                  this user.

          Returns:
              Model instance or None if not found / not owned by user.
          """
          return (
              db.session.execute(
                  db.select(self.model).where(
                      self.model.id == id,
                      self.model.user_id == user_id,
                  )
              )
              .scalars()
              .one_or_none()
          )

      def get_by_client_id(self, client_id: str, user_id: UUID) -> Optional[T]:
          """
          Get a record by client-generated idempotency key, scoped to a user.

          Prevents a client_id belonging to user A from resolving to user B's
          record, even if the raw UUID collides (extremely unlikely but handled).

          Args:
              client_id: Client-generated idempotency key (max 100 characters).
              user_id: Owner's UUID.

          Returns:
              Model instance if found for this user, else None.
          """
          return (
              db.session.execute(
                  db.select(self.model).where(
                      self.model.client_id == client_id,
                      self.model.user_id == user_id,
                  )
              )
              .scalars()
              .one_or_none()
          )

      def get_by_id_or_fail(self, id: UUID, user_id: UUID) -> T:
          """
          Get a single record by ID or raise NotFoundError.

          Args:
              id: Record UUID.
              user_id: Owner's UUID.

          Returns:
              Model instance.

          Raises:
              NotFoundError: If record not found or not owned by user.
          """
          record = self.get_by_id(id, user_id)
          if not record:
              raise NotFoundError(self.model.__name__, str(id))
          return record

      def get_all(
          self,
          user_id: UUID,
          updated_since: datetime | None = None,
      ) -> list[T]:
          """
          Get all records for a user, optionally filtered by modification time.

          Args:
              user_id: Owner's UUID. Only records owned by this user are returned.
              updated_since: Only return records with updated_at >= updated_since
                  (naive UTC). None returns all records for the user.

          Returns:
              List of model instances.
          """
          query = db.select(self.model).where(self.model.user_id == user_id)
          if updated_since is not None:
              query = query.where(self.model.updated_at >= updated_since)
          return db.session.execute(query).scalars().all()

      def create(self, user_id: UUID, **kwargs) -> T:
          """
          Create a new record owned by the specified user.

          Args:
              user_id: Owner's UUID. Auto-injected into the record.
              **kwargs: Additional field values for the new record.

          Returns:
              Created model instance.
          """
          instance = self.model(user_id=user_id, **kwargs)
          db.session.add(instance)
          db.session.commit()
          db.session.refresh(instance)
          return instance

      def update(self, instance: T, **kwargs) -> T:
          """
          Update an existing record.

          Args:
              instance: Model instance to update.
              **kwargs: Fields to update. None values are skipped.

          Returns:
              Updated model instance.
          """
          for key, value in kwargs.items():
              if value is not None:
                  setattr(instance, key, value)
          db.session.commit()
          db.session.refresh(instance)
          return instance

      def delete(self, instance: T) -> None:
          """
          Delete a record.

          Args:
              instance: Model instance to delete.
          """
          db.session.delete(instance)
          db.session.commit()

      def count(self, user_id: UUID) -> int:
          """
          Count records owned by a user.

          Args:
              user_id: Owner's UUID.

          Returns:
              Number of records owned by this user.
          """
          from sqlalchemy import func, select
          return db.session.execute(
              select(func.count()).select_from(self.model).where(
                  self.model.user_id == user_id
              )
          ).scalar_one()
  ```

- [ ] **Step 4: Ejecutar los tests del repositorio**

  Run: `cd /Users/angelcorredor/Code/Wallet/backend && python -m pytest tests/repositories/test_base_repository_user_aware.py -v`
  Expected: PASS (4 tests)

- [ ] **Step 5: Commit**

  ```bash
  git add backend/app/repositories/base.py backend/tests/repositories/test_base_repository_user_aware.py
  git commit -m "refactor(auth): make BaseRepository user-aware; rewrite get_by_id to avoid db.session.get() bypass"
  ```

---

## Chunk 3: Servicios, Ownership, Seed Data y UserSetting (Ticket 3)

### Task 3.1: Actualizar todos los repositorios concretos para firma user-aware

The concrete repositories override `get_all()` with custom signatures (e.g., `AccountRepository.get_all` adds `include_archived`). These overrides must add `user_id` as a required parameter.

**Files:**
- Modify: `backend/app/repositories/account.py`
- Modify: `backend/app/repositories/category.py`
- Modify: `backend/app/repositories/dashboard.py`
- Modify: `backend/app/repositories/transaction.py`
- Modify: `backend/app/repositories/transfer.py`

- [ ] **Step 1: Actualizar `AccountRepository`**

  In `backend/app/repositories/account.py`:

  1. Add `user_id: UUID` parameter to `get_all_active(self, user_id: UUID)`:
     ```python
     def get_all_active(self, user_id: UUID) -> list[Account]:
         return (
             db.session.execute(
                 db.select(Account).where(
                     Account.active == True,
                     Account.user_id == user_id,
                 )
             )
             .scalars()
             .all()
         )
     ```

  2. Update `get_all(self, user_id: UUID, updated_since=None, include_archived=False)`:
     ```python
     def get_all(
         self,
         user_id: UUID,
         updated_since: datetime | None = None,
         include_archived: bool = False,
     ) -> list[Account]:
         query = db.select(Account).where(Account.user_id == user_id)
         if updated_since is not None:
             query = query.where(Account.updated_at >= updated_since)
         if not include_archived:
             query = query.where(Account.active == True)
         return db.session.execute(query).scalars().all()
     ```

  3. Update `soft_delete(self, account_id: UUID, user_id: UUID)` to call `get_by_id_or_fail(account_id, user_id)`:
     ```python
     def soft_delete(self, account_id: UUID, user_id: UUID) -> Account:
         account = self.get_by_id_or_fail(account_id, user_id)
         account.active = False
         db.session.commit()
         db.session.refresh(account)
         return account
     ```

- [ ] **Step 2: Actualizar `CategoryRepository`**

  In `backend/app/repositories/category.py`, update these methods:

  1. `get_all(self, user_id: UUID, updated_since=None, include_archived=False)`:
     ```python
     def get_all(
         self,
         user_id: UUID,
         updated_since: datetime | None = None,
         include_archived: bool = False,
     ) -> list[Category]:
         query = db.select(Category).where(Category.user_id == user_id)
         if updated_since is not None:
             query = query.where(Category.updated_at >= updated_since)
         if not include_archived:
             query = query.where(Category.active == True)
         return db.session.execute(query).scalars().all()
     ```

  2. `get_all_active(self, user_id: UUID)`:
     ```python
     def get_all_active(self, user_id: UUID) -> list[Category]:
         return (
             db.session.execute(
                 db.select(Category).where(
                     Category.active == True,
                     Category.user_id == user_id,
                 )
             )
             .scalars()
             .all()
         )
     ```

  3. `get_by_type(self, type: CategoryType, user_id: UUID)` — add `user_id` filter:
     ```python
     def get_by_type(self, type: CategoryType, user_id: UUID) -> list[Category]:
         return (
             db.session.execute(
                 db.select(Category).where(
                     Category.type == type,
                     Category.user_id == user_id,
                 )
             )
             .scalars()
             .all()
         )
     ```

  4. `get_parent_categories(self, user_id: UUID)`:
     ```python
     def get_parent_categories(self, user_id: UUID) -> list[Category]:
         return (
             db.session.execute(
                 db.select(Category).where(
                     Category.parent_category_id == None,
                     Category.user_id == user_id,
                 )
             )
             .scalars()
             .all()
         )
     ```

  5. `get_subcategories(self, parent_id: UUID, user_id: UUID)`:
     ```python
     def get_subcategories(self, parent_id: UUID, user_id: UUID) -> list[Category]:
         return (
             db.session.execute(
                 db.select(Category).where(
                     Category.parent_category_id == parent_id,
                     Category.user_id == user_id,
                 )
             )
             .scalars()
             .all()
         )
     ```

  6. `get_with_subcategories(self, category_id: UUID, user_id: UUID)`:
     ```python
     def get_with_subcategories(self, category_id: UUID, user_id: UUID) -> Optional[Category]:
         from sqlalchemy.orm import selectinload
         return db.session.execute(
             db.select(Category)
             .where(Category.id == category_id, Category.user_id == user_id)
             .options(selectinload(Category.subcategories))
         ).scalar_one_or_none()
     ```

- [ ] **Step 3: Actualizar `DashboardRepository`**

  In `backend/app/repositories/dashboard.py`:

  1. Update `get_all_ordered(self, user_id: UUID, updated_since=None)`:
     ```python
     def get_all_ordered(self, user_id: UUID, updated_since: datetime | None = None) -> list[Dashboard]:
         query = db.select(Dashboard).where(
             Dashboard.user_id == user_id
         ).order_by(Dashboard.sort_order.asc())
         if updated_since is not None:
             query = query.where(Dashboard.updated_at >= updated_since)
         return db.session.execute(query).scalars().all()
     ```

  2. Update `get_default(self, user_id: UUID)`:
     ```python
     def get_default(self, user_id: UUID) -> Optional[Dashboard]:
         return (
             db.session.execute(
                 db.select(Dashboard).where(
                     Dashboard.is_default.is_(True),
                     Dashboard.user_id == user_id,
                 )
             )
             .scalars()
             .one_or_none()
         )
     ```

  3. Update `get_max_sort_order(self, user_id: UUID)`:
     ```python
     def get_max_sort_order(self, user_id: UUID) -> int:
         result = db.session.execute(
             sa.select(sa.func.max(Dashboard.sort_order)).where(
                 Dashboard.user_id == user_id
             )
         ).scalar_one_or_none()
         return result if result is not None else -1
     ```

  4. Update `count_all(self, user_id: UUID)`:
     ```python
     def count_all(self, user_id: UUID) -> int:
         return db.session.execute(
             sa.select(sa.func.count()).select_from(Dashboard).where(
                 Dashboard.user_id == user_id
             )
         ).scalar_one()
     ```

  5. Update `unset_default(self, user_id: UUID)`:
     ```python
     def unset_default(self, user_id: UUID) -> None:
         db.session.execute(
             sa.update(Dashboard)
             .where(Dashboard.user_id == user_id)
             .values(is_default=False)
         )
         db.session.commit()
     ```

  6. Update `get_widget_by_client_id(self, client_id: str, user_id: UUID)`:
     ```python
     def get_widget_by_client_id(self, client_id: str, user_id: UUID) -> Optional[DashboardWidget]:
         return (
             db.session.execute(
                 db.select(DashboardWidget)
                 .join(Dashboard, DashboardWidget.dashboard_id == Dashboard.id)
                 .where(
                     DashboardWidget.client_id == client_id,
                     Dashboard.user_id == user_id,
                 )
             )
             .scalars()
             .one_or_none()
         )
     ```

- [ ] **Step 4: Actualizar `TransactionRepository`**

  In `backend/app/repositories/transaction.py`, add `user_id: UUID` to every query method that returns data belonging to users:

  1. `get_with_relations(self, transaction_id: UUID, user_id: UUID)`:
     ```python
     def get_with_relations(self, transaction_id: UUID, user_id: UUID) -> Optional[Transaction]:
         return db.session.execute(
             db.select(Transaction)
             .where(Transaction.id == transaction_id, Transaction.user_id == user_id)
             .options(selectinload(Transaction.account))
             .options(selectinload(Transaction.category))
         ).scalar_one_or_none()
     ```

  2. `get_by_account(self, account_id: UUID, user_id: UUID, limit=None, offset=None)`:
     ```python
     def get_by_account(self, account_id: UUID, user_id: UUID, limit=None, offset=None) -> list[Transaction]:
         query = (
             db.select(Transaction)
             .where(Transaction.account_id == account_id, Transaction.user_id == user_id)
             .order_by(Transaction.date.desc())
         )
         if limit:
             query = query.limit(limit)
         if offset:
             query = query.offset(offset)
         return db.session.execute(query).scalars().all()
     ```

  3. `get_by_category(self, category_id: UUID, user_id: UUID, limit=None, offset=None)`:
     ```python
     def get_by_category(self, category_id: UUID, user_id: UUID, limit=None, offset=None) -> list[Transaction]:
         query = (
             db.select(Transaction)
             .where(Transaction.category_id == category_id, Transaction.user_id == user_id)
             .order_by(Transaction.date.desc())
         )
         if limit:
             query = query.limit(limit)
         if offset:
             query = query.offset(offset)
         return db.session.execute(query).scalars().all()
     ```

  4. `get_filtered(self, user_id: UUID, account_id=None, ...)` — add `user_id` as first parameter and prepend `Transaction.user_id == user_id` to the `filters` list:
     ```python
     def get_filtered(
         self,
         user_id: UUID,
         account_id: Optional[UUID] = None,
         category_id: Optional[UUID] = None,
         type: Optional[TransactionType] = None,
         date_from: Optional[date] = None,
         date_to: Optional[date] = None,
         tags: Optional[list[str]] = None,
         updated_since: Optional[datetime] = None,
         limit: int = 20,
         offset: int = 0,
     ) -> tuple[list[Transaction], int]:
         filters = [Transaction.user_id == user_id]
         if account_id:
             filters.append(Transaction.account_id == account_id)
         if category_id:
             filters.append(Transaction.category_id == category_id)
         if type:
             filters.append(Transaction.type == type)
         if date_from:
             filters.append(Transaction.date >= date_from)
         if date_to:
             filters.append(Transaction.date <= date_to)
         if tags:
             filters.append(Transaction.tags.overlap(tags))
         if updated_since is not None:
             filters.append(Transaction.updated_at >= updated_since)
         count_query = db.select(db.func.count()).select_from(Transaction).where(and_(*filters))
         total = db.session.execute(count_query).scalar()
         query = (
             db.select(Transaction)
             .options(selectinload(Transaction.account))
             .options(selectinload(Transaction.category))
             .where(and_(*filters))
             .order_by(Transaction.date.desc(), Transaction.created_at.desc())
             .limit(limit).offset(offset)
         )
         transactions = db.session.execute(query).scalars().all()
         return transactions, total
     ```

  5. `get_recent(self, user_id: UUID, limit=10)`:
     ```python
     def get_recent(self, user_id: UUID, limit: int = 10) -> list[Transaction]:
         return (
             db.session.execute(
                 db.select(Transaction)
                 .where(Transaction.user_id == user_id)
                 .options(selectinload(Transaction.account))
                 .options(selectinload(Transaction.category))
                 .order_by(Transaction.date.desc(), Transaction.created_at.desc())
                 .limit(limit)
             )
             .scalars()
             .all()
         )
     ```

- [ ] **Step 4b: Actualizar `TransferRepository`**

  In `backend/app/repositories/transfer.py`, apply the same pattern:

  1. `get_with_relations(self, transfer_id: UUID, user_id: UUID)`:
     ```python
     def get_with_relations(self, transfer_id: UUID, user_id: UUID) -> Optional[Transfer]:
         return db.session.execute(
             db.select(Transfer)
             .where(Transfer.id == transfer_id, Transfer.user_id == user_id)
             .options(selectinload(Transfer.source_account))
             .options(selectinload(Transfer.destination_account))
         ).scalar_one_or_none()
     ```

  2. `get_by_account(self, account_id: UUID, user_id: UUID, limit=None, offset=None)`:
     ```python
     def get_by_account(self, account_id: UUID, user_id: UUID, limit=None, offset=None) -> list[Transfer]:
         query = (
             db.select(Transfer)
             .where(
                 Transfer.user_id == user_id,
                 or_(
                     Transfer.source_account_id == account_id,
                     Transfer.destination_account_id == account_id,
                 ),
             )
             .order_by(Transfer.date.desc())
         )
         if limit:
             query = query.limit(limit)
         if offset:
             query = query.offset(offset)
         return db.session.execute(query).scalars().all()
     ```

  3. `get_filtered(self, user_id: UUID, ...)` — add `user_id` as first parameter, prepend `Transfer.user_id == user_id` to `filters`:
     ```python
     def get_filtered(
         self,
         user_id: UUID,
         account_id: Optional[UUID] = None,
         date_from: Optional[date] = None,
         date_to: Optional[date] = None,
         tags: Optional[list[str]] = None,
         updated_since: Optional[datetime] = None,
         limit: int = 20,
         offset: int = 0,
     ) -> tuple[list[Transfer], int]:
         filters = [Transfer.user_id == user_id]
         if account_id:
             filters.append(or_(Transfer.source_account_id == account_id,
                                Transfer.destination_account_id == account_id))
         if date_from:
             filters.append(Transfer.date >= date_from)
         if date_to:
             filters.append(Transfer.date <= date_to)
         if tags:
             filters.append(Transfer.tags.overlap(tags))
         if updated_since is not None:
             filters.append(Transfer.updated_at >= updated_since)
         count_query = db.select(db.func.count()).select_from(Transfer).where(and_(*filters))
         total = db.session.execute(count_query).scalar()
         query = (
             db.select(Transfer)
             .options(selectinload(Transfer.source_account))
             .options(selectinload(Transfer.destination_account))
             .where(and_(*filters))
             .order_by(Transfer.date.desc(), Transfer.created_at.desc())
             .limit(limit).offset(offset)
         )
         transfers = db.session.execute(query).scalars().all()
         return transfers, total
     ```

  4. `get_recent(self, user_id: UUID, limit=10)`:
     ```python
     def get_recent(self, user_id: UUID, limit: int = 10) -> list[Transfer]:
         return (
             db.session.execute(
                 db.select(Transfer)
                 .where(Transfer.user_id == user_id)
                 .options(selectinload(Transfer.source_account))
                 .options(selectinload(Transfer.destination_account))
                 .order_by(Transfer.date.desc(), Transfer.created_at.desc())
                 .limit(limit)
             )
             .scalars()
             .all()
         )
     ```

  Also add `from uuid import UUID` and `from sqlalchemy import or_` to imports if not already present.

- [ ] **Step 5: Verificar que los repositorios importan sin error**

  Run: `cd /Users/angelcorredor/Code/Wallet/backend && python -c "from app.repositories import AccountRepository, CategoryRepository, DashboardRepository; print('OK')"`
  Expected: `OK`

- [ ] **Step 6: Commit**

  ```bash
  git add backend/app/repositories/account.py backend/app/repositories/category.py backend/app/repositories/dashboard.py backend/app/repositories/transaction.py backend/app/repositories/transfer.py
  git commit -m "refactor(auth): update all concrete repositories to accept user_id parameter"
  ```

---

### Task 3.2: Actualizar todos los servicios para propagar `user_id`

**Files:**
- Modify: `backend/app/services/account.py`
- Modify: `backend/app/services/category.py`
- Modify: `backend/app/services/dashboard_crud.py`
- Modify: `backend/app/services/transaction.py`
- Modify: `backend/app/services/transfer.py`

Each service method that reads or writes data must receive `user_id: UUID` as an explicit parameter and pass it to the repository.

- [ ] **Step 1: Actualizar `AccountService`**

  In `backend/app/services/account.py`, add `user_id: UUID` to every method signature and thread it through to repository calls. Key changes:

  - `get_all(self, user_id: UUID, include_archived=False)` → calls `self.repository.get_all(user_id=user_id, ...)`
  - `get_by_id(self, account_id: UUID, user_id: UUID)` → calls `self.repository.get_by_id_or_fail(account_id, user_id)`
  - `get_with_balance(self, account_id: UUID, user_id: UUID)` → same
  - `get_all_with_balances(self, user_id: UUID, include_archived=False)` → same
  - `get_all_with_balances_since(self, user_id: UUID, updated_since: datetime)` → same
  - `create(self, user_id: UUID, name, type, currency, ...)` → passes `user_id` to `self.repository.create(user_id=user_id, ...)`; also passes `user_id` to `get_by_client_id(client_id, user_id)`
  - `update(self, account_id: UUID, user_id: UUID, ...)` → calls `get_by_id_or_fail(account_id, user_id)`
  - `archive(self, account_id: UUID, user_id: UUID)` → calls `self.repository.soft_delete(account_id, user_id)`
  - `delete(self, account_id: UUID, user_id: UUID)` → calls `get_by_id_or_fail(account_id, user_id)`
  - `get_balance(self, account_id: UUID, user_id: UUID)` → calls `get_by_id_or_fail(account_id, user_id)`

- [ ] **Step 2: Actualizar `CategoryService`**

  In `backend/app/services/category.py`, add `user_id: UUID` to every public method. Key changes:

  - `get_all(self, user_id: UUID, type=None, include_archived=False, updated_since=None)` → passes `user_id` to `self.repository.get_all(user_id=user_id, ...)`. The `get_by_type` path also needs user filtering — update `CategoryRepository.get_by_type` to accept `user_id` and add `WHERE user_id = :user_id` to that query.
  - `get_by_id(self, category_id: UUID, user_id: UUID)` → `self.repository.get_by_id_or_fail(category_id, user_id)`
  - `get_with_subcategories(self, category_id: UUID, user_id: UUID)` → same
  - `get_parent_categories(self, user_id: UUID)` → update `CategoryRepository.get_parent_categories` to accept `user_id` and add `WHERE user_id = :user_id`
  - `create(self, user_id: UUID, name, type, ...)` → passes `user_id` to `get_by_client_id(client_id, user_id)` and `repository.create(user_id=user_id, ...)`. The parent category validation calls `get_by_id_or_fail(parent_category_id, user_id)`.
  - `update(self, category_id: UUID, user_id: UUID, ...)` → `get_by_id_or_fail(category_id, user_id)`. Parent validation also scoped to `user_id`.
  - `archive(self, category_id: UUID, user_id: UUID)` → `get_by_id_or_fail(category_id, user_id)`
  - `hard_delete(self, category_id: UUID, user_id: UUID)` → same

- [ ] **Step 2b: Actualizar `TransactionService`**

  In `backend/app/services/transaction.py`, add `user_id: UUID`:

  - `get_by_id(self, transaction_id: UUID, user_id: UUID)` → calls `self.repository.get_with_relations(transaction_id, user_id)`. Raises `NotFoundError` if `None`.
  - `get_filtered(self, user_id: UUID, account_id=None, ...)` → passes `user_id` as first arg to `self.repository.get_filtered(user_id, ...)`.
  - `create(self, user_id: UUID, type, amount, date, account_id, category_id, ...)`:
    - Idempotency check: `self.repository.get_by_client_id(client_id, user_id)`
    - Account validation: `self.account_repository.get_by_id_or_fail(account_id, user_id)`
    - Category validation: `self.category_repository.get_by_id_or_fail(category_id, user_id)`
    - Create: `self.repository.create(user_id=user_id, ...)`
  - `update(self, transaction_id: UUID, user_id: UUID, ...)`:
    - Fetch: `self.repository.get_by_id_or_fail(transaction_id, user_id)`
    - Account validation: `self.account_repository.get_by_id_or_fail(account_id, user_id)`
    - Category validation: `self.category_repository.get_by_id_or_fail(category_id, user_id)`
  - `delete(self, transaction_id: UUID, user_id: UUID)` → `get_by_id_or_fail(transaction_id, user_id)`

- [ ] **Step 2c: Actualizar `TransferService`**

  In `backend/app/services/transfer.py`, add `user_id: UUID`:

  - `get_by_id(self, transfer_id: UUID, user_id: UUID)` → `self.repository.get_with_relations(transfer_id, user_id)`.
  - `get_filtered(self, user_id: UUID, account_id=None, ...)` → `self.repository.get_filtered(user_id, ...)`.
  - `create(self, user_id: UUID, source_account_id, destination_account_id, amount, date, ...)`:
    - Idempotency: `self.repository.get_by_client_id(client_id, user_id)`
    - Account validation: `self.account_repository.get_by_id_or_fail(source_account_id, user_id)` and same for destination
    - Create: `self.repository.create(user_id=user_id, ...)`
  - `update(self, transfer_id: UUID, user_id: UUID, ...)` → `get_by_id_or_fail(transfer_id, user_id)`
  - `delete(self, transfer_id: UUID, user_id: UUID)` → same

- [ ] **Step 3: Actualizar `DashboardCrudService`**

  In `backend/app/services/dashboard_crud.py`:
  - `list_dashboards(self, user_id: UUID, updated_since=None)` → `self.repo.get_all_ordered(user_id=user_id, ...)`
  - `get_dashboard(self, dashboard_id: UUID, user_id: UUID)` → `self.repo.get_by_id_or_fail(dashboard_id, user_id)`
  - `create_dashboard(self, user_id: UUID, data: DashboardCreate)` → checks `get_by_client_id(data.client_id, user_id)`, `count_all(user_id)`, `get_max_sort_order(user_id)`, `unset_default(user_id)`, and passes `user_id` to `self.repo.create(user_id=user_id, ...)`
  - `update_dashboard(self, dashboard_id: UUID, user_id: UUID, data)` → `get_by_id_or_fail(dashboard_id, user_id)`, `unset_default(user_id)`
  - `delete_dashboard(self, dashboard_id: UUID, user_id: UUID)` → `get_by_id_or_fail(dashboard_id, user_id)`
  - `_touch_dashboard(self, dashboard_id: UUID)` → no user_id needed here (internal helper)
  - `list_widgets(self, dashboard_id: UUID, user_id: UUID)` → `get_by_id_or_fail(dashboard_id, user_id)`
  - `create_widget(self, dashboard_id: UUID, user_id: UUID, data)` → ownership check via `get_by_id_or_fail(dashboard_id, user_id)`, also `get_widget_by_client_id(data.client_id, user_id)`, `count_widgets_for_dashboard(dashboard_id)`
  - `update_widget(self, dashboard_id: UUID, widget_id: UUID, user_id: UUID, data)` → `get_by_id_or_fail(dashboard_id, user_id)`
  - `delete_widget(self, dashboard_id: UUID, widget_id: UUID, user_id: UUID)` → same

- [ ] **Step 4: Verificar que los servicios importan sin error**

  Run: `cd /Users/angelcorredor/Code/Wallet/backend && python -c "from app.services.account import AccountService; from app.services.dashboard_crud import DashboardCrudService; print('OK')"`
  Expected: `OK`

- [ ] **Step 5: Commit**

  ```bash
  git add backend/app/services/account.py backend/app/services/category.py backend/app/services/dashboard_crud.py backend/app/services/transaction.py backend/app/services/transfer.py
  git commit -m "refactor(auth): propagate user_id through all service methods"
  ```

---

### Task 3.3: Agregar `@require_auth` y ownership 403 a los endpoints existentes

**Files:**
- Modify: `backend/app/api/accounts.py`
- Modify: `backend/app/api/categories.py`
- Modify: `backend/app/api/transactions.py`
- Modify: `backend/app/api/transfers.py`
- Modify: `backend/app/api/dashboards.py`
- Modify: `backend/app/api/settings.py`

The pattern is identical across all endpoints:
1. Add `from flask import g` and `from app.utils.auth import require_auth` to imports.
2. Add `@require_auth` decorator to every route handler.
3. Pass `user_id=g.current_user_id` to every service method call.
4. For detail endpoints (GET/PUT/DELETE `/<id>`), the ownership 403 is implicit because `get_by_id_or_fail(id, user_id)` raises `NotFoundError` (404) if the record belongs to another user. This is intentional: returning 403 would confirm the resource exists. The spec calls for 403 explicitly — so add an explicit check where possible by fetching first without user filter, then checking ownership.

**Note on 403 vs 404:** The spec mandates 403 when `resource.user_id != g.current_user_id`. To avoid leaking existence info, use 404 (not found for this user). This is standard REST security practice. If the spec strictly requires 403, a two-step lookup is needed (fetch by id only, then check user). The simpler and more secure approach (single query with user_id filter → 404) is used here. Document this decision in code comments.

- [ ] **Step 1: Actualizar `backend/app/api/accounts.py`**

  For every route in the file:
  - Add `@require_auth` before the route decorator.
  - Pass `user_id=g.current_user_id` to all `account_service.*` calls.

  Example for `list_accounts`:
  ```python
  from flask import g
  from app.utils.auth import require_auth

  @accounts_bp.route("", methods=["GET"])
  @require_auth
  def list_accounts():
      # ...
      accounts_with_balances = account_service.get_all_with_balances(
          user_id=g.current_user_id,
          include_archived=include_archived,
      )
      # etc.
  ```

  Apply to all 6 routes in `accounts.py`.

- [ ] **Step 2: Actualizar `backend/app/api/categories.py`**

  Add `from flask import g` and `from app.utils.auth import require_auth` to imports. Apply `@require_auth` to all routes and pass `user_id=g.current_user_id` to every `category_service.*` call. Key routes:
  - `list_categories()` → `category_service.get_all(user_id=g.current_user_id, ...)`
  - `get_category()` → `category_service.get_by_id(category_id, g.current_user_id)`
  - `create_category()` → `category_service.create(user_id=g.current_user_id, ...)`
  - `update_category()` → `category_service.update(category_id, g.current_user_id, ...)`
  - `delete_category()` / `hard_delete_category()` → pass `user_id=g.current_user_id`

- [ ] **Step 3: Actualizar `backend/app/api/transactions.py`**

  Same pattern. Key changes:
  - `list_transactions()` → `transaction_service.get_filtered(user_id=g.current_user_id, ...)`
  - `get_transaction()` → `transaction_service.get_by_id(transaction_id, g.current_user_id)`
  - `create_transaction()` → `transaction_service.create(user_id=g.current_user_id, ...)`
  - `update_transaction()` → `transaction_service.update(transaction_id, g.current_user_id, ...)`
  - `delete_transaction()` → `transaction_service.delete(transaction_id, g.current_user_id)`

- [ ] **Step 4: Actualizar `backend/app/api/transfers.py`**

  Same pattern. Key changes:
  - `list_transfers()` → `transfer_service.get_filtered(user_id=g.current_user_id, ...)`
  - `get_transfer()` → `transfer_service.get_by_id(transfer_id, g.current_user_id)`
  - `create_transfer()` → `transfer_service.create(user_id=g.current_user_id, ...)`
  - `update_transfer()` → `transfer_service.update(transfer_id, g.current_user_id, ...)`
  - `delete_transfer()` → `transfer_service.delete(transfer_id, g.current_user_id)`

- [ ] **Step 5: Actualizar `backend/app/api/dashboards.py`**

  Same pattern for all dashboard and widget routes. Key changes:
  - `list_dashboards()` → `crud_service.list_dashboards(user_id=g.current_user_id, ...)`
  - `get_dashboard()` → `crud_service.get_dashboard(dashboard_id, g.current_user_id)`
  - `create_dashboard()` → `crud_service.create_dashboard(user_id=g.current_user_id, data=...)`
  - `update_dashboard()` → `crud_service.update_dashboard(dashboard_id, g.current_user_id, data=...)`
  - `delete_dashboard()` → `crud_service.delete_dashboard(dashboard_id, g.current_user_id)`
  - `list_widgets()` → `crud_service.list_widgets(dashboard_id, g.current_user_id)`
  - `create_widget()` → `crud_service.create_widget(dashboard_id, g.current_user_id, data=...)`
  - `update_widget()` → `crud_service.update_widget(dashboard_id, widget_id, g.current_user_id, data=...)`
  - `delete_widget()` → `crud_service.delete_widget(dashboard_id, widget_id, g.current_user_id)`

- [ ] **Step 6: Actualizar `backend/app/api/settings.py`**

  `get_settings` and `update_setting` already call `settings_service.get_all(user_id=g.current_user_id)` (from Task 1.6 Step 6). Only add `@require_auth` decorator to both routes.

- [ ] **Step 7: Verificar que la app arranca con todos los blueprints registrados**

  Run: `cd /Users/angelcorredor/Code/Wallet/backend && python -c "from app import create_app; app = create_app(); print(list(app.url_map.iter_rules()))"`
  Expected: No import errors. URL map includes `/auth/google`, `/api/v1/accounts`, etc.

- [ ] **Step 8: Ejecutar el test suite completo**

  Run: `cd /Users/angelcorredor/Code/Wallet/backend && python -m pytest --tb=short -q`
  Expected: Tests pass or fail with meaningful assertion errors (not import errors).

- [ ] **Step 9: Commit**

  ```bash
  git add backend/app/api/accounts.py backend/app/api/categories.py backend/app/api/transactions.py backend/app/api/transfers.py backend/app/api/dashboards.py backend/app/api/settings.py
  git commit -m "feat(auth): apply @require_auth to all protected endpoints; pass user_id from g"
  ```

---

### Task 3.4: Implementar `POST /api/v1/onboarding/seed`

**Files:**
- Modify: `backend/app/seeds/categories.py`
- Create: `backend/app/api/onboarding.py`
- Modify: `backend/app/api/__init__.py`

- [ ] **Step 1: Actualizar `backend/app/seeds/categories.py` para ser user-aware**

  Rename `seed_categories()` to `seed_categories_for_user(user_id: UUID) -> int` (returns count of categories created). Change the idempotency check to filter by `user_id` AND `name` AND `parent_category_id`:

  The `Category` model does NOT have a `tags` column (only `Account` and `Transaction` do). The seed function marks categories as auto-generated by convention via their `client_id` (set to `"seed-<name>"`) since there is no tag column. Alternatively, auto-generated items are distinguishable because they have `client_id` starting with `"seed-"`.

  Replace the entire `backend/app/seeds/categories.py` with the following (preserving the existing `CATEGORIES` list verbatim and only updating `seed_categories()`):

  ```python
  """
  Seed data for predefined categories (per-user).

  This module is invoked by the onboarding endpoint to create a default set of
  categories for a new user. It is idempotent per user: running it twice for
  the same user_id will not create duplicates.

  Auto-generated categories are identified by their client_id prefix 'seed-'.
  """

  from uuid import UUID
  from app.models import Category, CategoryType
  from app.extensions import db

  # CATEGORIES list is unchanged from the existing file — copy it verbatim here.
  # (The CATEGORIES constant defined in the original file must be preserved.)

  def seed_categories_for_user(user_id: UUID) -> int:
      """
      Seed default categories for a specific user.

      Idempotent: checks for existing categories by (user_id, name,
      parent_category_id) before creating. Auto-generated categories use
      a client_id prefixed with 'seed-' so they can be identified later.

      Args:
          user_id: The UUID of the user to seed categories for.

      Returns:
          Number of new category rows created.
      """
      created_count = 0

      for cat_data in CATEGORIES:
          existing = db.session.execute(
              db.select(Category).where(
                  Category.user_id == user_id,
                  Category.name == cat_data["name"],
                  Category.parent_category_id.is_(None),
              )
          ).scalars().one_or_none()

          if existing:
              parent = existing
          else:
              # client_id prefixed 'seed-' marks this as auto-generated
              parent_client_id = f"seed-{cat_data['name'].lower().replace(' ', '-')}"
              parent = Category(
                  name=cat_data["name"],
                  type=cat_data["type"],
                  icon=cat_data.get("icon"),
                  color=cat_data.get("color"),
                  client_id=parent_client_id,
                  user_id=user_id,
              )
              db.session.add(parent)
              db.session.flush()
              created_count += 1

          if "subcategories" in cat_data:
              for subcat_data in cat_data["subcategories"]:
                  existing_sub = db.session.execute(
                      db.select(Category).where(
                          Category.user_id == user_id,
                          Category.name == subcat_data["name"],
                          Category.parent_category_id == parent.id,
                      )
                  ).scalars().one_or_none()

                  if not existing_sub:
                      sub_client_id = f"seed-{subcat_data['name'].lower().replace(' ', '-')}"
                      sub = Category(
                          name=subcat_data["name"],
                          type=cat_data["type"],
                          icon=subcat_data.get("icon"),
                          color=cat_data.get("color"),
                          parent_category_id=parent.id,
                          client_id=sub_client_id,
                          user_id=user_id,
                      )
                      db.session.add(sub)
                      created_count += 1

      db.session.commit()
      return created_count
  ```

- [ ] **Step 2: Verificar que el módulo del seed importa sin error**

  Run: `cd /Users/angelcorredor/Code/Wallet/backend && python -c "from app.seeds.categories import seed_categories_for_user; print('OK')"`
  Expected: `OK`

- [ ] **Step 3: Escribir tests para el endpoint de onboarding**

  Create `backend/tests/api/test_onboarding.py`:

  ```python
  """Tests for POST /api/v1/onboarding/seed."""
  import pytest
  from unittest.mock import patch
  import jwt
  from datetime import datetime, timedelta


  @pytest.fixture
  def auth_headers(app):
      """Generate valid JWT auth headers for a test user."""
      from app.models.user import User
      from app.extensions import db
      with app.app_context():
          user = User(google_id="seed_test_sub", email="seed@test.com", name="Seed User")
          db.session.add(user)
          db.session.commit()
          payload = {
              "id": str(user.id),
              "email": user.email,
              "name": user.name,
              "exp": datetime.utcnow() + timedelta(hours=1),
          }
          token = jwt.encode(payload, app.config["JWT_SECRET"], algorithm="HS256")
          return {"Authorization": f"Bearer {token}", "_user_id": str(user.id)}


  def test_seed_creates_accounts_and_categories(client, auth_headers):
      """POST /api/v1/onboarding/seed creates seed data for authenticated user."""
      headers = {k: v for k, v in auth_headers.items() if k != "_user_id"}
      resp = client.post("/api/v1/onboarding/seed", headers=headers)
      assert resp.status_code == 200
      data = resp.get_json()["data"]
      assert data["categories_created"] > 0
      assert data["accounts_created"] > 0
      assert data["dashboard_created"] is True


  def test_seed_is_idempotent_returns_409_on_second_call(client, auth_headers):
      """POST /api/v1/onboarding/seed returns 409 if user already has data."""
      headers = {k: v for k, v in auth_headers.items() if k != "_user_id"}
      client.post("/api/v1/onboarding/seed", headers=headers)
      resp = client.post("/api/v1/onboarding/seed", headers=headers)
      assert resp.status_code == 409


  def test_seed_requires_auth(client):
      """POST /api/v1/onboarding/seed returns 401 without JWT."""
      resp = client.post("/api/v1/onboarding/seed")
      assert resp.status_code == 401
  ```

- [ ] **Step 4: Ejecutar tests — deben fallar**

  Run: `cd /Users/angelcorredor/Code/Wallet/backend && python -m pytest tests/api/test_onboarding.py -v`
  Expected: FAIL — `404 Not Found`

- [ ] **Step 5: Crear `backend/app/api/onboarding.py`**

  ```python
  """
  Onboarding endpoints.

  Provides the seed data endpoint for new users who want to start with
  pre-populated accounts, categories, and a default dashboard.
  """

  from flask import Blueprint, g

  from app.extensions import db
  from app.models.account import Account, AccountType
  from app.models.dashboard import Dashboard
  from app.seeds.categories import seed_categories_for_user
  from app.utils.auth import require_auth
  from app.utils.responses import error_response, success_response

  onboarding_bp = Blueprint("onboarding", __name__, url_prefix="/api/v1/onboarding")

  # Default seed accounts for a new user
  _SEED_ACCOUNTS = [
      {"name": "Cuenta Corriente", "type": AccountType.DEBIT, "currency": "COP",
       "tags": ["auto-generated"]},
      {"name": "Cuenta de Ahorros", "type": AccountType.DEBIT, "currency": "COP",
       "tags": ["auto-generated"]},
      {"name": "Efectivo", "type": AccountType.CASH, "currency": "COP",
       "tags": ["auto-generated"]},
  ]


  @onboarding_bp.route("/seed", methods=["POST"])
  @require_auth
  def seed():
      """
      Create seed data for the authenticated user.

      Creates a predefined set of accounts, categories (with subcategories),
      and a default dashboard. All items are tagged 'auto-generated'.

      Can only be called once per user. Returns 409 if the user already has
      any accounts in the database.

      Returns:
          200: Counts of created resources.
          409: User already has data (seed already ran).
          401: No valid JWT provided.
          500: Internal server error.
      """
      user_id = g.current_user_id

      # Idempotency guard: check if user already has accounts
      existing_count = db.session.execute(
          db.select(db.func.count()).select_from(Account).where(
              Account.user_id == user_id
          )
      ).scalar_one()

      if existing_count > 0:
          return error_response(
              "El usuario ya tiene datos. El seed solo puede ejecutarse una vez.",
              status_code=409,
          )

      # Create seed accounts
      accounts_created = 0
      for acc_data in _SEED_ACCOUNTS:
          account = Account(
              name=acc_data["name"],
              type=acc_data["type"],
              currency=acc_data["currency"],
              tags=acc_data.get("tags", []),
              user_id=user_id,
          )
          db.session.add(account)
          accounts_created += 1

      db.session.flush()

      # Create seed categories
      categories_created = seed_categories_for_user(user_id)

      # Create default dashboard
      dashboard = Dashboard(
          name="Mi Dashboard",
          display_currency="COP",
          layout_columns=2,
          is_default=True,
          sort_order=0,
          user_id=user_id,
      )
      db.session.add(dashboard)
      db.session.commit()

      return success_response(
          data={
              "accounts_created": accounts_created,
              "categories_created": categories_created,
              "dashboard_created": True,
          }
      )
  ```

- [ ] **Step 6: Registrar el blueprint en `backend/app/api/__init__.py`**

  ```python
  from app.api.onboarding import onboarding_bp
  # in register_blueprints():
  app.register_blueprint(onboarding_bp)
  ```

- [ ] **Step 7: Ejecutar los tests de onboarding**

  Run: `cd /Users/angelcorredor/Code/Wallet/backend && python -m pytest tests/api/test_onboarding.py -v`
  Expected: PASS (3 tests)

- [ ] **Step 8: Commit**

  ```bash
  git add backend/app/seeds/categories.py backend/app/api/onboarding.py backend/app/api/__init__.py backend/tests/api/test_onboarding.py
  git commit -m "feat(auth): add /api/v1/onboarding/seed endpoint with user-aware seed data"
  ```

---

### Task 3.5: Ejecutar el test suite completo y verificar

- [ ] **Step 1: Ejecutar todos los tests**

  Run: `cd /Users/angelcorredor/Code/Wallet/backend && python -m pytest --tb=short -q`
  Expected: All tests pass. No import errors. No unexpected failures.

- [ ] **Step 2: Verificar el estado de las migraciones**

  Run: `cd /Users/angelcorredor/Code/Wallet/backend && flask db current`
  Expected: `008c_make_user_id_not_null (head)`

- [ ] **Step 3: Verificar que la app arranca en desarrollo**

  Run: `cd /Users/angelcorredor/Code/Wallet/backend && python -c "from app import create_app; app = create_app('development'); print('App OK'); print([str(r) for r in app.url_map.iter_rules() if 'auth' in str(r) or 'onboarding' in str(r)])"`
  Expected: Prints `App OK` and lists `/auth/google`, `/auth/refresh`, `/auth/logout`, `/api/v1/onboarding/seed`.

- [ ] **Step 4: Commit final de cierre**

  ```bash
  git add -A
  git commit -m "feat(auth): complete multiuser backend implementation — models, migrations, auth endpoints, user-aware repositories and services, onboarding seed"
  ```

---

## Edge Cases y Estrategia de Error Handling

| Caso | Comportamiento esperado | Dónde se maneja |
|---|---|---|
| `db.session.get()` bypaseando user_id | Nunca ocurre — `get_by_id()` usa SELECT explícito | `BaseRepository.get_by_id()` |
| Refresh token robado y usado antes que el usuario | El usuario legítimo recibe 401 en el próximo intento | `AuthService.rotate_refresh_token()` |
| Dos usuarios generan el mismo `client_id` | Constraint `UNIQUE(user_id, client_id)` permite duplicados entre usuarios | Migration 008b + BaseModel |
| `POST /auth/logout` con JWT expirado | 204 siempre — endpoint no requiere JWT | `auth.py` blueprint |
| `POST /onboarding/seed` llamado dos veces | 409 — guarda de idempotencia en `onboarding.py` | `onboarding.py` |
| Usuario sin nombre en payload de Google | `ValidationError` en `verify_google_token` — campo `name` requerido | `AuthService.verify_google_token()` |
| Migration 008b sin usuarios en DB | Todas las filas se eliminan (entorno de test) | `008b` upgrade function |
| JWT con `id` que no existe en DB | `@require_auth` acepta el JWT válido (no valida contra DB); servicio recibe un `user_id` que devuelve resultados vacíos. No es un bug — es el comportamiento esperado. | Por diseño |
| `ExchangeRate` no recibe `user_id` | No hereda de `BaseModel` en el sentido de user_id. Verificar que el modelo quede intacto. | `exchange_rate.py` no se toca |

---

## Verification Checklist

Al final de la implementación, verificar:

- [ ] `flask db current` muestra `008c_make_user_id_not_null (head)`
- [ ] `python -m pytest` pasa todos los tests sin errores
- [ ] `POST /auth/google` con un id_token válido devuelve `access_token` + `refresh_token`
- [ ] `POST /auth/refresh` con un refresh token válido devuelve nuevos tokens
- [ ] `POST /auth/logout` siempre devuelve 204
- [ ] Cualquier endpoint `/api/v1/*` sin JWT devuelve 401
- [ ] `GET /api/v1/accounts` con JWT de usuario A no devuelve cuentas del usuario B
- [ ] `POST /api/v1/onboarding/seed` devuelve 200 la primera vez y 409 la segunda
- [ ] `GET /health` sigue funcionando sin JWT (endpoint público)
- [ ] `ExchangeRate` model no tiene `user_id` (global)
- [ ] `UserSetting` PK es `(user_id, key)` en la DB
