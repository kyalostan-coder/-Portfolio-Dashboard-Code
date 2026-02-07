import streamlit as st
import yfinance as yf
import pandas as pd
import matplotlib.pyplot as plt

# 1. Sidebar Inputs [2, 3]
st.sidebar.title("Stock Dashboard")
ticker = st.sidebar.text_input("Enter Stock Ticker", value="MSFT") # Default to Microsoft [2, 4]
start_date = st.sidebar.date_input("Start Date") # User selects start date [2]
end_date = st.sidebar.date_input("End Date")     # User selects end date [2]

# 2. Fetching Data [3, 4]
# The video mentions using yf.download or the Ticker object
data = yf.download(ticker, start=start_date, end=end_date)

# 3. Initialize Tabs [3]
# The transcript lists specific tabs created for the dashboard
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "Raw Data", 
    "Price Chart", 
    "Volume Chart", 
    "Moving Averages", 
    "Dividends & Splits"
])

# Tab 1: Raw Data [3, 5]
with tab1:
    # Shows the tail of the data (e.g., 2020-2024)
    st.write(data.tail())
    
    # Button to download data to CSV
    csv = data.to_csv().encode('utf-8')
    st.download_button(
        label="Download data to CSV",
        data=csv,
        file_name=f'{ticker}_data.csv',
        mime='text/csv',
    )

# Tab 2: Price Chart [6, 7]
with tab2:
    if not data.empty:
        st.line_chart(data['Close'])
    else:
        st.write("Closing price data is not available for this stock")

# Tab 3: Volume Chart [8]
with tab3:
    # Described as a bar chart with default blue color
    st.bar_chart(data['Volume'])

# Tab 4: Moving Averages [9-11]
with tab4:
    # The transcript mentions moving averages are "controllable in days"
    # and uses Matplotlib (plt)
    ma_days = st.slider("Select Days for Moving Average", 5, 50, 20) # Range 20-50 mentioned in [11]
    
    fig, ax = plt.subplots()
    ax.plot(data['Close'], label='Close Price')
    ax.plot(data['Close'].rolling(window=ma_days).mean(), label=f'{ma_days}-Day MA')
    ax.legend()
    st.pyplot(fig)

# Tab 5: Dividends and Splits [11, 12]
with tab5:
    # Accessing dividend and split data via the Ticker object
    stock = yf.Ticker(ticker)
    
    st.write("Dividends")
    st.write(stock.dividends)
    
    st.write("Splits")
    st.write(stock.splits)

