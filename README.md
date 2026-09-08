# Dynamic Risk Exposure Engine

> A machine learning and quantitative finance project for dynamic equity exposure management under realistic trading constraints.

**📊 [View the live interactive report](https://rigojohn.github.io/Dynamic-Risk-Exposure-Engine/)** — full Plotly dashboard with Abstract, Architecture, Features, SHAP interpretability, candlestick chart, walk-forward validation and metrics. *(Link goes live once GitHub Pages is enabled — see "Live Interactive Report" section below.)*

## Overview

This project develops a risk-aware trading research framework that uses machine learning probabilities to dynamically adjust equity market exposure.

Instead of forecasting exact stock prices or producing simple buy/sell signals, the system estimates the probability of favorable future market conditions and translates this signal into position-sizing decisions.

The main objective is to improve the overall risk-return profile by reducing maximum drawdown, maintaining competitive returns, and evaluating performance through metrics such as Sharpe Ratio, Calmar Ratio, total return, and drawdown.

## Key Contributions

- Built a time-series-aware machine learning framework for equity exposure management, converting XGBoost probability estimates into dynamic position-sizing decisions.

- Engineered technical, cross-market, and sentiment-based features under strict chronological train-validation-test separation to reduce lookahead bias.

- Implemented a risk-controlled allocation engine targeting lower drawdowns, improved Sharpe and Calmar ratios, and competitive net returns after transaction costs and cash allocation assumptions.

- Validated strategy robustness through walk-forward model selection and a final out-of-sample holdout backtest with turnover-aware execution and exposure constraints.

## Methodology

The workflow follows a financial time-series structure:

1. Historical market data collection
2. Technical indicator and cross-market feature construction
3. News and sentiment feature integration
4. Future-return target construction
5. Chronological train-validation-test split
6. XGBoost model training and probability estimation
7. Dynamic exposure and risk-control mechanism
8. Walk-forward validation
9. Final out-of-sample holdout backtest

## Risk-Aware Exposure Logic

The model output is not treated as a direct trading signal.

Predicted risk-on probabilities are converted into dynamic exposure levels, allowing the strategy to adapt market participation according to estimated market conditions.

The exposure engine incorporates:

- Risk-on / risk-off conditions
- Volatility and drawdown controls
- Transaction costs
- Cash allocation assumptions
- Turnover-aware execution
- Exposure constraints

## Evaluation Focus

Performance is evaluated not only by return, but by the quality of the risk-return trade-off.

Main evaluation metrics include:

- Total Return
- Annualized Return
- Sharpe Ratio
- Calmar Ratio
- Maximum Drawdown
- Turnover
- Win Rate

## Live Interactive Report

Running the notebook (`Run All`) regenerates `presentation_outputs/ml_model_presentation_latest.html` — a self-contained, interactive Plotly report (SHAP charts, candlestick chart, walk-forward metrics, etc.).

GitHub does **not** execute JavaScript when you open an `.html` file inside the repo file browser — it only shows the raw source. To view the report as a real, interactive page, publish it with **GitHub Pages** (free, static hosting, one-time setup):

1. Push/upload this repo to GitHub (including `index.html` at the repo root and the `presentation_outputs/` folder).
2. On GitHub, go to **Settings → Pages**.
3. Under **Build and deployment → Source**, choose **Deploy from a branch**.
4. Branch: `main`, folder: `/ (root)` → **Save**.
5. After a minute, GitHub shows the live URL:
   `https://rigojohn.github.io/Dynamic-Risk-Exposure-Engine/`
   The root `index.html` automatically redirects to the latest report.

Whenever you regenerate the report (new ticker / re-run), just push the updated `presentation_outputs/ml_model_presentation_latest.html` — the same live URL will always show the latest version.

## Disclaimer

This project is for academic and research purposes only.

It does not constitute financial advice and should not be used as a live trading system without further validation, risk assessment, and market testing.
