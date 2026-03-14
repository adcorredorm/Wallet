# Incremental Sync — Backend Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Agregar soporte de cursor opaco (`If-Sync-Cursor` / `X-Sync-Cursor`) a los endpoints GET del backend para que solo retornen registros modificados desde el último sync, respondiendo `304 Not Modified` cuando no hubo cambios.

**Architecture:** Se crea un helper `sync_cursor.py` que encapsula encode/decode del cursor. Los repositorios reciben `updated_since: datetime | None` en sus métodos de listado. Los endpoints leen `If-Sync-Cursor`, filtran por `updated_since`, y siempre retornan un nuevo cursor en `X-Sync-Cursor`. Para transactions y transfers con cursor se retorna lista plana (no paginada). Para responses con headers custom se usa `make_response(jsonify(body), status)`.

**Tech Stack:** Python 3.11+, Flask 3.x, SQLAlchemy 2.0, pytest

**Notion ticket:** https://www.notion.so/32379901d1b8811c9d93e2846d707336

**Spec:** `docs/superpowers/specs/2026-03-14-incremental-sync-design.md`

---

## Fixtures de test requeridas

Antes de escribir tests, agregar estas fixtures a `backend/tests/conftest.py`. Las fixtures existentes usan `Mock` — estas usan la DB real (requieren fixture `app`).

```python
# Agregar al final de backend/tests/conftest.py

# ============================================================================
# REAL DB FACTORY FIXTURES (para integration y repository tests)
# ============================================================================

@pytest.fixture
def make_account(app):
    """Factory que crea Account reales en DB.
    NO usar with app.app_context() — el fixture `app` ya activa el contexto
    para toda la duración del test. Anidar contextos crea sesiones separadas
    que causan DetachedInstanceError al mutar objetos fuera del factory.
    """
    from app.extensions import db
    from app.models.account import Account, AccountType
    from uuid import uuid4

    def _make(**kwargs):
        defaults = dict(
            name=f"Cuenta {uuid4().hex[:6]}",
            type=AccountType.DEBIT,
            currency="MXN",
            active=True,
        )
        defaults.update(kwargs)
        account = Account(**defaults)
        db.session.add(account)
        db.session.commit()
        db.session.refresh(account)
        return account
    yield _make


@pytest.fixture
def make_category(app):
    """Factory que crea Category reales en DB."""
    from app.extensions import db
    from app.models.category import Category, CategoryType
    from uuid import uuid4

    def _make(**kwargs):
        defaults = dict(
            name=f"Cat {uuid4().hex[:6]}",
            type=CategoryType.EXPENSE,
            active=True,
        )
        defaults.update(kwargs)
        cat = Category(**defaults)
        db.session.add(cat)
        db.session.commit()
        db.session.refresh(cat)
        return cat
    yield _make


@pytest.fixture
def make_dashboard(app):
    """Factory que crea Dashboard reales en DB.
    display_currency es nullable=False — siempre proveer un valor.
    """
    from app.extensions import db
    from app.models.dashboard import Dashboard
    from uuid import uuid4

    def _make(**kwargs):
        defaults = dict(
            name=f"Dashboard {uuid4().hex[:6]}",
            is_default=False,
            sort_order=0,
            display_currency="USD",   # required, nullable=False
        )
        defaults.update(kwargs)
        d = Dashboard(**defaults)
        db.session.add(d)
        db.session.commit()
        db.session.refresh(d)
        return d
    yield _make


@pytest.fixture
def make_widget(app):
    """Factory que crea DashboardWidget reales en DB."""
    from app.extensions import db
    from app.models.dashboard_widget import DashboardWidget, WidgetType
    from uuid import uuid4

    def _make(dashboard_id, **kwargs):
        defaults = dict(
            dashboard_id=dashboard_id,
            widget_type=WidgetType.LINE,
            title=f"Widget {uuid4().hex[:6]}",
            position_x=0,
            position_y=0,
            width=4,
            height=2,
            config={},
        )
        defaults.update(kwargs)
        w = DashboardWidget(**defaults)
        db.session.add(w)
        db.session.commit()
        db.session.refresh(w)
        return w
    yield _make


@pytest.fixture
def make_exchange_rate(app):
    """Factory que crea ExchangeRate reales en DB."""
    from app.extensions import db
    from app.models.exchange_rate import ExchangeRate
    from decimal import Decimal
    from datetime import datetime
    from uuid import uuid4

    def _make(currency_code=None, **kwargs):
        code = currency_code or f"T{uuid4().hex[:3].upper()}"
        defaults = dict(
            currency_code=code,
            rate_to_usd=Decimal("1.0"),
            source="test",
            fetched_at=datetime.utcnow(),
        )
        defaults.update(kwargs)
        er = ExchangeRate(**defaults)
        db.session.add(er)
        db.session.commit()
        db.session.refresh(er)
        return er
    yield _make


@pytest.fixture
def make_transaction(app, make_account, make_category):
    """Factory que crea Transaction reales en DB."""
    from app.extensions import db
    from app.models.transaction import Transaction, TransactionType
    from decimal import Decimal
    from datetime import date

    def _make(**kwargs):
        if "account_id" not in kwargs:
            kwargs["account_id"] = make_account().id
        if "category_id" not in kwargs:
            kwargs["category_id"] = make_category().id
        defaults = dict(
            type=TransactionType.EXPENSE,
            amount=Decimal("100.00"),
            date=date.today(),
            title="Test transaction",
        )
        defaults.update(kwargs)
        t = Transaction(**defaults)
        db.session.add(t)
        db.session.commit()
        db.session.refresh(t)
        return t
    yield _make


@pytest.fixture
def make_transfer(app, make_account):
    """Factory que crea Transfer reales en DB."""
    from app.extensions import db
    from app.models.transfer import Transfer
    from decimal import Decimal
    from datetime import date

    def _make(**kwargs):
        if "source_account_id" not in kwargs:
            kwargs["source_account_id"] = make_account().id
        if "destination_account_id" not in kwargs:
            kwargs["destination_account_id"] = make_account().id
        defaults = dict(
            amount=Decimal("50.00"),
            date=date.today(),
        )
        defaults.update(kwargs)
        t = Transfer(**defaults)
        db.session.add(t)
        db.session.commit()
        db.session.refresh(t)
        return t
    yield _make
```

