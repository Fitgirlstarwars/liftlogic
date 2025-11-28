"""
Authentication - Google OAuth for user login and Gemini API access.

Users login with Google OAuth. Their access token is used to:
1. Authenticate API requests
2. Access Gemini API with THEIR quota (zero cost for us)

Flow:
    Frontend: Google Sign-In → access_token
    Backend: Verify token → get user email → use token for Gemini
"""

from .deps import get_current_user, get_current_user_optional, UserContext
from .encryption import TokenEncryption, encryption

__all__ = [
    "get_current_user",
    "get_current_user_optional",
    "UserContext",
    "TokenEncryption",
    "encryption",
]
