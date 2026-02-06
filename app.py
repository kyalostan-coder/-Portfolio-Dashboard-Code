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
st.set_page_config(page_title="Global Portfolio Analytics Dashboard", layout="wide")
st.title("🌍 Portfolio Analytics Dashboard using QuantStats")

# Extend pandas with QuantStats methods
qs.extend_pandas()

# -------------------------------
# 2. Helper Functions
# -------------------------------
def fetch_data(tickers, start_date, end_date):
    """Fetch adjusted close prices for tickers, skip failures."""
    valid_data = {}
    for t in tickers:
        try:
            # Fetching 'Close' prices
            df = yf.download(t, start=start_date, end=end_date)['Close']
            if not df.empty:
                # Ensure we handle cases where yf returns a MultiIndex or Series
                if isinstance(df, pd.DataFrame):
                    valid_data[t] = df.iloc[:, 0]
                else:
                    valid_data[t] = df
            else:
                st.warning(f"No data found for {t} in the selected range.")
        except Exception as e:
            st.warning(f"Ticker {t} failed: {e}")

    if not valid_data:
        return None

    # Align all Series into a single DataFrame
    return pd.concat(valid_data.values(), axis=1, keys=valid_data.keys())

def compute_portfolio_returns(data, ticker_weight_map):
    """Compute portfolio returns with weights realigned to available tickers."""
    valid_tickers = list(data.columns)
    
    # Extract weights only for tickers that successfully downloaded
    raw_weights = [ticker_weight_map[t] for t in valid_tickers]
    
    # Re-normalize weights to sum to 1.0 (in case some tickers were dropped)
    total_w = sum(raw_weights)
    valid_weights = [w / total_w for w in raw_weights] if total_w > 0 else [1/len(valid_tickers)] * len(valid_tickers)

    # Calculate daily returns
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
    st.subheader("Key Metrics")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Sharpe Ratio", round(qs.stats.sharpe(portfolio_returns), 2))
    with col2:
        st.metric("Max Drawdown", f"{round(qs.stats.max_drawdown(portfolio_returns)*100, 2)}%")
    with col3:
        st.metric("CAGR", f"{round(qs.stats.cagr(portfolio_returns)*100, 2)}%")
    with col4:
        st.metric("Volatility", f"{round(qs.stats.volatility(portfolio_returns)*100, 2)}%")

def plot_weights(tickers, weights):
    st.subheader("Portfolio Weights (Realigned)")
    pie_data = pd.DataFrame({'Ticker': tickers, 'Weight': weights})
    fig_pie = px.pie(pie_data, values='Weight', names='Ticker', title='Final Portfolio Allocation')
    st.plotly_chart(fig_pie, use_container_width=True)

def plot_returns(portfolio_returns):
    if portfolio_returns.empty:
        return
    st.subheader("Monthly Returns Heatmap")
    # QuantStats monthly returns returns a DF
    m_ret = qs.stats.monthly_returns(portfolio_returns)
    st.dataframe(m_ret.style.format("{:.2%}"))
    
    st.subheader("Cumulative Returns")
    cum_returns = (1 + portfolio_returns).cumprod()
    st.plotly_chart(px.line(cum_returns, title="Cumulative Returns Growth"), use_container_width=True)
    
    st.subheader("End of Year Returns")
    eoy_returns = qs.stats.yearly_returns(portfolio_returns) * 100
    st.bar_chart(eoy_returns)

def generate_report(portfolio_returns, benchmark=None):
    if portfolio_returns.empty:
        return
    st.subheader("Download Report")
    with tempfile.NamedTemporaryFile(delete=False, suffix=".html") as tmp_file:
        qs.reports.html(portfolio_returns, benchmark=benchmark, output=tmp_file.name, title="Portfolio Performance Report")
        with open(tmp_file.name, "rb") as file:
            st.download_button("Download Full QuantStats Report", file, "portfolio_report.html", "text/html")
    try:
        os.remove(tmp_file.name)
    except:
        pass

# -------------------------------
# 3. Sidebar Configurations
# -------------------------------
st.sidebar.header("Portfolio Configurations")

# Default input
tickers_input = st.sidebar.text_area("Enter tickers (comma separated)", value="SCOM.NR, EQTY.NR, KCB.NR, EABL.NR")
tickers = [t.strip() for t in tickers_input.split(",") if t.strip()]

weights = []
if tickers:
    st.sidebar.subheader("Assign Portfolio Weights")
    for t in tickers:
        default_val = 100 // len(tickers)
        w = st.sidebar.slider(f"Weight for {t} (%)", 0, 100, default_val, 1)
        weights.append(w)
    
    total_weight_input = sum(weights)
    # Create normalized weights (sum to 1.0)
    normalized_weights = [w / total_weight_input for w in weights] if total_weight_input > 0 else [1/len(tickers)] * len(tickers)
    
    # Create the mapping for robustness
    ticker_weight_map = dict(zip(tickers, normalized_weights))

start_date = st.sidebar.date_input("Start Date", datetime.date(2015, 1, 1))
end_date = st.sidebar.date_input("End Date", datetime.date.today())
benchmark_ticker = st.sidebar.text_input("Benchmark Ticker", value="^GSPC")

# -------------------------------
# 4. Analysis Execution
# -------------------------------
if st.sidebar.button("Generate Analysis"):
    if not tickers:
        st.error("Please enter at least one ticker.")
    elif start_date >= end_date:
        st.error("Start Date must be before End Date.")
    else:
        with st.spinner("Fetching data and computing analytics..."):
            data = fetch_data(tickers, start_date, end_date)
            
            if data is not None:
                # Identify which tickers actually made it into the data
                valid_tickers_list = list(data.columns)
                
                if len(valid_tickers_list) < len(tickers):
                    missing = set(tickers) - set(valid_tickers_list)
                    st.warning(f"Skipped tickers with no data: {', '.join(missing)}. Weights have been realigned.")

                # Compute Returns
                portfolio_returns = compute_portfolio_returns(data, ticker_weight_map)
                
                # Display Results
                display_metrics(portfolio_returns)
                
                # Plot dynamic weights (re-normalized)
                current_weights = [ticker_weight_map[t] for t in valid_tickers_list]
                total_curr = sum(current_weights)
                final_weights = [cw/total_curr for cw in current_weights]
                plot_weights(valid_tickers_list, final_weights)
                
                plot_returns(portfolio_returns)

                # Benchmark handling
                benchmark = None
                if benchmark_ticker:
                    try:
                        bench_data = yf.download(benchmark_ticker, start=start_date, end=end_date)['Close']
                        if not bench_data.empty:
                            benchmark = bench_data.pct_change().dropna()
                    except Exception as e:
                        st.warning(f"Benchmark {benchmark_ticker} failed: {e}")

                generate_report(portfolio_returns, benchmark=benchmark)
            else:
                st.error("No data could be retrieved for any of the tickers. Please check the symbols.")
