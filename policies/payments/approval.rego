# Policy: Payment Approval
# Controls when payments can be automatically approved vs requiring human approval
# Owned by Risk/Compliance. Evaluated by policy-registry.

package payments.approval

import future.keywords.if
import future.keywords.in

# Default deny (require human approval)
allow := false

# Auto-approve small amounts for trusted customers
allow if {
    input.amount != null
    input.amount <= 5000
    input.customer_risk_score != null
    input.customer_risk_score <= 30  # Low risk score (0-100 scale)
    input.account_age_days != null
    input.account_age_days >= 90  # Account at least 90 days old
    input.previous_failed_payments == 0
}

# Auto-approve if within daily limit
allow if {
    input.amount != null
    input.daily_payment_total != null
    input.daily_payment_total + input.amount <= 50000  # Daily limit
    input.customer_risk_score != null
    input.customer_risk_score <= 50
}

# Always allow if human escalation requested
allow if {
    input.escalation_requested == true
}

# Deny if account is frozen or blocked
deny if {
    input.account_status == "frozen"
}

deny if {
    input.account_status == "blocked"
}

# Deny if exceeds monthly limit
deny if {
    input.monthly_payment_total != null
    input.monthly_payment_total + input.amount > 200000
}
