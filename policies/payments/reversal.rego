# Policy: Payment Reversal
# Controls when payment reversals can be processed
# Owned by Risk/Compliance. Evaluated by policy-registry.

package payments.reversal

import future.keywords.if
import future.keywords.in

# Default deny (require human review)
allow := false

# Allow reversal for technical errors
allow if {
    input.reversal_reason in ["system_error", "duplicate_charge", "processing_error"]
    input.reversal_amount != null
    input.reversal_amount <= 10000
    input.transaction_age_hours != null
    input.transaction_age_hours <= 48  # Within 48 hours
}

# Allow reversal if original payment failed but was charged
allow if {
    input.original_payment_status == "failed"
    input.chargeback_requested == false
    input.reversal_amount != null
    input.reversal_amount <= 5000
}

# Always allow if human escalation requested
allow if {
    input.escalation_requested == true
}

# Deny if transaction is settled (too late)
deny if {
    input.transaction_status == "settled"
    input.transaction_age_days > 7
}

# Deny if chargeback already initiated
deny if {
    input.chargeback_requested == true
}

# Deny if reversal amount exceeds original
deny if {
    input.reversal_amount > input.original_amount
}
