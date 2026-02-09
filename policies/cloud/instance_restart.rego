package cloud.instance_restart

# Policy for restarting cloud instances
# Ensures proper checks before allowing instance restart

default allow = false

# Allow restart if all conditions met
allow {
    # Instance must be in a restartable state
    valid_instance_state
    
    # Must not be in maintenance window
    not in_maintenance_window
    
    # Recent restarts not excessive
    restart_count_acceptable
    
    # Must have valid justification
    has_valid_reason
}

# Check instance state
valid_instance_state {
    input.instance_state != "terminating"
    input.instance_state != "terminated"
}

# Check if in maintenance window
in_maintenance_window {
    # Maintenance windows: 00:00-02:00 UTC
    # During maintenance, require explicit approval
    input.time_hour >= 0
    input.time_hour < 2
    not input.explicit_approval
}

# Check restart count in last hour
restart_count_acceptable {
    input.recent_restart_count < 3
}

# Valid reasons for restart
has_valid_reason {
    input.reason == "health_check_failure"
}

has_valid_reason {
    input.reason == "high_memory_usage"
}

has_valid_reason {
    input.reason == "manual_request"
    input.approved_by != ""
}

# Deny with reason
deny[msg] {
    not valid_instance_state
    msg := "Instance is in terminating or terminated state"
}

deny[msg] {
    in_maintenance_window
    msg := "Instance restart during maintenance window requires explicit approval"
}

deny[msg] {
    input.recent_restart_count >= 3
    msg := sprintf("Too many recent restarts: %d in last hour (max: 3)", [input.recent_restart_count])
}

deny[msg] {
    not has_valid_reason
    msg := sprintf("Invalid restart reason: %s", [input.reason])
}
