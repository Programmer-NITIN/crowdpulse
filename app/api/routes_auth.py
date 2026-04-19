"""
api/routes_auth.py
------------------
Firebase Authentication routes — token verification and user identity.
"""

from typing import Optional

from fastapi import APIRouter, HTTPException, Header

from app.google_services.firebase_auth import verify_token

router = APIRouter()


@router.get(
    "/auth/verify",
    summary="Verify a Firebase ID token",
)
async def verify_auth_token(
    authorization: Optional[str] = Header(None, description="Bearer <id_token>"),
):
    """Verifies a Firebase ID token from the Authorization header.

    Accepts: Authorization: Bearer <token>
    In mock mode, tokens starting with 'mock-' are always accepted.
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or malformed Authorization header.")

    token = authorization[7:]  # Strip "Bearer "
    claims = verify_token(token)

    if claims is None:
        raise HTTPException(status_code=401, detail="Invalid or expired token.")

    return {
        "authenticated": True,
        "uid": claims.get("uid"),
        "email": claims.get("email"),
        "name": claims.get("name"),
    }
