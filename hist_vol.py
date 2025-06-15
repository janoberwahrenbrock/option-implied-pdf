import sqlite3
import numpy as np
import random
from datetime import datetime, timedelta
from typing import List


def sample_returns_from_db(
    db_path: str,
    table_name: str,
    start: datetime,
    end: datetime,
    size: int,
    delta: timedelta,
    tolerance: timedelta
) -> List[float]:
    """
    Wählt `size` zufällige Zeitpunkte zwischen `start` und `end` (in ms),
    sucht in der SQLite-DB nach dem `open`-Preis zum Zeitpunkt sowie zum Zeitpunkt + delta (ms),
    jeweils innerhalb einer tolerance (ebenfalls in ms),
    und berechnet die relative Preisänderung.

    Gibt eine Liste von Returns zurück.
    """

    def find_price(cursor, timestamp_ms: int, mode: str = "any") -> float | None:
        tol_ms = int(tolerance.total_seconds() * 1000)
        if mode == "any":
            lower = timestamp_ms - tol_ms
            upper = timestamp_ms + tol_ms
        elif mode == "forward":
            lower = timestamp_ms
            upper = timestamp_ms + tol_ms
        else:
            raise ValueError("mode muss 'any' oder 'forward' sein.")

        cursor.execute(f"""
            SELECT open FROM {table_name}
            WHERE opentime BETWEEN ? AND ?
            ORDER BY opentime ASC
            LIMIT 1
        """, (lower, upper))
        res = cursor.fetchone()
        return res[0] if res else None

    # === Verbindung ===
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    returns = []

    # Millisekunden-Bereiche für random
    start_ms = int(start.timestamp() * 1000)
    end_ms   = int(end.timestamp()   * 1000)
    delta_ms = int(delta.total_seconds() * 1000)
    tol_ms   = int(tolerance.total_seconds() * 1000)

    # Damit später_ts <= end_ms
    min_ts = start_ms
    max_ts = end_ms - delta_ms - tol_ms

    for i in range(size):
        random_ts = random.randint(min_ts, max_ts)
        later_ts  = random_ts + delta_ms

        price_now   = find_price(cursor, random_ts, mode="any")
        price_later = find_price(cursor, later_ts,  mode="forward")

        if price_now is None or price_later is None:
            print(f"[{i+1}/{size}] Kein Preis für {random_ts} oder {later_ts} im Toleranzfenster.")
            continue

        returns.append((price_later - price_now) / price_now)

    conn.close()
    return returns


if __name__ == "__main__":
    # Beispielaufruf
    db_path    = "hist_data.db"           # oder dein DB-Name
    table_name = "hist_data"              # oder dein Table-Name
    start      = datetime(2022, 6, 15)
    end        = datetime(2025, 6, 14)
    size       = 1000
    delta      = timedelta(days=5)
    tolerance  = timedelta(minutes=2)

    returns = sample_returns_from_db(
        db_path, table_name, start, end, size, delta, tolerance
    )
    print(f"Anzahl der Returns: {len(returns)}")
    print("Beispiel Returns:", returns[:10])
