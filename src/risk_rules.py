"""
risk_rules.py

Contains simple, explainable rule logic that converts
transaction features and patterns into a risk_score and risk_bucket.

This is where you show how a risk analyst would turn observed behavior
into a numeric score.
"""

import pandas as pd


def apply_risk_rules(tx: pd.DataFrame) -> pd.DataFrame:
    """
    Add risk_score and risk_bucket columns to the transaction DataFrame.

    Rules (illustrative, not production grade):
    - New wallet with large outbound amount          -> +40
    - Tagged as mixing-like behavior                 -> +30
    - Tagged as high-risk counterparty               -> +40
    - Very large transaction                         -> +20
    - High-risk chains for this simulation (e.g. BTC)-> +10

    Bucketing:
    - risk_score < 30        -> LOW
    - 30 <= risk_score < 60  -> MEDIUM
    - risk_score >= 60       -> HIGH
    """

    tx = tx.copy()

    # Start everyone at zero
    tx["risk_score"] = 0

    # Rule 1: New wallet large outbound
    # We approximated this pattern in generate_data using "new_wallet_large_outbound".
    new_wallet_mask = tx["pattern_tags"].str.contains("new_wallet_large_outbound", na=False)
    tx.loc[new_wallet_mask, "risk_score"] += 40

    # Rule 2: Mixing-like behavior
    mixing_mask = tx["pattern_tags"].str.contains("mixing_like_outbound", na=False)
    tx.loc[mixing_mask, "risk_score"] += 30

    # Rule 3: High-risk counterparty interaction
    high_risk_counterparty_mask = tx["pattern_tags"].str.contains("high_risk_counterparty", na=False)
    tx.loc[high_risk_counterparty_mask, "risk_score"] += 40

    # Rule 4: Very large amount regardless of pattern tags
    very_large_amount_mask = tx["amount"] >= 1000.0
    tx.loc[very_large_amount_mask, "risk_score"] += 20

    # Rule 5: Simple chain-based adjustment
    # In some environments, specific chains may carry different fraud risk profiles.
    btc_mask = tx["chain"] == "BTC"
    tx.loc[btc_mask, "risk_score"] += 10

    # Finally, create a bucket for easier classification
    def bucket_score(score: int) -> str:
        if score < 30:
            return "LOW"
        elif score < 60:
            return "MEDIUM"
        else:
            return "HIGH"

    tx["risk_bucket"] = tx["risk_score"].apply(bucket_score)

    return tx
