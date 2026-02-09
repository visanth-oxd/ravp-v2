"""RBAC (Role-Based Access Control) for agents."""

from typing import Optional, Dict, Any, List


def get_user_from_token(authorization: Optional[str], user_email_header: Optional[str] = None) -> Dict[str, Any]:
    """
    Extract user information from authorization token.
    
    Args:
        authorization: Authorization header value (e.g., "Bearer demo_platform_admin_abc123")
        user_email_header: Optional X-User-Email header value (from UI session state)
    
    Returns:
        Dict with user info: {"email": "...", "role": "...", "domain": "..."}
    """
    if not authorization:
        return {"email": None, "role": "agent_creator", "domain": "general"}
    
    # Demo: parse token format "demo_{role}_{hash}"
    # In production, this would decode a JWT
    auth_str = authorization.replace("Bearer ", "").strip()
    
    # Use email from header if provided (from UI session state)
    email = user_email_header
    
    # Determine role from token
    if "demo_platform_admin" in auth_str:
        role = "platform_admin"
        if not email:
            email = "admin@platform.com"  # Default
        domain = "platform"
    elif "demo_agent_creator" in auth_str:
        role = "agent_creator"
        if not email:
            email = "user@platform.com"  # Default
        domain = "general"
    else:
        role = "agent_creator"
        domain = "general"
    
    # Determine domain from email if available
    if email and "@" in email:
        email_lower = email.lower()
        if "admin" in email_lower or "platform" in email_lower:
            domain = "platform"
        elif "payments" in email_lower:
            domain = "payments"
        elif "customer" in email_lower:
            domain = "customer_service"
        else:
            # Extract domain from email
            domain_part = email_lower.split("@")[1]
            domain = domain_part.split(".")[0] if "." in domain_part else domain_part
    
    return {"email": email, "role": role, "domain": domain}


def get_user_from_token_with_email(authorization: Optional[str], user_email: Optional[str] = None) -> Dict[str, Any]:
    """
    Extract user information from authorization token, with optional email override.
    
    This is useful when email is available from session state (UI) but not in token.
    
    Args:
        authorization: Authorization header value
        user_email: Optional email override (from session state)
    
    Returns:
        Dict with user info: {"email": "...", "role": "...", "domain": "..."}
    """
    user = get_user_from_token(authorization)
    
    # Override email if provided
    if user_email:
        user["email"] = user_email
    
    # Determine domain from email if available
    if user.get("email"):
        email = user["email"].lower()
        if "@" in email:
            domain_part = email.split("@")[1]
            # Map common domains
            if "admin" in domain_part or "platform" in domain_part:
                user["domain"] = "platform"
            elif "payments" in domain_part:
                user["domain"] = "payments"
            elif "customer" in domain_part:
                user["domain"] = "customer_service"
            else:
                user["domain"] = domain_part.split(".")[0]  # Use first part of domain
    
    return user


def can_view_agent(agent: Dict[str, Any], user: Dict[str, Any]) -> bool:
    """
    Check if user can view an agent.
    
    Args:
        agent: Agent definition dict
        user: User info dict with email, role, domain
    
    Returns:
        True if user can view the agent
    """
    user_role = user.get("role", "agent_creator")
    user_email = user.get("email", "")
    user_domain = user.get("domain", "general")
    
    # Platform admins can view everything
    if user_role == "platform_admin":
        return True
    
    # Get RBAC settings (default to public if not set)
    rbac = agent.get("rbac", {})
    creator = rbac.get("creator", "")
    visibility = rbac.get("visibility", "public")
    
    # Creator can always view their agents
    if creator and user_email and creator.lower() == user_email.lower():
        return True
    
    # Check visibility rules
    if visibility == "public":
        return True
    
    if visibility == "domain":
        agent_domain = agent.get("domain", "general")
        return user_domain == agent_domain
    
    if visibility == "private":
        allowed_users = rbac.get("allowed_users", [])
        return user_email.lower() in [u.lower() for u in allowed_users]
    
    if visibility == "restricted":
        allowed_users = rbac.get("allowed_users", [])
        allowed_roles = rbac.get("allowed_roles", [])
        allowed_domains = rbac.get("allowed_domains", [])
        
        if user_email and user_email.lower() in [u.lower() for u in allowed_users]:
            return True
        if user_role in allowed_roles:
            return True
        if user_domain in allowed_domains:
            return True
        return False
    
    # Default: public
    return True


