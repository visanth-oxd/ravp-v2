# Policy: KYC (Know Your Customer) Verification
# Controls when KYC verification is required or can be automated
# Owned by Compliance Team. Evaluated by policy-registry.

package compliance.kyc_verification

import future.keywords.if
import future.keywords.in

# Default deny (require verification)
allow := false

# Auto-verify for low-risk customers with good history
allow if {
    input.customer_risk_tier == "low"
    input.account_age_days >= 365  # At least 1 year old
    input.verification_status == "partial"
    input.transaction_volume_12m < 50000
    input.no_suspicious_activity == true
}

# Auto-verify if documents already verified
allow if {
    input.identity_documents_verified == true
    input.address_verified == true
    input.kyc_level == "standard"
}

# Always allow if human escalation requested
allow if {
    input.escalation_requested == true
}

# Deny auto-verification for high-risk customers
deny if {
    input.customer_risk_tier == "high"
}

# Deny auto-verification for PEP
deny if {
    input.is_pep == true
}

# Deny auto-verification for large transaction volumes
deny if {
    input.transaction_volume_12m >= 100000
}

# Deny auto-verification if documents expired
deny if {
    input.identity_documents_expired == true
}
