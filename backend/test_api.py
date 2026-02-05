"""
Simple API testing script.

This script demonstrates how to use the Wallet API with real HTTP requests.
Run the server first: python run.py
"""

import requests
import json
from datetime import date, timedelta

BASE_URL = "http://localhost:5000/api/v1"


def print_response(title, response):
    """Pretty print API response."""
    print(f"\n{'='*60}")
    print(f"{title}")
    print(f"{'='*60}")
    print(f"Status: {response.status_code}")
    try:
        data = response.json()
        print(json.dumps(data, indent=2, default=str))
    except:
        print(response.text)


def test_health_check():
    """Test health check endpoint."""
    response = requests.get("http://localhost:5000/health")
    print_response("HEALTH CHECK", response)
    return response.status_code == 200


def test_accounts():
    """Test account endpoints."""
    # Create account
    account_data = {
        "nombre": "Test Checking Account",
        "tipo": "debito",
        "divisa": "MXN",
        "descripcion": "Test account for API testing",
        "tags": ["test", "checking"]
    }
    response = requests.post(f"{BASE_URL}/accounts", json=account_data)
    print_response("CREATE ACCOUNT", response)

    if response.status_code != 201:
        return None

    account = response.json()["data"]
    account_id = account["id"]

    # Get account
    response = requests.get(f"{BASE_URL}/accounts/{account_id}")
    print_response("GET ACCOUNT", response)

    # List accounts
    response = requests.get(f"{BASE_URL}/accounts")
    print_response("LIST ACCOUNTS", response)

    # Update account
    update_data = {
        "descripcion": "Updated test account"
    }
    response = requests.put(f"{BASE_URL}/accounts/{account_id}", json=update_data)
    print_response("UPDATE ACCOUNT", response)

    return account_id


def test_categories():
    """Test category endpoints."""
    # Create parent category
    category_data = {
        "nombre": "Test Expenses",
        "tipo": "gasto",
        "icono": "shopping-cart",
        "color": "#EF4444"
    }
    response = requests.post(f"{BASE_URL}/categories", json=category_data)
    print_response("CREATE CATEGORY", response)

    if response.status_code != 201:
        return None

    category = response.json()["data"]
    category_id = category["id"]

    # Create subcategory
    subcategory_data = {
        "nombre": "Test Groceries",
        "tipo": "gasto",
        "icono": "shopping-bag",
        "categoria_padre_id": category_id
    }
    response = requests.post(f"{BASE_URL}/categories", json=subcategory_data)
    print_response("CREATE SUBCATEGORY", response)

    # Get category with subcategories
    response = requests.get(f"{BASE_URL}/categories/{category_id}")
    print_response("GET CATEGORY WITH SUBCATEGORIES", response)

    # List categories
    response = requests.get(f"{BASE_URL}/categories")
    print_response("LIST CATEGORIES", response)

    return category_id


def test_transactions(account_id, category_id):
    """Test transaction endpoints."""
    if not account_id or not category_id:
        print("\nSkipping transaction tests (missing account or category)")
        return None

    # Create expense transaction
    transaction_data = {
        "tipo": "gasto",
        "monto": 150.75,
        "fecha": str(date.today()),
        "cuenta_id": account_id,
        "categoria_id": category_id,
        "titulo": "Test Grocery Shopping",
        "descripcion": "Weekly groceries",
        "tags": ["food", "weekly"]
    }
    response = requests.post(f"{BASE_URL}/transactions", json=transaction_data)
    print_response("CREATE TRANSACTION (EXPENSE)", response)

    if response.status_code != 201:
        return None

    transaction = response.json()["data"]
    transaction_id = transaction["id"]

    # Create income transaction
    income_data = {
        "tipo": "ingreso",
        "monto": 5000.00,
        "fecha": str(date.today() - timedelta(days=1)),
        "cuenta_id": account_id,
        "categoria_id": category_id,  # This should fail if category is expense-only
        "titulo": "Test Salary",
        "descripcion": "Monthly salary"
    }
    response = requests.post(f"{BASE_URL}/transactions", json=income_data)
    print_response("CREATE TRANSACTION (INCOME - may fail)", response)

    # List transactions
    response = requests.get(f"{BASE_URL}/transactions")
    print_response("LIST TRANSACTIONS", response)

    # List with filters
    params = {
        "cuenta_id": account_id,
        "tipo": "gasto",
        "page": 1,
        "limit": 10
    }
    response = requests.get(f"{BASE_URL}/transactions", params=params)
    print_response("LIST TRANSACTIONS (FILTERED)", response)

    # Update transaction
    update_data = {
        "monto": 175.00,
        "descripcion": "Weekly groceries (updated)"
    }
    response = requests.put(f"{BASE_URL}/transactions/{transaction_id}", json=update_data)
    print_response("UPDATE TRANSACTION", response)

    return transaction_id


