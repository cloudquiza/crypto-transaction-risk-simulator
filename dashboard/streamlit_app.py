"""
streamlit_app.py

Crypto Transaction Risk Simulator dashboard.

What this dashboard shows:
- Portfolio-level KPIs for synthetic crypto transactions
- High-risk wallets and their basic stats
- Transaction-level view filtered by chain, country, and risk bucket
- Simple network view around a selected wallet using NetworkX

This is designed to mimic an internal risk analyst tool at a crypto exchange or fintech.
"""

from pathlib import Path

import pandas as pd
import streamlit as st
import networkx as nx
import matplotlib.pyplot as plt

# ---------- Paths & Data Loading ----------

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data"


@st.cache_data
def load_data():
    """
    Load scored transactions and wallet metadata from CSV.

    Returns:
    - tx: transaction-level DataFrame with risk_score and risk_bucket
    - wallets: wallet-level DataFrame
    - wallet_risk: aggregated wallet-level risk stats (joined with wallet metadata)
    """
    tx_path = DATA_DIR / "transactions_scored.csv"
    wallets_path = DATA_DIR / "wallets.csv"

    tx = pd.read_csv(tx_path, parse_dates=["timestamp"])
    wallets = pd.read_csv(wallets_path)

    # Ensure scored columns exist
    if "risk_score" not in tx.columns or "risk_bucket" not in tx.columns:
        raise ValueError(
            "transactions_scored.csv is missing risk_score or risk_bucket. "
            "Run src/run_scoring.py first."
        )

    # Some older CSVs may not have is_fraud_pattern; default to 0 if missing
    if "is_fraud_pattern" not in tx.columns:
        tx["is_fraud_pattern"] = 0

    # Boolean for readability
    tx["has_fraud_pattern"] = tx["is_fraud_pattern"].astype(bool)

    # ---- Build wallet-level risk view based on FROM wallet behavior ----
    wallet_group = (
        tx.groupby("from_wallet")
        .agg(
            tx_count=("tx_id", "count"),
            avg_risk_score=("risk_score", "mean"),
            max_risk_score=("risk_score", "max"),
            fraud_tx_count=("has_fraud_pattern", "sum"),
        )
        .reset_index()
        .rename(columns={"from_wallet": "wallet_id"})
    )

    # Join wallet metadata (age, country, exchange flag)
    wallets_short = wallets[["wallet_id", "wallet_age_days", "country", "is_exchange_linked"]]
    wallet_risk = wallet_group.merge(wallets_short, on="wallet_id", how="left")

    # Bucket wallets by max risk score
    def wallet_bucket(score: float) -> str:
        if pd.isna(score):
            return "UNKNOWN"
        if score < 30:
            return "LOW"
        elif score < 60:
            return "MEDIUM"
        else:
            return "HIGH"

    wallet_risk["wallet_risk_bucket"] = wallet_risk["max_risk_score"].apply(wallet_bucket)
    wallet_risk["fraud_rate"] = wallet_risk["fraud_tx_count"] / wallet_risk["tx_count"]

    return tx, wallets, wallet_risk


# ---------- Helper Functions ----------

def filter_data(tx: pd.DataFrame, wallet_risk: pd.DataFrame,
                chains, countries, wallet_buckets):
    """
    Apply sidebar filters to both transaction and wallet-level views.

    We filter at the wallet level (country, bucket), then restrict transactions
    to those whose from_wallet is in the allowed wallet set.
    """
    tx_filtered = tx.copy()
    wallet_filtered = wallet_risk.copy()

    # Chain filter (transaction-level)
    if chains:
        tx_filtered = tx_filtered[tx_filtered["chain"].isin(chains)]

    # Country filter (wallet-level)
    if countries:
        wallet_filtered = wallet_filtered[wallet_filtered["country"].isin(countries)]

    # Risk bucket filter (wallet-level)
    if wallet_buckets:
        wallet_filtered = wallet_filtered[
            wallet_filtered["wallet_risk_bucket"].isin(wallet_buckets)
        ]

    # Restrict transactions to wallets that passed wallet-level filters
    allowed_wallets = wallet_filtered["wallet_id"].unique()
    tx_filtered = tx_filtered[tx_filtered["from_wallet"].isin(allowed_wallets)]

    return tx_filtered, wallet_filtered


def compute_kpis(tx: pd.DataFrame, wallet_risk: pd.DataFrame):
    """
    Compute top-line KPIs for the current filtered view.
    """
    total_tx = len(tx)
    total_wallets = wallet_risk["wallet_id"].nunique()

    high_risk_wallets = wallet_risk[
        wallet_risk["wallet_risk_bucket"] == "HIGH"
    ]["wallet_id"].nunique()

    fraud_pattern_rate = 0.0
    if total_tx > 0:
        fraud_pattern_rate = tx["has_fraud_pattern"].sum() / total_tx

    avg_risk_score = tx["risk_score"].mean() if total_tx > 0 else 0.0

    return {
        "total_tx": total_tx,
        "total_wallets": total_wallets,
        "high_risk_wallets": high_risk_wallets,
        "fraud_pattern_rate": fraud_pattern_rate,
        "avg_risk_score": avg_risk_score,
    }


