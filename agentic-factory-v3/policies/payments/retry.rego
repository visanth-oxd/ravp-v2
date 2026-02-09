# Policy: Payment Retry – Core Banking Retry Rules
# Controls when failed payments can be automatically retried
# Owned by Risk/Compliance. Evaluated by policy-registry.

package payments.retry

import future.keywords.if
import future.keywords.in

# Default deny (require human review)
allow := false

# ============================================
# RETRY RULES BY ERROR TYPE
# ============================================

# Allow retry for transient errors (network, timeout, system errors)
allow if {
    input.error_type in ["network_error", "timeout", "system_error", "processing_error"]
    input.amount != null
    input.amount <= 50000
    input.previous_retries != null
    input.previous_retries < 3  # More retries allowed for transient errors
    input.exception_age_hours != null
    input.exception_age_hours <= 24  # Within 24 hours
}

# Allow retry for insufficient funds if account likely to be funded soon
allow if {
    input.error_type == "insufficient_funds"
    input.amount != null
    input.amount <= 10000
    input.previous_retries != null
    input.previous_retries < 2
    input.customer_tier in ["premium", "vip"]  # Premium customers get more retries
    input.account_balance_history_trend == "increasing"  # Balance trending up
}

# Allow retry for insufficient funds for regular customers (more restrictive)
allow if {
    input.error_type == "insufficient_funds"
    input.amount != null
    input.amount <= 5000
    input.previous_retries == 0  # Only one retry for regular customers
    input.exception_age_hours != null
    input.exception_age_hours >= 2  # Wait at least 2 hours
    input.exception_age_hours <= 48  # Within 48 hours
}

# Allow retry for account validation errors (likely fixable)
allow if {
    input.error_type in ["account_validation_error", "routing_error", "account_not_found"]
    input.amount != null
    input.amount <= 25000
    input.previous_retries == 0  # Only one retry for validation errors
    input.exception_age_hours != null
    input.exception_age_hours <= 12
}

# ============================================
# AMOUNT-BASED RULES
# ============================================

# Allow retry for small amounts (low risk)
allow if {
    input.amount != null
    input.amount <= 1000
    input.previous_retries != null
    input.previous_retries < 3
    input.error_type != "fraud_detected"
    input.error_type != "account_frozen"
}

# Allow retry for medium amounts with good customer history
allow if {
    input.amount != null
    input.amount > 1000
    input.amount <= 10000
    input.previous_retries != null
    input.previous_retries < 2
    input.customer_risk_score != null
    input.customer_risk_score <= 30  # Low risk customer
    input.payment_success_rate != null
    input.payment_success_rate >= 0.95  # 95%+ success rate
}

# ============================================
# TIME-BASED RULES
# ============================================

# Allow retry if enough time has passed since last retry
allow if {
    input.hours_since_last_retry != null
    input.hours_since_last_retry >= 4  # At least 4 hours between retries
    input.amount != null
    input.amount <= 10000
    input.previous_retries != null
    input.previous_retries < 3
}

# Allow retry for recent exceptions (within retry window)
allow if {
    input.exception_age_hours != null
    input.exception_age_hours <= 24  # Within 24 hours
    input.amount != null
    input.amount <= 5000
    input.previous_retries != null
    input.previous_retries < 2
}

# ============================================
# CUSTOMER TIER RULES
# ============================================

# Premium/VIP customers get more lenient retry rules
allow if {
    input.customer_tier in ["premium", "vip"]
    input.amount != null
    input.amount <= 25000
    input.previous_retries != null
    input.previous_retries < 3
    input.customer_risk_score != null
    input.customer_risk_score <= 50
}

# ============================================
# ESCALATION OVERRIDE
# ============================================

# Always allow if human escalation requested (human-in-the-loop)
allow if {
    input.escalation_requested == true
}

# ============================================
# DENY RULES (Hard Blocks)
# ============================================

# Deny if beneficiary/account blocked
deny if {
    input.beneficiary_blocked == true
}

deny if {
    input.account_status == "blocked"
}

deny if {
    input.account_status == "frozen"
}

# Deny if fraud detected
deny if {
    input.error_type == "fraud_detected"
}

deny if {
    input.fraud_flag == true
}

# Deny if too many retries already attempted
deny if {
    input.previous_retries != null
    input.previous_retries >= 3
    input.error_type != "network_error"  # Network errors can have more retries
}

# Deny if exception is too old (stale)
deny if {
    input.exception_age_days != null
    input.exception_age_days > 7  # Older than 7 days
}

# Deny if amount exceeds threshold
deny if {
    input.amount != null
    input.amount > 50000
    input.escalation_requested != true
}

# Deny if customer has poor payment history
deny if {
    input.payment_success_rate != null
    input.payment_success_rate < 0.70  # Less than 70% success rate
    input.previous_retries != null
    input.previous_retries >= 1
}
