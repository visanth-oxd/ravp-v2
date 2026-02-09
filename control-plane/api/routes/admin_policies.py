"""Platform Admin: list/get/update/delete Rego policy files under policies/; domain grouping."""

import sys
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Optional

control_plane_dir = Path(__file__).resolve().parent.parent.parent
repo_root = control_plane_dir.parent
if str(control_plane_dir) not in sys.path:
    sys.path.insert(0, str(control_plane_dir))
from .auth import require_platform_admin

router = APIRouter(prefix="/api/v2/admin/policies", tags=["admin-policies"])
POLICIES_DIR = repo_root / "policies"


def _list_policy_files() -> List[dict]:
    out = []
    if not POLICIES_DIR.exists():
        return out
    for path in sorted(POLICIES_DIR.rglob("*.rego")):
        rel = path.relative_to(POLICIES_DIR)
        policy_id = str(rel.with_suffix("")).replace("\\", "/")
        # Domain is first path segment (e.g. payments/retry -> payments)
        domain = policy_id.split("/")[0] if "/" in policy_id else "general"
        out.append({
            "policy_id": policy_id,
            "domain": domain,
            "path": str(rel),
            "full_path": str(path),
        })
    return out


def _policies_by_domain() -> dict:
    """Group policies by domain for UI."""
    policies = _list_policy_files()
    by_domain: dict = {}
    for p in policies:
        d = p.get("domain", "general")
        by_domain.setdefault(d, []).append(p)
    return by_domain


@router.get("/domains")
def list_policy_domains(_=Depends(require_platform_admin)):
    """List policy domains with counts."""
    by_domain = _policies_by_domain()
    return {
        "domains": [
            {"domain": d, "policy_count": len(pols), "policies": pols}
            for d, pols in sorted(by_domain.items())
        ]
    }


@router.get("")
def list_policies_admin(domain: Optional[str] = Query(None), _=Depends(require_platform_admin)):
    """List all policies; optional ?domain= to filter by domain."""
    policies = _list_policy_files()
    if domain:
        policies = [p for p in policies if p.get("domain") == domain]
    return {"policies": policies}


@router.get("/{policy_id:path}")
def get_policy_content(policy_id: str, _=Depends(require_platform_admin)):
    path = POLICIES_DIR / f"{policy_id}.rego"
    if not path.exists() or not path.is_file():
        raise HTTPException(status_code=404, detail=f"Policy not found: {policy_id}")
    return {"policy_id": policy_id, "content": path.read_text()}


@router.put("/{policy_id:path}")
def update_policy(policy_id: str, body: dict, _=Depends(require_platform_admin)):
    content = body.get("content")
    if not content:
        raise HTTPException(status_code=400, detail="Missing 'content' in body")
    path = POLICIES_DIR / f"{policy_id}.rego"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)
    return {"message": f"Policy '{policy_id}' saved", "path": str(path)}


@router.delete("/{policy_id:path}")
def delete_policy(policy_id: str, _=Depends(require_platform_admin)):
    path = POLICIES_DIR / f"{policy_id}.rego"
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"Policy not found: {policy_id}")
    path.unlink()
    return {"message": f"Policy '{policy_id}' deleted"}