---

## Chunk 1: Helper sync_cursor.py

### Task 1: Cursor helper — encode y decode

**Files:**
- Create: `backend/app/utils/sync_cursor.py`
- Create: `backend/tests/unit/test_sync_cursor.py`

- [ ] **Step 1: Crear tests**

```python
# backend/tests/unit/test_sync_cursor.py
"""Tests for sync_cursor helper."""
import pytest
from datetime import datetime
from app.utils.sync_cursor import encode_cursor, decode_cursor


def test_encode_returns_nonempty_string():
    assert isinstance(encode_cursor(), str)
    assert len(encode_cursor()) > 0


def test_encode_decode_roundtrip():
    cursor = encode_cursor()
    dt = decode_cursor(cursor)
    assert dt is not None
    assert isinstance(dt, datetime)
    assert dt.tzinfo is None  # naive UTC, compatible con BaseModel.updated_at


def test_decode_none_returns_none():
    assert decode_cursor(None) is None


def test_decode_empty_string_returns_none():
    assert decode_cursor("") is None


def test_decode_invalid_base64_returns_none():
    assert decode_cursor("not-valid-base64!!!") is None


def test_decode_invalid_json_returns_none():
    import base64
    assert decode_cursor(base64.urlsafe_b64encode(b"not json").decode()) is None


def test_decode_missing_t_field_returns_none():
    import base64, json
    payload = base64.urlsafe_b64encode(json.dumps({"v": 1}).encode()).decode()
    assert decode_cursor(payload) is None


def test_decode_unknown_version_returns_none():
    import base64, json
    payload = base64.urlsafe_b64encode(
        json.dumps({"t": "2026-03-14T10:00:00.000000Z", "v": 999}).encode()
    ).decode()
    assert decode_cursor(payload) is None


def test_decode_invalid_timestamp_returns_none():
    import base64, json
    payload = base64.urlsafe_b64encode(
        json.dumps({"t": "not-a-date", "v": 1}).encode()
    ).decode()
    assert decode_cursor(payload) is None


def test_decoded_timestamp_is_close_to_now():
    from datetime import timedelta
    cursor = encode_cursor()
    dt = decode_cursor(cursor)
    now = datetime.utcnow()
    assert abs((now - dt).total_seconds()) < 5


def test_two_cursors_have_different_timestamps(monkeypatch):
    from datetime import datetime, timezone
    import app.utils.sync_cursor as sc
    calls = [0]
    times = [
        datetime(2026, 3, 14, 10, 0, 0, tzinfo=timezone.utc),
        datetime(2026, 3, 14, 10, 0, 1, tzinfo=timezone.utc),
    ]
    def fake_now(tz=None):
        t = times[calls[0]]; calls[0] += 1; return t
    monkeypatch.setattr(sc, "_now", fake_now)
    assert encode_cursor() != encode_cursor()
```

- [ ] **Step 2: Verificar que los tests fallan**

```bash
cd backend && python -m pytest tests/unit/test_sync_cursor.py -v 2>&1 | head -10
```
Expected: `ModuleNotFoundError`

- [ ] **Step 3: Implementar `sync_cursor.py`**

```python
# backend/app/utils/sync_cursor.py
"""
Opaque sync cursor for incremental sync.

Format (v1): base64url(JSON({"t": "ISO_UTC_Z", "v": 1}))
"t" is the time the query was made (not the time of the last change).
The cursor is always opaque to the client.
"""
import base64
import json
from datetime import datetime, timezone


def _now(tz=None) -> datetime:
    """Injectable clock for tests."""
    return datetime.now(tz or timezone.utc)


def encode_cursor() -> str:
    """Generate a cursor encoding the current UTC timestamp."""
    ts = _now(timezone.utc)
    payload = json.dumps({"t": ts.strftime("%Y-%m-%dT%H:%M:%S.%f") + "Z", "v": 1})
    return base64.urlsafe_b64encode(payload.encode()).decode().rstrip("=")


def decode_cursor(header: str | None) -> datetime | None:
    """
    Decode cursor to naive UTC datetime. Returns None on any error.
    Naive datetime for compatibility with BaseModel.updated_at (also naive).
    """
    if not header:
        return None
    try:
        padding = 4 - len(header) % 4
        padded = header + ("=" * padding if padding != 4 else "")
        data = json.loads(base64.urlsafe_b64decode(padded.encode()).decode())
        if not isinstance(data, dict) or data.get("v") != 1:
            return None
        t = data.get("t")
        if not t:
            return None
        return datetime.fromisoformat(t.rstrip("Z")).replace(tzinfo=None)
    except Exception:
        return None
```

