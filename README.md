# Dynamic Risk Exposure Engine

### A Walk-Forward Validated Machine Learning Framework for Dynamic Equity Exposure Management

**📊 [Live Interactive Report](https://rigojohn.github.io/Dynamic-Risk-Exposure-Engine/)** · **📓 [Notebook](Trading_Oriented_MachineLearning_Project.ipynb)** · **📄 [Requirements](requirements.txt)**

---

## Abstract

This work presents a validation-disciplined machine learning framework that converts probabilistic estimates of favorable market regimes into a deterministic, risk-controlled equity exposure policy. Rather than forecasting price levels or issuing binary buy/sell signals, an XGBoost classifier estimates `P(y_t = 1 | X_t)` — the probability that a forward-looking, weighted open-to-open return exceeds a train-derived threshold — and a separate, non-learned exposure engine maps this probability, together with point-in-time trend, volatility, drawdown and sentiment state, into a target position. The framework is **asset-agnostic**: it accepts any sufficiently liquid stock, ETF or index ticker, is evaluated walk-forward, and is benchmarked against buy-and-hold on out-of-sample, cost-adjusted, risk-first metrics (Sharpe ratio, Calmar ratio, maximum drawdown, turnover) for that asset. The same probability-to-exposure architecture extends naturally to other continuously-traded instruments, including cryptocurrency markets (Section 17). The central research question is whether this probability-to-exposure pipeline improves the *risk-adjusted* profile of a passive holding, rather than raw return alone.

## 1. Introduction and Research Objective

**Research question.** Does a validation-disciplined XGBoost probability model, translated through a deterministic exposure engine, improve risk-adjusted out-of-sample behavior relative to buy-and-hold?

The classifier does not predict price or daily return directly. It estimates

```
risk_on_proba = P(y_t = 1 | X_t)
```

where `y_t` is a binary label for a favorable future-return regime, defined from a weighted blend of forward open-to-open returns exceeding a threshold derived strictly from training data. The exposure engine then converts this probability into `target_position` using trend, volatility, drawdown, sentiment and risk controls. An execution/backtest layer applies a one-row execution delay, a no-trade (rebalance) band, transaction costs, cash yield on unallocated capital, and financing costs for leverage above 1.0, before comparing against buy-and-hold under identical timing and cost assumptions.

**Evaluation philosophy.** Assessment is risk-first: emphasis is placed on the Sharpe/Calmar edge over buy-and-hold, drawdown reduction, volatility, turnover and transaction costs — not on maximizing raw return in isolation.

**Scope.** The workflow accepts any sufficiently liquid stock, ETF or index ticker and constructs ticker-based price, cross-market, sentiment and filing/event features without hardcoded, asset-specific assumptions.

## 2. System Architecture

The system is deliberately separated into three stages — **prediction**, **exposure construction**, and **execution/backtesting** — so that timing and tuning boundaries stay explicit and lookahead/leakage risk is minimized:

1. **Data / context** — daily OHLCV with a warm-up history window, cross-market variables, real-news sentiment, and SEC filing/event context for the selected asset.
2. **Point-in-time features** — technical, volatility, volume, trend, sentiment and event features aligned to the after-close signal time; news and filing inputs are shifted one trading row.
3. **Chronological split and labels** — train/validation/test order is preserved in time; labels use weighted forward open-to-open returns and thresholds derived only from the allowed training window.
4. **Probability models** — a weighted XGBoost baseline and an Optuna-tuned candidate estimate `risk_on_proba = P(y_t = 1 | X_t)`. The output is a probability, never a trade.
5. **Validation / walk-forward selection** — candidates are compared across walk-forward folds; exposure, sentiment and risk settings are selected on validation using train-only probabilities and locked before the final test.
6. **Final test and metrics** — the selected probability path and locked engine settings are evaluated once on the held-out test window.

## 3. Data and Market Context

Primary prices (daily OHLCV) are sourced via Yahoo Finance (`yfinance`) for the selected asset. A two-year warm-up period precedes the formal sample so that rolling indicators stabilize before the modeling sample begins; the sample then remains in strict chronological train → validation → test order — **there is no random split**.

- **Technical market state** — trend, momentum, volatility, drawdown and volume-pressure indicators over 1d/3d/5d/10d/20d windows (RSI, StochRSI, MACD family, SMA/EMA trend, VWMA, ATR, Bollinger width, realized volatility, drawdown-from-peak, volume/dollar-volume z-scores).
- **Cross-market context** — regime information from related markets, used without hardcoded per-asset assumptions.
- **Sentiment context** — real-news sentiment features (optional FinBERT integration).
- **Filing/event context** — SEC filing counts (total, 8-K, 10-Q/10-K, days-since-filing) resolved via CIK when available; shifted by one trading row; neutral when unavailable ("best-effort", never fabricated).

## 4. Feature Engineering

Features are constructed to be strictly point-in-time: the model observes information available **after** the market close at time `t`, builds the feature row for that close, and the exposure engine executes at the **next** market open. Sentiment and filing/event inputs are shifted by one trading row so that same-day news or filings are never treated as tradable information for that row; no-news / no-filing periods remain neutral rather than being coerced into an artificial positive or negative signal.

Feature families include trend and momentum (multi-horizon returns/momentum), volatility and stress (`atr_14_pct`, `bb_width_pct`, `bb_position`, `volatility_5d/20d/60d`, `volatility_ratio_5_20`, `volatility_ratio_20_60`, `drawdown_20d/60d`, `overnight_gap`, `gap_volatility_20d`), liquidity/volume, cross-market regime, sentiment, and filing/event context.

## 5. Target Construction and Chronological Split

The target is a **binary label for a favorable future-return regime** — not a raw price prediction and not a prediction of the next close. Because the trading workflow acts at the next session open, the executable entry is `Open.shift(-1)`, matching the exposure engine's next-session execution timing. Labels are based on a weighted blend of 3-day, 5-day and 10-day open-to-open forward returns.

The feature table `df_ta` is split chronologically into train (earliest 60%), validation (next 20%) and test (final 20%) **before** `add_future_return_target()` is applied independently within each split — preventing future-return boundary leakage across splits. The classification threshold is derived from training data only (`WF_TARGET_QUANTILE = 0.60`) and re-derived per fold during walk-forward evaluation; validation and test rows never set their own threshold.

## 6. Machine Learning Models

For each trading day `t`, the model receives a feature vector `X_t` built from the technical, volatility, volume, cross-market, sentiment and event variables above, and learns from the binary label `y_t ∈ {0,1}` constructed in Section 5. The output is

```
risk_on_proba = P(y_t = 1 | X_t)
```

**Model family.** XGBoost — an additive ensemble of decision trees, where the raw score is the sum of individual tree contributions:

```
score(X_t) = sum_k f_k(X_t)
```

This raw score is mapped to a probability via a sigmoid link. Two candidates are compared: a **weighted XGBoost baseline** and an **Optuna-tuned** variant (TPE sampler, 50 trials) that jointly searches XGBoost hyperparameters and a compact set of trading/exposure parameters (`decision_threshold`, `low_exposure`, `high_exposure`, `risk_off_exposure`, `risk_on_boost`, `rebalance_threshold`, `fast_vol_threshold`). The tuned candidate is treated as a *candidate*, never an automatic replacement for the baseline.

## 7. Dynamic Exposure Engine

The exposure engine is **not** a second machine learning model — it is a fixed, deterministic set of portfolio rules. Given a candidate probability `p_t`, point-in-time market state `Z_t`, and a locked parameter set `θ`, it outputs the desired `target_position`, the realized position after execution delay, net returns, equity curves, drawdowns and final metrics:

```
p_t^(W)  --engine-->  metrics^(W)
p_t^(O)  --engine-->  metrics^(O)
```

Because both the weighted-baseline path `p_t^(W)` and the Optuna-tuned path `p_t^(O)` are passed through the *identical* engine and execution rules, the comparison isolates the effect of the probability signal itself. The engine incorporates:

- Risk-on / risk-off regime switching
- Volatility- and drawdown-based exposure controls
- Fast risk-off (defensive) and early risk-on (recovery) overlays
- Multiplicative sentiment scaling
- Turnover-aware, rebalance-band execution
- Transaction costs, cash yield on unallocated capital, and financing costs for leverage above 1.0
- Hard exposure constraints

## 8. Walk-Forward Model Selection and Validation-Safe Tuning

The weighted-baseline and Optuna-tuned candidates are compared over the chronological train + validation region using an **expanding-window walk-forward** protocol: each fold trains on all available past data, predicts the next unseen block, computes probability thresholds from fold-training probabilities only, and evaluates fixed preliminary exposure rules on the evaluation block.

Risk/exposure settings, fast-risk-off controls, early-risk-on behavior and sentiment settings are then selected — in that order — with a **train-only validation model**, merged into `selected_risk_settings`, and **locked** before final testing; the test set is never used for tuning. Early-risk-on remains gated by `fast_risk_off == 0`, and an active fast-risk-off defensive cap can override it.

## 9. Validation Discipline

A subtle but critical detail: `lower_threshold` and `upper_threshold` are computed **from fold-training probabilities only** — the evaluation fold never influences its own thresholds. Computing thresholds on train + evaluation combined would let the evaluation period indirectly set the bar for its own classification, a form of lookahead bias that inflates apparent performance. This isolation is enforced at every pipeline step:

| Stage | Uses |
|---|---|
| Target-label threshold | Train only |
| Validation-model training | Train only |
| Risk / sentiment / overlay selection | Train-only validation model, evaluated on validation |
| Final model | Train + validation only |
| Final metrics | Held-out test only, never used for tuning |

## 10. Recommended Extension: Purged Walk-Forward Validation

The walk-forward protocol in Section 8 already restricts thresholds and tuning to train-only information at each fold. However, because labels are built from a **blended 3-day/5-day/10-day forward return** (Section 5), every row's label depends on price information up to 10 trading days *ahead* of that row. This creates **label overlap** at every fold boundary — and at the main train/validation/test boundaries — even though the split itself is strictly chronological: a training row just before a cut can share realized-return information with the first evaluation rows after it. This is a well-known, subtle leakage channel in financial machine learning (López de Prado, *Advances in Financial Machine Learning*, 2018), and purging is the standard remedy.

**Purging.** Before evaluating any fold or split boundary, drop training observations whose label horizon `[t, t+H]` overlaps the evaluation block's time range, where `H` is the maximum label horizon in use (10 trading days here, matching the 3/5/10-day blend). This removes exactly the training rows near a boundary that would otherwise leak forward information into evaluation.

**Embargo.** After purging, add a further buffer of a few trading days *after* each evaluation block before its data becomes eligible for training again, to also absorb serial correlation in features and model predictions that purging alone does not fully remove.

**How it extends the current design:**

- Apply purge + embargo at every walk-forward fold boundary (Section 8), in addition to the existing train-only threshold and tuning discipline (Section 9).
- Apply the same purge logic at the main 60/20/20 train/validation/test boundaries (Section 5), not only at walk-forward folds.
- Practical starting parameters: purge width = `H = 10` trading days; embargo width = a small fixed buffer (e.g. 1–5 trading days) or ~1% of the evaluation block size, as a tunable setting.

**Why this matters for scaling further:**

- It tightens the "no lookahead bias" guarantee that Section 9 already emphasizes — the more assets, tickers and overlapping-horizon targets the framework is run across (including a 24/7 crypto calendar per Section 17, which has no session gaps to naturally separate folds), the more fold boundaries exist, and purging removes the leakage risk at each one systematically rather than case by case.
- It reduces optimistic bias in the Sharpe/Calmar estimates used for candidate and hyperparameter selection (Section 8, Optuna search), which matters more as the number of assets and search trials grows — with more trials, it becomes easier to "discover" a configuration that only looks good because of boundary leakage.
- It is a natural stepping stone to **Combinatorial Purged Cross-Validation (CPCV)**: generating multiple purged train/test path combinations from the same data to estimate a **Probability of Backtest Overfitting (PBO)**. This becomes directly useful once the framework is evaluated across many tickers and many tuning trials, where the odds of selecting an overfit configuration purely by chance increase with scale.
- Implementation cost is modest: purge/embargo logic is a filter on training indices at fold-construction time — it does not require changes to the classifier, the exposure engine, or the metrics layer.

## 11. Interpretability

Model behavior is inspected with **SHAP** (SHapley Additive exPlanations) to attribute the probability output to individual features, supporting qualitative checks that the model relies on financially sensible signals rather than spurious correlations.

## 12. Empirical Results

Each run produces a full out-of-sample backtest for whichever ticker is selected — any liquid stock, ETF or index — and compares the dynamic exposure strategy against a buy-and-hold benchmark on the same asset over the same held-out window. Because the pipeline is asset-agnostic, results are not tied to a single name: the notebook maintains a running **cross-asset history**, appending each run's final out-of-sample metrics to a shared table (including repeated tickers across time), so performance can be compared *across* equities rather than read off one example.

For each asset, the metrics comparison reports strategy vs. buy-and-hold side by side, plus an **Edge** column (strategy − buy-and-hold) for each metric: positive Edge (Sharpe, Calmar, return) is favorable, and a positive Sharpe Edge with lower or comparable drawdown is the working definition of "successful" for that asset. This lets the framework be evaluated as a general policy — does it tend to improve the risk-adjusted profile across many equities — rather than as a fit to any one instrument. Full metrics, candlestick and equity-curve charts for the current run, and the complete cross-asset history, are in the [live interactive report](https://rigojohn.github.io/Dynamic-Risk-Exposure-Engine/).

## 13. Evaluation Metrics

- Total Return, Annualized Return
- Sharpe Ratio, Sortino Ratio, Calmar Ratio
- Maximum Drawdown
- Annualized Volatility
- Turnover
- Win Rate

## 14. Limitations and Disclaimer

This project is for **academic and research purposes only**. It does not constitute financial advice and should not be used as a live trading system without further validation, risk assessment and market testing. SEC filing and sentiment features are best-effort and degrade gracefully to neutral values when data is unavailable; FinBERT sentiment scoring is optional and disabled by default. Results are asset- and period-specific and are not a guarantee of future performance.

## 15. Reproducibility

1. Extract/clone the repository — no hardcoded paths are required; the notebook must run from the project root.
2. Open `Trading_Oriented_MachineLearning_Project.ipynb` with Python 3.11 or 3.12 (64-bit), in Jupyter, JupyterLab or VS Code + Jupyter extension. Avoid Python 3.13.
3. Run the core install cell (`requirements.txt`). Set `USE_LIVE_SENTIMENT=False` for offline/slow connections; `transformers`/`torch` are not required unless `USE_FINBERT=True`.
4. Select a ticker in Yahoo Finance format (e.g. `AAPL`, `MSFT`, `SPY`, `^GSPC`) — see the [Yahoo Finance lookup](https://finance.yahoo.com/lookup/).
5. Run All. An internet connection is required for market data and news. The report is written to `presentation_outputs/ml_model_presentation_latest.html`.

## 16. Extensibility to Other Instruments

Nothing in the probability-to-exposure architecture (Section 2) is specific to any one equity — the classifier, feature pipeline and exposure engine operate on any point-in-time OHLCV-plus-context series and any train-derived target threshold. Generalizing to a new liquid stock, ETF or index is already handled by selecting a different ticker (Section 15); no structural change is required.

## 17. Scaling to Cryptocurrency Markets

The same architecture can, in principle, be extended to cryptocurrency pairs with comparatively few changes, since crypto markets are electronically traded, liquid, and produce the same kind of OHLCV time series the pipeline already consumes. The main adaptation is that crypto trades **24/7/365**, with no exchange session boundaries — which changes several assumptions that are currently built around equity market hours:

| Component | Equities (current) | Crypto (adaptation needed) |
|---|---|---|
| Trading calendar | Fixed session (e.g. 9:30–16:00, weekdays only) | Continuous — redefine "day" as a fixed UTC bar (e.g. 00:00 UTC close) instead of an exchange close |
| Execution timing | `Open.shift(-1)` at next session open | Next fixed-interval bar open (e.g. next UTC daily/hourly open); no session gap to wait for |
| Overnight-gap features | `overnight_gap`, `gap_volatility_20d` (close→next open) | Not meaningful without session breaks — drop or replace with short-horizon realized-volatility features |
| Market data source | `yfinance` (equities/ETFs) | Exchange API or aggregator (e.g. Binance/Coinbase REST, CCXT) for OHLCV, funding rates, order-book depth |
| Filing/event context | SEC filings via CIK (8-K, 10-Q/10-K) | No direct equivalent — drop, or substitute protocol-level events (exchange listings, halvings, governance votes) or on-chain metrics (active addresses, exchange net-flows), kept neutral by default like today's best-effort SEC handling |
| Cross-market context | Equity indices / sector proxies | Crypto-specific proxies (e.g. BTC/ETH dominance, stablecoin flows, DXY/macro liquidity) |
| Sentiment pipeline | News sentiment (optional FinBERT) | Largely reusable — repoint at crypto-specific news/social sources |
| Transaction costs & financing | Commission (bps), margin financing | Exchange taker/maker fees, funding-rate carry for perpetuals, borrow costs for leverage |
| Volatility / risk calibration | Tuned for equity volatility regimes | Re-tune thresholds, rebalance band and exposure caps — crypto volatility and drawdowns are structurally larger |

Everything downstream of these inputs — the XGBoost probability model, the walk-forward selection protocol, the validation-safe tuning order, and the deterministic exposure engine itself (Sections 5–9) — carries over unchanged. In short, scaling to crypto is a **data-source and calendar substitution**, plus re-calibration of risk parameters to a higher-volatility regime, not a redesign of the modeling framework.

## 18. Live Interactive Report

GitHub does not execute JavaScript when an `.html` file is opened inside the repository's file browser — it only renders the raw source. This repository is published with **GitHub Pages** instead, so the report is viewable as a live, fully interactive page (charts, SHAP plots, section navigation):

**→ https://rigojohn.github.io/Dynamic-Risk-Exposure-Engine/**

`index.html` at the repository root redirects to the current report at `presentation_outputs/ml_model_presentation_latest.html`; the link above always reflects the latest run.

## Tech Stack

`pandas` · `numpy` · `scikit-learn` · `xgboost` · `optuna` · `shap` · `pandas-ta` · `plotly` · `yfinance` · `scipy` · `beautifulsoup4`

---

*Author: Theodoros Rigogiannis.*
