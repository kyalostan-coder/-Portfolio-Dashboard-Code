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

qs.extend_pandas()

# -------------------------------
# 2. Helper Functions
# -------------------------------
def fetch_data(tickers, start_date, end_date):
    """Fetch adjusted close prices for tickers, skip failures."""
    valid_data = {}
    for t in tickers:
        try:
            df = yf.download(t, start=start_date, end=end_date)['Close']
            if not df.empty:
                valid_data[t] = df
            else:
                st.warning(f"No data for {t}. Skipped.")
        except Exception as e:
            st.warning(f"Ticker {t} failed: {e}")
    if not valid_data:
        return None
    return pd.DataFrame(valid_data)

def compute_portfolio_returns(data, weights):
    """Compute portfolio returns given price data and normalized weights."""
    returns = data.pct_change().dropna()
    if returns.empty:
        return pd.Series(dtype=float)
    portfolio_returns = (returns * weights).sum(axis=1)
    return portfolio_returns

def display_metrics(portfolio_returns):
    """Show key portfolio metrics safely."""
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
    st.subheader("Portfolio Weights")
    pie_data = pd.DataFrame({'Ticker': tickers, 'Weight': weights})
    fig_pie = px.pie(pie_data, values='Weight', names='Ticker', title='Portfolio Allocation')
    st.plotly_chart(fig_pie, use_container_width=True)

def plot_returns(portfolio_returns):
    if portfolio_returns.empty:
        return
    st.subheader("Monthly Returns Heatmap")
    st.dataframe(qs.stats.monthly_returns(portfolio_returns).style.format("{:.2%}"))
    st.subheader("Cumulative Returns")
    cum_returns = (1 + portfolio_returns).cumprod()
    st.plotly_chart(px.line(cum_returns, title="Cumulative Returns"), use_container_width=True)
    st.subheader("End of Year Returns")
    eoy_returns = qs.stats.yearly_returns(portfolio_returns) * 100
    st.bar_chart(eoy_returns.T)

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

tickers_input = st.sidebar.text_area("Enter tickers (comma separated)", value="AAPL, MSFT, TSLA, ^GSPC")
tickers = [t.strip() for t in tickers_input.split(",") if t.strip()]

weights = []
if tickers:
    st.sidebar.subheader("Assign Portfolio Weights")
    for t in tickers:
        default_value = int(100 / len(tickers))
        w = st.sidebar.slider(f"Weight for {t} (%)", 0, 100, default_value, 1)
        weights.append(w)
    total_weight = sum(weights)
    normalized_weights = [w / total_weight for w in weights] if total_weight > 0 else [1 / len(tickers)] * len(tickers)

start_date = st.sidebar.date_input("Start Date", datetime.date(2015, 1, 1))
end_date = st.sidebar.date_input("End Date", datetime.date.today())
benchmark_ticker = st.sidebar.text_input("Benchmark Ticker", value="^GSPC")

# -------------------------------
# 4. Analysis Execution
# -------------------------------
if st.sidebar.button("Generate Analysis"):
    if not tickers:
        st.error("Please enter at least one ticker.")
    else:
        with st.spinner("Fetching data and computing analytics..."):
            data = fetch_data(tickers, start_date, end_date)
            if data is not None:
                portfolio_returns = compute_portfolio_returns(data, normalized_weights)
                display_metrics(portfolio_returns)
                plot_weights(tickers, normalized_weights)
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
