# Policy: Fraud Investigation
# Controls when fraud investigations should be initiated
# Owned by Fraud Prevention Team. Evaluated by policy-registry.

package fraud.investigation

import future.keywords.if
import future.keywords.in

# Default deny (no investigation needed)
allow := false

# Initiate investigation for high-risk transactions
allow if {
    input.fraud_score != null
    input.fraud_score >= 75  # High fraud score (0-100)
    input.transaction_amount != null
    input.transaction_amount >= 1000
}

# Initiate investigation for suspicious patterns
allow if {
    input.suspicious_patterns != null
    count(input.suspicious_patterns) >= 2  # Multiple suspicious indicators
    input.transaction_amount >= 500
}

# Initiate investigation if velocity check fails
allow if {
    input.transactions_last_hour >= 10  # Too many transactions
    input.transaction_amount >= 500
}

# Initiate investigation for unusual geography
allow if {
    input.geolocation_mismatch == true
    input.transaction_amount >= 1000
}

# Always allow if human escalation requested
allow if {
    input.escalation_requested == true
}

# Deny investigation if already flagged
deny if {
    input.account_status == "flagged"
    input.investigation_in_progress == true
}
