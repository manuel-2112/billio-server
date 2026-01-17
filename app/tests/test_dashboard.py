"""
Tests for dashboard API endpoints.
"""

import pytest
from httpx import AsyncClient

from app.models.account import Account
from app.models.location import Location
from app.models.restaurant import Restaurant
from app.models.table import Table


@pytest.mark.anyio
async def test_list_tables(
    async_client: AsyncClient,
    admin_token: str,
):
    """Test listing all tables with status."""
    response = await async_client.get(
        "/api/v1/dashboard/tables",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200

    data = response.json()
    assert "tables" in data
    assert "location_name" in data
    assert "restaurant_name" in data
    assert len(data["tables"]) == 5  # 5 tables from seed data


@pytest.mark.anyio
async def test_list_tables_unauthorized(
    async_client: AsyncClient,
):
    """Test that listing tables requires authentication."""
    response = await async_client.get("/api/v1/dashboard/tables")
    assert response.status_code == 401


@pytest.mark.anyio
async def test_add_item_to_table(
    async_client: AsyncClient,
    admin_token: str,
    test_table: Table,
):
    """Test adding an item to a table."""
    response = await async_client.post(
        f"/api/v1/dashboard/tables/{test_table.id}/items",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "name": "Hamburguesa",
            "quantity": 2,
            "unit_price": 8500,
        },
    )
    assert response.status_code == 201

    data = response.json()
    assert data["status"] == "open"
    assert len(data["items"]) == 1
    assert data["items"][0]["name"] == "Hamburguesa"
    assert data["items"][0]["quantity"] == 2
    assert data["items"][0]["total_price"] == 17000  # 2 * 8500
    assert data["subtotal"] == 17000
    assert data["tax"] == 3230  # 19% of 17000


@pytest.mark.anyio
async def test_add_multiple_items(
    async_client: AsyncClient,
    admin_token: str,
    test_table: Table,
):
    """Test adding multiple items to a table."""
    # Add first item
    await async_client.post(
        f"/api/v1/dashboard/tables/{test_table.id}/items",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"name": "Pizza", "quantity": 1, "unit_price": 12000},
    )

    # Add second item
    response = await async_client.post(
        f"/api/v1/dashboard/tables/{test_table.id}/items",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"name": "Cerveza", "quantity": 3, "unit_price": 3500},
    )
    assert response.status_code == 201

    data = response.json()
    assert len(data["items"]) == 2
    # Pizza (12000) + Cerveza (3 * 3500 = 10500) = 22500
    assert data["subtotal"] == 22500
    assert data["tax"] == 4275  # 19% of 22500


@pytest.mark.anyio
async def test_remove_item(
    async_client: AsyncClient,
    admin_token: str,
    test_account: Account,
):
    """Test removing an item from an account."""
    # Get the first item ID
    item_id = test_account.items[0].id

    response = await async_client.delete(
        f"/api/v1/dashboard/items/{item_id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200

    data = response.json()
    assert len(data["items"]) == 1  # Only one item left


@pytest.mark.anyio
async def test_cancel_account(
    async_client: AsyncClient,
    admin_token: str,
    test_account: Account,
):
    """Test cancelling an account."""
    response = await async_client.post(
        f"/api/v1/dashboard/accounts/{test_account.id}/cancel",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200

    data = response.json()
    assert data["status"] == "cancelled"


@pytest.mark.anyio
async def test_get_account_history_empty(
    async_client: AsyncClient,
    admin_token: str,
):
    """Test getting account history when no paid accounts exist."""
    response = await async_client.get(
        "/api/v1/dashboard/accounts",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200

    data = response.json()
    assert data["accounts"] == []
    assert data["total_revenue"] == 0
    assert data["total_tips"] == 0
    assert data["count"] == 0


@pytest.mark.anyio
async def test_get_table_account(
    async_client: AsyncClient,
    admin_token: str,
    test_table: Table,
    test_account: Account,
):
    """Test getting a specific table's account."""
    response = await async_client.get(
        f"/api/v1/dashboard/tables/{test_table.id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200

    data = response.json()
    assert data["id"] == str(test_account.id)
    assert data["status"] == "open"


@pytest.mark.anyio
async def test_get_table_account_not_found(
    async_client: AsyncClient,
    admin_token: str,
    test_table: Table,
):
    """Test getting account for table without active account."""
    response = await async_client.get(
        f"/api/v1/dashboard/tables/{test_table.id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "No hay cuenta abierta para esta mesa"
