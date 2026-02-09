"""List and evaluate policies. Rego evaluation via subprocess OPA or stub."""

import json
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Any


def get_policies_dir() -> Path:
    """
    Get policies directory path.
    
    Uses POLICIES_DIR environment variable if set, otherwise defaults to
    repo_root/policies relative to this file.
    """
    if os.environ.get("POLICIES_DIR"):
        return Path(os.environ["POLICIES_DIR"])
    
    # Path: control-plane/policy_registry/loader.py
    # Go up: policy_registry -> control-plane -> repo root
    repo_root = Path(__file__).resolve().parent.parent.parent
    return repo_root / "policies"


def list_policies() -> list[dict[str, Any]]:
    """
    List all registered policies.
    
    Scans policies/ directory for .rego files and returns policy IDs
    based on file paths (e.g. policies/payments/retry.rego -> "payments/retry").
    
    Returns:
        List of dicts with "id" and "path" fields
    """
    policies_dir = get_policies_dir()
    
    if not policies_dir.exists():
        return []
    
    policies = []
    for path in policies_dir.rglob("*.rego"):
        # Get relative path from policies_dir
        rel_path = path.relative_to(policies_dir)
        # Convert to policy ID: payments/retry.rego -> payments/retry
        policy_id = str(rel_path.with_suffix("")).replace(os.sep, "/")
        policies.append({
            "id": policy_id,
            "path": str(path)
        })
    
    return policies


def evaluate(policy_id: str, input_json: dict[str, Any]) -> dict[str, Any]:
    """
    Evaluate a policy with input data.
    
    Uses OPA (Open Policy Agent) if available, otherwise falls back to
    a stub implementation for basic policies.
    
    Args:
        policy_id: Policy identifier (e.g. "payments/retry")
        input_json: Input data for policy evaluation
    
    Returns:
        Dict with "allowed" (bool), "reason" (str), and "details" (dict)
    """
    policies_dir = get_policies_dir()
    
    # Map policy_id to file: payments/retry -> policies/payments/retry.rego
    policy_path = policies_dir / f"{policy_id.replace('/', os.sep)}.rego"
    
    if not policy_path.exists():
        return {
            "allowed": False,
            "reason": f"Policy not found: {policy_id}",
            "details": {}
        }
    
    # Try OPA evaluation (if OPA is installed)
    try:
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(input_json, f)
            input_path = f.name
        
        # Extract package name from policy_id (e.g. payments/retry -> payments.retry)
        package_name = policy_id.replace("/", ".")
        query = f"data.{package_name}.allow"
        
        result = subprocess.run(
            ["opa", "eval", "-d", str(policy_path), "-i", input_path, query],
            capture_output=True,
            text=True,
            timeout=5,
        )
        
        # Clean up temp file
        try:
            os.unlink(input_path)
        except Exception:
            pass
        
        if result.returncode == 0:
            # Check if result contains "true"
            if "true" in (result.stdout or ""):
                return {
                    "allowed": True,
                    "reason": "opa_eval",
                    "details": {"output": result.stdout}
                }
            else:
                return {
                    "allowed": False,
                    "reason": "opa_eval_deny",
                    "details": {"output": result.stdout}
                }
    except FileNotFoundError:
        # OPA not installed, use stub
        pass
    except subprocess.TimeoutExpired:
        return {
            "allowed": False,
            "reason": "opa_timeout",
            "details": {}
        }
    except Exception as e:
        # OPA error, fall back to stub
        pass
    
    # Stub implementation for payments/retry policy
    # This provides basic functionality when OPA is not available
    if policy_id == "payments/retry":
        amount = input_json.get("amount")
        previous_retries = input_json.get("previous_retries", 0)
        escalation_requested = input_json.get("escalation_requested", False)
        beneficiary_blocked = input_json.get("beneficiary_blocked", False)
        
        # Deny if beneficiary is blocked
        if beneficiary_blocked:
            return {
                "allowed": False,
                "reason": "stub_deny",
                "details": {"message": "Beneficiary is blocked"}
            }
        
        # Allow if escalation requested (human-in-the-loop)
        if escalation_requested:
            return {
                "allowed": True,
                "reason": "stub_policy",
                "details": {"message": "Escalation requested"}
            }
        
        # Allow if amount <= 10000 and retries < 2
        if amount is not None and amount <= 10000 and previous_retries < 2:
            return {
                "allowed": True,
                "reason": "stub_policy",
                "details": {"message": "Within limits"}
            }
        
        return {
            "allowed": False,
            "reason": "stub_deny",
            "details": {"message": "Amount or retry limit exceeded"}
        }
    
    # Unknown policy, deny by default
    return {
        "allowed": False,
        "reason": "unknown_policy",
        "details": {"message": f"No stub implementation for policy: {policy_id}"}
    }
