package cloud.log_access

# Policy for accessing cloud logs
# Controls who can access logs and what severity levels

default allow = false

# Allow log access if authorized
allow {
    valid_requester
    valid_severity_level
    not contains_sensitive_data
}

# Valid requesters
valid_requester {
    # Platform admins can access all logs
    input.requester_role == "platform_admin"
}

valid_requester {
    # Cloud engineers can access cloud logs
    input.requester_role == "cloud_engineer"
    input.log_domain == "cloud_platform"
}

valid_requester {
    # Agents can access logs they need for their domain
    input.requester_type == "agent"
    input.agent_domain == "cloud_platform"
}

valid_requester {
    # Any authenticated user can access INFO/WARNING logs
    input.requester_type != ""
    input.max_severity == "INFO"
}

valid_requester {
    input.requester_type != ""
    input.max_severity == "WARNING"
}

# Valid severity levels for requester
valid_severity_level {
    # Platform admin: all levels
    input.requester_role == "platform_admin"
}

valid_severity_level {
    # Cloud engineers: ERROR and below
    input.requester_role == "cloud_engineer"
    severity_rank(input.max_severity) <= severity_rank("ERROR")
}

valid_severity_level {
    # Agents: WARNING and below for routine ops
    input.requester_type == "agent"
    input.agent_domain == "cloud_platform"
    severity_rank(input.max_severity) <= severity_rank("ERROR")
}

# Severity ranking
severity_rank("INFO") = 1
severity_rank("WARNING") = 2
severity_rank("ERROR") = 3
severity_rank("CRITICAL") = 4

# Check for sensitive data
contains_sensitive_data {
    # PII logs require special permission
    input.contains_pii == true
    not input.pii_access_approved
}

# Allow specific agents to investigate incidents
allow {
    input.requester_type == "agent"
    input.agent_id == "cloud_reliability"
    input.purpose == "incident_investigation"
    input.incident_id != ""
}

# Deny with reasons
deny[msg] {
    not valid_requester
    msg := sprintf("Requester %s not authorized for log access", [input.requester_type])
}

deny[msg] {
    contains_sensitive_data
    msg := "Logs contain PII and require special approval"
}
