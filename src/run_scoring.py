"""
run_scoring.py

Loads synthetic transactions, applies risk rules,
and saves a scored dataset.

Outputs:
- data/transactions_scored.csv
"""

from pathlib import Path
import pandas as pd

from risk_rules import apply_risk_rules

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data"


def main():
    tx_path = DATA_DIR / "transactions.csv"
    if not tx_path.exists():
        raise FileNotFoundError(
            f"{tx_path} not found. Run generate_data.py first to create synthetic transactions."
        )

    print(f"Loading transactions from {tx_path}...")
    tx = pd.read_csv(tx_path, parse_dates=["timestamp"])

    print("Applying risk rules...")
    tx_scored = apply_risk_rules(tx)

    output_path = DATA_DIR / "transactions_scored.csv"
    tx_scored.to_csv(output_path, index=False)
    print(f"Saved scored transactions to {output_path}")


if __name__ == "__main__":
    main()
