import streamlit as st
import yfinance as yf
import quantstats as qs
import pandas as pd
import plotly.express as px
import tempfile
import os

# 1. Page Configuration [4, 5]
st.set_page_config(page_title="Portfolio Analytics Dashboard", layout="wide")
st.title("Portfolio Analytics Dashboard using QuantStats")

# 2. Sidebar Configurations [6]
st.sidebar.header("Portfolio Configurations")

# Ticker Input [7, 8]
# The video suggests starting with a predefined list of tickers (e.g., NSE tickers)
tickers_list = ['TCS.NS', 'ICICIBANK.NS', 'ITC.NS', 'INFY.NS', 'HDFC.NS'] # Example list based on video
tickers = st.sidebar.multiselect(
    "Select Stocks", 
    options=tickers_list, 
    default=['TCS.NS', 'ICICIBANK.NS', 'ITC.NS']
)

# Weight Assignment Logic [9-11]
weights = []
if tickers:
    st.sidebar.subheader("Assign Portfolio Weights")
    for t in tickers:
        # Loop to create a slider for each ticker
        # Default value is 1 divided by the number of tickers (equal weight)
        default_value = int(100 / len(tickers))
        w = st.sidebar.slider(f"Weight for {t} (%)", min_value=0, max_value=100, value=default_value, step=1)
        weights.append(w)
    
    # Normalization logic described in the video to ensure sum is 1 (100%)
    total_weight = sum(weights)
    if total_weight > 0:
        normalized_weights = [w / total_weight for w in weights]
    else:
        normalized_weights = [1 / len(tickers) for _ in tickers] # Fallback to equal weights

# Date Inputs [12]
start_date = st.sidebar.date_input("Start Date")
end_date = st.sidebar.date_input("End Date")

# 3. Analysis Execution [13, 14]
if st.sidebar.button("Generate Analysis"):
    # Error Handling [15]
    if not tickers:
        st.error("Please select at least one stock.")
    else:
        with st.spinner("Fetching data and computing analytics..."): # [16]
            
            # 4. Data Fetching & Calculation [16, 17]
            # Fetching 'Close' price and calculating percentage change
            data = yf.download(tickers, start=start_date, end=end_date)['Close']
            returns = data.pct_change().dropna()
            
            # Calculate Portfolio Returns: returns * weights
            # The video specifies using dot product or multiplication with sum along axis 1
            portfolio_returns = (returns * normalized_weights).sum(axis=1)
            
            # Extend pandas with QuantStats features [18]
            qs.extend_pandas()

            # 5. Key Metrics Output [18, 19]
            st.subheader("Key Metrics")
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                # Sharpe Ratio
                sharpe = qs.stats.sharpe(portfolio_returns)
                st.metric("Sharpe Ratio", round(sharpe, 2))
            
            with col2:
                # Max Drawdown
                mdd = qs.stats.max_drawdown(portfolio_returns) * 100
                st.metric("Max Drawdown", f"{round(mdd, 2)}%")
            
            with col3:
                # CAGR
                cagr = qs.stats.cagr(portfolio_returns) * 100
                st.metric("CAGR", f"{round(cagr, 2)}%")
                
            with col4:
                # Volatility
                vol = qs.stats.volatility(portfolio_returns) * 100
                st.metric("Volatility", f"{round(vol, 2)}%")

            # 6. Visualizations
            
            # Pie Chart for Weights [20, 21]
            st.subheader("Portfolio Weights")
            # Creating a dataframe for the pie chart
            pie_data = pd.DataFrame({'Ticker': tickers, 'Weight': normalized_weights})
            fig_pie = px.pie(pie_data, values='Weight', names='Ticker', title='Portfolio Allocation')
            st.plotly_chart(fig_pie, use_container_width=True)

            # Monthly Returns Heatmap [22]
            st.subheader("Monthly Returns Heatmap")
            # The transcript mentions using styling to format percentages
            # Note: exact qs heatmap implementation might vary, but st.dataframe is used
            st.write("Monthly returns table generated via QuantStats:")
            st.dataframe(qs.stats.monthly_returns(portfolio_returns).style.format("{:.2%}"))

            # Cumulative Returns Plot [23, 24]
            st.subheader("Cumulative Returns")
            # Formula: (1 + portfolio_returns).cumprod()
            cum_returns = (1 + portfolio_returns).cumprod()
            st.line_chart(cum_returns)

            # End of Year Returns [24]
            st.subheader("End of Year Returns")
            # Resampling to annual ('A') and applying summation/compounding logic
            # Simplest approximation based on video description:
            eoy_returns = portfolio_returns.resample('YE').apply(qs.stats.comp) * 100
            st.bar_chart(eoy_returns)

            # 7. Report Generation [25-27]
            st.subheader("Download Report")
            
            # Using tempfile to handle the HTML report generation
            with tempfile.NamedTemporaryFile(delete=False, suffix=".html") as tmp_file:
                qs.reports.html(portfolio_returns, output=tmp_file.name, title="Portfolio Performance Report")
                
                with open(tmp_file.name, "rb") as file:
                    st.download_button(
                        label="Download Full QuantStats Report",
                        data=file,
                        file_name="portfolio_report.html",
                        mime="text/html"
                    )
