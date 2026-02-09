# Policy: AML (Anti-Money Laundering) Check
# Controls when transactions trigger AML investigation
# Owned by Compliance Team. Evaluated by policy-registry.

package compliance.aml_check

import future.keywords.if
import future.keywords.in

# Default allow (no AML concern)
allow := true

# Trigger AML investigation for large transactions
deny if {
    input.transaction_amount >= 10000  # $10k threshold
    input.transaction_type == "cash"
}

# Trigger AML investigation for suspicious patterns
deny if {
    input.suspicious_patterns != null
    count(input.suspicious_patterns) >= 3
}

# Trigger AML investigation for high-risk countries
deny if {
    input.destination_country in ["high_risk_countries"]
    input.transaction_amount >= 5000
}

# Trigger AML investigation for structuring patterns
deny if {
    input.structuring_detected == true
}

# Trigger AML investigation for PEP (Politically Exposed Person)
deny if {
    input.is_pep == true
    input.transaction_amount >= 1000
}

# Always allow if human escalation requested (override)
allow if {
    input.escalation_requested == true
    input.escalation_reason == "false_positive"
}