- [ ] **Step 4: Correr tests**

```bash
cd backend && python -m pytest tests/unit/test_sync_cursor.py -v
```
Expected: todos pasan

- [ ] **Step 5: Commit**

```bash
git add backend/app/utils/sync_cursor.py backend/tests/unit/test_sync_cursor.py
git commit -m "feat(sync): add sync_cursor encode/decode helper"
```

---

## Chunk 2: Cambios en repositorios y servicios

### Task 2: `updated_since` en repositorios

**Files:**
- Modify: `backend/app/repositories/base.py`
- Modify: `backend/app/repositories/category.py`
- Modify: `backend/app/repositories/dashboard.py`
- Modify: `backend/app/repositories/exchange_rate.py`
- Modify: `backend/app/repositories/account.py`
- Modify: `backend/app/repositories/transaction.py`
- Modify: `backend/app/repositories/transfer.py`
- Modify: `backend/app/services/transaction.py`
- Modify: `backend/app/services/transfer.py`
- Modify: `backend/app/services/account.py`
- Modify: `backend/app/services/exchange_rate.py`
- Modify: `backend/tests/conftest.py` ← agregar fixtures de la sección anterior
- Create: `backend/tests/unit/repositories/test_updated_since.py`

- [ ] **Step 1: Agregar fixtures reales a `tests/conftest.py`**

Copiar el bloque de fixtures de la sección "Fixtures de test requeridas" al final de `backend/tests/conftest.py`. Verificar que `backend/tests/unit/repositories/__init__.py` existe (está en git status como untracked — ya existe, no crear de nuevo).

- [ ] **Step 2: Escribir los tests de repositorios**

```python
# backend/tests/unit/repositories/test_updated_since.py
"""Tests that updated_since filtering works across repositories."""
import pytest
from datetime import datetime


def test_base_get_all_no_filter_returns_all(app, make_account):
    with app.app_context():
        a1 = make_account()
        a2 = make_account()
        from app.repositories.account import AccountRepository
        repo = AccountRepository()
        result = repo.get_all(updated_since=None)
        ids = {r.id for r in result}
        assert a1.id in ids and a2.id in ids


def test_base_get_all_updated_since_excludes_older(app, make_account):
    with app.app_context():
        from app.extensions import db
        old = make_account()
        old.updated_at = datetime(2020, 1, 1)
        db.session.commit()

        cutoff = datetime(2025, 1, 1)
        newer = make_account()

        from app.repositories.account import AccountRepository
        result = AccountRepository().get_all(updated_since=cutoff)
        ids = {r.id for r in result}
        assert newer.id in ids
        assert old.id not in ids


def test_base_get_all_updated_since_inclusive(app, make_account):
    """Record updated exactly at cutoff must be included (>= not >)."""
    with app.app_context():
        from app.extensions import db
        exact = datetime(2026, 3, 14, 10, 0, 0)
        a = make_account()
        a.updated_at = exact
        db.session.commit()

        from app.repositories.account import AccountRepository
        result = AccountRepository().get_all(updated_since=exact)
        assert any(r.id == a.id for r in result)


def test_category_get_all_updated_since(app, make_category):
    with app.app_context():
        from app.extensions import db
        old = make_category()
        old.updated_at = datetime(2020, 1, 1)
        db.session.commit()

        cutoff = datetime(2025, 1, 1)
        new = make_category()

        from app.repositories.category import CategoryRepository
        result = CategoryRepository().get_all(updated_since=cutoff)
        ids = {r.id for r in result}
        assert new.id in ids
        assert old.id not in ids


def test_category_get_all_updated_since_with_include_archived(app, make_category):
    """updated_since + include_archived=True returns archived records too."""
    with app.app_context():
        from app.extensions import db
        archived = make_category(active=False)
        archived.updated_at = datetime.utcnow()
        db.session.commit()

        cutoff = datetime(2020, 1, 1)
        from app.repositories.category import CategoryRepository
        result = CategoryRepository().get_all(updated_since=cutoff, include_archived=True)
        assert any(r.id == archived.id for r in result)


def test_dashboard_get_all_ordered_updated_since(app, make_dashboard):
    with app.app_context():
        from app.extensions import db
        old = make_dashboard()
        old.updated_at = datetime(2020, 1, 1)
        db.session.commit()

        cutoff = datetime(2025, 1, 1)
        new = make_dashboard()

        from app.repositories.dashboard import DashboardRepository
        result = DashboardRepository().get_all_ordered(updated_since=cutoff)
        ids = {r.id for r in result}
        assert new.id in ids
        assert old.id not in ids


def test_exchange_rate_get_all_updated_since(app, make_exchange_rate):
    with app.app_context():
        from app.extensions import db
        old = make_exchange_rate(currency_code="OLD")
        old.updated_at = datetime(2020, 1, 1)
        db.session.commit()

        cutoff = datetime(2025, 1, 1)
        new = make_exchange_rate(currency_code="NEW")

        from app.repositories.exchange_rate import ExchangeRateRepository
        result = ExchangeRateRepository().get_all(updated_since=cutoff)
        codes = {r.currency_code for r in result}
        assert "NEW" in codes
        assert "OLD" not in codes
```

- [ ] **Step 3: Verificar que los tests fallan**

```bash
cd backend && python -m pytest tests/unit/repositories/test_updated_since.py -v 2>&1 | head -20
```

- [ ] **Step 4: Actualizar `BaseRepository.get_all()`**

En `backend/app/repositories/base.py`, modificar `get_all`:

