"""
Token Encryption - Secure storage for OAuth tokens.

Uses Fernet symmetric encryption for storing refresh tokens
and other sensitive data in the database.
"""

from __future__ import annotations

import logging
import os
import secrets

from cryptography.fernet import Fernet

logger = logging.getLogger(__name__)


class TokenEncryption:
    """Handles encryption/decryption of OAuth tokens."""

    def __init__(self) -> None:
        key = os.getenv("OAUTH_ENCRYPTION_KEY")

        if not key:
            # Generate temporary key for development
            logger.warning("OAUTH_ENCRYPTION_KEY not set - generating temporary key")
            key = Fernet.generate_key().decode()
            logger.warning("Set OAUTH_ENCRYPTION_KEY=%s in production!", key)

        self.cipher = Fernet(key.encode() if isinstance(key, str) else key)

    def encrypt(self, token: str) -> str:
        """
        Encrypt a token.

        Args:
            token: Plain text token

        Returns:
            Encrypted token string (base64)
        """
        if not token:
            return ""

        try:
            return self.cipher.encrypt(token.encode()).decode()
        except Exception as e:
            logger.error("Encryption failed: %s", e)
            raise

    def decrypt(self, encrypted_token: str) -> str:
        """
        Decrypt a token.

        Args:
            encrypted_token: Encrypted token string

        Returns:
            Plain text token
        """
        if not encrypted_token:
            return ""

        try:
            return self.cipher.decrypt(encrypted_token.encode()).decode()
        except Exception as e:
            logger.error("Decryption failed: %s", e)
            raise


# Global instance
encryption = TokenEncryption()