def build_wallet_network(tx: pd.DataFrame, center_wallet: str, max_neighbors: int = 25):
    """
    Build a simple NetworkX graph focused on a center wallet.

    - Nodes: wallets
    - Edges: transactions between wallets in the filtered data
    - Only includes edges touching the center_wallet and its direct neighbors.
    """
    sub_tx = tx[
        (tx["from_wallet"] == center_wallet) | (tx["to_wallet"] == center_wallet)
    ].copy()

    if len(sub_tx) > max_neighbors:
        sub_tx = sub_tx.sort_values("timestamp", ascending=False).head(max_neighbors)

    G = nx.Graph()

    for _, row in sub_tx.iterrows():
        fw = row["from_wallet"]
        tw = row["to_wallet"]
        G.add_edge(fw, tw, risk_score=row["risk_score"])

    return G


def draw_wallet_network(G: nx.Graph, center_wallet: str):
    """
    Render the NetworkX graph using matplotlib and display it in Streamlit.
    """
    if G.number_of_nodes() == 0:
        st.info("No network connections to display for this wallet in the current view.")
        return

    plt.figure(figsize=(6, 4))
    pos = nx.spring_layout(G, seed=42)

    # All nodes
    nx.draw_networkx_nodes(G, pos, node_size=300, alpha=0.8)

    # Highlight center wallet
    if center_wallet in G.nodes:
        nx.draw_networkx_nodes(
            G,
            pos,
            nodelist=[center_wallet],
            node_size=600,
            node_shape="s",
        )

    nx.draw_networkx_edges(G, pos, alpha=0.5)
    nx.draw_networkx_labels(G, pos, font_size=8)

    plt.axis("off")
    st.pyplot(plt.gcf())
    plt.close()


# ---------- Streamlit App ----------

def main():
    st.set_page_config(
        page_title="Crypto Transaction Risk Simulator",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    st.title("Crypto Transaction Risk Simulator")
    st.caption(
        "Synthetic on-chain-style transactions, risk scoring, and wallet relationship analysis."
    )

    # Load data
    tx, wallets, wallet_risk = load_data()

    # ----- Sidebar Filters -----
    st.sidebar.header("Filters")

    # Chains (from transaction-level data)
    all_chains = sorted(tx["chain"].unique().tolist())
    selected_chains = st.sidebar.multiselect(
        "Chain",
        options=all_chains,
        default=all_chains,
    )

    # Countries (from wallet-level data)
    all_countries = sorted(wallet_risk["country"].dropna().unique().tolist())
    selected_countries = st.sidebar.multiselect(
        "Country",
        options=all_countries,
        default=all_countries,
    )

    # Wallet risk buckets
    all_buckets = ["LOW", "MEDIUM", "HIGH"]
    selected_buckets = st.sidebar.multiselect(
        "Wallet risk bucket",
        options=all_buckets,
        default=all_buckets,
    )

    # Apply filters
    tx_filtered, wallet_filtered = filter_data(
        tx, wallet_risk, selected_chains, selected_countries, selected_buckets
    )

    # ----- KPIs -----
    kpis = compute_kpis(tx_filtered, wallet_filtered)

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Transactions", f"{kpis['total_tx']:,}")
    col2.metric("Wallets", f"{kpis['total_wallets']:,}")
    col3.metric("High-risk wallets", f"{kpis['high_risk_wallets']:,}")
    col4.metric(
        "Fraud pattern rate",
        f"{kpis['fraud_pattern_rate']*100:.1f}%",
    )

    st.markdown("---")

    # ----- Layout: left = wallet table, right = details + network -----
    left_col, right_col = st.columns([1.2, 1])

    with left_col:
        st.subheader("High-risk wallets")

        if not wallet_filtered.empty:
            top_wallets = (
                wallet_filtered.sort_values("max_risk_score", ascending=False)
                .head(50)
                .copy()
            )

            display_cols = [
                "wallet_id",
                "wallet_risk_bucket",
                "max_risk_score",
                "tx_count",
                "fraud_tx_count",
                "fraud_rate",
                "wallet_age_days",
                "country",
                "is_exchange_linked",
            ]
            display_cols = [c for c in display_cols if c in top_wallets.columns]

            st.dataframe(
                top_wallets[display_cols],
                use_container_width=True,
                height=400,
            )
        else:
            st.info("No wallets match the selected filters.")

    with right_col:
        st.subheader("Wallet details and network")

        if not wallet_filtered.empty:
            wallet_choices = wallet_filtered["wallet_id"].sort_values().unique().tolist()
            selected_wallet = st.selectbox(
                "Select wallet",
                options=wallet_choices,
            )

            selected_stats = wallet_filtered[wallet_filtered["wallet_id"] == selected_wallet]
            if not selected_stats.empty:
                row = selected_stats.iloc[0]
                st.markdown(f"**Wallet ID:** `{row['wallet_id']}`")
                st.markdown(f"**Wallet risk bucket:** {row['wallet_risk_bucket']}")
                st.markdown(f"**Max risk score:** {row['max_risk_score']:.1f}")
                st.markdown(f"**Transactions:** {int(row['tx_count'])}")
                st.markdown(f"**Fraud transactions:** {int(row['fraud_tx_count'])}")
                st.markdown(f"**Fraud rate:** {row['fraud_rate']*100:.1f}%")
                st.markdown(f"**Wallet age (days):** {int(row['wallet_age_days'])}")
                st.markdown(f"**Country:** {row['country']}")
                st.markdown(
                    f"**Exchange linked:** {'Yes' if row['is_exchange_linked'] == 1 else 'No'}"
                )

            st.markdown("### Wallet network view")

            G = build_wallet_network(tx_filtered, selected_wallet)
            draw_wallet_network(G, selected_wallet)
        else:
            st.info("No wallet details to display with the current filters.")


if __name__ == "__main__":
    main()

