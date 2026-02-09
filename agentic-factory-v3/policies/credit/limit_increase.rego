# Policy: Credit Limit Increase
# Controls when credit limit increases can be approved automatically
# Owned by Credit Risk Team. Evaluated by policy-registry.

package credit.limit_increase

import future.keywords.if
import future.keywords.in

# Default deny (require human review)
allow := false

# Auto-approve small increases for good customers
allow if {
    input.requested_increase != null
    input.requested_increase <= 5000
    input.current_limit != null
    input.credit_score >= 700
    input.payment_history_score >= 0.95  # 95% on-time payments
    input.account_age_months >= 12
    input.current_utilization < 0.5  # Less than 50% utilization
}

# Auto-approve if utilization is very low
allow if {
    input.current_utilization < 0.3
    input.requested_increase <= 10000
    input.credit_score >= 650
    input.payment_history_score >= 0.90
}

# Always allow if human escalation requested
allow if {
    input.escalation_requested == true
}

# Deny if credit score too low
deny if {
    input.credit_score < 600
}

# Deny if payment history poor
deny if {
    input.payment_history_score < 0.80
}

# Deny if recent increase already granted
deny if {
    input.last_increase_days_ago != null
    input.last_increase_days_ago < 90  # Within 90 days
    input.requested_increase > 5000
}

# Deny if high utilization
deny if {
    input.current_utilization >= 0.8
}