```python
from datetime import datetime  # agregar al import al inicio

def get_all(self, updated_since: datetime | None = None) -> list[T]:
    """
    Get all records, optionally filtered by modification time.

    Args:
        updated_since: Only return records with updated_at >= updated_since
            (naive UTC). None returns all records.
    """
    query = db.select(self.model)
    if updated_since is not None:
        query = query.where(self.model.updated_at >= updated_since)
    return db.session.execute(query).scalars().all()
```

- [ ] **Step 5: Actualizar `CategoryRepository.get_all()`**

`CategoryRepository` sobrescribe `get_all()` con `include_archived`. Agregar `updated_since`:

```python
# En backend/app/repositories/category.py, reemplazar get_all():
from datetime import datetime  # agregar al import

def get_all(
    self,
    include_archived: bool = False,
    updated_since: datetime | None = None,
) -> list[Category]:
    """
    Get all categories, optionally filtered by archived status and/or update time.

    Args:
        include_archived: When False (default), return only active categories.
        updated_since: If provided, only return records with updated_at >= value.
    """
    query = db.select(Category)
    if not include_archived:
        query = query.where(Category.active == True)
    if updated_since is not None:
        query = query.where(Category.updated_at >= updated_since)
    return db.session.execute(query).scalars().all()
```

- [ ] **Step 6: Actualizar `DashboardRepository.get_all_ordered()`**

```python
# En backend/app/repositories/dashboard.py
from datetime import datetime  # agregar al import

def get_all_ordered(self, updated_since: datetime | None = None) -> list[Dashboard]:
    """Return dashboards ordered by sort_order, optionally filtered by updated_at."""
    query = db.select(Dashboard).order_by(Dashboard.sort_order.asc())
    if updated_since is not None:
        query = query.where(Dashboard.updated_at >= updated_since)
    return db.session.execute(query).scalars().all()
```

- [ ] **Step 7: Actualizar `ExchangeRateRepository.get_all()`**

```python
# En backend/app/repositories/exchange_rate.py
from datetime import datetime  # agregar al import

def get_all(self, updated_since: datetime | None = None) -> list[ExchangeRate]:
    """Return all exchange rate rows, optionally filtered by updated_at."""
    query = db.select(ExchangeRate).order_by(ExchangeRate.currency_code)
    if updated_since is not None:
        query = query.where(ExchangeRate.updated_at >= updated_since)
    return db.session.execute(query).scalars().all()
```

- [ ] **Step 8: Actualizar `AccountRepository` — agregar método para sync**

`AccountRepository` no sobrescribe `get_all()` (usa el de base). Agregar método específico para sync incremental:

```python
# En backend/app/repositories/account.py
from datetime import datetime  # agregar al import

def get_all_updated_since(
    self,
    updated_since: datetime,
    include_archived: bool = True,
) -> list[Account]:
    """
    Return accounts modified since updated_since (naive UTC, inclusive).
    For incremental sync: include_archived=True to propagate active=False changes.
    """
    query = db.select(Account).where(Account.updated_at >= updated_since)
    if not include_archived:
        query = query.where(Account.active == True)
    return db.session.execute(query).scalars().all()
```

- [ ] **Step 9: Actualizar `TransactionRepository.get_filtered()` — agregar `updated_since`**

En `backend/app/repositories/transaction.py`, modificar la firma:

```python
from datetime import date, datetime  # modificar import existente

def get_filtered(
    self,
    account_id: Optional[UUID] = None,
    category_id: Optional[UUID] = None,
    type: Optional[TransactionType] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    tags: Optional[list[str]] = None,
    limit: int = 20,
    offset: int = 0,
    updated_since: Optional[datetime] = None,  # ← nuevo
) -> tuple[list[Transaction], int]:
```

Agregar al bloque de `filters`:
```python
if updated_since is not None:
    filters.append(Transaction.updated_at >= updated_since)
```

- [ ] **Step 10: Actualizar `TransferRepository.get_filtered()` — agregar `updated_since`**

Igual en `backend/app/repositories/transfer.py`:

```python
from datetime import date, datetime  # modificar import

def get_filtered(
    self,
    account_id: Optional[UUID] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    tags: Optional[list[str]] = None,
    limit: int = 20,
    offset: int = 0,
    updated_since: Optional[datetime] = None,  # ← nuevo
) -> tuple[list[Transfer], int]:
```

Agregar al bloque de `filters`:
```python
if updated_since is not None:
    filters.append(Transfer.updated_at >= updated_since)
```

- [ ] **Step 11: Actualizar `TransactionService.get_filtered()` — propagar `updated_since`**

En `backend/app/services/transaction.py`:

```python
from datetime import date, datetime  # modificar import

def get_filtered(
    self,
    account_id: UUID | None = None,
    category_id: UUID | None = None,
    type: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    tags: list[str] | None = None,
    page: int = 1,
    limit: int = 20,
    updated_since: datetime | None = None,  # ← nuevo
) -> tuple[list[Transaction], int]:
    ...
    return self.repository.get_filtered(
        account_id=account_id,
        category_id=category_id,
        type=type_enum,
        date_from=date_from,
        date_to=date_to,
        tags=tags,
        limit=limit,
        offset=offset,
        updated_since=updated_since,  # ← nuevo
    )
```

- [ ] **Step 12: Actualizar `TransferService.get_filtered()` — propagar `updated_since`**

En `backend/app/services/transfer.py`:

