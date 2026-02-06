import streamlit as st
import yfinance as yf
import quantstats as qs
import pandas as pd
import plotly.express as px
import os
import tempfile
import datetime

# -------------------------------
# 1. Page Configuration
# -------------------------------
st.set_page_config(page_title="Kenyan Portfolio Analytics Dashboard", layout="wide")
st.title("🌍 Kenyan Portfolio Analytics Dashboard")

qs.extend_pandas()

# -------------------------------
# 2. Helper Functions
# -------------------------------
def fetch_data(tickers, start_date, end_date):
    """Fetch data with fallback logic for Kenyan tickers."""
    valid_data = {}
    for t in tickers:
        try:
            # We use auto_adjust=True to handle split/dividend adjustments automatically
            df = yf.download(t, start=start_date, end=end_date, auto_adjust=True, progress=False)
            
            if not df.empty:
                # In newer yfinance versions, df might have a MultiIndex if one ticker is passed
                # We extract the 'Close' column safely
                if 'Close' in df.columns:
                    valid_data[t] = df['Close']
                else:
                    # Fallback to the first available column if 'Close' isn't named explicitly
                    valid_data[t] = df.iloc[:, 0]
            else:
                st.warning(f"No data for {t}. Trying alternative suffix...")
                # Attempt fallback to .NR if .KE was used (or vice versa)
                alt_t = t.replace(".KE", ".NR") if ".KE" in t else t.replace(".NR", ".KE")
                df_alt = yf.download(alt_t, start=start_date, end=end_date, auto_adjust=True, progress=False)
                if not df_alt.empty:
                    col = 'Close' if 'Close' in df_alt.columns else df_alt.columns[0]
                    valid_data[alt_t] = df_alt[col]
                    st.success(f"Found data using {alt_t}")

        except Exception as e:
            st.error(f"Error fetching {t}: {e}")

    if not valid_data:
        return None

    return pd.concat(valid_data.values(), axis=1, keys=valid_data.keys())

def compute_portfolio_returns(data, ticker_weight_map):
    """Compute returns and handle re-normalization if some tickers failed."""
    valid_tickers = list(data.columns)
    
    # Map weights to the tickers that actually returned data
    # We use .get() to handle cases where the ticker name might have changed (e.g., KE to NR)
    raw_weights = []
    for t in valid_tickers:
        weight = ticker_weight_map.get(t)
        if weight is None:
            # Fallback for alternative suffix matching
            base = t.split('.')[0]
            weight = next((v for k, v in ticker_weight_map.items() if k.startswith(base)), 0)
        raw_weights.append(weight)
    
    total_w = sum(raw_weights)
    valid_weights = [w / total_w for w in raw_weights] if total_w > 0 else [1/len(valid_tickers)] * len(valid_tickers)

    returns = data.pct_change().dropna()
    if returns.empty:
        return pd.Series(dtype=float)

    portfolio_returns = (returns * valid_weights).sum(axis=1)
    return portfolio_returns

def display_metrics(portfolio_returns):
    if portfolio_returns.empty:
        st.error("Calculated returns are empty.")
        return
    st.subheader("Performance Summary")
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("Sharpe Ratio", round(qs.stats.sharpe(portfolio_returns), 2))
    with c2:
        st.metric("Max Drawdown", f"{round(qs.stats.max_drawdown(portfolio_returns)*100, 2)}%")
    with c3:
        st.metric("CAGR", f"{round(qs.stats.cagr(portfolio_returns)*100, 2)}%")
    with c4:
        st.metric("Volatility", f"{round(qs.stats.volatility(portfolio_returns)*100, 2)}%")

def plot_results(portfolio_returns):
    st.subheader("Growth of Investment (Cumulative)")
    cum_ret = (1 + portfolio_returns).cumprod()
    st.line_chart(cum_ret)
    
    st.subheader("Monthly Returns")
    m_ret = qs.stats.monthly_returns(portfolio_returns)
    st.dataframe(m_ret.style.format("{:.2%}"))

# -------------------------------
# 3. Sidebar
# -------------------------------
st.sidebar.header("Configuration")
tickers_in = st.sidebar.text_area("Tickers", value="SCOM.KE, EQTY.KE, KCB.KE, EABL.KE")
tickers = [t.strip() for t in tickers_in.split(",") if t.strip()]

ticker_weight_map = {}
if tickers:
    st.sidebar.subheader("Weights (%)")
    for t in tickers:
        w = st.sidebar.slider(f"Weight: {t}", 0, 100, 25)
        ticker_weight_map[t] = w / 100

start = st.sidebar.date_input("Start", datetime.date(2020, 1, 1))
end = st.sidebar.date_input("End", datetime.date.today())
bench = st.sidebar.text_input("Benchmark", "^NASI")

# -------------------------------
# 4. Execution
# -------------------------------
if st.sidebar.button("Generate Analysis"):
    with st.spinner("Accessing Financial Data..."):
        data = fetch_data(tickers, start, end)
        
        if data is not None:
            returns = compute_portfolio_returns(data, ticker_weight_map)
            
            if not returns.empty:
                display_metrics(returns)
                plot_results(returns)
                
                # Report Generation
                if bench:
                    try:
                        b_data = yf.download(bench, start=start, end=end, auto_adjust=True, progress=False)
                        if not b_data.empty:
                            b_ret = b_data.iloc[:, 0].pct_change().dropna()
                            with tempfile.NamedTemporaryFile(delete=False, suffix=".html") as tmp:
                                qs.reports.html(returns, benchmark=b_ret, output=tmp.name, title="NSE Report")
                                with open(tmp.name, "rb") as f:
                                    st.download_button("Download Full PDF/HTML Report", f, "Report.html")
                    except:
                        st.info("Benchmark report skipped (no benchmark data).")
            else:
                st.error("Insufficient data points to calculate returns. Try a wider date range.")
        else:
            st.error("Failed to retrieve any data. Please check your internet connection or ticker symbols.")
