package fraud.flag

# Policy for flagging accounts for review

default allow = true

# Always allow flagging if risk score is medium or high
allow {
    input.risk_score >= 0.5
}

allow {
    count(input.risk_factors) >= 1
}

# Deny flagging if risk score is very low
reason = "Risk score too low" {
    input.risk_score < 0.3
    count(input.risk_factors) == 0
}