```python
from datetime import date, datetime  # modificar import

def get_filtered(
    self,
    account_id: UUID | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    tags: list[str] | None = None,
    page: int = 1,
    limit: int = 20,
    updated_since: datetime | None = None,  # ← nuevo
) -> tuple[list[Transfer], int]:
    ...
    return self.repository.get_filtered(
        account_id=account_id,
        date_from=date_from,
        date_to=date_to,
        tags=tags,
        limit=limit,
        offset=offset,
        updated_since=updated_since,  # ← nuevo
    )
```

- [ ] **Step 13: Actualizar `AccountService` — agregar `get_all_with_balances_since()`**

En `backend/app/services/account.py`:

```python
from datetime import datetime  # agregar al import

def get_all_with_balances_since(
    self, updated_since: datetime
) -> list[tuple[Account, Decimal]]:
    """
    Return accounts modified since updated_since (inclusive) with balances.
    Always includes archived accounts (to propagate active=False changes).
    Used by incremental sync.
    """
    accounts = self.repository.get_all_updated_since(
        updated_since=updated_since,
        include_archived=True,
    )
    return [
        (account, self.repository.calculate_balance(account.id))
        for account in accounts
    ]
```

- [ ] **Step 14: Actualizar `ExchangeRateService.get_all()` — propagar `updated_since`**

En `backend/app/services/exchange_rate.py`:

```python
from datetime import datetime  # agregar al import

def get_all(self, updated_since: datetime | None = None) -> list[ExchangeRate]:
    """Return all exchange rates, optionally filtered by updated_at."""
    return self.repository.get_all(updated_since=updated_since)
```

- [ ] **Step 15: Correr los tests**

```bash
cd backend && python -m pytest tests/unit/repositories/test_updated_since.py -v
```
Expected: todos pasan

- [ ] **Step 16: Correr suite completa**

```bash
cd backend && python -m pytest -v
```
Expected: todos pasan

- [ ] **Step 17: Commit**

```bash
git add backend/app/repositories/ backend/app/services/ backend/tests/
git commit -m "feat(sync): add updated_since filter to repositories and services"
```

---

## Chunk 3: DashboardCrudService cascade

### Task 3: Cascade `updated_at` al Dashboard padre en operaciones de widget

**Files:**
- Modify: `backend/app/services/dashboard_crud.py`
- Create: `backend/tests/unit/services/test_dashboard_cascade.py`

- [ ] **Step 1: Escribir los tests**

```python
# backend/tests/unit/services/test_dashboard_cascade.py
"""Tests that widget mutations cascade updated_at to the parent dashboard."""
import time
import pytest


def test_create_widget_cascades_updated_at(app, make_dashboard):
    with app.app_context():
        from app.extensions import db
        from app.services.dashboard_crud import DashboardCrudService
        from app.schemas.dashboard_crud import WidgetCreate

        svc = DashboardCrudService()
        dashboard = make_dashboard()
        original_ts = dashboard.updated_at

        time.sleep(0.02)

        svc.create_widget(dashboard.id, WidgetCreate(
            widget_type="line",
            title="Test Widget",
            position_x=0, position_y=0,
            width=4, height=2,
            config=None,
        ))

        db.session.refresh(dashboard)
        assert dashboard.updated_at > original_ts


def test_update_widget_cascades_updated_at(app, make_dashboard, make_widget):
    with app.app_context():
        from app.extensions import db
        from app.services.dashboard_crud import DashboardCrudService
        from app.schemas.dashboard_crud import WidgetUpdate

        svc = DashboardCrudService()
        dashboard = make_dashboard()
        widget = make_widget(dashboard_id=dashboard.id)
        original_ts = dashboard.updated_at

        time.sleep(0.02)

        svc.update_widget(dashboard.id, widget.id, WidgetUpdate(width=6))

        db.session.refresh(dashboard)
        assert dashboard.updated_at > original_ts


def test_delete_widget_cascades_updated_at(app, make_dashboard, make_widget):
    with app.app_context():
        from app.extensions import db
        from app.services.dashboard_crud import DashboardCrudService

        svc = DashboardCrudService()
        dashboard = make_dashboard()
        widget = make_widget(dashboard_id=dashboard.id)
        original_ts = dashboard.updated_at

        time.sleep(0.02)

        svc.delete_widget(dashboard.id, widget.id)

        db.session.refresh(dashboard)
        assert dashboard.updated_at > original_ts
```

- [ ] **Step 2: Verificar que los tests fallan**

```bash
cd backend && python -m pytest tests/unit/services/test_dashboard_cascade.py -v 2>&1 | head -15
```

- [ ] **Step 3: Agregar `_touch_dashboard` y llamarlo en `DashboardCrudService`**

En `backend/app/services/dashboard_crud.py`, agregar imports si no existen:
```python
from datetime import datetime, timezone
import sqlalchemy as sa
from app.models.dashboard import Dashboard  # puede ya estar importado
```

Agregar método privado a la clase:
```python
def _touch_dashboard(self, dashboard_id) -> None:
    """Update dashboard.updated_at to now after a widget mutation."""
    from app.extensions import db
    db.session.execute(
        sa.update(Dashboard)
        .where(Dashboard.id == dashboard_id)
        .values(updated_at=datetime.now(timezone.utc).replace(tzinfo=None))
    )
    db.session.commit()
```

En `create_widget`, al final (después de `return widget, True` — antes del return), NO: agregar llamada después de la línea `return widget, True` es imposible. En su lugar, convertirlo a:

