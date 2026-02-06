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
st.set_page_config(page_title="NSE Portfolio Analytics", layout="wide")
st.title("🇰🇪 Kenyan Portfolio Analytics Dashboard (NSE)")

# Extend pandas with QuantStats methods for financial analysis
qs.extend_pandas()

# -------------------------------
# 2. Helper Functions
# -------------------------------
def fetch_data(tickers, start_date, end_date):
    """Fetch adjusted close prices for NSE tickers with fallback logic."""
    valid_data = {}
    for t in tickers:
        try:
            # Using auto_adjust=True to handle NSE-specific adjustments
            df = yf.download(t, start=start_date, end=end_date, auto_adjust=True, progress=False)
            
            if not df.empty:
                # Ensure we capture the price column regardless of naming conventions
                col = 'Close' if 'Close' in df.columns else df.columns[0]
                valid_data[t] = df[col]
            else:
                st.warning(f"No data for {t}. Ensure you use the '.KE' suffix.")
        except Exception as e:
            st.error(f"Error fetching {t}: {e}")

    if not valid_data:
        return None

    return pd.concat(valid_data.values(), axis=1, keys=valid_data.keys())

def compute_portfolio_returns(data, ticker_weight_map):
    """Compute returns based on NSE ticker weights."""
    valid_tickers = list(data.columns)
    
    # Map selected weights to successfully downloaded tickers
    raw_weights = [ticker_weight_map.get(t, 0) for t in valid_tickers]
    
    # Re-normalize weights to 100% (1.0) for the valid subset
    total_w = sum(raw_weights)
    valid_weights = [w / total_w for w in raw_weights] if total_w > 0 else [1/len(valid_tickers)] * len(valid_tickers)

    returns = data.pct_change().dropna()
    if returns.empty:
        return pd.Series(dtype=float)

    # Calculate weighted daily returns
    portfolio_returns = (returns * valid_weights).sum(axis=1)
    return portfolio_returns

def display_nse_metrics(portfolio_returns):
    st.subheader("Key Performance Metrics")
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("Sharpe Ratio", round(qs.stats.sharpe(portfolio_returns), 2))
    with c2:
        st.metric("Max Drawdown", f"{round(qs.stats.max_drawdown(portfolio_returns)*100, 2)}%")
    with c3:
        st.metric("CAGR", f"{round(qs.stats.cagr(portfolio_returns)*100, 2)}%")
    with c4:
        st.metric("Volatility", f"{round(qs.stats.volatility(portfolio_returns)*100, 2)}%")

# -------------------------------
# 3. Sidebar: Portfolio Setup
# -------------------------------
st.sidebar.header("NSE Portfolio Configuration")

# Standard Kenyan Blue-chip Tickers
default_tickers = "SCOM.KE, EQTY.KE, KCB.KE, EABL.KE, ABSA.KE, COOP.KE"
tickers_in = st.sidebar.text_area("Enter NSE Tickers (comma separated)", value=default_tickers)
tickers = [t.strip() for t in tickers_in.split(",") if t.strip()]

ticker_weight_map = {}
if tickers:
    st.sidebar.subheader("Asset Allocation (%)")
    for t in tickers:
        # Default equal weighting
        w = st.sidebar.slider(f"{t}", 0, 100, 100 // len(tickers))
        ticker_weight_map[t] = w / 100

# Date selection and local benchmark
start = st.sidebar.date_input("Analysis Start Date", datetime.date(2019, 1, 1))
end = st.sidebar.date_input("Analysis End Date", datetime.date.today())
bench = st.sidebar.text_input("Benchmark Symbol", "^NASI")

# -------------------------------
# 4. Execution Logic
# -------------------------------
if st.sidebar.button("Generate Kenyan Market Analysis"):
    with st.spinner("Fetching NSE historical data..."):
        data = fetch_data(tickers, start, end)
        
        if data is not None:
            returns = compute_portfolio_returns(data, ticker_weight_map)
            
            if not returns.empty:
                display_nse_metrics(returns)
                
                # Visualizations
                st.subheader("Portfolio Growth vs. Time")
                cum_ret = (1 + returns).cumprod()
                st.line_chart(cum_ret)
                
                st.subheader("Monthly Performance Heatmap")
                m_ret = qs.stats.monthly_returns(returns)
                st.dataframe(m_ret.style.format("{:.2%}"))
                
                # Benchmark Comparison and PDF Report
                if bench:
                    try:
                        b_data = yf.download(bench, start=start, end=end, auto_adjust=True, progress=False)
                        if not b_data.empty:
                            b_ret = b_data.iloc[:, 0].pct_change().dropna()
                            st.subheader("QuantStats Report")
                            with tempfile.NamedTemporaryFile(delete=False, suffix=".html") as tmp:
                                qs.reports.html(returns, benchmark=b_ret, output=tmp.name, title="NSE Portfolio Report")
                                with open(tmp.name, "rb") as f:
                                    st.download_button("Download Full Performance Report", f, "NSE_Report.html")
                    except Exception:
                        st.info("Benchmark comparison (NASI) currently unavailable.")
            else:
                st.error("Could not calculate returns. Ensure your selected date range has active trading days.")
        else:
            st.error("No data retrieved. Verify that symbols use '.KE' and the market was open during your dates.")
