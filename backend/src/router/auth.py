# src/router/auth.py

from typing import Literal, Optional

import httpx
from fastapi import APIRouter, Depends, HTTPException, Header, Path, status
from pydantic import BaseModel, Field

from config.settings import settings

router = APIRouter(prefix="/api/login", tags=["auth"])


# --------------------------------------------------
# Pydantic Models
# --------------------------------------------------

class TokenRequest(BaseModel):
    """Request body for OAuth token exchange"""
    code: str = Field(..., description="Authorization code from OAuth redirect")
    redirect_uri: str = Field(..., description="Must match the redirect URI used in authorization request")
    code_verifier: str = Field(..., min_length=43, max_length=128, description="PKCE code verifier")


class UserInfo(BaseModel):
    """User info from OAuth provider"""
    sub: str
    email: str
    name: Optional[str] = None
    picture: Optional[str] = None


class TokenResponse(BaseModel):
    """Response from OAuth token exchange"""
    access_token: str
    refresh_token: Optional[str] = None
    id_token: Optional[str] = None
    expires_in: Optional[int] = None
    userinfo: UserInfo


class MeResponse(BaseModel):
    """Current user information response"""
    sub: Optional[str] = None
    email: str
    name: Optional[str] = None
    picture: Optional[str] = None
    provider: Literal["google", "authentik"]
    role: Optional[str] = None


# --------------------------------------------------
# Token Verification
# --------------------------------------------------

async def verify_google_token(token: str) -> dict:
    """Verify Google access token by calling userinfo endpoint."""
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(
            settings.google.userinfo_url,
            headers={"Authorization": f"Bearer {token}"},
        )
        if resp.status_code != 200:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid Google token",
            )
        return resp.json()


async def verify_authentik_token(token: str) -> dict:
    """Verify Authentik access token by calling userinfo endpoint."""
    if not settings.authentik.url:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentik not configured",
        )
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(
            settings.authentik.userinfo_url,
            headers={"Authorization": f"Bearer {token}"},
        )
        if resp.status_code != 200:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid Authentik token",
            )
        return resp.json()


async def verify_bearer_token(
    authorization: Optional[str] = Header(None),
) -> dict:
    """Verify token from Authorization header (tries Google then Authentik)"""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Authorization header",
        )

    token = authorization.removeprefix("Bearer ").strip()

    # Try Google first
    try:
        userinfo = await verify_google_token(token)
        userinfo["_provider"] = "google"
        return userinfo
    except HTTPException:
        pass

    # Try Authentik
    try:
        userinfo = await verify_authentik_token(token)
        userinfo["_provider"] = "authentik"
        return userinfo
    except HTTPException:
        pass

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired token",
    )


# --------------------------------------------------
# Endpoints
# --------------------------------------------------

@router.get("/me", response_model=MeResponse)
async def me(userinfo: dict = Depends(verify_bearer_token)) -> MeResponse:
    """Get current user information. Requires valid Bearer token."""
    provider = userinfo.get("_provider", "authentik")
    return MeResponse(
        sub=userinfo.get("sub"),
        email=userinfo.get("email", ""),
        name=userinfo.get("preferred_username") or userinfo.get("name"),
        picture=userinfo.get("picture"),
        provider=provider,
        role=None,  # Add role logic here if needed
    )


@router.post("/{provider}/token", response_model=TokenResponse)
async def token_exchange(
    request: TokenRequest,
    provider: Literal["google", "authentik"] = Path(..., description="OAuth provider"),
) -> TokenResponse:
    """Exchange authorization code for tokens. Supports Google and Authentik."""
    if provider == "google":
        return await _exchange_google(request)
    else:
        return await _exchange_authentik(request)


async def _exchange_google(request: TokenRequest) -> TokenResponse:
    """Exchange Google authorization code for tokens."""
    if not settings.google.client_secret:
        raise HTTPException(status_code=500, detail="Google OAuth not configured")

    async with httpx.AsyncClient(timeout=15.0) as client:
        try:
            resp = await client.post(
                settings.google.token_url,
                data={
                    "grant_type": "authorization_code",
                    "code": request.code,
                    "redirect_uri": request.redirect_uri,
                    "client_id": settings.google.client_id,
                    "client_secret": settings.google.client_secret,
                    "code_verifier": request.code_verifier,
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )

            if resp.status_code != 200:
                detail = resp.json() if "application/json" in resp.headers.get("content-type", "") else resp.text
                raise HTTPException(status_code=400, detail=f"Google token exchange failed: {detail}")

            tokens = resp.json()

            # Fetch user info
            userinfo_resp = await client.get(
                settings.google.userinfo_url,
                headers={"Authorization": f"Bearer {tokens['access_token']}"},
            )

            if userinfo_resp.status_code != 200:
                raise HTTPException(status_code=400, detail="Failed to fetch Google user info")

            userinfo = userinfo_resp.json()

            return TokenResponse(
                access_token=tokens["access_token"],
                refresh_token=tokens.get("refresh_token"),
                id_token=tokens.get("id_token"),
                expires_in=tokens.get("expires_in"),
                userinfo=UserInfo(
                    sub=userinfo["sub"],
                    email=userinfo["email"],
                    name=userinfo.get("name"),
                    picture=userinfo.get("picture"),
                ),
            )

        except httpx.TimeoutException:
            raise HTTPException(status_code=504, detail="Google OAuth timeout")
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))


async def _exchange_authentik(request: TokenRequest) -> TokenResponse:
    """Exchange Authentik authorization code for tokens (public client)."""
    if not settings.authentik.url or not settings.authentik.client_id:
        raise HTTPException(status_code=500, detail="Authentik OAuth not configured")

    async with httpx.AsyncClient(timeout=15.0) as client:
        try:
            resp = await client.post(
                settings.authentik.token_url,
                data={
                    "grant_type": "authorization_code",
                    "code": request.code,
                    "redirect_uri": request.redirect_uri,
                    "client_id": settings.authentik.client_id,
                    "code_verifier": request.code_verifier,
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )

            if resp.status_code != 200:
                detail = resp.json() if "application/json" in resp.headers.get("content-type", "") else resp.text
                raise HTTPException(status_code=400, detail=f"Authentik token exchange failed: {detail}")

            tokens = resp.json()

            # Fetch user info
            userinfo_resp = await client.get(
                settings.authentik.userinfo_url,
                headers={"Authorization": f"Bearer {tokens['access_token']}"},
            )

            if userinfo_resp.status_code != 200:
                raise HTTPException(status_code=400, detail="Failed to fetch Authentik user info")

            userinfo = userinfo_resp.json()

            return TokenResponse(
                access_token=tokens["access_token"],
                refresh_token=tokens.get("refresh_token"),
                id_token=tokens.get("id_token"),
                expires_in=tokens.get("expires_in"),
                userinfo=UserInfo(
                    sub=userinfo["sub"],
                    email=userinfo["email"],
                    name=userinfo.get("preferred_username") or userinfo.get("name"),
                    picture=userinfo.get("picture"),
                ),
            )

        except httpx.TimeoutException:
            raise HTTPException(status_code=504, detail="Authentik OAuth timeout")
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
