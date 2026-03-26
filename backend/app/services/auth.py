"""
AuthService: business logic for Google OAuth, JWT issuance, and token rotation.

Flow:
1. Client sends Google id_token → POST /auth/google
2. AuthService.verify_google_token() validates it locally (no HTTP round-trip needed
   after initial key fetch)
3. AuthService.find_or_create_user() returns (User, is_new_user)
4. AuthService.issue_tokens() emits JWT (24h) + opaque refresh token (90d)
5. On subsequent visits: POST /auth/refresh with refresh token
6. AuthService.rotate_refresh_token() deletes old token, inserts new one
7. POST /auth/logout → AuthService.revoke_refresh_token()
"""

import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Any
from uuid import UUID

import jwt
from flask import current_app
from google.oauth2 import id_token as google_id_token
from google.auth.transport import requests as google_requests

from app.extensions import db
from app.models.user import User
from app.models.refresh_token import RefreshToken
from app.utils.exceptions import ValidationError


def _hash_token(token: str) -> str:
    """
    Return the SHA-256 hex digest of a plaintext token string.

    Args:
        token: Plaintext token to hash.

    Returns:
        64-character lowercase hex string.
    """
    return hashlib.sha256(token.encode()).hexdigest()


class AuthService:
    """
    Handles the full authentication lifecycle.

    Responsibilities:
    - Validate Google id_token and extract user info
    - Find or create User records on first login
    - Issue JWT access tokens and opaque refresh tokens
    - Rotate refresh tokens (delete old, insert new)
    - Revoke refresh tokens on logout

    At most one refresh token exists per user at any time. Rotation
    physically deletes the old row before inserting a new one — there is
    no soft-delete or revoked_at column.
    """

    def verify_google_token(self, id_token_str: str) -> dict[str, Any]:
        """
        Verify a Google id_token and return its payload.

        Validation is performed using the google-auth library which fetches
        Google's public certificates on first call and caches them.

        Args:
            id_token_str: The raw id_token string from Google Sign-In.

        Returns:
            Verified payload dict containing at least 'sub', 'email', 'name'.

        Raises:
            ValidationError: If the token is invalid, expired, or audience mismatch.
        """
        try:
            payload = google_id_token.verify_oauth2_token(
                id_token_str,
                google_requests.Request(),
                current_app.config["GOOGLE_CLIENT_ID"],
            )
        except Exception as e:
            raise ValidationError(f"Token de Google inválido: {str(e)}")

        required_fields = {"sub", "email", "name"}
        if not required_fields.issubset(payload.keys()):
            raise ValidationError(
                "Token de Google no contiene los campos requeridos (sub, email, name)"
            )
        return payload

    def find_or_create_user(
        self, google_payload: dict[str, Any]
    ) -> tuple[User, bool]:
        """
        Find an existing user by google_id or create a new one.

        Args:
            google_payload: Verified Google id_token payload with 'sub',
                'email', 'name'.

        Returns:
            Tuple of (User instance, is_new_user bool).
        """
        google_id = google_payload["sub"]
        existing = (
            db.session.execute(
                db.select(User).where(User.google_id == google_id)
            )
            .scalars()
            .one_or_none()
        )
        if existing:
            return existing, False

        user = User(
            google_id=google_id,
            email=google_payload["email"],
            name=google_payload["name"],
        )
        db.session.add(user)
        db.session.commit()
        db.session.refresh(user)
        return user, True

    def _build_jwt(self, user: User) -> str:
        """
        Build a signed JWT containing user identity payload.

        Payload claims:
        - sub: user UUID string (standard JWT subject claim)
        - email: user email address
        - name: user display name
        - iat: issued-at timestamp (UTC)
        - exp: expiration timestamp (UTC, 24h by default)

        Args:
            user: User instance to embed in the token.

        Returns:
            Signed JWT string.
        """
        expiry_hours = current_app.config["JWT_EXPIRY_HOURS"]
        now = datetime.utcnow()
        payload = {
            "sub": str(user.id),
            "email": user.email,
            "name": user.name,
            "iat": now,
            "exp": now + timedelta(hours=expiry_hours),
        }
        return jwt.encode(
            payload,
            current_app.config["JWT_SECRET"],
            algorithm="HS256",
        )

    def _issue_refresh_token(self, user: User, full_replace: bool = False) -> str:
        """
        Create a new refresh token row for a user.

        Args:
            user: User instance to issue a refresh token for.
            full_replace: When True (Google sign-in path), delete ALL existing
                tokens for this user before inserting the new one.
                When False (rotation path), only delete tokens whose grace
                period has expired (superseded_at < utcnow() - grace_seconds).

        Returns:
            Plaintext opaque token string (64 hex chars). Only returned once;
            only the hash is stored in the database.
        """
        expiry_days = current_app.config["REFRESH_TOKEN_EXPIRY_DAYS"]
        grace_seconds = current_app.config["REFRESH_TOKEN_GRACE_SECONDS"]
        token_plain = secrets.token_hex(32)  # 64-char hex string
        token_hash = _hash_token(token_plain)
        expires_at = datetime.utcnow() + timedelta(days=expiry_days)

        if full_replace:
            # Google sign-in: delete ALL tokens for this user unconditionally
            db.session.execute(
                db.delete(RefreshToken).where(RefreshToken.user_id == user.id)
            )
        else:
            # Rotation path: only remove tokens whose grace window has expired
            grace_cutoff = datetime.utcnow() - timedelta(seconds=grace_seconds)
            db.session.execute(
                db.delete(RefreshToken).where(
                    RefreshToken.user_id == user.id,
                    RefreshToken.superseded_at.is_not(None),
                    RefreshToken.superseded_at < grace_cutoff,
                )
            )

        new_token = RefreshToken(
            user_id=user.id,
            token_hash=token_hash,
            expires_at=expires_at,
        )
        db.session.add(new_token)
        db.session.commit()
        return token_plain

    def issue_tokens(self, user: User) -> dict[str, str]:
        """
        Issue a JWT and a fresh refresh token for the given user.

        Uses full_replace=True: on Google sign-in, all existing tokens
        for the user are invalidated unconditionally.

        Args:
            user: Authenticated User instance.

        Returns:
            Dict with 'access_token' (signed JWT) and 'refresh_token' (opaque
            64-char hex string). The refresh token is only ever returned here
            and on rotation — it is not stored in plaintext anywhere.
        """
        access_token = self._build_jwt(user)
        refresh_token = self._issue_refresh_token(user, full_replace=True)
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
        }

    def rotate_refresh_token(self, token_plain: str) -> dict[str, str]:
        """
        Validate and rotate a refresh token.

        Finds the stored token by hash, verifies it is not expired, then
        deletes the old row and issues a new JWT + refresh token pair.

        Args:
            token_plain: Plaintext refresh token from the client.

        Returns:
            Dict with new 'access_token' and 'refresh_token'.

        Raises:
            ValidationError: If token is not found or has expired.
        """
        token_hash = _hash_token(token_plain)
        stored = (
            db.session.execute(
                db.select(RefreshToken).where(
                    RefreshToken.token_hash == token_hash
                )
            )
            .scalars()
            .one_or_none()
        )

        if stored is None:
            raise ValidationError("Refresh token inválido o ya utilizado")

        if stored.expires_at < datetime.utcnow():
            # Token expired: clean it up
            db.session.delete(stored)
            db.session.commit()
            raise ValidationError("Refresh token expirado")

        # Load the user before _issue_refresh_token deletes the stored token
        user = db.session.get(User, stored.user_id)
        if user is None:
            db.session.delete(stored)
            db.session.commit()
            raise ValidationError("Usuario no encontrado")

        # _issue_refresh_token deletes all tokens for this user then inserts new
        return self.issue_tokens(user)

    def revoke_refresh_token(self, token_plain: str) -> None:
        """
        Revoke a refresh token by deleting its DB row.

        Idempotent: no-op if the token does not exist (e.g., already rotated
        or never existed). Always safe to call on logout.

        Args:
            token_plain: Plaintext refresh token to revoke.
        """
        token_hash = _hash_token(token_plain)
        db.session.execute(
            db.delete(RefreshToken).where(
                RefreshToken.token_hash == token_hash
            )
        )
        db.session.commit()
