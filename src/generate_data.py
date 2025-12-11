"""
generate_data.py

Generates synthetic crypto wallets and transactions.
This is the foundation for the Crypto Transaction Risk Simulator.

Outputs:
- data/wallets.csv
- data/transactions.csv
"""

from pathlib import Path
import numpy as np
import pandas as pd
from datetime import datetime, timedelta

# Set a random seed so results are reproducible
np.random.seed(42)

# Base paths
PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data"
DATA_DIR.mkdir(exist_ok=True)


def generate_wallets(n_wallets: int = 2000) -> pd.DataFrame:
    """
    Create a synthetic set of crypto wallets.

    Each wallet has:
    - wallet_id: unique string ID
    - wallet_age_days: how many days since first activity
    - country: rough geo bucket
    - is_exchange_linked: whether this wallet is linked to an exchange
    """

    wallet_ids = [f"WALLET_{i:05d}" for i in range(1, n_wallets + 1)]

    # Wallet age between 0 and 720 days (0 means very new)
    wallet_age_days = np.random.randint(0, 720, size=n_wallets)

    countries = np.random.choice(
        ["US", "GB", "BR", "DE", "NG", "IN", "SG", "CA"],
        size=n_wallets,
        p=[0.25, 0.1, 0.1, 0.08, 0.08, 0.15, 0.12, 0.12],
    )

    # Most wallets are not directly tied to an exchange
    is_exchange_linked = np.random.choice(
        [0, 1],
        size=n_wallets,
        p=[0.8, 0.2],
    )

    wallets = pd.DataFrame(
        {
            "wallet_id": wallet_ids,
            "wallet_age_days": wallet_age_days,
            "country": countries,
            "is_exchange_linked": is_exchange_linked,
        }
    )

    return wallets


def generate_transactions(wallets: pd.DataFrame, n_transactions: int = 30000) -> pd.DataFrame:
    """
    Generate synthetic crypto transactions between wallets.

    Each transaction has:
    - tx_id: unique transaction ID
    - timestamp: when it happened
    - from_wallet: source wallet
    - to_wallet: destination wallet
    - amount: value of the transfer
    - chain: which chain (simplified)
    - tx_type: rough category for behavior
    """

    wallet_ids = wallets["wallet_id"].values
    n_wallets = len(wallet_ids)

    # Choose random pairs of wallets for from/to
    from_indices = np.random.randint(0, n_wallets, size=n_transactions)
    to_indices = np.random.randint(0, n_wallets, size=n_transactions)

    # Make sure from_wallet and to_wallet differ
    to_indices = np.where(
        to_indices == from_indices,
        (to_indices + 1) % n_wallets,
        to_indices,
    )

    from_wallets = wallet_ids[from_indices]
    to_wallets = wallet_ids[to_indices]

    # Generate timestamps over the last 90 days
    end_time = datetime.utcnow()
    start_time = end_time - timedelta(days=90)
    # Uniformly sample seconds in this window
    seconds_span = int((end_time - start_time).total_seconds())
    random_seconds = np.random.randint(0, seconds_span, size=n_transactions)
    timestamps = [start_time + timedelta(seconds=int(s)) for s in random_seconds]

    # Chains and transaction types
    chains = np.random.choice(
        ["BTC", "ETH", "USDC"],
        size=n_transactions,
        p=[0.3, 0.4, 0.3],
    )

    tx_types = np.random.choice(
        ["transfer", "swap", "contract_interaction"],
        size=n_transactions,
        p=[0.7, 0.2, 0.1],
    )

    # Amounts: log-normal like distribution to simulate heavy tails
    base_amounts = np.random.lognormal(mean=2.0, sigma=1.0, size=n_transactions)
    # Make some very small and some very large transactions
    amounts = np.round(base_amounts, 2)

    tx_ids = [f"TX_{i:06d}" for i in range(1, n_transactions + 1)]

    tx = pd.DataFrame(
        {
            "tx_id": tx_ids,
            "timestamp": timestamps,
            "from_wallet": from_wallets,
            "to_wallet": to_wallets,
            "amount": amounts,
            "chain": chains,
            "tx_type": tx_types,
        }
    )

    # Sort by time to make downstream analysis easier
    tx = tx.sort_values("timestamp").reset_index(drop=True)

    return tx


