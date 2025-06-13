import asyncio
from collections import deque
from datetime import datetime, timezone

from deribit import Deribit, Option


async def fetch_and_store_point(deribit: Deribit, option: Option, points: list):
    """
    Holt den aktuellen Mark-Preis für das gegebene Option-Objekt
    und speichert ein Tupel (strike, mark_price).
    """
    try:
        ticker = deribit._get_ticker(option.instrument_name)
        mark = ticker["mark_price"]
        points.append((option.strike, mark))
        print(f"[{datetime.now().time()}] {option.instrument_name} - ({option.strike}, {mark}) gespeichert")
    except Exception as e:
        print(f"Fehler bei {option.instrument_name}: {e}")


async def run_ticker_loop(deribit: Deribit, stack: deque, points: list, interval: float = 1.0):
    """
    Ruft alle `interval` Sekunden asynchron get_ticker mit dem obersten Option-Objekt auf
    und speichert (strike, mark_price) in der Liste `points`.
    Danach wird das Option-Objekt wieder ans Ende des Stacks gehängt.
    """
    while True:
        if stack:
            option = stack.popleft()
            asyncio.create_task(fetch_and_store_point(deribit, option, points))
            stack.append(option)
        await asyncio.sleep(interval)


async def main():
    deribit = Deribit()

    # Beispiel: Verfall am 20. Juni 2025, 08:00:00 UTC
    expiration = datetime(2025, 6, 20, 8, 0, 0, tzinfo=timezone.utc)

    # Call-Optionen holen
    options = deribit.fetch_calls(expiration)

    if not options:
        print("Keine Call-Optionen gefunden.")
        return

    # Stack vorbereiten und Punkteliste initialisieren
    stack = deque(options)
    points: list[tuple[int, float]] = []

    print(f"{len(stack)} Call-Optionen gefunden. Starte Ticker-Loop ...")

    await run_ticker_loop(deribit, stack, points)


if __name__ == "__main__":
    asyncio.run(main())
