package fraud.block

# Policy for blocking transactions/accounts due to fraud

default allow = false

# Allow blocking if risk score is high
allow {
    input.risk_score >= 0.8
    input.risk_factors[_] == "Multiple failed transactions"
}

allow {
    input.risk_score >= 0.9
}

# Deny blocking if risk score is low
reason = "Risk score too low for blocking" {
    input.risk_score < 0.8
}

reason = "Insufficient risk factors" {
    count(input.risk_factors) < 2
}
