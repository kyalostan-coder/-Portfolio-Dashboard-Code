import streamlit as st
import yfinance as yf
import pandas as pd
import matplotlib.pyplot as plt
import datetime

# -------------------------------
# 1. Page Configuration
# -------------------------------
st.set_page_config(page_title="NSE Stock Dashboard", layout="wide")
st.title("🇰🇪 Kenyan Market Stock Dashboard")

# -------------------------------
# 2. Sidebar Inputs
# -------------------------------
st.sidebar.header("Stock Dashboard Settings")
# For Kenyan stocks, remind users to add .KE
ticker = st.sidebar.text_input("Enter Stock Ticker (e.g., SCOM.KE, EQTY.KE)", value="SCOM.KE")
start_date = st.sidebar.date_input("Start Date", datetime.date(2023, 1, 1))
end_date = st.sidebar.date_input("End Date", datetime.date.today())

# -------------------------------
# 3. Robust Data Fetching
# -------------------------------
@st.cache_data # Cache to improve performance
def fetch_stock_data(ticker_symbol, start, end):
    try:
        # download fetches OHLCV data
        df = yf.download(ticker_symbol, start=start, end=end, progress=False)
        
        if not df.empty:
            # Flatten MultiIndex if yfinance returns multi-level headers
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
            
            # Handle liquidity gaps (common in NSE) by forward filling
            df = df.ffill().dropna()
            return df
        return None
    except Exception as e:
        st.error(f"Error fetching data: {e}")
        return None

data = fetch_stock_data(ticker, start_date, end_date)

# -------------------------------
# 4. Initialize Tabs
# -------------------------------
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "Raw Data", 
    "Price Chart", 
    "Volume Chart", 
    "Moving Averages", 
    "Dividends & Splits"
])

if data is not None and not data.empty:
    # Tab 1: Raw Data
    with tab1:
        st.subheader(f"Recent Data for {ticker}")
        st.write(data.tail())
        
        csv = data.to_csv().encode('utf-8')
        st.download_button(
            label="Download data to CSV",
            data=csv,
            file_name=f'{ticker}_data.csv',
            mime='text/csv',
        )

    # Tab 2: Price Chart
    with tab2:
        st.subheader("Closing Price History")
        st.line_chart(data['Close'])

    # Tab 3: Volume Chart
    with tab3:
        st.subheader("Daily Trading Volume")
        st.bar_chart(data['Volume'])

    # Tab 4: Moving Averages
    with tab4:
        st.subheader("Trend Analysis")
        ma_days = st.slider("Select Days for Moving Average", 5, 100, 20)
        
        fig, ax = plt.subplots(figsize=(10, 5))
        ax.plot(data.index, data['Close'], label='Close Price', color='blue', alpha=0.5)
        ax.plot(data.index, data['Close'].rolling(window=ma_days).mean(), 
                label=f'{ma_days}-Day Moving Average', color='red')
        ax.set_title(f"{ticker} Moving Average")
        ax.legend()
        st.pyplot(fig)

    # Tab 5: Dividends and Splits
    with tab5:
        st.subheader("Corporate Actions")
        stock_obj = yf.Ticker(ticker)
        
        col1, col2 = st.columns(2)
        with col1:
            st.write("**Dividends History**")
            # Pulls dividend data directly from Ticker object
            st.write(stock_obj.dividends if not stock_obj.dividends.empty else "No dividends found.")
        with col2:
            st.write("**Stock Splits**")
            st.write(stock_obj.splits if not stock_obj.splits.empty else "No splits found.")
else:
    st.error("No data available. Please check the ticker symbol and date range.")
