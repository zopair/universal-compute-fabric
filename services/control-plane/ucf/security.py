from __future__ import annotations

import hashlib
import hmac
import secrets

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from ucf.config import settings
from ucf.database import get_db
from ucf.entities import NodeRecord


def create_node_token() -> str:
    return secrets.token_urlsafe(32)


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def require_admin(x_ucf_admin_key: str | None = Header(default=None)) -> None:
    configured = settings.admin_api_key
    if not configured:
        if settings.production:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Administrative authentication is not configured",
            )
        return
    if not x_ucf_admin_key or not hmac.compare_digest(x_ucf_admin_key, configured):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid admin credential")


def require_node(
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> NodeRecord:
    scheme, _, token = (authorization or "").partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise HTTPException(status_code=401, detail="Node bearer token required")
    record = db.query(NodeRecord).filter(NodeRecord.credential_hash == hash_token(token)).one_or_none()
    if record is None:
        raise HTTPException(status_code=401, detail="Invalid node credential")
    return record