```python
# Al final de create_widget, reemplazar:
#   return widget, True
# Por:
self._touch_dashboard(dashboard_id)
return widget, True
```

En `update_widget`, al final reemplazar `return self.repo.update_widget(...)` por:
```python
updated_widget = self.repo.update_widget(widget, **update_fields)
self._touch_dashboard(dashboard_id)
return updated_widget
```

En `delete_widget`, al final de `self.repo.delete_widget(widget)` agregar:
```python
self._touch_dashboard(dashboard_id)
```

- [ ] **Step 4: Correr los tests**

```bash
cd backend && python -m pytest tests/unit/services/test_dashboard_cascade.py -v
```
Expected: todos pasan

- [ ] **Step 5: Correr suite completa**

```bash
cd backend && python -m pytest -v
```

- [ ] **Step 6: Commit**

```bash
git add backend/app/services/dashboard_crud.py backend/tests/unit/services/test_dashboard_cascade.py
git commit -m "feat(sync): cascade Dashboard.updated_at on widget mutations"
```

---

## Chunk 4: Cambios en endpoints

### Task 4: Endpoints con soporte de cursor

**Nota sobre `make_response` + cursor headers:** `success_response()` retorna `(dict, int)`. Para agregar headers, usar:
```python
from flask import jsonify, make_response
resp = make_response(jsonify(body), status_code)
resp.headers["X-Sync-Cursor"] = new_cursor
return resp
```
donde `body` es el dict `{"success": True, "data": ...}` construido manualmente.

**Files:**
- Modify: `backend/app/api/accounts.py`
- Modify: `backend/app/api/categories.py`
- Modify: `backend/app/api/transactions.py`
- Modify: `backend/app/api/transfers.py`
- Modify: `backend/app/api/dashboards.py`
- Modify: `backend/app/api/exchange_rates.py`
- Create: `backend/tests/api/test_sync_cursor_endpoints.py`

- [ ] **Step 1: Escribir los tests de integración**

```python
# backend/tests/api/test_sync_cursor_endpoints.py
"""Integration tests: cursor-based incremental sync on GET endpoints."""
import json, base64, pytest
from datetime import datetime, timedelta


def _cursor(dt: datetime) -> str:
    import base64, json
    payload = json.dumps({"t": dt.strftime("%Y-%m-%dT%H:%M:%S.%f") + "Z", "v": 1})
    return base64.urlsafe_b64encode(payload.encode()).decode().rstrip("=")

def future_cursor(): return _cursor(datetime.utcnow() + timedelta(hours=1))
def past_cursor():   return _cursor(datetime.utcnow() - timedelta(hours=1))


# ── No cursor → 200 + X-Sync-Cursor ─────────────────────────────────────────

def test_accounts_no_cursor_returns_200_and_cursor(client, make_account):
    make_account()
    r = client.get("/api/v1/accounts")
    assert r.status_code == 200
    assert "X-Sync-Cursor" in r.headers


# ── Future cursor → 304 + new cursor + no body ───────────────────────────────

def test_accounts_future_cursor_304(client, make_account):
    make_account()
    old = future_cursor()
    r = client.get("/api/v1/accounts", headers={"If-Sync-Cursor": old})
    assert r.status_code == 304
    assert r.data == b""
    assert r.headers["X-Sync-Cursor"] != old  # always a new cursor


def test_transactions_future_cursor_304(client, make_transaction):
    make_transaction()
    r = client.get("/api/v1/transactions", headers={"If-Sync-Cursor": future_cursor()})
    assert r.status_code == 304
    assert r.data == b""
    assert "X-Sync-Cursor" in r.headers


def test_transfers_future_cursor_304(client, make_transfer):
    make_transfer()
    r = client.get("/api/v1/transfers", headers={"If-Sync-Cursor": future_cursor()})
    assert r.status_code == 304


def test_categories_future_cursor_304(client, make_category):
    make_category()
    r = client.get("/api/v1/categories", headers={"If-Sync-Cursor": future_cursor()})
    assert r.status_code == 304


def test_exchange_rates_future_cursor_304(client, make_exchange_rate):
    make_exchange_rate()
    r = client.get("/api/v1/exchange-rates", headers={"If-Sync-Cursor": future_cursor()})
    assert r.status_code == 304


# ── Past cursor → 200 + changed records ──────────────────────────────────────

def test_transactions_past_cursor_returns_flat_list(client, make_transaction):
    """With cursor, response is flat list, not paginated wrapper."""
    make_transaction()
    r = client.get("/api/v1/transactions", headers={"If-Sync-Cursor": past_cursor()})
    assert r.status_code == 200
    body = json.loads(r.data)
    # Flat list: data is a list, NOT {"items": ..., "pagination": ...}
    assert isinstance(body["data"], list)


def test_transactions_no_cursor_returns_paginated(client, make_transaction):
    """Without cursor, transactions returns paginated wrapper."""
    make_transaction()
    r = client.get("/api/v1/transactions")
    assert r.status_code == 200
    body = json.loads(r.data)
    assert "items" in body["data"]


def test_transfers_past_cursor_returns_flat_list(client, make_transfer):
    make_transfer()
    r = client.get("/api/v1/transfers", headers={"If-Sync-Cursor": past_cursor()})
    assert r.status_code == 200
    body = json.loads(r.data)
    assert isinstance(body["data"], list)


def test_exchange_rates_past_cursor_returns_flat_list(client, make_exchange_rate):
    """With cursor, exchange-rates returns flat list (not {rates, last_updated})."""
    make_exchange_rate()
    r = client.get("/api/v1/exchange-rates", headers={"If-Sync-Cursor": past_cursor()})
    assert r.status_code == 200
    body = json.loads(r.data)
    assert isinstance(body["data"], list)


# ── Invalid cursor → treated as no cursor (full sync) ────────────────────────

def test_invalid_cursor_treated_as_no_cursor(client, make_account):
    make_account()
    r = client.get("/api/v1/accounts", headers={"If-Sync-Cursor": "invalid!!!"})
    assert r.status_code == 200
    assert "X-Sync-Cursor" in r.headers


# ── Empty DB + no cursor → 200 (not 304) ────────────────────────────────────

def test_empty_db_no_cursor_returns_200(client):
    r = client.get("/api/v1/accounts")
    assert r.status_code == 200
```

