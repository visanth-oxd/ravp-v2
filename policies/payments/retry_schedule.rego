# Policy: Payment Retry Schedule
# Determines optimal retry timing and frequency for failed payments
# Owned by Payments Operations. Evaluated by policy-registry.

package payments.retry_schedule

import future.keywords.if
import future.keywords.in

# Default: immediate retry
retry_delay_hours := 0
max_retries := 1

# ============================================
# RETRY SCHEDULE BY ERROR TYPE
# ============================================

# Network errors: retry quickly (1 hour delay, up to 3 retries)
retry_delay_hours := 1 if {
    input.error_type == "network_error"
}
max_retries := 3 if {
    input.error_type == "network_error"
}

# Timeout errors: retry after 2 hours, up to 2 retries
retry_delay_hours := 2 if {
    input.error_type == "timeout"
}
max_retries := 2 if {
    input.error_type == "timeout"
}

# Insufficient funds: wait longer (4-6 hours), fewer retries
retry_delay_hours := 4 if {
    input.error_type == "insufficient_funds"
    input.customer_tier == "regular"
}
retry_delay_hours := 2 if {
    input.error_type == "insufficient_funds"
    input.customer_tier in ["premium", "vip"]
}
max_retries := 2 if {
    input.error_type == "insufficient_funds"
    input.customer_tier in ["premium", "vip"]
}
max_retries := 1 if {
    input.error_type == "insufficient_funds"
    input.customer_tier == "regular"
}

# System errors: retry after 1 hour, up to 3 retries
retry_delay_hours := 1 if {
    input.error_type == "system_error"
}
max_retries := 3 if {
    input.error_type == "system_error"
}

# Account validation errors: retry after 6 hours (time to fix), 1 retry
retry_delay_hours := 6 if {
    input.error_type in ["account_validation_error", "routing_error"]
}
max_retries := 1 if {
    input.error_type in ["account_validation_error", "routing_error"]
}

# ============================================
# RETRY SCHEDULE BY AMOUNT
# ============================================

# Large amounts: longer delay, fewer retries
retry_delay_hours := 6 if {
    input.amount != null
    input.amount > 10000
    input.amount <= 50000
}
max_retries := 2 if {
    input.amount != null
    input.amount > 10000
    input.amount <= 50000
}

# Very large amounts: even longer delay
retry_delay_hours := 12 if {
    input.amount != null
    input.amount > 50000
}
max_retries := 1 if {
    input.amount != null
    input.amount > 50000
}

# ============================================
# RETRY SCHEDULE BY CUSTOMER TIER
# ============================================

# Premium/VIP: faster retries, more attempts
retry_delay_hours := 1 if {
    input.customer_tier in ["premium", "vip"]
    input.error_type != "insufficient_funds"
}
max_retries := 3 if {
    input.customer_tier in ["premium", "vip"]
    input.amount <= 25000
}

# Regular customers: standard schedule
retry_delay_hours := 4 if {
    input.customer_tier == "regular"
    input.error_type == "insufficient_funds"
}
max_retries := 2 if {
    input.customer_tier == "regular"
    input.amount <= 10000
}

# ============================================
# RETRY SCHEDULE BY TIME OF DAY
# ============================================

# Business hours: faster retries
retry_delay_hours := 2 if {
    input.hour_of_day >= 9
    input.hour_of_day <= 17
    input.error_type == "insufficient_funds"
}

# Off-hours: longer delay (wait for next business day)
retry_delay_hours := 8 if {
    input.hour_of_day < 9
    input.hour_of_day > 17
    input.error_type == "insufficient_funds"
}

# ============================================
# EXPONENTIAL BACKOFF
# ============================================

# Apply exponential backoff for repeated failures
retry_delay_hours := 8 if {
    input.previous_retries == 1
    input.error_type == "insufficient_funds"
}

retry_delay_hours := 24 if {
    input.previous_retries == 2
    input.error_type == "insufficient_funds"
}
