# Policy: Payment Failure Handling Strategy
# Determines the appropriate handling strategy for different payment failure types
# Owned by Payments Operations. Evaluated by policy-registry.

package payments.failure_handling

import future.keywords.if
import future.keywords.in

# Default action: escalate (require human review)
recommended_action := "escalate"

# ============================================
# RETRY STRATEGY
# ============================================

# Recommend retry for transient errors
recommended_action := "retry" if {
    input.error_type in ["network_error", "timeout", "system_error", "processing_error"]
    input.amount != null
    input.amount <= 50000
}

# Recommend retry for insufficient funds with good customer profile
recommended_action := "retry" if {
    input.error_type == "insufficient_funds"
    input.customer_tier in ["premium", "vip"]
    input.payment_success_rate >= 0.90
    input.amount <= 10000
}

# ============================================
# REFUND STRATEGY
# ============================================

# Recommend refund for duplicate charges
recommended_action := "refund" if {
    input.error_type == "duplicate_transaction"
    input.transaction_age_hours <= 24
}

# Recommend refund for merchant errors
recommended_action := "refund" if {
    input.error_type == "merchant_error"
    input.transaction_age_hours <= 48
    input.amount <= 5000
}

# Recommend refund for failed payments that can't be retried
recommended_action := "refund" if {
    input.error_type == "insufficient_funds"
    input.previous_retries >= 2
    input.transaction_age_hours >= 48
    input.customer_requested_refund == true
}

# ============================================
# WAIVE FEE STRATEGY
# ============================================

# Recommend waiving fees for system errors
recommended_action := "waive_fee" if {
    input.error_type in ["system_error", "processing_error"]
    input.fee_amount != null
    input.fee_amount <= 50
    input.customer_tier in ["premium", "vip"]
}

# Recommend waiving fees for first-time failures
recommended_action := "waive_fee" if {
    input.previous_failures_count == 0
    input.fee_amount != null
    input.fee_amount <= 25
    input.customer_tier != "high_risk"
}

# ============================================
# ESCALATE STRATEGY (Default)
# ============================================

# Always escalate high-value transactions
recommended_action := "escalate" if {
    input.amount != null
    input.amount > 50000
}

# Escalate fraud-related errors
recommended_action := "escalate" if {
    input.error_type == "fraud_detected"
}

# Escalate account issues
recommended_action := "escalate" if {
    input.error_type in ["account_frozen", "account_closed", "account_suspended"]
}

# Escalate after multiple retries failed
recommended_action := "escalate" if {
    input.previous_retries >= 2
    input.error_type == "insufficient_funds"
}

# Escalate for regulatory/compliance issues
recommended_action := "escalate" if {
    input.error_type in ["aml_flag", "sanctions_check_failed", "kyc_issue"]
}
