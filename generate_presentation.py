import json
import os
from datetime import datetime
from html import escape as html_escape
from pathlib import Path

OUTPUT_DIR = Path(__file__).resolve().parent / "presentation_outputs"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
LEGACY_OUTPUT_DIR = Path(r"C:\Users\teorg\Documents\Codex\2026-06-09\files-mentioned-by-the-user-ml\outputs")
HISTORY_FILE = OUTPUT_DIR / "stock_metrics_history.json"
LEGACY_HISTORY_FILE = LEGACY_OUTPUT_DIR / "stock_metrics_history.json"
HTML_FILE = OUTPUT_DIR / "ml_model_presentation_latest.html"


def load_history():
    source = HISTORY_FILE if HISTORY_FILE.exists() else LEGACY_HISTORY_FILE
    if source.exists():
        with open(source, "r", encoding="utf-8") as f:
            history = json.load(f)
        if "runs" not in history:
            history = {"runs": []}
        return history
    return {"runs": []}


def save_history(history):
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(history, f, indent=2, ensure_ascii=False)


def normalize_strategy_metrics(metrics):
    metrics = dict(metrics or {})
    if "Total Return" not in metrics and "Strategy Total Return" in metrics:
        metrics["Total Return"] = metrics["Strategy Total Return"]
    return metrics


def normalize_buy_hold_metrics(metrics):
    metrics = dict(metrics or {})
    if "Total Return" not in metrics and "Buy & Hold Total Return" in metrics:
        metrics["Total Return"] = metrics["Buy & Hold Total Return"]
    return metrics


def metric_value(metrics, key, aliases=()):
    for candidate in (key, *aliases):
        if candidate not in metrics:
            continue
        value = metrics.get(candidate)
        if value is None:
            continue
        try:
            if value != value:
                continue
        except TypeError:
            pass
        return value
    return None


def add_current_run(symbol, model_name, strategy_metrics, buy_hold_metrics):
    strategy_metrics = normalize_strategy_metrics(strategy_metrics)
    buy_hold_metrics = normalize_buy_hold_metrics(buy_hold_metrics)
    history = load_history()
    run_timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Normalize symbol for stable overwrite behavior.
    # AAPL, aapl and " AAPL " are the same stock in Previous Stocks.
    canonical_symbol = str(symbol).strip().upper()
    if not canonical_symbol:
        raise ValueError("symbol is empty; cannot save presentation history")

    new_run = {
        "symbol": canonical_symbol,
        "date": run_timestamp,
        "model_name": model_name,
        "strategy_metrics": strategy_metrics,
        "buy_hold_metrics": buy_hold_metrics,
    }

    # Remove ALL previous entries for the same symbol (case-insensitive), then append latest.
    # This guarantees one row per stock in the HTML Previous Stocks table.
    history["runs"] = [
        run for run in history.get("runs", [])
        if str(run.get("symbol", "")).strip().upper() != canonical_symbol
    ]
    history["runs"].append(new_run)

    save_history(history)
    return history


def fmt_pct(v):
    if v is None:
        return ""
    return f"{float(v) * 100:.2f}%"


def fmt_ratio(v):
    if v is None:
        return ""
    return f"{float(v):.2f}"


def fmt_num(v):
    if v is None:
        return ""
    return f"{float(v):.2f}"


def html_text(value: object) -> str:
    return html_escape(str(value), quote=True)


def script_json_payload(value: object) -> str:
    return str(value or "").replace("</", "<\\/")


def calc_edge(strategy_value, benchmark_value):
    if strategy_value is None or benchmark_value is None:
        return None
    return float(strategy_value) - float(benchmark_value)


def edge_css(value):
    if value is None:
        return ""
    return "positive" if value > 0 else "negative" if value < 0 else ""


def generate_previous_stocks_section(history):
    runs = history["runs"]
    if not runs:
        return ""

    rows_html = ""
    for run in runs:
        run_symbol = html_text(run.get("symbol", ""))
        run_date = html_text(run.get("date", ""))
        run_model_name = html_text(run.get("model_name", ""))
        sm = normalize_strategy_metrics(run.get("strategy_metrics", {}))
        bm = normalize_buy_hold_metrics(run.get("buy_hold_metrics", {}))
        strat_total_return = metric_value(sm, "Total Return", ("Strategy Total Return",))
        buy_hold_total_return = metric_value(bm, "Total Return", ("Buy & Hold Total Return",))
        strategy_sharpe = metric_value(sm, "Sharpe Ratio")
        buy_hold_sharpe = metric_value(bm, "Sharpe Ratio")
        strategy_ann_return = metric_value(sm, "Annualized Return")
        buy_hold_ann_return = metric_value(bm, "Annualized Return")
        strategy_ann_vol = metric_value(sm, "Annualized Volatility")
        buy_hold_ann_vol = metric_value(bm, "Annualized Volatility")
        strategy_sortino = metric_value(sm, "Sortino Ratio")
        buy_hold_sortino = metric_value(bm, "Sortino Ratio")
        strategy_drawdown = metric_value(sm, "Max Drawdown")
        buy_hold_drawdown = metric_value(bm, "Max Drawdown")
        strategy_profit_factor = metric_value(sm, "Profit Factor")
        buy_hold_profit_factor = metric_value(bm, "Profit Factor")

        ret_edge = calc_edge(strat_total_return, buy_hold_total_return)
        ann_return_edge = calc_edge(strategy_ann_return, buy_hold_ann_return)
        vol_reduction_edge = calc_edge(buy_hold_ann_vol, strategy_ann_vol)
        sharpe_edge = calc_edge(strategy_sharpe, buy_hold_sharpe)
        sortino_edge = calc_edge(strategy_sortino, buy_hold_sortino)
        dd_edge = calc_edge(strategy_drawdown, buy_hold_drawdown)
        profit_factor_edge = calc_edge(strategy_profit_factor, buy_hold_profit_factor)

        return_class = edge_css(ret_edge)
        ann_return_class = edge_css(ann_return_edge)
        vol_reduction_class = edge_css(vol_reduction_edge)
        sharpe_class = edge_css(sharpe_edge)
        sortino_class = edge_css(sortino_edge)
        dd_class = edge_css(dd_edge)
        profit_factor_class = edge_css(profit_factor_edge)
        rows_html += f"""
        <tr>
          <td><strong>{run_symbol}</strong></td>
          <td>{run_date}</td>
          <td>{run_model_name}</td>
          <td>{fmt_pct(strat_total_return)}</td>
          <td>{fmt_pct(buy_hold_total_return)}</td>
          <td class="{return_class}">{fmt_pct(ret_edge)}</td>
          <td>{fmt_pct(strategy_ann_return)}</td>
          <td>{fmt_pct(buy_hold_ann_return)}</td>
          <td class="{ann_return_class}">{fmt_pct(ann_return_edge)}</td>
          <td>{fmt_pct(strategy_ann_vol)}</td>
          <td>{fmt_pct(buy_hold_ann_vol)}</td>
          <td class="{vol_reduction_class}">{fmt_pct(vol_reduction_edge)}</td>
          <td>{fmt_ratio(strategy_sharpe)}</td>
          <td>{fmt_ratio(buy_hold_sharpe)}</td>
          <td class="{sharpe_class}">{fmt_ratio(sharpe_edge)}</td>
          <td>{fmt_ratio(strategy_sortino)}</td>
          <td>{fmt_ratio(buy_hold_sortino)}</td>
          <td class="{sortino_class}">{fmt_ratio(sortino_edge)}</td>
          <td>{fmt_pct(strategy_drawdown)}</td>
          <td>{fmt_pct(buy_hold_drawdown)}</td>
          <td class="{dd_class}">{fmt_pct(dd_edge)}</td>
          <td>{fmt_ratio(sm.get('Calmar Ratio'))}</td>
          <td>{fmt_ratio(strategy_profit_factor)}</td>
          <td>{fmt_ratio(buy_hold_profit_factor)}</td>
          <td class="{profit_factor_class}">{fmt_ratio(profit_factor_edge)}</td>
          <td>{fmt_pct(sm.get('Win Rate'))}</td>
          <td>{fmt_pct(sm.get('Average Exposure'))}</td>
          <td>{fmt_num(sm.get('Total Turnover'))}</td>
        </tr>"""

    return f"""
    <section id="history"><div class="section-inner">
      <h2 class="section-title">13. Previous Stocks Database</h2>
      <p class="lead">Accumulated out-of-sample results from all previously analyzed stocks. Each row represents one complete walk-forward evaluation on the untouched test window.</p>
      <p>This database tracks the strategy's performance across multiple stocks over time. Each time the notebook is run, its final out-of-sample metrics are appended to this table, previous runs are preserved, including repeated symbols. The "Edge" columns show the difference between strategy and buy-and-hold metrics: positive values (green) indicate the strategy outperformed, negative values (red) indicate underperformance. This allows cross-stock comparison and helps identify which asset types benefit most from the Machine Learning-based exposure timing.</p>
      <div class="artifact-card table-wrap" style="overflow-x:auto;">
        <h3>All Runs Comparison</h3>
        <table class="dataframe" style="font-size:12px; min-width:1900px;">
          <thead>
            <tr>
              <th>Symbol</th>
              <th>Date</th>
              <th>Model</th>
              <th>Strat Return</th>
              <th>B&H Return</th>
              <th>Return Edge</th>
              <th>Strat Ann Return</th>
              <th>B&H Ann Return</th>
              <th>Ann Return Edge</th>
              <th>Strat Ann Vol</th>
              <th>B&H Ann Vol</th>
              <th>Vol Reduction Edge</th>
              <th>Strat Sharpe</th>
              <th>B&H Sharpe</th>
              <th>Sharpe Edge</th>
              <th>Strat Sortino</th>
              <th>B&H Sortino</th>
              <th>Sortino Edge</th>
              <th>Strat DD</th>
              <th>B&H DD</th>
              <th>DD Edge</th>
              <th>Calmar</th>
              <th>Strat Profit F.</th>
              <th>B&H Profit F.</th>
              <th>Profit F. Edge</th>
              <th>Win Rate</th>
              <th>Avg Exp.</th>
              <th>Turnover</th>
            </tr>
          </thead>
          <tbody>{rows_html}
          </tbody>
        </table>
      </div>
      <style>
        td.positive {{ color: #16a34a; font-weight: 700; }}
        td.negative {{ color: #dc2626; font-weight: 700; }}
      </style>
    </div></section>"""


