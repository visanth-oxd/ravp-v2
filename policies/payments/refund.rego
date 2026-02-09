# Policy: Payment Refund
# Controls when refunds can be processed automatically
# Owned by Risk/Compliance. Evaluated by policy-registry.

package payments.refund

import future.keywords.if
import future.keywords.in

# Default deny (require human review)
allow := false

# Auto-approve refunds for recent transactions within limits
allow if {
    input.refund_amount != null
    input.refund_amount <= 1000
    input.original_transaction_age_hours != null
    input.original_transaction_age_hours <= 24  # Within 24 hours
    input.refund_reason in ["duplicate", "cancelled", "merchant_error"]
    input.previous_refunds_count != null
    input.previous_refunds_count < 3  # Not excessive refunds
}

# Auto-approve if original payment was failed
allow if {
    input.original_payment_status == "failed"
    input.refund_amount != null
    input.refund_amount <= 5000
}

# Always allow if human escalation requested
allow if {
    input.escalation_requested == true
}

# Deny if refund exceeds original amount
deny if {
    input.refund_amount > input.original_amount
}

# Deny if transaction is too old (fraud risk)
deny if {
    input.original_transaction_age_days != null
    input.original_transaction_age_days > 90
}

# Deny if account has excessive refunds
deny if {
    input.previous_refunds_count >= 5
    input.refund_amount > 500
}
