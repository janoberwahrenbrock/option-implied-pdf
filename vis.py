import streamlit as st
from datetime import datetime, timezone
import pandas as pd

from deribit import fetch_options_data

# Ziel-Datum (UTC)
target = datetime(2025, 5, 16, 8, 0, 0, tzinfo=timezone.utc)

# Optionen-Daten abrufen
data = fetch_options_data(target)

# Daten in DataFrames umwandeln und Strike extrahieren
calls = pd.DataFrame([
    dict(
        instrument_name=list(item.keys())[0],
        open_interest=list(item.values())[0]["open_interest"],
        best_bid_price=list(item.values())[0]["best_bid_price"],
        best_ask_price=list(item.values())[0]["best_ask_price"],
        implied_volatility=list(item.values())[0]["bid_iv"],
        best_bid_amount=list(item.values())[0]["best_bid_amount"],
        best_ask_amount=list(item.values())[0]["best_ask_amount"]
    )
    for item in data["calls"]
])
puts = pd.DataFrame([
    dict(
        instrument_name=list(item.keys())[0],
        open_interest=list(item.values())[0]["open_interest"],
        best_bid_price=list(item.values())[0]["best_bid_price"],
        best_ask_price=list(item.values())[0]["best_ask_price"],
        implied_volatility=list(item.values())[0]["bid_iv"],
        best_bid_amount=list(item.values())[0]["best_bid_amount"],
        best_ask_amount=list(item.values())[0]["best_ask_amount"]
    )
    for item in data["puts"]
])

# Strike als int extrahieren
calls["strike"] = calls["instrument_name"].apply(lambda s: int(s.split('-')[2]))
puts["strike"] = puts["instrument_name"].apply(lambda s: int(s.split('-')[2]))

# Sortieren nach Strike
calls.sort_values("strike", inplace=True)
puts.sort_values("strike", inplace=True)

# Streamlit UI
st.title("BTC-Optionen bei Deribit")
st.subheader(f"Ablauf: {target.strftime('%Y-%m-%d %H:%M UTC')}")

# Function to render charts section
def render_section(df: pd.DataFrame, title: str):
    st.write(f"## {title}")
    if df.empty:
        st.write(f"Keine {title.lower()} für dieses Ablaufdatum.")
        return
    df_indexed = df.set_index("strike")

    # Open Interest
    st.write("### Open Interest je Strike")
    st.bar_chart(df_indexed["open_interest"])

    # Bid vs. Ask Price
    st.write("### Bid vs. Ask Price je Strike")
    st.bar_chart(df_indexed[["best_bid_price", "best_ask_price"]])

    # Bid vs. Ask Amount
    st.write("### Bid vs. Ask Amount je Strike")
    st.bar_chart(df_indexed[["best_bid_amount", "best_ask_amount"]])

    # Implied Volatility
    st.write("### Implizite Volatilität (Bid IV) je Strike")
    st.bar_chart(df_indexed["implied_volatility"])

# Calls Charts
render_section(calls, "Calls")
# Puts Charts
render_section(puts, "Puts")