- [ ] **Step 2: Verificar que los tests fallan**

```bash
cd backend && python -m pytest tests/api/test_sync_cursor_endpoints.py -v 2>&1 | head -20
```

- [ ] **Step 3: Actualizar `list_accounts` en `backend/app/api/accounts.py`**

Agregar imports:
```python
from flask import jsonify, make_response
from app.utils.sync_cursor import encode_cursor, decode_cursor
```

Reemplazar el cuerpo de `list_accounts()`:

```python
@accounts_bp.route("", methods=["GET"])
def list_accounts():
    try:
        updated_since = decode_cursor(request.headers.get("If-Sync-Cursor"))
        new_cursor = encode_cursor()
        include_archived = request.args.get("include_archived", "false").lower() == "true"

        if updated_since is not None:
            accounts = account_service.get_all_with_balances_since(updated_since)
            if not accounts:
                resp = make_response("", 304)
                resp.headers["X-Sync-Cursor"] = new_cursor
                return resp
            data = [
                {**AccountResponse.model_validate(a).model_dump(mode="json"),
                 "balance": str(bal)}
                for a, bal in accounts
            ]
        else:
            accounts = account_service.get_all_with_balances(include_archived=include_archived)
            data = [
                {**AccountResponse.model_validate(a).model_dump(mode="json"),
                 "balance": str(bal)}
                for a, bal in accounts
            ]

        resp = make_response(jsonify({"success": True, "data": data}), 200)
        resp.headers["X-Sync-Cursor"] = new_cursor
        return resp

    except Exception as e:
        return error_response(f"Error al listar cuentas: {str(e)}", status_code=500)
```

- [ ] **Step 4: Actualizar `list_transactions` en `backend/app/api/transactions.py`**

Agregar imports:
```python
from flask import jsonify, make_response
from app.utils.sync_cursor import encode_cursor, decode_cursor
```

Al inicio de `list_transactions()`, antes del bloque de query params existente:

```python
@transactions_bp.route("", methods=["GET"])
def list_transactions():
    try:
        updated_since = decode_cursor(request.headers.get("If-Sync-Cursor"))
        new_cursor = encode_cursor()

        if updated_since is not None:
            # Incremental mode: flat list, no pagination, no other filters
            transactions, _ = transaction_service.get_filtered(
                updated_since=updated_since, limit=10000, offset=0
            )
            if not transactions:
                resp = make_response("", 304)
                resp.headers["X-Sync-Cursor"] = new_cursor
                return resp
            # Use TransactionResponse (same schema as the list endpoint's paginated path)
            # TransactionWithRelations requires eager-loaded relations (selectinload)
            # which get_filtered() does not use — avoid lazy-load errors.
            data = [TransactionResponse.model_validate(t).model_dump(mode="json")
                    for t in transactions]
            resp = make_response(jsonify({"success": True, "data": data}), 200)
            resp.headers["X-Sync-Cursor"] = new_cursor
            return resp

        # Full sync mode: existing paginated logic (unchanged below)
        # ... keep the rest of the existing function unchanged ...
```

Para el path de paginación (full sync), convertir el `return paginated_response(...)` final a:
```python
pag_body, status = paginated_response(transactions, total, page, per_page)
resp = make_response(jsonify(pag_body), status)
resp.headers["X-Sync-Cursor"] = new_cursor
return resp
```

- [ ] **Step 5: Aplicar el mismo patrón a `list_transfers` en `backend/app/api/transfers.py`**

El endpoint usa `TransferResponse` para serializar (línea 95 del archivo). Mismo patrón:

```python
from flask import jsonify, make_response
from app.utils.sync_cursor import encode_cursor, decode_cursor

# Al inicio del try en list_transfers():
updated_since = decode_cursor(request.headers.get("If-Sync-Cursor"))
new_cursor = encode_cursor()

if updated_since is not None:
    transfers, _ = transfer_service.get_filtered(
        updated_since=updated_since, limit=10000, offset=0
    )
    if not transfers:
        resp = make_response("", 304)
        resp.headers["X-Sync-Cursor"] = new_cursor
        return resp
    data = [TransferResponse.model_validate(t).model_dump(mode="json") for t in transfers]
    resp = make_response(jsonify({"success": True, "data": data}), 200)
    resp.headers["X-Sync-Cursor"] = new_cursor
    return resp
# else: existing paginated logic, convert final return to make_response + header
```

`TransferResponse` ya está importado en el archivo (línea 13).

- [ ] **Step 6: Actualizar `CategoryService.get_all()` para propagar `updated_since`**

Antes de modificar el endpoint, agregar `updated_since` al servicio en `backend/app/services/category.py`:

