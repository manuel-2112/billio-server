from typing import Annotated

from fastapi import Depends

from app.models.auth.functions import Authenticate, authorize, authorize_limited
from app.models.auth.schemas import TokenDecode, TokenEncode
from app.models.staff_user import StaffUser

# Token authorization (just validates token)
authorizeDep = Annotated[TokenDecode, Depends(authorize)]

# Token authorization with rate limiting
authorizeLimitDep = Annotated[TokenDecode, Depends(authorize_limited)]

# Authorize and load user from token
authorizeLoadDep = Annotated[StaffUser, Depends(Authenticate().from_token)]

# Authorize and load user with relationships
authorizeLoadRelationshipsDep = Annotated[StaffUser, Depends(Authenticate(True).from_token)]

# Authenticate with credentials (login)
authenticateDep = Annotated[StaffUser, Depends(Authenticate())]

# Authenticate and return token
authenticateTokenDep = Annotated[TokenEncode, Depends(Authenticate.to_token)]

# Authenticate with relationships
authenticateRelationshipsDep = Annotated[StaffUser, Depends(Authenticate(True))]

__all__ = [
    "authorizeDep",
    "authorizeLimitDep",
    "authorizeLoadDep",
    "authorizeLoadRelationshipsDep",
    "authenticateDep",
    "authenticateTokenDep",
    "authenticateRelationshipsDep",
]
