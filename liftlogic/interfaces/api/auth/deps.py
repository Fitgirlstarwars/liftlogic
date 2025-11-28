"""
Authentication Dependencies - Verify Google OAuth tokens.

Users authenticate via Google Sign-In on the frontend.
The access token is sent in the Authorization header.
We verify it and extract user info + the token for Gemini API calls.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional

import httpx
from fastapi import Header, HTTPException

logger = logging.getLogger(__name__)


@dataclass
class UserContext:
    """
    Authenticated user context.

    Contains user info and the OAuth token that can be used
    to call Google APIs (including Gemini) on the user's behalf.
    """

    email: str
    name: str | None
    picture: str | None
    access_token: str  # Can be used for Gemini API calls

    @property
    def is_authenticated(self) -> bool:
        return bool(self.email and self.access_token)


async def get_current_user(
    authorization: Optional[str] = Header(None),
) -> UserContext:
    """
    Verify Google OAuth token and return user context.

    Expects 'Authorization: Bearer <token>' header.
    The token is a Google OAuth access token from Sign-In.

    Returns:
        UserContext with email, name, picture, and access_token

    Raises:
        HTTPException 401 if authentication fails
    """
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing authentication header")

    try:
        parts = authorization.split()
        if len(parts) != 2 or parts[0].lower() != "bearer":
            raise HTTPException(status_code=401, detail="Invalid authentication scheme")

        token = parts[1]

        # Verify token by calling Google's userinfo endpoint
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://www.googleapis.com/oauth2/v3/userinfo",
                headers={"Authorization": f"Bearer {token}"},
            )

            if response.status_code != 200:
                logger.warning("Token validation failed: %s", response.text)
                raise HTTPException(
                    status_code=401, detail="Invalid authentication token"
                )

            user_info = response.json()
            email = user_info.get("email")

            if not email:
                raise HTTPException(
                    status_code=401, detail="Token does not contain email"
                )

            return UserContext(
                email=email,
                name=user_info.get("name"),
                picture=user_info.get("picture"),
                access_token=token,  # Keep token for Gemini calls
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Auth error: %s", e)
        raise HTTPException(status_code=401, detail="Authentication failed")


async def get_current_user_optional(
    authorization: Optional[str] = Header(None),
) -> UserContext | None:
    """
    Get user context if authenticated, None otherwise.

    Use this for endpoints that work with or without authentication,
    falling back to Ollama for unauthenticated users.
    """
    if not authorization:
        return None

    try:
        return await get_current_user(authorization)
    except HTTPException:
        return None
