import streamlit as st
import pandas as pd
import requests
import datetime
import quantstats as qs
import tempfile

# 1. Configuration from your screenshot
# Note: I've used the key visible in your provided image.
RAPID_API_KEY = "a538064f41mshc71e1793ca5fdf0p17493ajsn7f58ff8e39b7" 
RAPID_API_HOST = "yh-finance.p.rapidapi.com"

def fetch_data_rapidapi(ticker, start_date, end_date):
    """Fetches historical data using the YH Finance RapidAPI."""
    url = f"https://{RAPID_API_HOST}/stock/v3/get-historical-data"
    
    # RapidAPI requires Unix Timestamps
    p1 = int(datetime.datetime.combine(start_date, datetime.time()).timestamp())
    p2 = int(datetime.datetime.combine(end_date, datetime.time()).timestamp())
    
    querystring = {"symbol": ticker, "region": "US"} # 'US' region works for KE tickers
    headers = {
        "X-RapidAPI-Key": RAPID_API_KEY,
        "X-RapidAPI-Host": RAPID_API_HOST
    }

    try:
        response = requests.get(url, headers=headers, params=querystring)
        data = response.json()
        
        # Parse the 'prices' list from the JSON response
        prices = data.get('prices', [])
        if not prices:
            return None
        
        df = pd.DataFrame(prices)
        df['date'] = pd.to_datetime(df['date'], unit='s')
        df = df.set_index('date').sort_index()
        
        # Filter for your specific dates and return Adjusted Close
        mask = (df.index >= pd.Timestamp(start_date)) & (df.index <= pd.Timestamp(end_date))
        return df.loc[mask, 'adjclose']
        
    except Exception as e:
        st.error(f"Error fetching {ticker}: {e}")
        return None

# --- Main Dashboard Logic ---
st.title("🇰🇪 Reliable NSE Analytics (via RapidAPI)")

st.sidebar.header("Settings")
tickers_str = st.sidebar.text_area("NSE Tickers", "SCOM.KE, EQTY.KE, KCB.KE")
tickers = [t.strip() for t in tickers_str.split(",") if t.strip()]

start = st.sidebar.date_input("Start Date", datetime.date(2023, 1, 1))
end = st.sidebar.date_input("End Date", datetime.date.today())

if st.sidebar.button("Run Market Analysis"):
    with st.spinner("Fetching data from RapidAPI..."):
        portfolio_series = {}
        for t in tickers:
            series = fetch_data_rapidapi(t, start, end)
            if series is not None:
                portfolio_series[t] = series
        
        if portfolio_series:
            df = pd.concat(portfolio_series.values(), axis=1, keys=portfolio_series.keys())
            df = df.ffill().dropna()
            
            # Calculate returns (Equal Weighted)
            returns = df.pct_change().mean(axis=1).dropna()
            
            # Metrics
            st.metric("Total Return", f"{round(returns.add(1).prod() - 1, 2)*100}%")
            st.line_chart((1 + returns).cumprod())
            
            # QuantStats Report
            with tempfile.NamedTemporaryFile(delete=False, suffix=".html") as tmp:
                qs.extend_pandas()
                qs.reports.html(returns, output=tmp.name, title="NSE Performance Report")
                with open(tmp.name, "rb") as f:
                    st.download_button("Download Full Report", f, "NSE_Report.html")
        else:
            st.error("Could not retrieve any data. Check your API quota or ticker symbols.")
