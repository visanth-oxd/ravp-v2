# Policy: Customer Complaint Resolution
# Controls when complaints can be auto-resolved vs requiring human intervention
# Owned by Customer Service Team. Evaluated by policy-registry.

package customer_service.complaint_resolution

import future.keywords.if
import future.keywords.in

# Default deny (require human review)
allow := false

# Auto-resolve simple complaints
allow if {
    input.complaint_type in ["password_reset", "account_info_update", "statement_request"]
    input.complaint_severity == "low"
    input.customer_satisfaction_score != null
    input.customer_satisfaction_score >= 3  # Satisfied customer (1-5 scale)
}

# Auto-resolve billing disputes under threshold
allow if {
    input.complaint_type == "billing_dispute"
    input.dispute_amount != null
    input.dispute_amount <= 100
    input.previous_disputes_count < 2
}

# Auto-resolve service issues with standard response
allow if {
    input.complaint_type == "service_issue"
    input.complaint_severity == "low"
    input.resolution_template != null
    input.resolution_template != ""
}

# Always allow if human escalation requested
allow if {
    input.escalation_requested == true
}

# Deny auto-resolution for high-severity complaints
deny if {
    input.complaint_severity == "high"
}

# Deny auto-resolution for regulatory complaints
deny if {
    input.complaint_type == "regulatory"
}

# Deny auto-resolution for repeated complaints
deny if {
    input.previous_complaints_count >= 3
    input.complaint_severity != "low"
}
