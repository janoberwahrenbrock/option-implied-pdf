# Ab 2025 ist die opentime in mikrosekunden, vorher in millisekunden.

import pandas as pd
import sqlite3

csv_file = "data_spot_daily_klines_BTCUSDT_1m_2022-06-15_to_2025-06-14.csv"
db_file  = "hist_data.db"
table    = "hist_data"

# 1) CSV einlesen
df = pd.read_csv(csv_file, usecols=["opentime","open"])

# 2) Auf integer casten
df["opentime"] = df["opentime"].astype("int64")
df["open"]     = df["open"].astype(float)

# 3) Normalisierung: Mikros → Millis
#    alles oberhalb von 10^14 ist offenbar in μs, also //1000
mask = df["opentime"] > 10**14
df.loc[mask, "opentime"] = (df.loc[mask, "opentime"] // 1000)

# 4) (Optional) prüfen, ob jetzt alle 13-stelligen sind
assert df["opentime"].astype(str).map(len).max() == 13

# 5) DB neu bauen
conn = sqlite3.connect(db_file)
df.to_sql(table, conn, if_exists="replace", index=False)
conn.close()

print("DB neu erstellt, alle opentime jetzt in ms!")
