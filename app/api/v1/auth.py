"""
Authentication routes for staff login.
"""

from fastapi import APIRouter, status

from app.models.auth.dependencies import authenticateTokenDep
from app.models.auth.schemas import TokenDecode, TokenEncode
from app.models.auth.token import Token

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post(
    "/token",
    response_model=TokenEncode,
    status_code=status.HTTP_200_OK,
    summary="Login and get access token",
    description="Authenticate with email and password to get a JWT token.",
)
async def get_token(token: authenticateTokenDep):
    """
    Staff login endpoint.

    Returns a JWT token for authenticated staff users.
    """
    return token


@router.get(
    "/introspect",
    response_model=TokenDecode,
    status_code=status.HTTP_200_OK,
    summary="Validate and decode a token",
    description="Check if a token is valid and return its decoded content.",
)
async def introspect(token: str):
    """
    Token introspection endpoint.

    Validates a token and returns its decoded content.
    """
    return Token.decode(token)