def inject_fraud_patterns(wallets: pd.DataFrame, tx: pd.DataFrame) -> pd.DataFrame:
    """
    Inject simple synthetic fraud-like patterns into the transaction data.

    We add:
    - is_fraud_pattern: 1 if the transaction is part of a known synthetic pattern, else 0
    - pattern_tags: free-text field describing which pattern(s) were applied

    Patterns we simulate:
    - New wallet abuse: very new wallets sending large outbound transfers
    - Mixing-like behavior: wallets with many small inbound tx then one large outbound
    - High-risk counterparties: small set of wallets treated as "bad" and tagged
    """

    tx = tx.copy()
    tx["is_fraud_pattern"] = 0
    tx["pattern_tags"] = ""

    # Merge wallet features into transactions for easier labeling
    wallets_short = wallets[["wallet_id", "wallet_age_days", "country", "is_exchange_linked"]]
    tx = tx.merge(
        wallets_short.add_prefix("from_"),
        left_on="from_wallet",
        right_on="from_wallet_id",
        how="left",
    )
    tx = tx.merge(
        wallets_short.add_prefix("to_"),
        left_on="to_wallet",
        right_on="to_wallet_id",
        how="left",
    )

    # Pattern 1: New wallet abuse (very young wallets sending big amounts)
    young_threshold_days = 7
    large_amount_threshold = 500.0

    mask_new_wallet_abuse = (
        (tx["from_wallet_age_days"] <= young_threshold_days)
        & (tx["amount"] >= large_amount_threshold)
    )

    tx.loc[mask_new_wallet_abuse, "is_fraud_pattern"] = 1
    tx.loc[mask_new_wallet_abuse, "pattern_tags"] = tx.loc[
        mask_new_wallet_abuse, "pattern_tags"
    ].astype(str) + ";new_wallet_large_outbound"

    # Pattern 2: Mixing-like behavior
    # For wallets that receive many small inbound payments then send a big outbound one
    # Step 1: mark small inbound transactions
    small_inbound_threshold = 50.0

    small_inbound = tx[tx["amount"] <= small_inbound_threshold].groupby("to_wallet")[
        "tx_id"
    ].count()
    potential_mixers = small_inbound[small_inbound >= 10].index  # 10 or more small credits

    # For those potential mixer wallets, flag the largest outbound transaction as fraud pattern
    for w in potential_mixers:
        outbound_mask = tx["from_wallet"] == w
        if outbound_mask.sum() == 0:
            continue
        # pick the largest outbound
        idx = tx.loc[outbound_mask, "amount"].idxmax()
        tx.loc[idx, "is_fraud_pattern"] = 1
        tx.loc[idx, "pattern_tags"] = str(tx.loc[idx, "pattern_tags"]) + ";mixing_like_outbound"

    # Pattern 3: High-risk counterparties
    # Choose a few wallets as "known bad" and flag any transaction that interacts with them
    n_high_risk_wallets = max(5, int(len(wallets) * 0.01))
    high_risk_wallets = np.random.choice(wallets["wallet_id"].values, size=n_high_risk_wallets, replace=False)

    mask_high_risk_counterparty = tx["from_wallet"].isin(high_risk_wallets) | tx[
        "to_wallet"
    ].isin(high_risk_wallets)

    tx.loc[mask_high_risk_counterparty, "is_fraud_pattern"] = 1
    tx.loc[mask_high_risk_counterparty, "pattern_tags"] = tx.loc[
        mask_high_risk_counterparty, "pattern_tags"
    ].astype(str) + ";high_risk_counterparty"

    # Clean up helper merge columns we do not want in the final CSV
    drop_cols = [
        "from_wallet_id",
        "to_wallet_id",
    ]
    tx = tx.drop(columns=drop_cols)

    return tx


def main():
    """
    End-to-end data generation:
    - build wallets
    - build transactions
    - inject patterns
    - save to CSV
    """

    print("Generating wallets...")
    wallets = generate_wallets()
    wallets_path = DATA_DIR / "wallets.csv"
    wallets.to_csv(wallets_path, index=False)
    print(f"Saved wallets to {wallets_path}")

    print("Generating transactions...")
    tx = generate_transactions(wallets)
    print(f"Generated {len(tx)} transactions")

    print("Injecting fraud patterns...")
    tx_with_patterns = inject_fraud_patterns(wallets, tx)

    tx_path = DATA_DIR / "transactions.csv"
    tx_with_patterns.to_csv(tx_path, index=False)
    print(f"Saved transactions with patterns to {tx_path}")


if __name__ == "__main__":
    main()
