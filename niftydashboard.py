import streamlit as st
import pandas as pd
import yfinance as yf
import requests

st.title("NIFTY50 Valuation Dashboard")

# ----------------------------
# Load NIFTY50 List
# ----------------------------
@st.cache_data(ttl=86400)
def load_nifty50():

    url = "https://archives.nseindia.com/content/indices/ind_nifty50list.csv"

    df = pd.read_csv(url)

    df["YahooSymbol"] = df["Symbol"] + ".NS"

    return df


nifty_df = load_nifty50()

stock = st.selectbox(
    "Select NIFTY50 Stock",
    nifty_df["YahooSymbol"],
    format_func=lambda x: nifty_df[nifty_df["YahooSymbol"] == x]["Company Name"].values[0]
)

# ----------------------------
# Cached Yahoo Data
# ----------------------------
@st.cache_data(ttl=3600)
def get_stock_info(symbol):

    ticker = yf.Ticker(symbol)

    return ticker.info


info = get_stock_info(stock)

ticker = yf.Ticker(stock)

# ----------------------------
# Fundamental Metrics
# ----------------------------
current_price = info.get("currentPrice","N/A")
pe = info.get("trailingPE","N/A")
pb = info.get("priceToBook","N/A")
forward_pe = info.get("forwardPE","N/A")
target = info.get("targetMeanPrice","N/A")
opm = info.get("operatingMargins")
growth = info.get("earningsGrowth")

peg = None

if isinstance(pe,(int,float)) and isinstance(growth,(int,float)):
    peg = pe / (growth * 100)

# ----------------------------
# Metric Panel
# ----------------------------
st.subheader("Key Metrics")

col1,col2,col3 = st.columns(3)

col1.metric("Current Price",current_price)
col2.metric("PE Ratio",pe)
col3.metric("PB Ratio",pb)

col4,col5,col6 = st.columns(3)

col4.metric("Forward PE",forward_pe)
col5.metric("PEG Ratio",peg)

if opm:
    col6.metric("OPM",f"{opm*100:.2f}%")
else:
    col6.metric("OPM","N/A")

st.metric("Average Target Price",target)

# ----------------------------
# Price Chart
# ----------------------------
st.subheader("1 Year Price Chart")

hist = ticker.history(period="1y")

if not hist.empty:
    st.line_chart(hist["Close"])
else:
    st.write("Price data unavailable")

# ----------------------------
# Screener Holding Pattern
# ----------------------------
st.subheader("Institutional Holding Pattern")

symbol = stock.replace(".NS","")

try:

    url = f"https://www.screener.in/company/{symbol}/"

    headers = {"User-Agent":"Mozilla/5.0"}

    html = requests.get(url,headers=headers).text

    tables = pd.read_html(html)

    holding = None

    for table in tables:

        if "Shareholding Pattern" in table.columns[0]:

            holding = table

            break

    if holding is not None:

        holding = holding.set_index(holding.columns[0])

        holding = holding.iloc[:, -3:]

        st.dataframe(holding)

        latest = holding.iloc[:, -1]
        prev = holding.iloc[:, -2]

        change = latest - prev

        st.subheader("3 Month Change")

        st.table(change)

    else:

        st.write("Holding pattern not available")

except:

    st.write("Could not load Screener data")
# ---------------------------------------------------
# NIFTY50 Undervalued Stock Screener
# ---------------------------------------------------

st.header("Top Potentially Undervalued NIFTY50 Stocks")

@st.cache_data(ttl=3600)
def scan_nifty():

    results = []

    for symbol in nifty_df["YahooSymbol"][:25]:  # limit to avoid rate limit

        try:

            info = yf.Ticker(symbol).info

            pe = info.get("trailingPE")
            growth = info.get("earningsGrowth")

            if isinstance(pe,(int,float)) and isinstance(growth,(int,float)):

                peg = pe/(growth*100)

                if peg < 1 and pe < 30:

                    results.append({
                        "Stock":symbol,
                        "PE":pe,
                        "PEG":round(peg,2)
                    })

        except:

            pass

    return pd.DataFrame(results)


undervalued = scan_nifty()

if not undervalued.empty:

    st.dataframe(undervalued)

else:

    st.write("No undervalued stocks detected using PEG rule")
