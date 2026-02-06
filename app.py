import streamlit as st
import yfinance as yf
import quantstats as qs
import pandas as pd
import plotly.express as px
import os
import tempfile

# -------------------------------
# 1. Page Configuration
# -------------------------------
st.set_page_config(page_title="Portfolio Analytics Dashboard", layout="wide")
st.title("Portfolio Analytics Dashboard using QuantStats")

qs.extend_pandas()  # extend pandas once globally

# -------------------------------
# 2. Helper Functions
# -------------------------------
def fetch_data(tickers, start_date, end_date):
    """Fetch adjusted close prices for tickers."""
    try:
        data = yf.download(tickers, start=start_date, end=end_date)['Close']
        if data.empty:
            st.error("No data fetched. Check tickers or date range.")
            return None
        return data
    except Exception as e:
        st.error(f"Data fetch failed: {e}")
        return None

def compute_portfolio_returns(data, weights):
    """Compute portfolio returns given price data and normalized weights."""
    returns = data.pct_change().dropna()
    portfolio_returns = (returns * weights).sum(axis=1)
    return portfolio_returns

def display_metrics(portfolio_returns):
    """Show key portfolio metrics."""
    st.subheader("Key Metrics")
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        sharpe = qs.stats.sharpe(portfolio_returns)
        st.metric("Sharpe Ratio", round(sharpe, 2))

    with col2:
        mdd = qs.stats.max_drawdown(portfolio_returns) * 100
        st.metric("Max Drawdown", f"{round(mdd, 2)}%")

    with col3:
        cagr = qs.stats.cagr(portfolio_returns) * 100
        st.metric("CAGR", f"{round(cagr, 2)}%")

    with col4:
        vol = qs.stats.volatility(portfolio_returns) * 100
        st.metric("Volatility", f"{round(vol, 2)}%")

def plot_weights(tickers, weights):
    """Pie chart of portfolio weights."""
    st.subheader("Portfolio Weights")
    pie_data = pd.DataFrame({'Ticker': tickers, 'Weight': weights})
    fig_pie = px.pie(pie_data, values='Weight', names='Ticker', title='Portfolio Allocation')
    st.plotly_chart(fig_pie, use_container_width=True)

def plot_returns(portfolio_returns):
    """Visualizations for returns."""
    # Monthly Returns Heatmap
    st.subheader("Monthly Returns Heatmap")
    st.dataframe(qs.stats.monthly_returns(portfolio_returns).style.format("{:.2%}"))

    # Cumulative Returns
    st.subheader("Cumulative Returns")
    cum_returns = (1 + portfolio_returns).cumprod()
    fig_cum = px.line(cum_returns, title="Cumulative Returns")
    st.plotly_chart(fig_cum, use_container_width=True)

    # End of Year Returns
    st.subheader("End of Year Returns")
    eoy_returns = qs.stats.yearly_returns(portfolio_returns) * 100
    st.bar_chart(eoy_returns)

def generate_report(portfolio_returns, benchmark=None):
    """Generate downloadable QuantStats HTML report."""
    st.subheader("Download Report")
    with tempfile.NamedTemporaryFile(delete=False, suffix=".html") as tmp_file:
        qs.reports.html(portfolio_returns, benchmark=benchmark, output=tmp_file.name, title="Portfolio Performance Report")
        with open(tmp_file.name, "rb") as file:
            st.download_button(
                label="Download Full QuantStats Report",
                data=file,
                file_name="portfolio_report.html",
                mime="text/html"
            )
    os.remove(tmp_file.name)

# -------------------------------
# 3. Sidebar Configurations
# -------------------------------
st.sidebar.header("Portfolio Configurations")

tickers_list = ['TCS.NS', 'ICICIBANK.NS', 'ITC.NS', 'INFY.NS', 'HDFC.NS']
tickers = st.sidebar.multiselect("Select Stocks", options=tickers_list, default=['TCS.NS', 'ICICIBANK.NS', 'ITC.NS'])

weights = []
if tickers:
    st.sidebar.subheader("Assign Portfolio Weights")
    for t in tickers:
        default_value = int(100 / len(tickers))
        w = st.sidebar.slider(f"Weight for {t} (%)", min_value=0, max_value=100, value=default_value, step=1)
        weights.append(w)

    total_weight = sum(weights)
    normalized_weights = [w / total_weight for w in weights] if total_weight > 0 else [1 / len(tickers)] * len(tickers)

start_date = st.sidebar.date_input("Start Date", pd.to_datetime("2018-01-01"))
end_date = st.sidebar.date_input("End Date", pd.to_datetime("today"))

# -------------------------------
# 4. Analysis Execution
# -------------------------------
if st.sidebar.button("Generate Analysis"):
    if not tickers:
        st.error("Please select at least one stock.")
    else:
        with st.spinner("Fetching data and computing analytics..."):
            data = fetch_data(tickers, start_date, end_date)
            if data is not None:
                portfolio_returns = compute_portfolio_returns(data, normalized_weights)
                display_metrics(portfolio_returns)
                plot_weights(tickers, normalized_weights)
                plot_returns(portfolio_returns)

                # Optional: add benchmark comparison
                benchmark = yf.download("^NSEI", start=start_date, end=end_date)['Close'].pct_change().dropna()
                generate_report(portfolio_returns, benchmark=benchmark)