def generate_html(symbol, model_name, strategy_metrics, buy_hold_metrics,
                  equity_json="", drawdown_json="",
                  shap_bar_json="", shap_summary_json="", shap_binary_json="",
                  candlestick_json="", metrics_html=""):
    strategy_metrics = normalize_strategy_metrics(strategy_metrics)
    buy_hold_metrics = normalize_buy_hold_metrics(buy_hold_metrics)
    history = add_current_run(symbol, model_name, strategy_metrics, buy_hold_metrics)
    prev_section = generate_previous_stocks_section(history)

    sm = strategy_metrics
    bm = buy_hold_metrics
    display_symbol = html_text(symbol)
    display_model_name = html_text(model_name)
    equity_json_payload = script_json_payload(equity_json)
    drawdown_json_payload = script_json_payload(drawdown_json)
    shap_bar_json_payload = script_json_payload(shap_bar_json)
    shap_summary_json_payload = script_json_payload(shap_summary_json)
    shap_binary_json_payload = script_json_payload(shap_binary_json)
    candlestick_json_payload = script_json_payload(candlestick_json)

    metrics_table_rows = ""
    metric_keys = [
        ("Total Return", "pct"), ("Annualized Return", "pct"),
        ("Annualized Volatility", "pct"), ("Sharpe Ratio", "ratio"),
        ("Sortino Ratio", "ratio"), ("Calmar Ratio", "ratio"),
        ("Profit Factor", "ratio"), ("Max Drawdown", "pct"),
        ("Win Rate", "pct"), ("Average Exposure", "pct"),
        ("Total Turnover", "num"),
    ]
    for key, fmt in metric_keys:
        if key == "Total Return":
            sv = metric_value(sm, key, ("Strategy Total Return",))
            bv = metric_value(bm, key, ("Buy & Hold Total Return",))
        else:
            sv = sm.get(key)
            bv = bm.get(key)
        if fmt == "pct":
            s_str = fmt_pct(sv)
            b_str = fmt_pct(bv)
        elif fmt == "ratio":
            s_str = fmt_ratio(sv)
            b_str = fmt_ratio(bv)
        else:
            s_str = fmt_num(sv)
            b_str = fmt_num(bv)
        metrics_table_rows += f"""    <tr>
      <th>{html_text(key)}</th>
      <td>{html_text(s_str)}</td>
      <td>{html_text(b_str)}</td>
    </tr>
"""

    equity_chart = ""
    if equity_json:
        equity_chart = f"""      <div class="artifact-card">
    <h3>Equity Curve</h3>
    <div id="equity-chart"></div>
    <p class="caption">Final out-of-sample equity curve for {display_symbol}.</p>
  </div>"""

    drawdown_chart = ""
    if drawdown_json:
        drawdown_chart = f"""      <div class="artifact-card">
    <h3>Max Drawdown</h3>
    <div id="drawdown-chart"></div>
    <p class="caption">Final out-of-sample drawdown for {display_symbol}.</p>
  </div>"""

    def shap_artifact(title, payload, div_id, caption):
        if not payload:
            return ""
        safe_title = html_text(title)
        safe_caption = html_text(caption)
        if isinstance(payload, str) and payload.startswith("data:image/"):
            safe_payload = html_text(payload)
            return f"""        <div class="artifact-card figure-card shap-card">
    <h3>{safe_title}</h3>
    <img class="shap-plot zoomable" src="{safe_payload}" alt="{safe_title}" data-title="{safe_title}" />
    <p class="caption">{safe_caption}</p>
  </div>"""
        return f"""        <div class="artifact-card shap-card">
    <h3>{safe_title}</h3>
    <div id="{html_text(div_id)}" class="shap-plot"></div>
    <p class="caption">{safe_caption}</p>
  </div>"""

    shap_bar_chart = shap_artifact(
        "SHAP bar summary",
        shap_bar_json,
        "shap-bar-chart",
        f"Mean contribution ranking for {symbol}."
    )

    shap_summary_chart = shap_artifact(
        "SHAP summary plot",
        shap_summary_json,
        "shap-summary-chart",
        f"Distribution of SHAP values for {symbol}."
    )

    shap_binary_chart = shap_artifact(
        "Binary SHAP feature importance",
        shap_binary_json,
        "shap-binary-chart",
        f"Risk-off vs risk-on SHAP split for {symbol}."
    )

    candlestick_script = ""
    candlestick_div = ""
    if candlestick_json:
        candlestick_div = f"""      <div class="artifact-card"><h3>Candlestick Chart - Full Out-of-Sample Test Window - {display_symbol}</h3><div id="candlestick-chart"></div><p class="caption">Interactive Plotly output for the full out-of-sample test window for {display_symbol}.</p></div>"""

    walk_forward_section = """    <section id="selection"><div class="section-inner">
      <h2 class="section-title">8. Walk-Forward Model Selection and Validation-Safe Tuning</h2>
      <p>The current notebook compares a weighted XGBoost baseline with an optional Optuna-tuned XGBoost candidate over the chronological train + validation region. Each fold trains only on past observations, predicts the next unseen block, computes probability thresholds from fold-training probabilities, and evaluates fixed preliminary/default exposure rules on the evaluation block. Risk/exposure settings, fast-risk-off controls, early-risk-on behavior and sentiment settings are chosen later with a train-only validation model before final testing, the final test is not used for tuning.</p>

      <h3>What Is Walk-Forward Validation?</h3>
      <p>Walk-forward validation simulates a deployment-like research setting: train on past data, predict the next unseen period, then roll forward and repeat. This is fundamentally different from a single train/test split because it tests the model across multiple regime changes (bull markets, bear markets, consolidation periods). If a strategy performs well across all walk-forward folds but poorly on the final test, it may indicate overfitting to the validation period - a red flag that a single split would miss.</p>
      <p>The notebook uses an <strong>expanding window</strong> approach: each fold trains on all available past data (the training set grows over time). Expanding windows are chosen here for regime detection because more training data may help the model learn recurring patterns, sliding windows are a valid alternative when older regimes should be down-weighted. The tradeoff is higher computational cost as the dataset grows.</p>

      <div class="teacher"><span class="label">Current notebook discipline</span>The notebook separates model selection, validation-safe risk/exposure tuning, early-risk-on tuning, sentiment tuning and final testing. Risk/exposure templates are selected first, early-risk-on templates are validation-selected second and merged into <code>selected_risk_settings</code>, then sentiment templates are selected. Early-risk-on remains gated by <code>fast_risk_off == 0</code>, and the fast-risk-off defensive cap can override it. A train-only <code>validation_model</code> is used for validation tuning, while the <code>final_model</code> is trained on train + validation only after all selected settings are locked.</div>

      <div class="artifact-card table-wrap"><h3>Current Walk-Forward Variables</h3><table class="dataframe"><thead><tr><th>Variable</th><th>Role in the protocol</th></tr></thead><tbody>
        <tr><td><code>WF_FOLD_TEST_DAYS</code></td><td>Evaluation fold length, currently 63 trading days (~1 quarter).</td></tr>
        <tr><td><code>WF_FOLD_STEP_DAYS</code></td><td>Step size between folds, currently 63 trading days (non-overlapping evaluations).</td></tr>
        <tr><td><code>selection_raw</code></td><td>Chronological train + validation history used for walk-forward model comparison.</td></tr>
        <tr><td><code>train_raw_fold</code></td><td>Expanding past-only fold training window.</td></tr>
        <tr><td><code>eval_raw_fold</code></td><td>Next unseen chronological fold.</td></tr>
        <tr><td><code>validation_model</code></td><td>Model trained on train only and used for honest validation risk/exposure tuning, including fast-risk-off and any early-risk-on overlay.</td></tr>
        <tr><td><code>final_model</code></td><td>Model trained on train + validation after settings are locked, used for final test probabilities plus post-lock diagnostics/SHAP, not validation tuning.</td></tr>
        <tr><td><code>selected_risk_settings</code></td><td>Frozen risk/exposure and sentiment configuration selected on validation, including fast-risk-off controls and any gated early-risk-on overlay.</td></tr>
      </tbody></table></div>

      <h3>Fold Logic</h3>
      <pre class="code">for each walk-forward fold:
    train_raw_fold = all rows before fold
    eval_raw_fold = next unseen block
    fit candidate model on train_raw_fold
    predict risk_on_proba on eval_raw_fold
    compute lower/upper thresholds from train probabilities only
    run dynamic exposure backtest with warm-up context
    store fold Sharpe, return, drawdown</pre>
      <p>Fold imputation values, target thresholds, probability thresholds and model fits are derived from training rows only. Evaluation rows never set their own thresholds. The 63-day fold length (~1 quarter of trading) aligns with quarterly re-evaluation cycles common in systematic trading. Folds are non-overlapping in evaluation, so there is no leakage between adjacent folds (no purging or embargo needed).</p>

      <h3>Threshold Computation: A Critical Leakage Prevention</h3>
      <p>A subtle but critical detail: <code>lower_threshold</code> and <code>upper_threshold</code> are computed <strong>from fold-training probabilities only</strong>. The evaluation fold never influences its own thresholds. If thresholds were computed on the full dataset (train + eval), the evaluation period would indirectly set the bar for its own risk-on/risk-off classification - a form of lookahead bias that inflates performance. The notebook prevents this by isolating training and evaluation data at every step of the pipeline.</p>

      <h3>Model Selection Logic</h3>
      <p>The walk-forward protocol always runs for the Weighted XGBoost baseline. It also runs for the Optuna-tuned candidate only when <code>best_params</code> / an Optuna candidate exists. Each available candidate produces a vector of fold-level Sharpe ratios. The model family with the higher mean Sharpe across folds is selected. If the baseline outperforms Optuna, or if no Optuna candidate exists, the simpler model wins. The selected model family then determines which <code>final_model</code> is trained on train+validation after settings are locked for the final test.</p>

      <h3>Validation-Safe Risk and Sentiment Tuning</h3>
      <p>After the model family is selected, the notebook trains a <code>validation_model</code> on the train split only. That model produces validation probabilities for separate validation-safe template passes: risk/exposure first, early-risk-on second, sentiment third. The selected early-risk-on parameters are merged into <code>selected_risk_settings</code> and evaluated with the selected risk/exposure controls, the overlay remains gated by <code>fast_risk_off == 0</code>, and an active fast-risk-off defensive cap overrides it. The winning <code>selected_risk_settings</code> are locked before the <code>final_model</code> is fit on train + validation. The final test is not used during this tuning step.</p>
      <pre class="code">score = (
    Sharpe Ratio
    + 0.25 * Sortino Ratio
    + 0.50 * Annualized Return
    - 0.75 * abs(Max Drawdown)
    - 0.010 * Total_Turnover
)</pre>
      <p>This objective rewards risk-adjusted return, adds a smaller reward for downside-adjusted return and annualized return, and penalizes absolute drawdown plus turnover. It avoids selecting a high-return configuration that trades too often or creates excessive drawdown.</p>

      <div class="artifact-card table-wrap"><h3>Validation-Safe Tuning Sequence</h3><table class="dataframe"><thead><tr><th>Step</th><th>Data used</th><th>Purpose</th></tr></thead><tbody>
        <tr><td>Model family selection</td><td>Train + validation walk-forward folds</td><td>Choose Weighted XGBoost or Optuna XGBoost when the Optuna candidate exists.</td></tr>
        <tr><td><code>validation_model</code></td><td>Train only</td><td>Generate validation probabilities without fitting on validation labels.</td></tr>
        <tr><td>Template tuning</td><td>Validation only</td><td>Select compact templates in sequence: risk/exposure controls first, validation-selected early-risk-on parameters second, sentiment settings third. Early-risk-on is evaluated with the selected risk/exposure controls, gated by <code>fast_risk_off == 0</code>, and overridden by fast-risk-off defensive caps.</td></tr>
        <tr><td><code>selected_risk_settings</code></td><td>Locked after validation</td><td>Freeze exposure-engine settings before final training.</td></tr>
        <tr><td><code>final_model</code></td><td>Train + validation</td><td>Fit after settings lock for final test plus post-lock diagnostics/SHAP, not validation tuning.</td></tr>
      </tbody></table></div>

      <h3>Final Test Discipline</h3>
      <p>After validation tuning, settings are locked and final metrics are computed on the untouched test window. The test set is not used to choose model parameters, risk/exposure templates, fast-risk-off controls, early-risk-on overlay settings, sentiment settings, probability/exposure thresholds, or turnover controls.</p>

      <h3>Why an Untouched Test Set Matters</h3>
      <p>Final-test settings are locked before the final test window is evaluated. The test set is never used for model selection, hyperparameter tuning, risk template tuning, early-risk-on parameter tuning, sentiment parameter tuning, or threshold computation. If you compare configurations using the test set, you are implicitly optimizing on it - even if you do not formally adjust parameters. The test set loses its value as an unbiased performance estimate once it influences research choices.</p>
      <p>The pipeline enforces this discipline through two separate models: a <code>validation_model</code> trained on train only for separate validation passes over risk/exposure templates, early-risk-on templates and sentiment templates, and a separate <code>final_model</code> trained on train + validation only after those settings are locked. Final-test early-risk-on behavior uses the locked parameters inside the selected risk/exposure controls, remains gated by <code>fast_risk_off == 0</code>, and remains subject to fast-risk-off defensive override. The <code>final_model</code> supports final test measurement plus post-lock diagnostics/SHAP, not validation tuning. The test set never sees the validation model predictions, and the validation tuner never sees test set outcomes. This separation between validation-safe tuning and final evaluation is what distinguishes a research backtest from a validation-disciplined research workflow.</p>

      <div class="why"><span class="label">Why this matters</span>The presentation reports a validation-disciplined research workflow: validation selects settings, final test measures them. Validation reuses a compact template set, so validation overfitting is still possible, there is no test leakage, and the final test remains the unbiased holdout.</div>
    </div></section>"""

    dynamic_exposure_section = """
    <section id="engine"><div class="section-inner">
      <h2 class="section-title">7. Dynamic Exposure Engine</h2>
      <p class="lead">The Weighted XGBoost baseline gives one probability path, <code>p_t^W</code>. The Optuna-tuned candidate gives another probability path, <code>p_t^O</code>. Each value says how likely the model thinks day <code>t</code> belongs to a favorable future-return regime. Both paths then go through the exact same exposure and backtest rules, so the comparison is fair: only the probability path changes, not the trading engine.</p>
      <div class="formula">p_t^W -&gt; engine -&gt; metrics_W&nbsp;&nbsp;&nbsp;&nbsp; p_t^O -&gt; engine -&gt; metrics_O</div>
      <p>The engine is not another Machine Learning model. It is a fixed set of portfolio rules. It takes the candidate probability <code>p_t</code>, the market information available at that time <code>Z_t</code>, and the locked settings <code>&theta;</code>. It outputs the desired exposure <code>target_position</code>, the actually held <code>position</code>, net returns, equity curves, drawdowns and final metrics.</p>

      <h3>Variable Glossary: Plain Meaning, Source And Use</h3>
      <div class="artifact-card table-wrap"><h3>1) Model / Probability</h3><table class="dataframe"><thead><tr><th>Variable</th><th>Role and origin</th></tr></thead><tbody>
        <tr><td><code>risk_on_proba</code> / <code>p_t</code></td><td>The model probability for day <code>t</code>, created by <code>predict_proba(X_t)[:, 1]</code>. In simple terms, it is the model's estimate of <code>P(y_t=1 | X_t)</code>: how likely the future-return label is favorable.</td></tr>
        <tr><td><code>lower_threshold</code></td><td>The low probability reference point. It helps turn the raw probability into a usable exposure signal. If not supplied, the engine uses the 0.30 quantile of the probability path given to it.</td></tr>
        <tr><td><code>upper_threshold</code></td><td>The high probability reference point. If not supplied, the engine uses the 0.70 quantile of the probability path given to it.</td></tr>
        <tr><td><code>X_train_validation</code></td><td>The training-split feature matrix used by the train-only <code>validation_model</code> for validation-safe threshold tuning.</td></tr>
        <tr><td><code>train_validation_proba_series</code></td><td><code>validation_model.predict_proba(X_train_validation)[:, 1]</code> (same idea as train-only <code>X_train</code> probabilities). Candidate numeric thresholds come from this series using <code>(0.30,0.70)</code>, <code>(0.35,0.70)</code> and <code>(0.30,0.65)</code>, are judged on validation, and are frozen before test.</td></tr>
        <tr><td><code>proba_range</code></td><td><code>max(upper_threshold - lower_threshold, 1e-9)</code>. This is the usable distance between the two thresholds. The tiny <code>1e-9</code> floor avoids division by zero.</td></tr>
        <tr><td><code>probability_tilt</code></td><td>The model's exposure push, centered between <code>[-model_tilt, +model_tilt]</code>. A low <code>p_t</code> reduces exposure, a high <code>p_t</code> increases exposure.</td></tr>
        <tr><td><code>model_tilt</code></td><td>The maximum positive or negative exposure change that the model probability is allowed to make.</td></tr>
      </tbody></table></div>

      <div class="artifact-card table-wrap"><h3>2) Base Exposure / Trend</h3><table class="dataframe"><thead><tr><th>Variable</th><th>Role and origin</th></tr></thead><tbody>
        <tr><td><code>base_exposure</code></td><td>The starting risky-asset allocation before the model probability, trend filter and risk controls change it.</td></tr>
        <tr><td><code>trend_on</code></td><td>The long-term trend flag. It first checks <code>close_to_ema_200 &gt; 0</code>, if missing, it checks <code>price &gt; ema_200</code>, if both are missing, it stays neutral/on as <code>True</code>.</td></tr>
        <tr><td><code>trend_bonus</code></td><td>The exposure add-on when <code>trend_on=1</code>.</td></tr>
        <tr><td><code>trend_penalty</code></td><td>The exposure reduction when <code>trend_on=0</code>.</td></tr>
        <tr><td><code>trend_adjustment</code></td><td>The trend contribution used inside <code>raw_exposure</code>: <code>+trend_bonus</code> when <code>trend_on=1</code>, and <code>-trend_penalty</code> when <code>trend_on=0</code>.</td></tr>
        <tr><td><code>raw_exposure</code></td><td>The first exposure estimate before risk controls: <code>base_exposure + probability_tilt + trend_adjustment</code>.</td></tr>
      </tbody></table></div>

      <div class="artifact-card table-wrap"><h3>3) Volatility / Risk Multipliers</h3><table class="dataframe"><thead><tr><th>Variable</th><th>Role and origin</th></tr></thead><tbody>
        <tr><td><code>market_return</code></td><td>The return that the held position earns from one open to the next open: <code>Open.shift(-1) / Open - 1</code>. The last unavailable value is filled with <code>0</code>.</td></tr>
        <tr><td><code>past_open_return</code></td><td>Past open-to-open returns from <code>Open.pct_change(fill_method=None)</code>. These are used only to estimate recent volatility.</td></tr>
        <tr><td><code>realized_vol_20d</code></td><td><code>past_open_return.rolling(20).std().shift(1) * sqrt(252)</code>. This is yesterday-known 20-day annualized volatility, <code>shift(1)</code> prevents using the return being measured today.</td></tr>
        <tr><td><code>target_vol</code></td><td>The desired volatility level used in <code>target_vol / realized_vol_20d</code>.</td></tr>
        <tr><td><code>vol_floor</code></td><td>The lower limit for the volatility multiplier, so volatility control does not cut exposure too far only because volatility changed.</td></tr>
        <tr><td><code>vol_ceiling</code></td><td>The upper limit for the volatility multiplier, so volatility control does not raise exposure too far only because volatility changed.</td></tr>
        <tr><td><code>vol_multiplier</code></td><td><code>clip(target_vol / realized_vol_20d, vol_floor, vol_ceiling)</code>, filled with <code>1.0</code> when missing. It cuts exposure in high volatility and can raise it in low volatility.</td></tr>
        <tr><td><code>vix_level</code></td><td>The VIX market-stress level available in the feature set.</td></tr>
        <tr><td><code>vix_ma_20</code></td><td>The 20-day VIX average when <code>vix_level</code> exists.</td></tr>
        <tr><td><code>vix_risk_multiplier</code></td><td>The defensive multiplier used when prior <code>vix_level</code> is above prior <code>vix_ma_20</code>.</td></tr>
        <tr><td><code>vix_multiplier</code></td><td>Exact rule: <code>vix_multiplier = vix_risk_multiplier</code> when <code>vix_level.shift(1) &gt; vix_ma_20.shift(1)</code>, otherwise it is <code>1.0</code>.</td></tr>
        <tr><td><code>rolling_high_60d</code></td><td>The recent 60-day high used to measure drawdown.</td></tr>
        <tr><td><code>drawdown_60d</code></td><td>The current loss from the recent high. The equation is <code>drawdown_60d = Close.shift(1) / rolling_high_60d.shift(1) - 1</code>, so it uses only prior close information.</td></tr>
        <tr><td><code>drawdown_cutoff</code></td><td>The drawdown level that marks a defensive state.</td></tr>
        <tr><td><code>drawdown_risk_multiplier</code></td><td>The defensive multiplier used when shifted 60-day drawdown is worse than the cutoff.</td></tr>
        <tr><td><code>drawdown_multiplier</code></td><td>Exact rule: <code>drawdown_multiplier = drawdown_risk_multiplier</code> when <code>drawdown_60d &lt; drawdown_cutoff</code>, otherwise it is <code>1.0</code>.</td></tr>
      </tbody></table></div>

      <div class="artifact-card table-wrap"><h3>4) Defensive / Offensive Overlays</h3><table class="dataframe"><thead><tr><th>Variable</th><th>Role and origin</th></tr></thead><tbody>
        <tr><td><code>risk_off_exposure</code></td><td>The maximum exposure allowed when <code>trend_on == 0 and p_t &lt; lower_threshold</code>, and again when <code>fast_risk_off == 1</code>.</td></tr>
        <tr><td><code>fast_vol_threshold</code></td><td>The volatility-ratio cutoff used by the quick danger check.</td></tr>
        <tr><td><code>fast_conditions</code></td><td>The available quick danger inputs: <code>close_to_ema_20 &lt; 0</code>, <code>return_5d &lt; 0</code>, and <code>volatility_ratio_5_20 &gt; fast_vol_threshold</code>.</td></tr>
        <tr><td><code>fast_risk_score</code></td><td>The number of active quick danger inputs. Exact rule: <code>fast_risk_score = sum(condition.astype(int) for condition in fast_conditions)</code>. If no conditions exist, score is <code>0</code>.</td></tr>
        <tr><td><code>fast_risk_off</code></td><td>The defensive flag from the quick danger score. Exact rule: <code>fast_risk_off = fast_risk_score &gt;= min(2, len(fast_conditions))</code>. If no conditions exist, it is <code>False</code>.</td></tr>
        <tr><td><code>risk_on_boost</code></td><td>An extra exposure add-on when <code>p_t &gt;= upper_threshold</code>, <code>trend_on == 1</code>, <code>close_to_ema_20 &gt; 0</code>, and <code>fast_risk_off == 0</code>.</td></tr>
        <tr><td><code>recovery_risk_on</code></td><td>A recovery flag. Exact conditions: <code>strong_risk_on == True</code>, <code>return_20d &gt; 0</code>, and <code>return_5d &gt; 0</code>.</td></tr>
        <tr><td><code>recovery_min_exposure</code></td><td>The exposure floor used when <code>recovery_risk_on</code> is active.</td></tr>
        <tr><td><code>strong_bull_regime</code></td><td>A stronger bullish state. Exact conditions: <code>recovery_risk_on == True</code>, <code>return_60d &gt; 0</code>, <code>drawdown_20d &gt; -0.08</code>, and <code>volatility_ratio_5_20 &lt; fast_vol_threshold</code>.</td></tr>
        <tr><td><code>bull_min_exposure</code></td><td>The exposure floor used when <code>strong_bull_regime</code> is active.</td></tr>
        <tr><td><code>leveraged_bull_regime</code></td><td>The most aggressive bullish state. Exact conditions: <code>strong_bull_regime == True</code>, <code>return_20d &gt; 0.05</code>, and <code>return_60d &gt; 0.08</code>.</td></tr>
        <tr><td><code>bull_leverage_exposure</code></td><td>The exposure floor used when <code>leveraged_bull_regime</code> is active.</td></tr>
        <tr><td><code>early_risk_on_score</code></td><td>The early recovery score: <code>count(True)</code> across <code>close_to_ema_20 &gt; 0</code>, <code>ema_20_slope_3d &gt; 0</code>, <code>return_5d &gt; 0</code>, <code>return_3d_minus_10d &gt; 0</code>, <code>return_5d_minus_20d &gt; 0</code>, <code>volatility_ratio_5_20 &lt; fast_vol_threshold</code>, and optional <code>vix_change_5d &lt; 0</code>.</td></tr>
        <tr><td><code>early_risk_on_score_threshold</code></td><td>The minimum early recovery score needed to activate the flag. Default threshold is <code>4</code>.</td></tr>
        <tr><td><code>early_risk_on</code></td><td>The early recovery flag. Exact rule: <code>early_risk_on = (early_risk_on_score &gt;= early_risk_on_score_threshold) &amp; (df_bt["fast_risk_off"] == 0)</code>.</td></tr>
        <tr><td><code>early_risk_on_boost</code></td><td>The extra exposure added by <code>np.where</code> when <code>early_risk_on</code> is active.</td></tr>
        <tr><td><code>early_recovery_min_exposure</code></td><td>The exposure floor applied by <code>np.where</code> when <code>early_risk_on</code> is active.</td></tr>
      </tbody></table></div>

      <div class="artifact-card table-wrap"><h3>5) Sentiment</h3><table class="dataframe"><thead><tr><th>Variable</th><th>Role and origin</th></tr></thead><tbody>
        <tr><td><code>sentiment_ma_5d</code></td><td>A lagged 5-day real-news sentiment average from the feature pipeline. It is not synthetic. If there is no news, sentiment stays neutral.</td></tr>
        <tr><td><code>sentiment_change_3d</code></td><td>A lagged 3-day real-news sentiment change from the feature pipeline.</td></tr>
        <tr><td><code>sentiment_score_raw</code></td><td>The raw news score: <code>0.70*sentiment_ma_5d + 0.30*sentiment_change_3d</code>. It becomes <code>0.0</code> when no news exists.</td></tr>
        <tr><td><code>sentiment_score_scaled</code></td><td>The bounded news score: <code>tanh(sentiment_score_raw * sentiment_sensitivity)</code>. This keeps extreme sentiment bounded.</td></tr>
        <tr><td><code>news_volume</code></td><td>The number of headlines. It helps decide how much confidence to give the sentiment reading.</td></tr>
        <tr><td><code>news_volume_zscore</code></td><td>A flag-like volume signal showing whether headline volume is unusually high.</td></tr>
        <tr><td><code>sentiment_confidence_headlines</code></td><td>The headline-count scale used when computing sentiment confidence.</td></tr>
        <tr><td><code>sentiment_news_z_threshold</code></td><td>The high-news-volume threshold that can add <code>0.25</code> to confidence.</td></tr>
        <tr><td><code>sentiment_confidence</code></td><td>Exact rule: if <code>has_news</code>, use <code>clip(clip(news_volume / max(sentiment_confidence_headlines, 1e-9), 0, 1) + 0.25*(news_volume_zscore &gt; sentiment_news_z_threshold), 0, 1)</code>, otherwise use <code>0.0</code>.</td></tr>
        <tr><td><code>sentiment_positive_max_adjustment</code></td><td>The maximum positive exposure adjustment from sentiment.</td></tr>
        <tr><td><code>sentiment_negative_max_adjustment</code></td><td>The maximum negative exposure adjustment from sentiment before asymmetry.</td></tr>
        <tr><td><code>sentiment_asymmetric_factor</code></td><td>The factor applied to negative sentiment, so bad news can be treated differently from good news.</td></tr>
        <tr><td><code>sentiment_whipsaw_days</code></td><td>The persistence rule: <code>whipsaw_ok = (sentiment_dir == 0) | (cons_days &gt;= sentiment_whipsaw_days)</code>, where <code>sentiment_dir = sign(sentiment_score_scaled)</code>.</td></tr>
        <tr><td><code>sentiment_regime_gate</code></td><td>When active, composite fear is <code>(vix_multiplier &lt; 1.0) + (volatility_ratio_5_20 &gt; 1.5) + (drawdown_60d &lt; -0.10) &gt;= 2</code>. It sets positive sentiment multipliers above <code>1.0</code> back to <code>1.0</code>, in <code>strong_bull_regime == 1</code>, negative multipliers are floored at <code>0.97</code>.</td></tr>
        <tr><td><code>sentiment_multiplier</code></td><td>The final sentiment exposure multiplier. No-news rows and whipsaw-filtered rows use multiplier <code>1.0</code>.</td></tr>
        <tr><td><code>sentiment_adjustment</code></td><td>The distance of <code>sentiment_multiplier</code> from <code>1.0</code>.</td></tr>
      </tbody></table></div>

      <div class="artifact-card table-wrap"><h3>6) Execution / Costs</h3><table class="dataframe"><thead><tr><th>Variable</th><th>Role and origin</th></tr></thead><tbody>
        <tr><td><code>min_exposure</code></td><td>The lowest exposure allowed after controls and clipping.</td></tr>
        <tr><td><code>max_exposure</code></td><td>The highest exposure allowed after controls and clipping.</td></tr>
        <tr><td><code>target_position</code></td><td>The desired exposure after model probability, trend, risk controls, overlays and sentiment. It is clipped between <code>min_exposure</code> and <code>max_exposure</code>, and the fast-risk-off cap is reapplied after clipping.</td></tr>
        <tr><td><code>executable_target_position</code></td><td><code>target_position.shift(1).fillna(base_exposure)</code>. This is yesterday's target, used as today's tradable target, so there is no same-row trading.</td></tr>
        <tr><td><code>rebalance_threshold</code></td><td>The no-trade band. The engine changes exposure only when <code>abs(target - current_position) &gt;= rebalance_threshold</code>.</td></tr>
        <tr><td><code>recovery_step_up_limit</code></td><td>The maximum size of a below-base upward recovery step. It does not cap bullish/risk-on targets at <code>base_exposure</code>, it only makes movement toward higher targets gradual. Downward defensive moves are not capped.</td></tr>
        <tr><td><code>current_position</code></td><td>The previous exposure used in the rebalance loop.</td></tr>
        <tr><td><code>position</code></td><td>The actually held exposure after execution delay and rebalance threshold.</td></tr>
        <tr><td><code>turnover</code></td><td>The trading amount: <code>turnover = abs(diff(position))</code>.</td></tr>
        <tr><td><code>cost_bps</code></td><td>The cost setting in basis points.</td></tr>
        <tr><td><code>transaction_cost</code></td><td><code>cost_bps / 10000</code>. Cost is charged per unit of turnover.</td></tr>
        <tr><td><code>cash_yield</code></td><td>The annual cash-yield setting for capital not invested in the risky asset.</td></tr>
        <tr><td><code>cash_weight</code></td><td>The cash allocation: <code>cash_weight = clip(1 - position, lower=0)</code>.</td></tr>
        <tr><td><code>leverage_financing_rate</code></td><td>The financing-rate setting used when exposure is above <code>1.0</code>.</td></tr>
        <tr><td><code>leverage_amount</code></td><td>The exposure above <code>1.0</code>: <code>leverage_amount = clip(position - 1, lower=0)</code>.</td></tr>
        <tr><td><code>financing_cost</code></td><td>The daily cost charged for <code>leverage_amount</code>.</td></tr>
        <tr><td><code>strategy_return_gross</code>, <code>strategy_return_net</code></td><td>Gross return adds risky-asset return and cash yield, then subtracts leverage financing. Net return additionally subtracts turnover cost.</td></tr>
      </tbody></table></div>

      <div class="artifact-card table-wrap"><h3>7) Outputs / Metrics</h3><table class="dataframe"><thead><tr><th>Output</th><th>Meaning</th></tr></thead><tbody>
        <tr><td><code>strategy_equity</code>, <code>buy_hold_equity</code></td><td>The compounded value of the strategy and the passive buy-and-hold benchmark.</td></tr>
        <tr><td><code>strategy_drawdown</code>, <code>buy_hold_drawdown</code></td><td>How far each equity curve is below its own previous peak.</td></tr>
        <tr><td>Sharpe, Sortino, Calmar</td><td>Risk-adjusted summaries based on daily net returns, downside daily returns and maximum drawdown.</td></tr>
        <tr><td>Profit Factor, Win Rate</td><td>Profit Factor is gross positive daily net return divided by absolute gross negative daily net return. Win Rate is the share of days with positive net return.</td></tr>
        <tr><td>Max Drawdown, Total Turnover, Average Exposure</td><td>Simple diagnostics: worst peak-to-trough loss, total trading activity, and average risk exposure actually held.</td></tr>
        <tr><td>Rebalance Days, Average Daily Turnover</td><td>Rebalance Days counts days with <code>turnover &gt; 0</code>. Average Daily Turnover is <code>mean(turnover)</code>.</td></tr>
        <tr><td>Fast Risk-Off Days, Early Risk-On Days</td><td>Counts of days when the fast defensive overlay or early recovery overlay is active. The notebook also reports Average Early Risk-On Score.</td></tr>
        <tr><td>Strong Bull Days, Leveraged Days</td><td>Strong Bull Days counts rows where <code>strong_bull_regime</code> is active. Leveraged Days counts rows where the held <code>position</code> is above <code>1.0</code>.</td></tr>
        <tr><td>Average Leverage, Total Financing Cost</td><td>Average Leverage is <code>mean(leverage_amount)</code>, the average exposure above <code>1.0</code>. Total Financing Cost is <code>sum(financing_cost)</code>, the total daily cost charged for that leverage.</td></tr>
        <tr><td>Sentiment diagnostics, if present</td><td>Reported sentiment fields include Sentiment Risk-On Days, Sentiment Risk-Off Days, Average Sentiment Multiplier, Whipsaw Filtered Days and Average Sentiment Adjustment.</td></tr>
      </tbody></table></div>

      <h3>Timing And No-Leakage Discipline</h3>
      <p>The target exposure is computed after the close using only features and probabilities available for that row. The executable target is the prior row's target, <code>target_position.shift(1).fillna(base_exposure)</code>. The measured return is <code>market_return = Open.shift(-1) / Open - 1</code>, with the final unavailable row filled by <code>0</code>. So the engine cannot use the same row's open-to-next-open return to choose the position that earns that return. Volatility uses shifted past open returns, VIX stress uses prior VIX versus prior VIX moving average, and drawdown uses shifted close versus shifted rolling high.</p>

      <h3>Key Equations: Signal, Sentiment, Execution And Costs</h3>
      <p>The equations below show the main flow. Sentiment and execution/cost details stay inside the same code box because they are part of the same target-position and backtest process.</p>
      <pre class="code">1) Signal
p_t = P(y_t=1 | X_t)

probability_tilt_t = (2*clip((p_t-L)/(U-L), 0, 1) - 1) * model_tilt
raw_exposure_t = base_exposure + probability_tilt_t + trend_adjustment_t

target_position_t = raw_exposure_t * vol_multiplier_t * vix_multiplier_t * drawdown_multiplier_t
target_position_t = apply_trend_cap_fast_risk_off_cap_and_bull_recovery_overlays(target_position_t)

2) Sentiment Mechanism
has_news_t = news_volume_t &gt; 0
sentiment_score_raw_t = 0.70*sentiment_ma_5d_t + 0.30*sentiment_change_3d_t
sentiment_score_raw_t = where(has_news_t, sentiment_score_raw_t, 0.0)

sentiment_score_scaled_t = tanh(sentiment_score_raw_t * sentiment_sensitivity)

base_confidence_t = clip(news_volume_t / max(sentiment_confidence_headlines, 1e-9), 0, 1)
high_news_bonus_t = 0.25 * (news_volume_zscore_t &gt; sentiment_news_z_threshold)
sentiment_confidence_t = where(
    has_news_t,
    clip(base_confidence_t + high_news_bonus_t, 0, 1),
    0.0,
)

sentiment_dir_t = sign(sentiment_score_scaled_t)
streak_id_t = cumulative_sum(sentiment_dir_t != sentiment_dir<sub>t-1</sub>)
consecutive_same_direction_days_t = group_count(streak_id_t) + 1
whipsaw_ok_t = (sentiment_dir_t == 0) | (consecutive_same_direction_days_t &gt;= sentiment_whipsaw_days)

pos_limit = sentiment_positive_max_adjustment
neg_limit = sentiment_negative_max_adjustment * sentiment_asymmetric_factor

pos_scale_t = clip(sentiment_score_scaled_t, lower=0) * sentiment_confidence_t * pos_limit
neg_scale_t = clip(sentiment_score_scaled_t, upper=0) * sentiment_confidence_t * neg_limit

raw_mult_t = 1.0 + pos_scale_t + neg_scale_t
mult_t = where(has_news_t &amp; whipsaw_ok_t, raw_mult_t, 1.0)

composite_fear_t = ((vix_multiplier_t &lt; 1.0) + (volatility_ratio_5_20_t &gt; 1.5) + (drawdown_60d_t &lt; -0.10)) &gt;= 2
mult_t = where(composite_fear_t &amp; (mult_t &gt; 1.0), 1.0, mult_t)

mult_t = where(strong_bull_regime_t &amp; (mult_t &lt; 1.0), maximum(mult_t, 0.97), mult_t)

sentiment_multiplier_t = where(has_news_t, mult_t, 1.0)
sentiment_adjustment_t = sentiment_multiplier_t - 1.0
sentiment_whipsaw_active_t = (~whipsaw_ok_t).astype(int)
sentiment_risk_on_t = sentiment_multiplier_t &gt; 1.0
sentiment_risk_off_t = sentiment_multiplier_t &lt; 1.0

target_position_t = target_position_t * sentiment_multiplier_t
target_position_t = where(fast_risk_off_t == 1, minimum(target_position_t, risk_off_exposure), target_position_t)

3) Execution / Costs
target_position_t = reapply_fast_risk_off_cap_clip_and_reapply_cap(target_position_t)
executable_target_position_t = target_position<sub>t-1</sub>
position_t = rebalance_to_executable_target_only_when_band_is_exceeded(
    executable_target_position_t,
    position<sub>t-1</sub>,
    rebalance_threshold,
    recovery_step_up_limit,
)

turnover_t = abs(position_t - position<sub>t-1</sub>)
cash_weight_t = clip(1 - position_t, lower=0)
leverage_amount_t = clip(position_t - 1, lower=0)
financing_cost_t = leverage_amount_t * ((1 + leverage_financing_rate) ** (1/252) - 1)
turnover_cost_t = turnover_t * cost_bps / 10000
strategy_return_net_t = position_t * market_return_t + cash_weight_t * daily_cash_return_t - financing_cost_t - turnover_cost_t
strategy_equity_t = cumprod(1 + strategy_return_net_t)
strategy_drawdown_t = strategy_equity_t / running_max(strategy_equity_t) - 1</pre>

      <h3>Daily Algorithm For Trading Day <code>t</code></h3>
      <ol>
        <li>After the close, receive <code>p_t = P(y_t=1 | X_t)</code>, the point-in-time features, and the locked settings.</li>
        <li>Convert the probability into a centered exposure signal between negative and positive <code>model_tilt</code>.</li>
        <li>Add the trend effect and create the first exposure estimate.</li>
        <li>Scale exposure by known risk state: shifted realized volatility, prior VIX stress and shifted 60-day drawdown.</li>
        <li>Apply defensive and offensive overlays: trend-off cap, fast-risk-off cap, strong risk-on boost, recovery floor, strong-bull floor, leveraged-bull floor and early-risk-on boost/floor. Fast-risk-off is applied again after overlays.</li>
        <li>Apply real-news sentiment only when the overlay is active and real news exists. Then reapply the fast-risk-off cap, clip to <code>[min_exposure, max_exposure]</code>, and reapply fast-risk-off once more so clipping cannot weaken the defensive cap.</li>
        <li>Delay execution. The target computed after the close becomes tomorrow's <code>executable_target_position</code> through <code>target_position.shift(1)</code>. There is no same-row execution.</li>
        <li>Rebalance only if the executable target differs from <code>current_position</code> by at least <code>rebalance_threshold</code>. If held exposure is below <code>base_exposure</code> and the target is higher, <code>recovery_step_up_limit</code> caps only the step size toward the target, it does not cap risk-on targets at <code>base_exposure</code>. Downward defensive moves and existing above-base behavior are unchanged. Otherwise keep the previous <code>position</code>.</li>
        <li>Compute open-to-next-open return, turnover, cash yield, leverage financing, transaction costs, net return, equity, drawdown and metrics.</li>
      </ol>
      <div class="why"><span class="label">Final interpretation</span>The classifier supplies <code>p_t</code>. The deterministic exposure/backtest process turns it into tradable portfolio exposure. Because <code>p_t^W</code> and <code>p_t^O</code> use the same timing, risk, sentiment, cost and metric rules, the final comparison asks a clean question: which probability path is more useful after realistic portfolio translation?</div>
    </div></section>"""

    html = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Machine Learning Dynamic Risk Exposure</title>
  <script src="https://cdn.plot.ly/plotly-3.0.1.min.js"></script>
  <style>
    :root {{
      --bg: #f5f7fa; --paper: #ffffff; --ink: #172033; --muted: #5d6b7d;
      --line: #d9e1ec; --accent: #12355b; --accent-2: #1f77b4; --soft: #eef3f8;
      --code: #111827; --shadow: 0 14px 42px rgba(15,23,42,.08); --radius: 10px;
    }}
    * {{ box-sizing: border-box; }}
    html {{ scroll-behavior: smooth; }}
    body {{ margin:0; background:var(--bg); color:var(--ink); font-family:Inter,ui-sans-serif,system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",Arial,sans-serif; font-size:14px; line-height:1.55; }}
    .progress {{ position:fixed; top:0; left:0; height:4px; width:0; background:linear-gradient(90deg,var(--accent),var(--accent-2)); z-index:50; }}
    .layout {{ display:grid; grid-template-columns:260px minmax(0,1fr); min-height:100vh; }}
    aside {{ position:sticky; top:0; height:100vh; padding:22px 18px; background:#111827; color:#dfe8f4; overflow-y:auto; border-right:1px solid rgba(255,255,255,.08); }}
    .brand {{ padding-bottom:22px; margin-bottom:18px; border-bottom:1px solid rgba(255,255,255,.12); }}
    .eyebrow {{ color:#9fc5ea; font-size:12px; letter-spacing:.16em; text-transform:uppercase; font-weight:800; }}
    .brand h1 {{ font-family:Georgia,"Times New Roman",serif; margin:8px 0 6px; font-size:19px; line-height:1.15; }}
    .brand p {{ margin:0; color:#aab7c8; font-size:13px; }}
    nav a {{ display:block; padding:6px 8px; margin:2px 0; color:#c9d5e4; text-decoration:none; border-radius:8px; font-size:12px; }}
    nav a:hover, nav a.active {{ background:rgba(142,184,229,.15); color:white; }}
    .side-actions {{ display:grid; gap:10px; margin-top:22px; }}
    button {{ border:1px solid rgba(255,255,255,.18); background:rgba(255,255,255,.08); color:white; border-radius:8px; padding:9px 11px; cursor:pointer; font-weight:750; }}
    main {{ padding:30px clamp(18px,3.5vw,48px) 54px; max-width:1280px; width:100%; }}
    section {{ margin:0 0 22px; background:var(--paper); border:1px solid var(--line); border-radius:var(--radius); box-shadow:var(--shadow); overflow:hidden; }}
    .section-inner {{ padding:clamp(18px,3vw,30px); }}
    .hero {{ background:#101827; color:white; border:none; }}
    .hero .section-inner {{ padding:clamp(28px,4vw,48px); }}
    .hero h2 {{ max-width:1000px; margin:0 0 12px; font-family:Georgia,"Times New Roman",serif; font-size:clamp(28px,3.8vw,44px); line-height:1.05; letter-spacing:-.03em; }}
    .hero p {{ max-width:960px; color:#d9e5f4; font-size:15px; margin:0 0 12px; }}
    h2.section-title {{ margin:0 0 12px; font-family:Georgia,"Times New Roman",serif; font-size:clamp(23px,2.4vw,32px); line-height:1.1; letter-spacing:-.02em; }}
    h3 {{ margin:22px 0 8px; font-size:16px; color:var(--accent); }}
    p {{ margin:0 0 10px; }}
    .lead {{ color:var(--muted); font-size:15px; max-width:980px; }}
    .two-col {{ display:grid; grid-template-columns:minmax(0,1fr) minmax(0,1fr); gap:18px; }}
    .three-col {{ display:grid; grid-template-columns:repeat(3,minmax(0,1fr)); gap:14px; }}
    .card {{ background:var(--soft); border:1px solid var(--line); border-radius:8px; padding:14px; }}
    .card h3 {{ margin-top:0; }}
    .formula {{ background:#f7fafc; border-left:4px solid var(--accent-2); padding:13px 16px; margin:12px 0; font-family:"Cascadia Mono",Consolas,monospace; font-size:14px; color:#213044; }}
    pre.code {{ background:var(--code); color:#e5edf7; padding:18px; border-radius:8px; overflow-x:auto; font-size:13px; line-height:1.55; }}
    .note, .teacher, .why {{ border:1px solid var(--line); background:#fbfdff; border-radius:8px; padding:16px 18px; margin-top:18px; }}
    .label {{ display:block; margin-bottom:5px; color:var(--accent); font-weight:800; text-transform:uppercase; letter-spacing:.08em; font-size:12px; }}
    .pipeline {{ display:grid; gap:10px; margin-top:20px; }}
    .pipe-step {{ display:grid; grid-template-columns:46px minmax(0,1fr); gap:14px; align-items:start; padding:14px; background:#f8fafc; border:1px solid var(--line); border-radius:8px; }}
    .num {{ width:34px; height:34px; border-radius:999px; display:grid; place-items:center; background:var(--accent); color:white; font-weight:800; }}
    .artifact-card {{ margin-top:16px; background:#fff; border:1px solid var(--line); border-radius:8px; padding:14px; overflow:auto; }}
    .artifact-head {{ display:flex; justify-content:space-between; align-items:center; gap:16px; }}
    .artifact-head h3, .artifact-card h3 {{ margin:0 0 10px; }}
    .caption {{ color:var(--muted); font-size:13px; }}
    .figure-card img {{ display:block; max-width:100%; border-radius:8px; border:1px solid var(--line); background:white; }}
    #shap .shap-card {{ overflow:hidden; padding-bottom:10px; }}
    #shap .shap-plot {{ width:100%; max-height:360px; }}
    #shap img.shap-plot {{ height:auto; object-fit:contain; margin:0 auto; cursor:zoom-in; }}
    #shap div.shap-plot {{ height:360px; overflow:hidden; }}
    .open-figure {{ color:white; background:var(--accent); border-color:var(--accent); }}
    .dataframe {{ border-collapse:collapse; width:100%; font-size:12px; }}
    .dataframe th, .dataframe td {{ padding:7px 9px; border:1px solid var(--line); text-align:right; }}
    .dataframe tbody th {{ text-align:left; background:#f8fafc; color:#1f2937; }}
    .dataframe thead th {{ background:#10233f; color:white; }}
    .modal {{ position:fixed; inset:0; display:none; background:rgba(9,14,25,.78); z-index:100; padding:24px; }}
    .modal[aria-hidden="false"] {{ display:block; }}
    .modal-shell {{ background:white; border-radius:12px; height:calc(100vh - 48px); display:grid; grid-template-rows:auto 1fr; overflow:hidden; }}
    .modal-top {{ display:flex; align-items:center; justify-content:space-between; padding:14px 16px; border-bottom:1px solid var(--line); }}
    .modal-top h3 {{ margin:0; }}
    .modal-controls button {{ color:var(--ink); background:#f4f7fb; border:1px solid var(--line); }}
    .modal-view {{ overflow:auto; display:grid; place-items:start center; padding:18px; }}
    #modalImage {{ max-width:none; transform-origin:top center; }}
    @media (max-width:980px) {{ .layout {{ grid-template-columns:1fr; }} aside {{ position:relative; height:auto; }} .two-col,.three-col {{ grid-template-columns:1fr; }} #shap .shap-plot {{ max-height:320px; }} #shap div.shap-plot {{ height:320px; }} }}
  </style>
</head>
<body>
<div class="progress" id="progress"></div>
<div class="layout">
  <aside>
    <div class="brand">
      <div class="eyebrow">Research Presentation</div>
      <h1>Machine Learning Dynamic Risk Exposure</h1>
      <p>Validation-safe trading framework for converting Machine Learning probabilities into risk-managed exposure.</p>
    </div>
    <nav id="nav">
      <a href="#abstract">Abstract</a>
      <a href="#objective">Objective</a>
      <a href="#architecture">Architecture</a>
      <a href="#data">Data</a>
      <a href="#features">Features</a>
      <a href="#target">Target</a>
      <a href="#models">Models</a>
      <a href="#engine">Exposure Engine</a>
      <a href="#selection">Walk-Forward Selection</a>
      <a href="#validation">Validation Discipline</a>
      <a href="#shap">Interpretability</a>
      <a href="#empirical">Empirical Charts</a>
      <a href="#candlestick">Candlestick Chart</a>
      <a href="#metrics">Metrics</a>
      <a href="#history">Previous Stocks</a>
    </nav>
    <div class="side-actions">
      <button onclick="window.print()">Print / Save PDF</button>
      <button id="expandAll" type="button">Expand All</button>
      <button id="collapseAll" type="button">Collapse All</button>
    </div>
  </aside>
  <main>
    <section class="hero" id="abstract"><div class="section-inner">
      <div class="eyebrow">Machine Learning in Financial Risk Management</div>
      <h2>Machine Learning-Assisted Dynamic Risk Exposure</h2>
      <p>This presentation documents a walk-forward validated framework for converting Machine Learning signals into risk-managed exposure. The framework is asset-agnostic and has been evaluated across multiple stocks.</p>
      <p>The strategy adjusts exposure dynamically using Machine Learning probabilities, trend filters, volatility controls, drawdown protection, early risk-on recovery logic, multiplicative sentiment scaling and turnover-aware rebalance controls. Sections 1-9 describe the current notebook methodology. Sections 10-13 present the specific results for the selected asset: <strong>{display_symbol}</strong> with model <strong>{display_model_name}</strong>.</p>
    </div></section>

    <section id="objective"><div class="section-inner">
      <h2 class="section-title">1. Research Objective</h2>
      <p class="lead">Does a validation-disciplined XGBoost probability model, translated by a deterministic exposure engine, improve risk-adjusted out-of-sample behavior relative to buy-and-hold?</p>
      <p>The classifier does not predict the exact price or daily return. It estimates <code>risk_on_proba = P(y_t = 1 | X_t)</code>, where <code>y_t</code> is a favorable future-return regime label based on a weighted future open-to-open return exceeding a train-derived threshold. The exposure engine converts this probability into <code>target_position</code> using trend, volatility, drawdown, sentiment and risk controls. The execution/backtest layer then applies a one-row delay, rebalance band, transaction costs, cash yield and leverage financing before comparing out-of-sample results with buy-and-hold.</p>
      <div class="three-col">
        <div class="card"><h3>Risk-First Evaluation</h3><p>Assessment focuses on out-of-sample risk-adjusted behavior: Sharpe difference, drawdown, volatility, turnover, costs and annualized return.</p></div>
        <div class="card"><h3>General Asset Workflow</h3><p>The workflow accepts a selected stock, ETF or liquid instrument. It builds ticker-based price, context, sentiment and filing/event features without hardcoded company assumptions.</p></div>
        <div class="card"><h3>Execution Assumptions</h3><p>Signals trade through <code>target_position.shift(1)</code>. The backtest includes a no-trade band, 5 bps per unit turnover, cash yield on unallocated capital and financing for exposure above 1.0.</p></div>
      </div>
      <div class="teacher"><span class="label">Explanation</span>The model estimates favorable-regime probability only. The deterministic engine decides exposure, and the final test evaluates whether that exposure path has better risk-adjusted out-of-sample behavior than passive buy-and-hold under the same timing and cost assumptions.</div>
    </div></section>

    <section id="architecture"><div class="section-inner">
      <h2 class="section-title">2. System Architecture</h2>
      <p class="lead">The system separates prediction, exposure construction, and execution/backtesting.</p>
      <p>The classifier output is only a probability. A deterministic exposure layer maps <code>risk_on_proba</code> plus point-in-time market, risk and sentiment state into <code>target_position</code>. The execution layer applies delay, rebalance logic, transaction costs, cash return and leverage financing. This separation makes timing and tuning boundaries explicit and helps limit leakage and overfitting risk.</p>
      <div class="pipeline">
        <div class="pipe-step"><div class="num">1</div><div><strong>Data/context.</strong><br>Daily OHLCV, warm-up history, cross-market variables, real-news sentiment and filing/event context are collected for the selected asset.</div></div>
        <div class="pipe-step"><div class="num">2</div><div><strong>Point-in-time features.</strong><br>Technical, volatility, volume, trend, sentiment and event features are aligned to after-close signal time. News and filing/event inputs are shifted one trading row.</div></div>
        <div class="pipe-step"><div class="num">3</div><div><strong>Chronological split and labels.</strong><br>Train, validation and test remain ordered in time. Labels use weighted future open-to-open returns and thresholds derived from the allowed training window.</div></div>
        <div class="pipe-step"><div class="num">4</div><div><strong>Probability models.</strong><br>Weighted XGBoost and an Optuna-tuned candidate estimate <code>risk_on_proba = P(y_t = 1 | X_t)</code>. The output is a probability, not a trade.</div></div>
        <div class="pipe-step"><div class="num">5</div><div><strong>Validation/walk-forward selection.</strong><br>Model candidates are compared with walk-forward folds; exposure, sentiment and risk settings are selected on validation with train-only probabilities and locked before the final test.</div></div>
        <div class="pipe-step"><div class="num">6</div><div><strong>Final test and metrics.</strong><br>The selected probability path and locked engine settings are evaluated on the final holdout with net returns, drawdown, volatility, turnover, costs and buy-and-hold comparison metrics.</div></div>
      </div>
      <div class="artifact-card table-wrap"><h3>Prediction vs. Trading Layers</h3><table class="dataframe"><thead><tr><th>Layer</th><th>Output</th><th>Why separate?</th></tr></thead><tbody>
        <tr><td>Classifier</td><td><code>risk_on_proba</code></td><td>Estimates <code>P(y_t = 1 | X_t)</code> for the favorable-regime label.</td></tr>
        <tr><td>Exposure engine</td><td><code>target_position</code></td><td>Converts probability plus point-in-time risk state into desired exposure.</td></tr>
        <tr><td>Execution/backtest</td><td><code>position</code>, <code>strategy_return_net</code></td><td>Applies delay, rebalance band, costs, cash return and leverage financing.</td></tr>
      </tbody></table></div>
    </div></section>

    <section id="data"><div class="section-inner">
      <h2 class="section-title">3. Data and Market Context</h2>
      <p class="lead">The dataset combines selected-asset OHLCV, classic technical indicators, cross-market context, and real-news sentiment/event context into one chronological feature table.</p>
      <p>Primary prices come from daily Open/High/Low/Close/Volume fetched through Yahoo/yfinance for the selected asset. The notebook loads a 2-year warm-up period before the formal sample start so rolling indicators are stable, then keeps the modeling sample in chronological train, validation, and test order. There is no random split.</p>
      <div class="two-col">
        <div><h3>Technical Market State</h3><p>Classic indicators describe trend, momentum, volatility, drawdown and volume pressure using returns/momentum over 1d, 3d, 5d, 10d and 20d windows, RSI and StochRSI, MACD / MACD-derived features, SMA/EMA trend features, VWMA, ATR, Bollinger width and realized-volatility features, drawdown from recent peaks, and volume or dollar-volume z-score/anomaly features.</p></div>
        <div><h3>Cross-Market Context</h3><p>Macro and risk-regime inputs are aligned to the primary asset calendar, including VIX level, changes, spikes and above-moving-average flags, Treasury/rates proxy TNX, dollar index DXY, and ES/NQ/YM equity-index futures returns or momentum. These fields help separate asset-specific movement from broad market stress or risk-on/risk-off conditions.</p></div>
      </div>
      <div class="two-col">
        <div><h3>Real-News Sentiment</h3><p>Public headline sentiment is aggregated daily into compact features such as <code>sentiment_ma_5d</code>, <code>sentiment_change_3d</code>, <code>sentiment_extremity</code>, <code>news_volume</code>, <code>news_volume_zscore</code>, <code>sentiment_confidence</code>, and <code>sentiment_has_news</code>. No-news periods are neutral, not synthetic positive or negative sentiment. Raw daily sentiment and news volume are shifted one trading row before model use to avoid same-day news leakage. GDELT is one public source used for historical headline discovery, and source-query mechanics are not the focus of this section.</p></div>
        <div><h3>Compact Filing/Event Context</h3><p>When available, SEC filings add small event-count features such as total filing count, 8-K count, 10-Q/10-K count, and days since filing. The notebook resolves public-company filings through CIK when available, shifts filing counts by one trading row, and leaves unavailable filing context neutral.</p></div>
      </div>
      <h3>Data Quality and Preprocessing</h3>
      <p>Cross-market and context variables are forward-filled onto the primary asset's trading calendar. Later, model-matrix missingness is handled with train-split rules: columns with more than 10% missing values in train are dropped, and remaining train/validation/test feature gaps are filled with train means.</p>
      <div class="why"><span class="label">Leakage control</span>Chronological splitting matters because random shuffling would mix future market regimes into training. News sentiment and SEC/event context are shifted one trading row, so same-day headlines or filings are not treated as tradable information for that row.</div>
    </div></section>

    <section id="features"><div class="section-inner">
      <h2 class="section-title">4. Feature Engineering</h2>
      <p class="lead">Features convert raw market, news, and event data into point-in-time variables available at signal time. They describe trend, momentum, volatility, stress, liquidity and volume, cross-market regime, sentiment, and filing/event context.</p>
      <p>The timing convention is explicit. The model observes information after market close at time <code>t</code>, builds the feature row for that close, and the trading engine executes at the next market open. Technical and cross-market fields are aligned to the asset trading calendar. Sentiment inputs and SEC filing event inputs are shifted by one trading row before model use, so same-day news or filings are not treated as tradable information for that row. No-news and no-filing periods stay neutral rather than being converted into artificial positive or negative signals.</p>
      <div class="three-col">
        <div class="card"><h3>Trend and Momentum</h3><p>Return and momentum features cover several horizons, including <code>return_1d</code>, <code>return_3d</code>, <code>return_5d</code>, <code>return_10d</code>, <code>return_20d</code>, <code>return_40d</code>, <code>return_60d</code>, <code>mom_10_pct</code>, and <code>macd_pct</code>. Oscillator features include centered RSI fields <code>rsi_5_centered</code>, <code>rsi_10_centered</code>, <code>rsi_15_centered</code>, plus normalized StochRSI. Trend distance and slope features include <code>close_to_sma_5</code>, <code>close_to_sma_10</code>, <code>close_to_sma_20</code>, <code>close_to_ema_5</code>, <code>close_to_ema_10</code>, <code>close_to_ema_20</code>, <code>close_to_ema_50</code>, <code>close_to_ema_100</code>, <code>close_to_ema_200</code>, <code>ema_20_slope_3d</code>, <code>ema_50_slope_5d</code>, <code>ema_100_slope_5d</code>, <code>ema_200_slope_5d</code>, <code>ema_20_50_trend</code>, and <code>ema_50_200_trend</code>.</p></div>
        <div class="card"><h3>Volatility and Stress</h3><p>Volatility features normalize risk across price levels and time windows. The notebook uses <code>atr_14_pct</code>, <code>bb_width_pct</code>, <code>bb_position</code>, <code>volatility_5d</code>, <code>volatility_20d</code>, <code>volatility_60d</code>, <code>volatility_ratio_5_20</code>, and <code>volatility_ratio_20_60</code>. Stress fields include recent drawdown and gap behavior, such as <code>drawdown_20d</code>, <code>drawdown_60d</code>, <code>overnight_gap</code>, and <code>gap_volatility_20d</code>. These variables help distinguish normal trend movement from unstable or defensive market conditions.</p></div>
        <div class="card"><h3>Volume and Liquidity</h3><p>Volume features describe participation, confirmation, and abnormal activity. Examples include <code>volume_change_5d</code>, <code>volume_change_10d</code>, <code>volume_zscore_20</code>, <code>dollar_volume_zscore_20</code>, <code>obv_change_5d</code>, <code>ad_change_5d</code>, and <code>volume_price_confirmation</code>. These features help the model separate moves with broad participation from weaker price changes that occur on low or unusual volume.</p></div>
        <div class="card"><h3>Cross-Market Regime</h3><p>Context features describe whether the selected asset is moving with or against the wider market. VIX examples include <code>vix_level</code>, <code>vix_change_3d</code>, <code>vix_change_5d</code>, <code>vix_close_return_1d</code>, <code>vix_close_return_3d</code>, <code>vix_close_return_5d</code>, <code>vix_close_return_20d</code>, <code>vix_ma_20</code>, <code>vix_above_ma_20</code>, <code>vix_spike_3d</code>, and <code>vix_spike_5d</code>. Rates and dollar context include <code>tnx_level</code>, TNX changes, <code>dxy_level</code>, and DXY changes. Equity-index context uses ES, NQ, and YM returns or momentum, relative-strength fields such as <code>rel_strength_es_20d</code>, <code>rel_strength_nq_20d</code>, and <code>rel_strength_ym_20d</code>, plus combined regime fields <code>trend_vix_risk</code> and <code>momentum_vix_risk</code>.</p></div>
        <div class="card"><h3>Sentiment Layer</h3><p>Public-news sentiment is collected under bounded request caps, aggregated by publication day, and shifted one trading row before model use. The compact feature set includes <code>sentiment_daily</code>, <code>sentiment_ma_5d</code>, <code>sentiment_change_3d</code>, <code>sentiment_extremity</code>, <code>news_volume</code>, <code>news_volume_zscore</code>, <code>sentiment_confidence</code>, and <code>sentiment_has_news</code>. When no usable news is available for a trading row, sentiment impact is neutral and distinguishable through the news-volume and has-news fields.</p></div>
        <div class="card"><h3>SEC Filing Events</h3><p>SEC/event features add compact public filing context when it is available for the selected ticker. The model can use <code>sec_filing_count</code>, <code>sec_8k_count</code>, <code>sec_10q_10k_count</code>, <code>sec_material_event_flag</code>, <code>sec_registration_count</code>, <code>sec_amendment_count</code>, <code>sec_days_since_filing</code>, and <code>sec_data_available</code>. Filing counts are mapped to the trading calendar and shifted one trading row, while unavailable SEC data remains neutral.</p></div>
      </div>
      <h3>Feature Selection and Importance</h3>
      <p>After feature construction, the model matrix is filtered using training-split information only. Features with excessive missingness in the training split are removed, remaining train, validation, and test gaps are filled with train means, and correlation clustering removes redundant features with pairwise correlation above <code>0.82</code>. The final feature count is asset/run-dependent because availability, missingness, and correlation structure vary by run. SHAP then explains how the final model uses the selected features.</p>
      <pre class="code">signal_time = market_close_t
features_t = technical_t + cross_market_t + lagged_sentiment_t + lagged_sec_events_t
execution_time = next_market_open</pre>
    </div></section>

    <section id="target"><div class="section-inner">
      <h2 class="section-title">5. Target Construction And Chronological Split</h2>
      <p class="lead">The target is a binary label for a favorable future-return regime. It is not a raw price prediction and it is not a direct prediction of the next close.</p>
      <p>The notebook uses an open-to-open target because the trading workflow acts at the next session open. A feature row is built from information available after the close at time <code>t</code>. The executable entry is therefore <code>Open.shift(-1)</code>, matching the engine's next-session execution timing.</p>
      <p>The notebook first splits <code>df_ta</code> chronologically into train (earliest 60%), validation (next 20%), and test (final 20%). It then calls <code>add_future_return_target()</code> inside each split separately to compute <code>future_return</code> and <code>target</code>. This ordering prevents future-return boundary leakage across train, validation, and test.</p>
      <p>Labels are based on a weighted blend of 3-day, 5-day, and 10-day open-to-open forward returns. Because the future returns are computed inside each chronological split or walk-forward fold, rows near split boundaries are labeled only with data available inside that split. Rows where the required future open is unavailable become NaN and are dropped from the labeled set.</p>
      <pre class="code">for horizon in [3, 5, 10]:
    entry_price = Open.shift(-1)
    exit_price = Open.shift(-(horizon + 1))
    future_return_h = exit_price / entry_price - 1

future_return = (
    0.40 * future_return_3d
    + 0.35 * future_return_5d
    + 0.25 * future_return_10d
)

long_threshold = train_df["future_return"].quantile(0.60)
target = (future_return > long_threshold).astype(int)</pre>
      <h3>Binarization Threshold</h3>
      <p>The main split sets <code>long_threshold = train_df["future_return"].quantile(0.60)</code>. The 0.60 quantile is a manual research/design choice, not a threshold learned automatically by the model. It defines <code>target=1</code> as roughly the top 40% of training future-return outcomes, with <code>target=0</code> for the remaining outcomes.</p>
      <p>The same train-derived threshold is then applied to train, validation, and test labels in the main split. Validation and test rows do not set their own threshold. When the final model is refit, it uses train + validation labeled data and computes its 0.60 threshold from train + validation only, the test set still does not set the threshold. In walk-forward evaluation, the notebook uses <code>WF_TARGET_QUANTILE = 0.60</code> and recomputes the threshold using each fold's training subset only.</p>
      <div class="teacher"><span class="label">Leakage control</span>There is no target leakage from this construction. The threshold uses only the past/training return distribution. Future returns are labels, not model features. Split-edge rows are labeled inside their own split, and rows without enough future open prices are dropped before modeling.</div>
    </div></section>

    <section id="models"><div class="section-inner">
      <h2 class="section-title">6. Machine Learning Models</h2>
      <p class="lead">The machine-learning layer estimates the probability of a favorable future-return regime. It does not produce a direct buy/sell instruction and it does not forecast the exact future price.</p>
      <p>For each trading day <code>t</code>, the model receives <code>X_t</code>, a feature vector built from the technical, volatility, volume, cross-market, sentiment, and event variables described above. It learns from the binary label <code>y_t in {0,1}</code> constructed in Section 5. The model output is <code>risk_on_proba = P(y_t = 1 | X_t)</code>, interpreted as the estimated probability that the next labeled horizon belongs to the favorable regime.</p>

      <h3>Model Mechanism</h3>
      <p>XGBoost is an additive ensemble of decision trees. Each tree contributes a small function of the current feature vector, and the raw model score is the sum of those tree contributions.</p>
      <div class="formula">score(X_t) = sum_k f_k(X_t)</div>
      <p>The raw score is then mapped to a probability through the logistic sigmoid function.</p>
      <div class="formula">risk_on_proba = sigma(score) = 1 / (1 + exp(-score))</div>
      <p>The sigmoid transforms any real-valued score into the interval <code>[0,1]</code>, so large positive scores imply high estimated risk-on probability and large negative scores imply low estimated risk-on probability.</p>

      <h3>Training Objective</h3>
      <p>The classifier is trained with binary log loss, which penalizes confident wrong probabilities more strongly than uncertain errors.</p>
      <div class="formula">L = -[y log(p) + (1-y) log(1-p)]</div>
      <p>Regularization, restricted tree complexity, sample weighting, and chronological validation/model selection keep the tree ensemble from fitting noise too closely. This is especially important in financial data, where excessive model complexity can produce overconfident probabilities that do not generalize out of sample.</p>

      <h3>Class Imbalance</h3>
      <p>The 0.60 target threshold creates a roughly 60/40 label split, so one class is usually less frequent than the other. Balanced sample weights are used so the model does not ignore whichever class is minority in a given split, whether favorable or unfavorable. The goal is not to maximize naive accuracy, but to learn both sides of the risk-on/risk-off distinction.</p>

      <div class="two-col">
        <div><h3>Weighted XGBoost Baseline</h3>
        <p>The weighted XGBoost baseline is a fixed reference model. It uses balanced sample weights, restricted tree complexity, and regularization to estimate <code>risk_on_proba</code> without a broad search over alternative model and trading settings. Its role is to provide a robust benchmark: if a more complex candidate does not clearly improve the trading usefulness of the probability path, the baseline remains the safer reference.</p>
        </div>

        <div><h3>Optuna-Tuned Candidate</h3>
        <p>The Optuna-tuned XGBoost model is a candidate, not an automatic replacement for the baseline. The notebook uses a TPE sampler and runs <code>study.optimize(objective, n_trials=50)</code>. Each trial samples alternative XGBoost hyperparameters plus simple trading/exposure parameters: <code>decision_threshold</code>, <code>low_exposure</code>, <code>high_exposure</code>, <code>risk_off_exposure</code>, <code>risk_on_boost</code>, <code>rebalance_threshold</code>, and <code>fast_vol_threshold</code>.</p>
        <p>The purpose is not to declare that Optuna is better because it searched more settings. The purpose is to test whether an alternative probability path is more useful for trading after basic exposure rules are applied.</p>
        </div>
      </div>

      <h3>Preliminary Trading Score</h3>
      <p>The 50 Optuna trials are evaluated with <code>score_probability_strategy_next_open()</code>, not with the full <code>run_stock_strategy_backtest()</code> Dynamic Exposure Engine explained in Section 7. This keeps model/signal selection separate from full portfolio and risk construction.</p>
      <p>The mini scorer follows a simple causal flow: <code>risk_on_proba</code> is converted into a simple <code>target_exposure</code>, the exposure is shifted into an executable next-open position, open-to-next-open strategy returns are computed, and a compact trading score is assigned.</p>
      <div class="formula">score = Sharpe + 0.25*Sortino + 0.70*Annualized Return - drawdown_penalty - turnover_penalty<br>drawdown_penalty = 0.80 * abs(max_drawdown)<br>turnover_penalty = 0.003 * total_turnover</div>
      <p>This step avoids judging models by accuracy alone. It asks whether the probability sequence can support a tradable exposure path before adding the full Section 7 risk engine complexity.</p>

      <h3>Bridge to the Dynamic Exposure Engine</h3>
      <p>Section 6 selects and compares probability-producing models: the weighted baseline and the Optuna-tuned candidate. Section 7 then explains the full Dynamic Exposure Engine that converts the selected probabilities into final <code>target_position</code> with exposure limits, transaction-cost-aware rebalancing, defensive risk controls, and portfolio-level execution logic.</p>

      <h3>Why XGBoost?</h3>
      <p>XGBoost is a robust tabular model for noisy, mixed financial features. It captures nonlinear effects and feature interactions without requiring very large datasets, works well with modest sample sizes, supports regularization and constrained tree structure, and is compatible with SHAP-based interpretation. These properties make it a suitable academic baseline for technical, cross-market, sentiment, and event features.</p>
      <div class="teacher"><span class="label">Model Comparison Summary</span>The weighted XGBoost baseline is the reference. The Optuna-tuned variant is accepted only if validation or walk-forward evidence shows that its probability path improves the downstream trading objective without excessive overfitting. In both cases, the model outputs probability only, the risk engine decides the final exposure.</div>
    </div></section>

    {dynamic_exposure_section}

    {walk_forward_section}

    <section id="validation"><div class="section-inner">
      <h2 class="section-title">9. Validation Discipline</h2>
      <p class="lead">Compact recap of the chronology that keeps target construction, tuning, walk-forward selection, final testing and diagnostics separated.</p>
      <p>The main split is chronological 60/20/20: the earliest rows form train, the next block validation, and the final block test. The notebook first splits the feature table, then constructs <code>future_return</code> and <code>target</code> inside each split so labels do not cross split boundaries. During validation tuning, preprocessing choices, target-label thresholds, missing-value fills, the train-only <code>validation_model</code>, and probability/exposure threshold candidates come from training information only.</p>
      <h3>Validation Contract</h3>
      <p>Validation is used to choose compact model, risk, sentiment and overlay settings, it is not final performance evidence. The walk-forward protocol is an additional chronological check: each fold trains on past rows only, evaluates the next unseen block, uses preliminary/default exposure rules for candidate comparison, and includes the Optuna candidate only when <code>best_params</code> exists. After the model family and settings are locked, <code>final_model</code> is refit on train+validation labeled data only. The test window is then used only for final measurement, while SHAP is computed afterward as post-lock diagnostics rather than as a tuning signal.</p>
      <div class="artifact-card table-wrap"><h3>What Each Split Is Allowed To Do</h3><table class="dataframe"><thead><tr><th>Split</th><th>Allowed use</th><th>Forbidden use</th></tr></thead><tbody>
        <tr><td>Train</td><td>Fit preprocessing values, split-local labels, train-only validation model and training-derived threshold candidates.</td><td>Report final performance.</td></tr>
        <tr><td>Validation</td><td>Select model family and compact risk, sentiment, probability/exposure threshold and early-risk-on settings.</td><td>Measure final out-of-sample performance.</td></tr>
        <tr><td>Test</td><td>Measure the locked strategy after final train+validation refit.</td><td>Choose model, thresholds, overlays, rebalance settings or SHAP-based changes.</td></tr>
      </tbody></table></div>
      <div class="why"><span class="label">Why this matters</span>Walk-forward provides a stricter diagnostic than a single validation block because every fold respects time order. It does not guarantee robustness, and compact validation choices can still overfit the validation period. The locked final test therefore remains the primary holdout measurement, with SHAP reserved for interpretation after model and strategy choices are fixed.</div>
    </div></section>

    <section id="shap"><div class="section-inner">
      <h2 class="section-title">10. SHAP interpretability</h2>
      <p class="lead">SHAP explains which features push the locked model toward risk-on or risk-off for {display_symbol}.</p>
      <p>SHAP decomposes final-model predictions into feature contributions. Positive SHAP values push a prediction toward risk-on, while negative values push it toward risk-off. The bar summary shows average absolute contribution, the summary plot shows the distribution over the explanation sample, and the binary SHAP plot separates risk-on and risk-off contribution patterns. These views are interpretation and diagnostics after model and strategy choices are fixed, not tuning inputs.</p>
      {shap_bar_chart}
      {shap_summary_chart}
      {shap_binary_chart}
    </div></section>

    <section id="empirical"><div class="section-inner">
      <h2 class="section-title">11. Empirical Out-of-Sample</h2>
      <p class="lead">Final out-of-sample equity curve and drawdown for {display_symbol}. This locked holdout evaluation is the primary unbiased performance estimate.</p>
      <p>The equity curve shows the cumulative return of the dynamic exposure strategy vs buy-and-hold on the untouched test window. The drawdown chart shows the peak-to-trough decline at each point in time. A successful strategy should show higher cumulative returns with lower maximum drawdown compared to buy-and-hold. The Sharpe Edge metric (strategy Sharpe minus buy-and-hold Sharpe) quantifies the risk-adjusted improvement.</p>
      {equity_chart}
      {drawdown_chart}
    </div></section>

    <section id="candlestick"><div class="section-inner">
      <h2 class="section-title">12. Candlestick Chart - Full Out-of-Sample Test Window</h2>
      <p class="lead">Interactive candlestick chart with exposure overlay for the full out-of-sample test window for {display_symbol}. The chart shows price action and the strategy's exposure level on each day.</p>
      <p>The candlestick chart visualizes the daily OHLC price action along with the strategy's exposure level (shown as a secondary axis or color overlay). Days with high exposure (near 1.0 or leveraged) indicate the model predicted a favorable regime, while days with low exposure (near 0) indicate the model predicted unfavorable conditions. This visualization helps identify when the strategy was in/out of the market and how those decisions aligned with price movements.</p>
      {candlestick_div}
    </div></section>

    <section id="metrics"><div class="section-inner">
      <h2 class="section-title">13. Final Metrics - {display_symbol}</h2>
      <p class="lead">Final out-of-sample metrics comparing the dynamic exposure strategy vs buy-and-hold for {display_symbol}. These numbers represent the strategy's performance on the untouched test window after validation-safe model, risk, sentiment and early-risk-on selection.</p>
      <p>The metrics table shows the complete performance comparison. Key metrics include Total Return (cumulative gain), Sharpe Ratio (risk-adjusted return), Max Drawdown (worst peak-to-trough decline), and Win Rate (percentage of days with positive net return). The strategy is considered successful if it achieves a positive Sharpe Edge (strategy Sharpe > buy-and-hold Sharpe) while maintaining lower or comparable drawdown.</p>
      <div class="artifact-card table-wrap"><h3>Metrics Comparison - {display_symbol}</h3><div>
<table border="1" class="dataframe">
  <thead>
    <tr style="text-align: right;">
      <th></th>
      <th>Dynamic Exposure Strategy</th>
      <th>Buy &amp; Hold</th>
    </tr>
  </thead>
  <tbody>
{metrics_table_rows}  </tbody>
</table>
</div></div>
      <div class="artifact-card table-wrap"><h3>Metric Helper</h3><table class="dataframe"><thead><tr><th>Metric</th><th>Meaning</th><th>Formula / calculation</th></tr></thead><tbody>
        <tr><td>Total Return</td><td>Cumulative net gain over the test window.</td><td><code>ending equity / starting equity - 1</code></td></tr>
        <tr><td>Annualized Return</td><td>Average daily net return scaled to one trading year, this is not CAGR.</td><td><code>mean(daily net return) &times; 252</code></td></tr>
        <tr><td>Annualized Volatility</td><td>Year-scaled variability of daily net returns.</td><td><code>std(daily net return) &times; sqrt(252)</code></td></tr>
        <tr><td>Sharpe Ratio</td><td>Return earned per unit of total volatility.</td><td><code>Annualized Return / Annualized Volatility</code></td></tr>
        <tr><td>Sortino Ratio</td><td>Return earned per unit of downside volatility.</td><td><code>Annualized Return / annualized std(negative daily returns)</code></td></tr>
        <tr><td>Calmar Ratio</td><td>Return relative to the worst drawdown.</td><td><code>Annualized Return / abs(Max Drawdown)</code></td></tr>
        <tr><td>Profit Factor</td><td>Gross positive daily net returns compared with gross negative daily net returns.</td><td><code>sum(positive daily net returns) / abs(sum(negative daily net returns))</code></td></tr>
        <tr><td>Max Drawdown</td><td>Largest peak-to-trough equity decline.</td><td><code>min(equity / running max equity - 1)</code></td></tr>
        <tr><td>Win Rate</td><td>Share of days or observations with positive net return.</td><td><code>mean(strategy_returns &gt; 0)</code></td></tr>
        <tr><td>Average Exposure</td><td>Average capital allocation held by the strategy.</td><td><code>mean(position)</code></td></tr>
        <tr><td>Total Turnover</td><td>Total absolute position changes, used for cost measurement.</td><td><code>sum(abs(position<sub>t</sub> - position<sub>t-1</sub>))</code></td></tr>
      </tbody></table></div>
    </div></section>

    {prev_section}
  </main>
</div>
<div class="modal" id="figureModal" aria-hidden="true"><div class="modal-shell"><div class="modal-top"><h3 id="modalTitle">Figure</h3><div class="modal-controls"><button type="button" id="zoomOut">Zoom Out</button><button type="button" id="zoomIn">Zoom In</button><button type="button" id="resetZoom">Reset</button><button type="button" id="closeModal">Close</button></div></div><div class="modal-view"><img id="modalImage" alt="Expanded figure"></div></div></div>
<script id="equity-json" type="application/json">{equity_json_payload}</script>
<script id="drawdown-json" type="application/json">{drawdown_json_payload}</script>
<script id="shap-bar-json" type="application/json">{shap_bar_json_payload}</script>
<script id="shap-summary-json" type="application/json">{shap_summary_json_payload}</script>
<script id="shap-binary-json" type="application/json">{shap_binary_json_payload}</script>
<script id="candlestick-json" type="application/json">{candlestick_json_payload}</script>
<script>
const progress=document.getElementById('progress');
const navLinks=Array.from(document.querySelectorAll('#nav a'));
const sectionsForNav=navLinks.map(l=>document.querySelector(l.getAttribute('href'))).filter(Boolean);
function updateProgress(){{const max=document.documentElement.scrollHeight-window.innerHeight;progress.style.width=(max>0?window.scrollY/max*100:0)+'%';}}
const observer=new IntersectionObserver(entries=>{{entries.forEach(entry=>{{if(!entry.isIntersecting)return;navLinks.forEach(link=>link.classList.toggle('active',link.getAttribute('href')==='#'+entry.target.id));}});}},{{rootMargin:'-35% 0px -55% 0px',threshold:.01}});
sectionsForNav.forEach(s=>observer.observe(s));
window.addEventListener('scroll',updateProgress,{{passive:true}});
updateProgress();
const expandAll=document.getElementById('expandAll');
const collapseAll=document.getElementById('collapseAll');
if(expandAll) expandAll.addEventListener('click',()=>document.querySelectorAll('details').forEach(d=>d.open=true));
if(collapseAll) collapseAll.addEventListener('click',()=>document.querySelectorAll('details').forEach(d=>d.open=false));
function base64ToBytes(b64){{const binary=atob(b64);const bytes=new Uint8Array(binary.length);for(let i=0;i<binary.length;i++)bytes[i]=binary.charCodeAt(i);return bytes;}}
function decodeSpec(spec){{const bytes=base64ToBytes(spec.bdata);const view=new DataView(bytes.buffer,bytes.byteOffset,bytes.byteLength);const vals=[];if(spec.dtype==='f8'){{for(let i=0;i<bytes.byteLength;i+=8)vals.push(view.getFloat64(i,true));return vals;}}if(spec.dtype==='f4'){{for(let i=0;i<bytes.byteLength;i+=4)vals.push(view.getFloat32(i,true));return vals;}}if(spec.dtype==='i4'){{for(let i=0;i<bytes.byteLength;i+=4)vals.push(view.getInt32(i,true));return vals;}}return spec;}}
function decodePlotly(v){{if(Array.isArray(v))return v.map(decodePlotly);if(v&&typeof v==='object'){{if(typeof v.bdata==='string'&&typeof v.dtype==='string')return decodeSpec(v);const o={{}};Object.keys(v).forEach(k=>o[k]=decodePlotly(v[k]));return o;}}return v;}}
function compactPlotLayout(layout){{const next=Object.assign({{}},layout||{{}});const compactHeight=window.matchMedia('(max-width:980px)').matches?320:360;next.height=Math.min(Number(next.height)||compactHeight,compactHeight);next.autosize=true;next.margin=Object.assign({{l:48,r:18,t:18,b:42}},next.margin||{{}});return next;}}
function renderPlot(scriptId,targetId,compact=false){{const script=document.getElementById(scriptId);const target=document.getElementById(targetId);if(!window.Plotly||!script||!target)return;const fig=decodePlotly(JSON.parse(script.textContent));const config=Object.assign({{responsive:true,displaylogo:false,scrollZoom:true}},fig.config||{{}});const layout=compact?compactPlotLayout(fig.layout):fig.layout||{{}};Plotly.newPlot(target,fig.data||[],layout,config);}}
renderPlot('equity-json','equity-chart');
renderPlot('drawdown-json','drawdown-chart');
renderPlot('shap-bar-json','shap-bar-chart',true);
renderPlot('shap-summary-json','shap-summary-chart',true);
renderPlot('shap-binary-json','shap-binary-chart',true);
renderPlot('candlestick-json','candlestick-chart');
const modal=document.getElementById('figureModal'),modalImage=document.getElementById('modalImage'),modalTitle=document.getElementById('modalTitle');let zoom=1;
function setZoom(v){{zoom=Math.max(.35,Math.min(5,v));modalImage.style.transform='scale('+zoom+')';}}
function openModal(img){{if(!img)return;modalImage.src=img.src;modalTitle.textContent=img.dataset.title||img.alt||'Figure';setZoom(1);modal.setAttribute('aria-hidden','false');}}
document.querySelectorAll('.zoomable').forEach(img=>img.addEventListener('click',()=>openModal(img)));
document.querySelectorAll('.open-figure').forEach(btn=>btn.addEventListener('click',()=>openModal(btn.closest('.figure-card').querySelector('.zoomable'))));
document.getElementById('zoomIn').addEventListener('click',()=>setZoom(zoom+.25));
document.getElementById('zoomOut').addEventListener('click',()=>setZoom(zoom-.25));
document.getElementById('resetZoom').addEventListener('click',()=>setZoom(1));
document.getElementById('closeModal').addEventListener('click',()=>modal.setAttribute('aria-hidden','true'));
modal.addEventListener('click',e=>{{if(e.target===modal)modal.setAttribute('aria-hidden','true');}});
window.addEventListener('keydown',e=>{{if(e.key==='Escape')modal.setAttribute('aria-hidden','true');}});
</script></body></html>"""

    safe_symbol = str(symbol).replace("/", "_").replace("\\", "_").replace(":", "_")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    archive_file = OUTPUT_DIR / f"ml_model_presentation_{safe_symbol}_{timestamp}.html"

    with open(HTML_FILE, "w", encoding="utf-8") as f:
        f.write(html)
    with open(archive_file, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"HTML latest written to: {HTML_FILE}")
    print(f"HTML archived to: {archive_file}")
    print(f"History: {len(history['runs'])} runs ({', '.join(r['symbol'] for r in history['runs'])})")
    return str(HTML_FILE)
