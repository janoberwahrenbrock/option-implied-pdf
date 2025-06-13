from datetime import datetime, timezone

def datetime_to_timestamp_ms(dt: datetime) -> int:
    """
    Wandelt ein datetime-Objekt in einen Unix-Timestamp in Millisekunden um.
    """
    return int(dt.timestamp() * 1000)

def current_datetime_to_timestamp_ms() -> int:
    """
    Gibt den aktuellen UTC-Zeitpunkt als Unix-Timestamp in Millisekunden zurück.
    """
    return int(datetime.now(timezone.utc).timestamp() * 1000)

dt = datetime(2025, 6,13, 13, 30, 0, tzinfo=timezone.utc)
ts = datetime_to_timestamp_ms(dt)
print(ts)

print(current_datetime_to_timestamp_ms())