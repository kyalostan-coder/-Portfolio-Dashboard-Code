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

# Extend pandas with QuantStats methods
qs.extend_pandas()

# -------------------------------
# 2. Helper Functions
# -------------------------------
def fetch_data(tickers, start_date, end_date):
    """Fetch adjusted close prices for Kenyan tickers, skip failures."""
    valid_data = {}
    for t in tickers:
        try:
            # yfinance often returns a MultiIndex; we select 'Close' then the ticker
            df = yf.download(t, start=start_date, end=end_date, progress=False)
            if not df.empty and 'Close' in df.columns:
                valid_data[t] = df['Close']
            else:
                st.warning(f"No data found for {t}. Check the ticker suffix (e.g., .KE).")
        except Exception as e:
            st.warning(f"Ticker {t} failed: {e}")

    if not valid_data:
        return None

    # Align all series into a single DataFrame
    return pd.concat(valid_data.values(), axis=1, keys=valid_data.keys())

def compute_portfolio_returns(data, ticker_weight_map):
    """Compute portfolio returns with weights realigned to available tickers."""
    valid_tickers = list(data.columns)
    
    # Extract weights only for tickers that successfully downloaded
    raw_weights = [ticker_weight_map[t] for t in valid_tickers]
    
    # Re-normalize weights so they sum to 1.0
    total_w = sum(raw_weights)
    valid_weights = [w / total_w for w in raw_weights] if total_w > 0 else [1/len(valid_tickers)] * len(valid_tickers)

    # Calculate daily percent change
    returns = data.pct_change().dropna()
    if returns.empty:
        return pd.Series(dtype=float)

    # Weighted sum of returns
    portfolio_returns = (returns * valid_weights).sum(axis=1)
    return portfolio_returns

def display_metrics(portfolio_returns):
    if portfolio_returns.empty:
        st.error("Portfolio returns are empty. Adjust tickers or date range.")
        return
    st.subheader("Key Performance Metrics")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Sharpe Ratio", round(qs.stats.sharpe(portfolio_returns), 2))
    with col2:
        st.metric("Max Drawdown", f"{round(qs.stats.max_drawdown(portfolio_returns)*100, 2)}%")
    with col3:
        st.metric("CAGR", f"{round(qs.stats.cagr(portfolio_returns)*100, 2)}%")
    with col4:
        st.metric("Volatility", f"{round(qs.stats.volatility(portfolio_returns)*100, 2)}%")

def plot_returns(portfolio_returns):
    if portfolio_returns.empty:
        return
    
    st.subheader("Cumulative Returns Growth")
    cum_returns = (1 + portfolio_returns).cumprod()
    st.plotly_chart(px.line(cum_returns, labels={'value': 'Growth of 1 Unit', 'Date': 'Year'}), use_container_width=True)
    
    st.subheader("Monthly Returns Heatmap")
    m_ret = qs.stats.monthly_returns(portfolio_returns)
    st.dataframe(m_ret.style.format("{:.2%}"))

# -------------------------------
# 3. Sidebar Configurations
# -------------------------------
st.sidebar.header("Portfolio Settings")

# Corrected Kenyan Tickers: Safaricom, Equity, KCB, EABL
default_tickers = "SCOM.KE, EQTY.KE, KCB.KE, EABL.KE"
tickers_input = st.sidebar.text_area("Enter tickers (comma separated)", value=default_tickers)
tickers = [t.strip() for t in tickers_input.split(",") if t.strip()]

weights = []
if tickers:
    st.sidebar.subheader("Assign Weights (%)")
    for t in tickers:
        default_val = 100 // len(tickers)
        w = st.sidebar.slider(f"{t}", 0, 100, default_val)
        weights.append(w)
    
    total_w_in = sum(weights)
    normalized_weights = [w / total_w_in for w in weights] if total_w_in > 0 else [1/len(tickers)] * len(tickers)
    ticker_weight_map = dict(zip(tickers, normalized_weights))

start_date = st.sidebar.date_input("Start Date", datetime.date(2018, 1, 1))
end_date = st.sidebar.date_input("End Date", datetime.date.today())
# Local Kenyan Benchmark: NSE All-Share Index (^NASI)
benchmark_ticker = st.sidebar.text_input("Benchmark (e.g., ^NASI, ^GSPC)", value="^NASI")

# -------------------------------
# 4. Analysis Execution
# -------------------------------
if st.sidebar.button("Generate Analysis"):
    if not tickers:
        st.error("Please enter at least one valid ticker.")
    elif start_date >= end_date:
        st.error("Start date must be before the end date.")
    else:
        with st.spinner("Analyzing market data..."):
            data = fetch_data(tickers, start_date, end_date)
            
            if data is not None:
                valid_tickers_list = list(data.columns)
                
                # Notification for dropped tickers
                if len(valid_tickers_list) < len(tickers):
                    missing = set(tickers) - set(valid_tickers_list)
                    st.warning(f"Data missing for: {', '.join(missing)}. Weights realigned.")

                # Process results
                portfolio_returns = compute_portfolio_returns(data, ticker_weight_map)
                display_metrics(portfolio_returns)
                plot_returns(portfolio_returns)

                # Benchmark comparison
                if benchmark_ticker:
                    try:
                        b_data = yf.download(benchmark_ticker, start=start_date, end=end_date, progress=False)
                        if not b_data.empty and 'Close' in b_data.columns:
                            benchmark_returns = b_data['Close'].pct_change().dropna()
                            st.subheader("Benchmark Comparison")
                            # QuantStats report download
                            with tempfile.NamedTemporaryFile(delete=False, suffix=".html") as tmp:
                                qs.reports.html(portfolio_returns, benchmark=benchmark_returns, output=tmp.name, title="NSE Portfolio Report")
                                with open(tmp.name, "rb") as f:
                                    st.download_button("Download Full Performance Report", f, "NSE_Report.html", "text/html")
                    except Exception as e:
                        st.info(f"Could not load benchmark {benchmark_ticker}. Skipping comparison.")
            else:
                st.error("No data found. Ensure tickers use '.KE' and the date range is valid.")
