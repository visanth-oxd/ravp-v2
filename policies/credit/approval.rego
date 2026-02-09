# Policy: Credit Approval
# Controls when credit applications can be approved automatically
# Owned by Credit Risk Team. Evaluated by policy-registry.

package credit.approval

import future.keywords.if
import future.keywords.in

# Default deny (require human review)
allow := false

# Auto-approve for excellent credit profiles
allow if {
    input.credit_score >= 750
    input.income != null
    input.requested_limit != null
    input.requested_limit <= input.income * 0.2  # 20% of income
    input.employment_status == "employed"
    input.employment_months >= 12
    input.existing_debt_ratio < 0.3  # Less than 30% debt-to-income
}

# Auto-approve secured credit with collateral
allow if {
    input.credit_type == "secured"
    input.collateral_value != null
    input.requested_limit <= input.collateral_value * 0.8
    input.credit_score >= 600
}

# Always allow if human escalation requested
allow if {
    input.escalation_requested == true
}

# Deny if credit score too low
deny if {
    input.credit_score < 550
}

# Deny if requested limit too high relative to income
deny if {
    input.requested_limit > input.income * 0.5  # More than 50% of income
}

# Deny if high existing debt
deny if {
    input.existing_debt_ratio >= 0.5  # More than 50% debt-to-income
}

# Deny if recent bankruptcy or default
deny if {
    input.has_recent_bankruptcy == true
}

deny if {
    input.has_recent_default == true
}