def test_transfers(account_id):
    """Test transfer endpoints."""
    if not account_id:
        print("\nSkipping transfer tests (missing account)")
        return None

    # Create second account for transfer
    account_data = {
        "nombre": "Test Savings Account",
        "tipo": "debito",
        "divisa": "MXN",
        "descripcion": "Savings account for transfers"
    }
    response = requests.post(f"{BASE_URL}/accounts", json=account_data)

    if response.status_code != 201:
        print("\nCouldn't create second account for transfer test")
        return None

    account2_id = response.json()["data"]["id"]

    # Create transfer
    transfer_data = {
        "cuenta_origen_id": account_id,
        "cuenta_destino_id": account2_id,
        "monto": 500.00,
        "fecha": str(date.today()),
        "descripcion": "Test transfer",
        "tags": ["savings"]
    }
    response = requests.post(f"{BASE_URL}/transfers", json=transfer_data)
    print_response("CREATE TRANSFER", response)

    if response.status_code != 201:
        return None

    transfer = response.json()["data"]
    transfer_id = transfer["id"]

    # List transfers
    response = requests.get(f"{BASE_URL}/transfers")
    print_response("LIST TRANSFERS", response)

    # Update transfer
    update_data = {
        "monto": 600.00,
        "descripcion": "Updated test transfer"
    }
    response = requests.put(f"{BASE_URL}/transfers/{transfer_id}", json=update_data)
    print_response("UPDATE TRANSFER", response)

    return transfer_id


def test_dashboard():
    """Test dashboard endpoints."""
    # Get complete dashboard
    response = requests.get(f"{BASE_URL}/dashboard")
    print_response("GET DASHBOARD", response)

    # Get net worth
    response = requests.get(f"{BASE_URL}/dashboard/net-worth")
    print_response("GET NET WORTH", response)

    # Get monthly summary
    params = {
        "mes": date.today().month,
        "anio": date.today().year
    }
    response = requests.get(f"{BASE_URL}/dashboard/summary", params=params)
    print_response("GET MONTHLY SUMMARY", response)

    # Get recent activity
    response = requests.get(f"{BASE_URL}/dashboard/recent-activity")
    print_response("GET RECENT ACTIVITY", response)


def main():
    """Run all API tests."""
    print("\n" + "="*60)
    print("WALLET API TEST SUITE")
    print("="*60)
    print("\nMake sure the server is running: python run.py\n")

    # Test health check
    if not test_health_check():
        print("\nHealth check failed. Is the server running?")
        return

    # Test endpoints
    account_id = test_accounts()
    category_id = test_categories()
    transaction_id = test_transactions(account_id, category_id)
    transfer_id = test_transfers(account_id)
    test_dashboard()

    print("\n" + "="*60)
    print("TEST SUITE COMPLETED")
    print("="*60)
    print("\nNote: Some tests may fail if business rules are violated")
    print("(e.g., creating income transaction with expense-only category)")


if __name__ == "__main__":
    main()
