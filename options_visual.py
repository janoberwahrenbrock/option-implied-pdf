import streamlit as st
from datetime import datetime, timezone
import calendar
import pandas as pd

from deribit import Deribit

st.title("BTC-Optionen bei Deribit")

# -------------------------------
# 1) Eingabe Jahr, Monat & Tag
# -------------------------------
now = datetime.now(timezone.utc)

year = st.number_input(
    "Jahr auswählen",
    min_value=2000,
    max_value=2100,
    value=now.year,
    step=1
)

month = st.selectbox(
    "Monat auswählen",
    options=list(range(1, 13)),
    index=now.month - 1,
    format_func=lambda m: calendar.month_name[m]
)

day = st.number_input(
    "Tag auswählen",
    min_value=1,
    max_value=31,
    value=now.day,
    step=1
)

# 2) Zusammensetzen von Datum + fix 08:00 UTC
try:
    target = datetime(int(year), int(month), int(day), 8, 0, 0, tzinfo=timezone.utc)
except ValueError:
    st.error("Ungültige Datumskombination – bitte Jahr, Monat und Tag anpassen.")
    st.stop()

st.subheader(f"Ablauf: {target.strftime('%d.%m.%Y %H:%M')} UTC")

# -------------------------------
# 3) Daten holen & DataFrames
# -------------------------------
exchange = Deribit()
call_options = exchange.fetch_calls(target)
put_options  = exchange.fetch_puts(target)

# In DataFrames umwandeln
calls_df = pd.DataFrame([opt.model_dump() for opt in call_options])
puts_df  = pd.DataFrame([opt.model_dump() for opt in put_options])

# Relevante Spalten auswählen
cols = [
    "strike",
    "mark_price",
    "open_interest",
    "best_bid_price",
    "best_ask_price",
    "bid_iv",
    "ask_iv",
    "best_bid_amount",
    "best_ask_amount",
]

calls_df = (
    calls_df[cols]
    .set_index("strike")
)

puts_df = (
    puts_df[cols]
    .set_index("strike")
)

# -------------------------------
# 4) Chart-Rendering-Funktion
# -------------------------------
def render_section(df: pd.DataFrame, title: str):
    st.write(f"## {title}")
    if df.empty:
        st.write(f"Keine {title.lower()} für dieses Ablaufdatum.")
        return
    
    st.write("### Mark-Preis je Strike")
    st.bar_chart(df["mark_price"])

    st.write("### Open Interest je Strike")
    st.bar_chart(df["open_interest"])

    st.write("### Bid vs. Ask Price je Strike")
    st.bar_chart(df[["best_bid_price", "best_ask_price"]])

    st.write("### Bid vs. Ask Amount je Strike")
    st.bar_chart(df[["best_bid_amount", "best_ask_amount"]])

    st.write("### Implizite Volatilität je Strike")
    st.bar_chart(df[["bid_iv", "ask_iv"]])

# -------------------------------
# 5) Anzeige
# -------------------------------
render_section(calls_df, "Calls")
render_section(puts_df,  "Puts")
