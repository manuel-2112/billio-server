"""
Tests for public API endpoints.
"""

import pytest
from httpx import AsyncClient

from app.models.account import Account
from app.models.location import Location
from app.models.restaurant import Restaurant
from app.models.table import Table


@pytest.mark.anyio
async def test_get_table_account_success(
    async_client: AsyncClient,
    test_restaurant: Restaurant,
    test_location: Location,
    test_table: Table,
    test_account: Account,
):
    """Test getting account for a table with open account."""
    response = await async_client.get(
        f"/api/v1/{test_restaurant.slug}/{test_location.slug}/{test_table.number}"
    )
    assert response.status_code == 200

    data = response.json()
    assert data["id"] == str(test_account.id)
    assert data["status"] == "open"
    assert len(data["items"]) == 2
    assert data["subtotal"] == 27500  # (2 * 8500) + (3 * 3500)
    assert data["tax"] == 5225  # 19% of subtotal


@pytest.mark.anyio
async def test_get_table_account_not_found(
    async_client: AsyncClient,
):
    """Test getting account for non-existent table."""
    response = await async_client.get("/api/v1/nonexistent/location/1")
    assert response.status_code == 404
    assert response.json()["detail"] == "Mesa no encontrada"


@pytest.mark.anyio
async def test_get_table_no_active_account(
    async_client: AsyncClient,
    test_restaurant: Restaurant,
    test_location: Location,
    test_table: Table,
):
    """Test getting account when table has no open account."""
    response = await async_client.get(
        f"/api/v1/{test_restaurant.slug}/{test_location.slug}/{test_table.number}"
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "No hay cuenta abierta para esta mesa"


@pytest.mark.anyio
async def test_update_tip_percentage(
    async_client: AsyncClient,
    test_restaurant: Restaurant,
    test_location: Location,
    test_table: Table,
    test_account: Account,
):
    """Test updating tip by percentage."""
    response = await async_client.patch(
        f"/api/v1/accounts/{test_account.id}/tip",
        json={"tip_percentage": 15},
    )
    assert response.status_code == 200

    data = response.json()
    expected_tip = int(27500 * 0.15)  # 15% of subtotal
    assert data["tip"] == expected_tip


@pytest.mark.anyio
async def test_update_tip_amount(
    async_client: AsyncClient,
    test_restaurant: Restaurant,
    test_location: Location,
    test_table: Table,
    test_account: Account,
):
    """Test updating tip by fixed amount."""
    response = await async_client.patch(
        f"/api/v1/accounts/{test_account.id}/tip",
        json={"tip_amount": 5000},
    )
    assert response.status_code == 200

    data = response.json()
    assert data["tip"] == 5000
