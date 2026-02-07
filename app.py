import streamlit as st
import pandas as pd
import requests
import datetime
import quantstats as qs
import tempfile
import os

# --- 1. CONFIGURATION ---
# Key from your RapidAPI dashboard screenshot
RAPID_API_KEY = "a538064f41mshc71e1793ca5fdf0p17493ajsn7f58ff8e39b7"
RAPID_API_HOST = "yh-finance.p.rapidapi.com"

# --- 2. DATA FETCHING ---
def fetch_historical_data(ticker, start_date, end_date):
    """Fetches and parses historical data from YH Finance API."""
    url = f"https://{RAPID_API_HOST}/stock/v3/get-historical-data"
    
    # Convert dates to Unix timestamps (required by this API)
    p1 = int(datetime.datetime.combine(start_date, datetime.time()).timestamp())
    p2 = int(datetime.datetime.combine(end_date, datetime.time()).timestamp())
    
    querystring = {"symbol": ticker, "region": "US"}
    headers = {
        "x-rapidapi-key": RAPID_API_KEY,
        "x-rapidapi-host": RAPID_API_HOST
    }

    try:
        response = requests.get(url, headers=headers, params=querystring, timeout=15)
        
        # Check for HTTP errors before parsing
        if response.status_code != 200:
            st.error(f"API Error {response.status_code} for {ticker}: {response.text}")
            return None
        
        # Verify response isn't empty to avoid "line 1 column 1" error
        if not response.content:
            st.error(f"Empty response received for {ticker}")
            return None
            
        json_data = response.json()
        
        # Access the nested 'prices' key in the YH Finance response structure
        prices_list = json_data.get('prices', [])
        if not prices_list:
            st.warning(f"No price data found in response for {ticker}")
            return None
            
        df = pd.DataFrame(prices_list)
        
        # Convert timestamps and clean data
        df['date'] = pd.to_datetime(df['date'], unit='s')
        df = df.set_index('date').sort_index()
        
        # Select adjusted close for accurate total returns
        if 'adjclose' in df.columns:
            series = df['adjclose']
        else:
            series = df['close']
            
        # Filter for requested range
        mask = (series.index >= pd.Timestamp(start_date)) & (series.index <= pd.Timestamp(end_date))
        return series.loc[mask]

    except requests.exceptions.JSONDecodeError:
        st.error(f"Failed to parse JSON for {ticker}. Check your API subscription/quota.")
        return None
    except Exception as e:
        st.error(f"Unexpected error with {ticker}: {e}")
        return None

# --- 3. UI SETUP ---
st.set_page_config(page_title="NSE Portfolio Analytics", layout="wide")
st.title("🇰🇪 Kenyan Portfolio Analytics (RapidAPI)")

with st.sidebar:
    st.header("Portfolio Configuration")
    tickers_input = st.text_area("NSE Tickers (comma separated)", "SCOM.KE, EQTY.KE, KCB.KE")
    tickers = [t.strip() for t in tickers_input.split(",") if t.strip()]
    
    start_dt = st.date_input("Analysis Start", datetime.date(2023, 1, 1))
    end_dt = st.date_input("Analysis End", datetime.date.today())
    
    run_btn = st.button("Generate Kenyan Market Analysis")

# --- 4. EXECUTION ---
if run_btn:
    with st.spinner("Accessing financial databases..."):
        all_series = {}
        for t in tickers:
            data = fetch_historical_data(t, start_dt, end_dt)
            if data is not None:
                all_series[t] = data
        
        if all_series:
            # Combine into DataFrame and handle missing trading days
            combined_df = pd.concat(all_series.values(), axis=1, keys=all_series.keys())
            combined_df = combined_df.ffill().dropna()
            
            # Compute portfolio returns (Equal Weighted)
            returns = combined_df.pct_change().mean(axis=1).dropna()
            
            # --- Visualizations ---
            col1, col2 = st.columns(2)
            with col1:
                st.subheader("Performance Metrics")
                st.metric("Total Period Return", f"{round((returns.add(1).prod() - 1) * 100, 2)}%")
                st.metric("Daily Volatility", f"{round(returns.std() * 100, 2)}%")
            
            with col2:
                st.subheader("Cumulative Growth")
                st.line_chart((1 + returns).cumprod())
            
            # --- Heatmap ---
            st.subheader("Monthly Performance Heatmap")
            qs.extend_pandas()
            monthly_ret = qs.stats.monthly_returns(returns)
            st.dataframe(monthly_ret.style.format("{:.2%}"), use_container_width=True)
            
            # --- QuantStats HTML Report ---
            st.subheader("Download Detailed Report")
            with tempfile.NamedTemporaryFile(delete=False, suffix=".html") as tmp:
                qs.reports.html(returns, output=tmp.name, title="NSE Portfolio Analytics Report")
                with open(tmp.name, "rb") as f:
                    st.download_button("Download Full HTML Report", f, "NSE_Report.html")
        else:
            st.error("No valid data retrieved. Verify ticker symbols and API key.")