def can_use_agent(agent: Dict[str, Any], user: Dict[str, Any]) -> bool:
    """
    Check if user can use an agent.
    
    Args:
        agent: Agent definition dict
        user: User info dict with email, role, domain
    
    Returns:
        True if user can use the agent
    """
    # Must be able to view first
    if not can_view_agent(agent, user):
        return False
    
    user_role = user.get("role", "agent_creator")
    user_email = user.get("email", "")
    user_domain = user.get("domain", "general")
    
    # Platform admins can use everything
    if user_role == "platform_admin":
        return True
    
    # Get RBAC settings
    rbac = agent.get("rbac", {})
    creator = rbac.get("creator", "")
    visibility = rbac.get("visibility", "public")
    
    # Creator can always use their agents
    if creator and user_email and creator.lower() == user_email.lower():
        return True
    
    # If visibility is public, anyone can use
    if visibility == "public":
        return True
    
    # Check explicit permissions
    allowed_users = rbac.get("allowed_users", [])
    allowed_roles = rbac.get("allowed_roles", [])
    allowed_domains = rbac.get("allowed_domains", [])
    
    if user_email and user_email.lower() in [u.lower() for u in allowed_users]:
        return True
    if user_role in allowed_roles:
        return True
    if user_domain in allowed_domains:
        return True
    
    # For domain visibility, users in same domain can use
    if visibility == "domain":
        agent_domain = agent.get("domain", "general")
        return user_domain == agent_domain
    
    return False


def can_edit_agent(agent: Dict[str, Any], user: Dict[str, Any]) -> bool:
    """
    Check if user can edit an agent.
    
    Args:
        agent: Agent definition dict
        user: User info dict with email, role, domain
    
    Returns:
        True if user can edit the agent
    """
    user_role = user.get("role", "platform_admin")
    user_email = user.get("email", "")
    
    # Platform admins can edit everything
    if user_role == "platform_admin":
        return True
    
    # Creator can edit their agents
    rbac = agent.get("rbac", {})
    creator = rbac.get("creator", "")
    if creator and user_email and creator.lower() == user_email.lower():
        return True
    
    return False


def can_delete_agent(agent: Dict[str, Any], user: Dict[str, Any]) -> bool:
    """
    Check if user can delete an agent.
    
    Args:
        agent: Agent definition dict
        user: User info dict with email, role, domain
    
    Returns:
        True if user can delete the agent
    """
    # Same as edit permissions
    return can_edit_agent(agent, user)


def get_agent_permissions(agent: Dict[str, Any], user: Dict[str, Any]) -> Dict[str, bool]:
    """
    Get all permissions for a user on an agent.
    
    Args:
        agent: Agent definition dict
        user: User info dict with email, role, domain
    
    Returns:
        Dict with permission flags: {"can_view": bool, "can_use": bool, "can_edit": bool, "can_delete": bool}
    """
    return {
        "can_view": can_view_agent(agent, user),
        "can_use": can_use_agent(agent, user),
        "can_edit": can_edit_agent(agent, user),
        "can_delete": can_delete_agent(agent, user),
    }


def filter_agents_by_permission(agents: List[Dict[str, Any]], user: Dict[str, Any], permission: str = "can_view") -> List[Dict[str, Any]]:
    """
    Filter agents by user permission.
    
    Args:
        agents: List of agent definitions
        user: User info dict
        permission: Permission to check ("can_view", "can_use", "can_edit", "can_delete")
    
    Returns:
        Filtered list of agents
    """
    if permission == "can_view":
        return [a for a in agents if can_view_agent(a, user)]
    elif permission == "can_use":
        return [a for a in agents if can_use_agent(a, user)]
    elif permission == "can_edit":
        return [a for a in agents if can_edit_agent(a, user)]
    elif permission == "can_delete":
        return [a for a in agents if can_delete_agent(a, user)]
    else:
        return agents
