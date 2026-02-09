package cloud.database_scaling

# Policy for scaling Cloud SQL instances
# Ensures safe scaling operations with proper thresholds

default allow = false

# Allow scaling if conditions are met
allow {
    # Must have valid scaling reason
    valid_scaling_reason
    
    # Target tier must be appropriate
    valid_target_tier
    
    # Must not exceed budget constraints
    within_budget
    
    # Not during peak hours without approval
    not requires_peak_hour_approval
}

# Valid reasons for scaling
valid_scaling_reason {
    input.cpu_utilization >= 80
    input.reason == "high_cpu"
}

valid_scaling_reason {
    input.memory_utilization >= 85
    input.reason == "high_memory"
}

valid_scaling_reason {
    input.connection_usage >= 90  # percent of max connections
    input.reason == "connection_exhaustion"
}

valid_scaling_reason {
    input.disk_io_wait_ms > 20
    input.reason == "slow_disk_io"
}

valid_scaling_reason {
    input.reason == "planned_capacity"
    input.approved_by != ""
}

# Validate target tier
valid_target_tier {
    # Must be scaling up (not down) during incidents
    input.current_tier != input.target_tier
    tier_rank(input.target_tier) > tier_rank(input.current_tier)
}

valid_target_tier {
    # Planned scaling can go up or down
    input.reason == "planned_capacity"
}

# Tier ranking (higher = more capacity)
tier_rank("db-n1-standard-1") = 1
tier_rank("db-n1-standard-2") = 2
tier_rank("db-n1-standard-4") = 4
tier_rank("db-n1-standard-8") = 8
tier_rank("db-n1-standard-16") = 16
tier_rank("db-n1-highmem-2") = 3
tier_rank("db-n1-highmem-4") = 6
tier_rank("db-n1-highmem-8") = 12

# Budget constraint: don't scale beyond tier 8 without approval
within_budget {
    tier_rank(input.target_tier) <= 8
}

within_budget {
    tier_rank(input.target_tier) > 8
    input.budget_approved == true
}

# Peak hours: 08:00-18:00 UTC (business hours)
requires_peak_hour_approval {
    input.time_hour >= 8
    input.time_hour < 18
    input.environment == "production"
    not input.incident_severity == "P1"  # P1 incidents auto-approved
    not input.approved_by
}

# Deny with reasons
deny[msg] {
    not valid_scaling_reason
    msg := sprintf("Invalid or insufficient reason for scaling: %s", [input.reason])
}

deny[msg] {
    not valid_target_tier
    msg := sprintf("Invalid tier transition: %s -> %s", [input.current_tier, input.target_tier])
}

deny[msg] {
    not within_budget
    tier_rank(input.target_tier) > 8
    msg := sprintf("Target tier %s exceeds budget limit (tier 8) without approval", [input.target_tier])
}

deny[msg] {
    requires_peak_hour_approval
    msg := "Scaling during peak hours (08:00-18:00 UTC) requires explicit approval for non-P1 incidents"
}
