# src/router/auth.py
import os
from fastapi import APIRouter, HTTPException, Header, status
from pydantic import BaseModel
from typing import Optional
import httpx

router = APIRouter(prefix="/api/login", tags=["auth"])

# Google config
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "")
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v3/userinfo"


class GoogleTokenRequest(BaseModel):
    code: str
    redirect_uri: str
    code_verifier: str


async def verify_google_token(token: str) -> dict:
    """Verify Google access token by calling userinfo endpoint."""
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(
            GOOGLE_USERINFO_URL,
            headers={"Authorization": f"Bearer {token}"},
        )
        if resp.status_code != 200:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid Google token",
            )
        return resp.json()


async def verify_bearer_token(
    authorization: Optional[str] = Header(None),
) -> dict:
    """Verify token from Authorization header"""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Authorization header",
        )

    token = authorization.removeprefix("Bearer ").strip()

    # Verify with Google userinfo endpoint
    try:
        userinfo = await verify_google_token(token)
        userinfo["_provider"] = "google"
        return userinfo
    except HTTPException:
        pass

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired token",
    )


@router.post("/google/token")
async def google_token_exchange(request: GoogleTokenRequest):
    """Exchange Google authorization code for tokens (handles client secret server-side)"""
    if not GOOGLE_CLIENT_SECRET:
        raise HTTPException(
            status_code=500,
            detail="Google OAuth not configured (missing client secret)",
        )

    async with httpx.AsyncClient(timeout=15.0) as client:
        try:
            resp = await client.post(
                GOOGLE_TOKEN_URL,
                data={
                    "grant_type": "authorization_code",
                    "code": request.code,
                    "redirect_uri": request.redirect_uri,
                    "client_id": GOOGLE_CLIENT_ID,
                    "client_secret": GOOGLE_CLIENT_SECRET,
                    "code_verifier": request.code_verifier,
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )

            if resp.status_code != 200:
                error_detail = resp.json() if resp.headers.get("content-type", "").startswith("application/json") else resp.text
                print(f"Google token exchange failed: {error_detail}")
                raise HTTPException(
                    status_code=resp.status_code,
                    detail=f"Google token exchange failed: {error_detail}",
                )

            tokens = resp.json()

            # Fetch user info
            userinfo_resp = await client.get(
                GOOGLE_USERINFO_URL,
                headers={"Authorization": f"Bearer {tokens['access_token']}"},
            )

            if userinfo_resp.status_code != 200:
                raise HTTPException(
                    status_code=userinfo_resp.status_code,
                    detail="Failed to fetch Google user info",
                )

            userinfo = userinfo_resp.json()

            return {
                "access_token": tokens["access_token"],
                "refresh_token": tokens.get("refresh_token"),
                "id_token": tokens.get("id_token"),
                "expires_in": tokens.get("expires_in"),
                "userinfo": userinfo,
            }

        except httpx.TimeoutException:
            raise HTTPException(status_code=504, detail="Google OAuth timeout")
        except HTTPException:
            raise
        except Exception as e:
            print(f"Google token exchange error: {e}")
            raise HTTPException(status_code=500, detail=str(e))
