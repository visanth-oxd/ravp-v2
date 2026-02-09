# Policy: Account Modification
# Controls when account modifications can be made automatically
# Owned by Operations Team. Evaluated by policy-registry.

package customer_service.account_modification

import future.keywords.if
import future.keywords.in

# Default deny (require human approval)
allow := false

# Allow simple profile updates
allow if {
    input.modification_type in ["email_update", "phone_update", "address_update"]
    input.verification_status == "verified"
    input.account_age_days >= 30
}

# Allow preference changes
allow if {
    input.modification_type in ["notification_preferences", "language_preference"]
    input.verification_status == "verified"
}

# Always allow if human escalation requested
allow if {
    input.escalation_requested == true
}

# Deny sensitive modifications without verification
deny if {
    input.modification_type in ["account_closure", "beneficiary_change", "limit_change"]
    input.verification_status != "verified"
}

# Deny modifications for frozen accounts
deny if {
    input.account_status == "frozen"
}

# Deny modifications for accounts under investigation
deny if {
    input.account_status == "under_investigation"
}
