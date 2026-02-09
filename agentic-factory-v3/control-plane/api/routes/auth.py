"""Auth for v2: login and platform_admin role."""

from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel
from typing import Optional
import hashlib

router = APIRouter(prefix="/api/v2/auth", tags=["auth"])

# Demo: no JWT for minimal setup; role by email
DEMO_ADMIN_EMAILS = {"admin@platform.com", "platform@admin.com"}


class LoginRequest(BaseModel):
    email: str
    password: str


def get_role(email: str) -> str:
    return "platform_admin" if (email and email.strip().lower() in DEMO_ADMIN_EMAILS) else "agent_creator"


@router.post("/login")
def login(credentials: LoginRequest):
    email = (credentials.email or "").strip().lower()
    role = get_role(credentials.email)
    return {
        "token": f"demo_{role}_{hashlib.sha256(email.encode()).hexdigest()[:16]}",
        "user": {"email": credentials.email, "name": email.split("@")[0] if email else "User", "role": role},
    }


def require_auth(authorization: Optional[str] = Header(None, alias="Authorization")):
    """Dependency: require any authenticated user (agent_creator or platform_admin)."""
    if not authorization:
        raise HTTPException(status_code=401, detail="Not authenticated")
    # Demo: allow if token looks like our demo token; real impl would decode JWT and check role
    if "demo_platform_admin" in (authorization or "") or "demo_agent_creator" in (authorization or ""):
        return "authenticated"
    if "Bearer demo_" in (authorization or ""):
        return "authenticated"
    raise HTTPException(status_code=401, detail="Invalid token")


def require_platform_admin(authorization: Optional[str] = Header(None, alias="Authorization")):
    """Dependency: require platform_admin. Accept any Bearer token and derive role from token or allow for demo."""
    if not authorization:
        raise HTTPException(status_code=401, detail="Not authenticated")
    # Demo: allow if token looks like our demo token; real impl would decode JWT and check role
    if "demo_platform_admin" in (authorization or ""):
        return "admin"
    if "Bearer demo_" in (authorization or ""):
        raise HTTPException(status_code=403, detail="Platform Admin role required")
    raise HTTPException(status_code=401, detail="Invalid token")
