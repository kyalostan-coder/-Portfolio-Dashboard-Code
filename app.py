import streamlit as st
import yfinance as yf
import quantstats as qs
import pandas as pd
import tempfile
import datetime

# -------------------------------
# 1. Page Configuration
# -------------------------------
st.set_page_config(page_title="NSE Portfolio Analytics", layout="wide")
st.title("🇰🇪 Kenyan Portfolio Analytics Dashboard (NSE)")

# Extend pandas with QuantStats
qs.extend_pandas()

# -------------------------------
# 2. Helper Functions
# -------------------------------
def fetch_data(tickers, start_date, end_date):
    """Fetch price data and handle MultiIndex/Missing value issues."""
    valid_data = {}
    
    for t in tickers:
        try:
            # Download individual ticker data
            df = yf.download(t, start=start_date, end=end_date, progress=False)
            
            if not df.empty:
                # Handle MultiIndex if present, then extract price
                if isinstance(df.columns, pd.MultiIndex):
                    # Flatten columns if yfinance returns multi-level (Price, Ticker)
                    df.columns = df.columns.get_level_values(0)
                
                # Prioritize Adjusted Close for accurate total returns
                col = 'Adj Close' if 'Adj Close' in df.columns else 'Close'
                valid_data[t] = df[col]
            else:
                st.warning(f"No data found for {t} on Yahoo Finance.")
        except Exception as e:
            st.error(f"Error fetching {t}: {e}")

    if not valid_data:
        return None

    # Combine all series into one DataFrame
    combined_df = pd.concat(valid_data.values(), axis=1, keys=valid_data.keys())
    
    # NSE specific fix: fill missing prices (holidays/non-trading days)
    combined_df = combined_df.ffill().dropna()
    return combined_df

def compute_portfolio_returns(data, ticker_weight_map):
    """Compute weighted daily returns for the portfolio."""
    # Ensure we only use weights for tickers that successfully downloaded
    valid_tickers = data.columns
    raw_weights = [ticker_weight_map.get(t, 0) for t in valid_tickers]
    
    # Re-normalize weights to ensure they sum to 1.0
    total_w = sum(raw_weights)
    weights = [w / total_w for w in raw_weights] if total_w > 0 else [1/len(valid_tickers)] * len(valid_tickers)

    # Calculate returns
    returns = data.pct_change().dropna()
    portfolio_returns = (returns * weights).sum(axis=1)
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

default_tickers = "SCOM.KE, EQTY.KE, KCB.KE, EABL.KE, ABSA.KE, COOP.KE"
tickers_in = st.sidebar.text_area("Enter NSE Tickers (comma separated)", value=default_tickers)
tickers = [t.strip() for t in tickers_in.split(",") if t.strip()]

ticker_weight_map = {}
if tickers:
    st.sidebar.subheader("Asset Allocation (%)")
    for t in tickers:
        w = st.sidebar.slider(f"{t}", 0, 100, 100 // len(tickers))
        ticker_weight_map[t] = w / 100

start = st.sidebar.date_input("Analysis Start Date", datetime.date(2019, 1, 1))
end = st.sidebar.date_input("Analysis End Date", datetime.date.today())
bench_sym = st.sidebar.text_input("Benchmark Symbol (e.g., ^NASI or SPY)", "^NASI")

# -------------------------------
# 4. Execution Logic
# -------------------------------
if st.sidebar.button("Generate Kenyan Market Analysis"):
    with st.spinner("Analyzing NSE Market Data..."):
        data = fetch_data(tickers, start, end)
        
        if data is not None and not data.empty:
            returns = compute_portfolio_returns(data, ticker_weight_map)
            
            if not returns.empty:
                display_nse_metrics(returns)
                
                # Visualizations
                st.subheader("Cumulative Returns (Portfolio Growth)")
                cum_ret = (1 + returns).cumprod()
                st.line_chart(cum_ret)
                
                st.subheader("Monthly Returns Heatmap")
                m_ret = qs.stats.monthly_returns(returns)
                st.dataframe(m_ret.style.format("{:.2%}"), use_container_width=True)
                
                # Benchmark Comparison
                if bench_sym:
                    try:
                        b_data = yf.download(bench_sym, start=start, end=end, progress=False)
                        if not b_data.empty:
                            # Handle Benchmark MultiIndex
                            if isinstance(b_data.columns, pd.MultiIndex):
                                b_data.columns = b_data.columns.get_level_values(0)
                            
                            b_col = 'Adj Close' if 'Adj Close' in b_data.columns else 'Close'
                            b_ret = b_data[b_col].pct_change().dropna()
                            
                            st.subheader("QuantStats HTML Report")
                            with tempfile.NamedTemporaryFile(delete=False, suffix=".html") as tmp:
                                qs.reports.html(returns, benchmark=b_ret, output=tmp.name, title="NSE Portfolio Report")
                                with open(tmp.name, "rb") as f:
                                    st.download_button("Download Full Performance Report", f, "NSE_Report.html")
                        else:
                            st.info(f"Benchmark {bench_sym} returned no data. Report generated without benchmark.")
                    except Exception as e:
                        st.warning(f"Benchmark analysis failed: {e}")
            else:
                st.error("Calculated returns were empty. Check if the dates selected are valid trading days.")
        else:
            st.error("No data could be retrieved. Please check your internet connection or ticker symbols.")