```python
from datetime import datetime  # agregar al import

def get_all(
    self,
    type: str | None = None,
    include_archived: bool = False,
    updated_since: datetime | None = None,  # ← nuevo
) -> list[Category]:
    if type:
        from app.models.category import CategoryType
        return self.repository.get_by_type(CategoryType(type))
    return self.repository.get_all(
        include_archived=include_archived,
        updated_since=updated_since,
    )
```

- [ ] **Step 7: Actualizar `list_categories` en `backend/app/api/categories.py`**

El endpoint usa `category_service` (variable) y `CategoryResponse` (schema). Mismo patrón:

```python
from flask import jsonify, make_response
from app.utils.sync_cursor import encode_cursor, decode_cursor

# Al inicio del try en list_categories():
updated_since = decode_cursor(request.headers.get("If-Sync-Cursor"))
new_cursor = encode_cursor()
include_archived = request.args.get("include_archived", "false").lower() == "true"

if updated_since is not None:
    # Incremental: include_archived=True para propagar cambios de active
    categories = category_service.get_all(
        updated_since=updated_since,
        include_archived=True,
    )
    if not categories:
        resp = make_response("", 304)
        resp.headers["X-Sync-Cursor"] = new_cursor
        return resp
    data = [CategoryResponse.model_validate(c).model_dump(mode="json") for c in categories]
    resp = make_response(jsonify({"success": True, "data": data}), 200)
    resp.headers["X-Sync-Cursor"] = new_cursor
    return resp
# else: existing behavior (agrega X-Sync-Cursor al final del path normal)

- [ ] **Step 8: Actualizar `DashboardCrudService.list_dashboards()` para aceptar `updated_since`**

En `backend/app/services/dashboard_crud.py`, el método `list_dashboards()` llama a `self.repo.get_all_ordered()`:

```python
from datetime import datetime  # agregar al import

def list_dashboards(self, updated_since: datetime | None = None) -> list[Dashboard]:
    """Return all dashboards ordered by sort_order."""
    return self.repo.get_all_ordered(updated_since=updated_since)
```

- [ ] **Step 9: Actualizar `list_dashboards` en `backend/app/api/dashboards.py`**

El blueprint usa `_service = DashboardCrudService()` (variable `_service`). El schema es el que ya usa `list_dashboards()` — revisar el blueprint para ver qué schema serializa la lista:

```python
from flask import jsonify, make_response
from app.utils.sync_cursor import encode_cursor, decode_cursor

# Al inicio del try en list_dashboards():
updated_since = decode_cursor(request.headers.get("If-Sync-Cursor"))
new_cursor = encode_cursor()

if updated_since is not None:
    dashboards = _service.list_dashboards(updated_since=updated_since)
    if not dashboards:
        resp = make_response("", 304)
        resp.headers["X-Sync-Cursor"] = new_cursor
        return resp
    # Usar el mismo schema que usa la lista normal (ver código existente)
    data = [<schema>.model_validate(d).model_dump(mode="json") for d in dashboards]
    resp = make_response(jsonify({"success": True, "data": data}), 200)
    resp.headers["X-Sync-Cursor"] = new_cursor
    return resp
# else: existing behavior + header
```

Leer las líneas 55-70 del archivo para ver el schema exacto usado en el path normal y reutilizarlo.

- [ ] **Step 10: Actualizar `list_exchange_rates` en `backend/app/api/exchange_rates.py`**

```python
from flask import jsonify, make_response
from app.utils.sync_cursor import encode_cursor, decode_cursor

# Al inicio del try:
updated_since = decode_cursor(request.headers.get("If-Sync-Cursor"))
new_cursor = encode_cursor()

if updated_since is not None:
    rates = exchange_rate_service.get_all(updated_since=updated_since)
    if not rates:
        resp = make_response("", 304)
        resp.headers["X-Sync-Cursor"] = new_cursor
        return resp
    # Flat list (not ExchangeRatesListResponse wrapper)
    data = [ExchangeRateResponse.model_validate(r).model_dump(mode="json") for r in rates]
    resp = make_response(jsonify({"success": True, "data": data}), 200)
    resp.headers["X-Sync-Cursor"] = new_cursor
    return resp

# Full sync path (existing):
rates = exchange_rate_service.get_all()
last_updated = exchange_rate_service.get_last_updated()
response_obj = ExchangeRatesListResponse(
    rates=[ExchangeRateResponse.model_validate(r) for r in rates],
    last_updated=last_updated,
)
body = {"success": True, "data": response_obj.model_dump(mode="json")}
resp = make_response(jsonify(body), 200)
resp.headers["X-Sync-Cursor"] = new_cursor
return resp
```

- [ ] **Step 11: Correr los tests de integración**

```bash
cd backend && python -m pytest tests/api/test_sync_cursor_endpoints.py -v
```

- [ ] **Step 12: Correr suite completa**

```bash
cd backend && python -m pytest -v
```
Expected: todos pasan

- [ ] **Step 13: Commit**

```bash
git add backend/app/api/ backend/app/services/ backend/tests/api/test_sync_cursor_endpoints.py
git commit -m "feat(sync): add cursor-based incremental sync to all GET endpoints"
```

---

## Verificación final

- [ ] **Suite completa limpia**

```bash
cd backend && python -m pytest -v
```

- [ ] **Actualizar Notion ticket a Done**

Actualizar https://www.notion.so/32379901d1b8811c9d93e2846d707336 Status → `Done`.
