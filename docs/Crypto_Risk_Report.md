# Crypto Transaction Risk Simulation – Risk Notes

This document summarizes the synthetic crypto risk scenario modeled in the **Crypto Transaction Risk Simulator**. The goal is not to predict real-world blockchain crime, but to create a safe environment to practice how on-chain style risk analysis might work end to end.

---

## Scenario Overview

The dataset represents synthetic wallet-to-wallet activity across multiple chains. Each wallet has:

- **Country** – simple geographic context for flows.
- **wallet_age_days** – how long the wallet has existed.
- **is_exchange_linked** – whether the wallet is treated as being tied to an exchange or not.

Each transaction includes:

- **timestamp** – when the transfer occurred.
- **from_wallet / to_wallet** – source and destination wallets.
- **chain** – which blockchain the transfer is on (e.g., Chain A, Chain B).
- **amount** – transfer size.
- **is_fraud_pattern** – a synthetic label indicating that the transaction is part of an injected pattern.
- **risk_score / risk_bucket** – rule-based outputs that summarize risk.

This structure mirrors the kinds of fields a crypto exchange or fintech risk team would use to analyze on-chain exposure.

---

## Modeled Risk Patterns

The rules and labels are intentionally simplified but designed to look like common on-chain risk themes:

- **New wallet abuse**

  - Very young wallets (low `wallet_age_days`) sending larger or more frequent transactions.
  - Reflects scenarios where newly created wallets are used to quickly move funds before controls catch up.

- **High-risk counterparties**

  - Wallets that repeatedly appear in transactions with `is_fraud_pattern = 1`.
  - Represents counterparties that accumulate negative history over time.

- **Concentrated flows**

  - Many wallets sending into a small set of “hub” wallets.
  - Mimics patterns where funds are funneled to aggregation points or mixers.

- **Chain-level and country-level risk**
  - Some chains or countries have a higher share of flagged activity.
  - Illustrates how risk teams might reason about elevated exposure in specific segments of the network.

These patterns are not meant to be exhaustive. They are designed to give a realistic playground for talking through how rules might work in production.

---

## Scoring Approach

Each transaction is passed through a set of rule-based checks in `src/risk_rules.py`. The output includes:

- **risk_score** – a numeric score that increases as more risk conditions are met.
- **risk_bucket**:
  - `LOW` – score below a low-risk threshold.
  - `MEDIUM` – score in a mid-range.
  - `HIGH` – score above the high-risk threshold.

At the wallet level, the project aggregates:

- **tx_count** – number of outgoing transactions.
- **max_risk_score** – highest risk score seen for that wallet.
- **fraud_tx_count** – number of transactions where `is_fraud_pattern = 1`.
- **fraud_rate** – fraud transactions divided by total transactions.

This matches the way internal tools often surface both **transaction-level** and **wallet-level** views.

---

## How an Analyst Might Use This

The Streamlit dashboard and notebook are designed around a realistic analyst workflow:

1. **Filter the portfolio view**

   - By chain, country, or wallet risk bucket.

2. **Scan KPIs**

   - Total transactions in view.
   - Total wallets in view.
   - Number of high-risk wallets.
   - Overall fraud pattern rate.

3. **Review high-risk wallets**

   - Sort by `max_risk_score`, `fraud_rate`, or transaction count.
   - Focus on wallets that combine high risk and meaningful volume.

4. **Inspect a specific wallet**

   - Look at wallet age, country, and exchange link flag.
   - Understand how often it triggers patterns and what its fraud rate looks like.

5. **Check the wallet network**
   - Use the simple NetworkX graph to see which wallets it is most connected to in the current filtered view.
   - Identify potential hub wallets or suspicious clusters.

This is meant to mimic the feel of an internal tool where an analyst can move from top-level metrics down to individual wallets and relationships.

---

## Intended Use in an Interview Context

This project is not about building a production-grade blockchain analytics system. It is meant to:

- Show **end-to-end reasoning** about crypto-style transaction risk.
- Demonstrate the ability to:
  - Design synthetic data that resembles real-world fields.
  - Inject plausible risk patterns.
  - Build explainable rule-based scoring.
  - Surface insights in a dashboard.
  - Add UI tests to validate the core workflows.

The risk notes here provide a written narrative that can be referenced during an interview to explain how the simulator works and how it relates to real on-chain risk scenarios.
