import asyncio
import threading
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
from collections import deque
from datetime import datetime, timezone

from deribit import Deribit, Option

# Globale Punkteliste
points: list[tuple[int, float]] = []

# Async-Teil in eigenem Thread starten
def start_asyncio_loop(stack: deque):
    async def fetch_and_store_point(deribit: Deribit, option: Option):
        try:
            ticker = deribit._get_ticker(option.instrument_name)
            mark = ticker["mark_price"]
            points.append((option.strike, mark))
            print(f"[{datetime.now().time()}] {option.instrument_name} - ({option.strike}, {mark})")
        except Exception as e:
            print(f"Fehler bei {option.instrument_name}: {e}")

    async def run_ticker_loop(deribit: Deribit, stack: deque, interval: float = 1.0):
        while True:
            if stack:
                option = stack.popleft()
                asyncio.create_task(fetch_and_store_point(deribit, option))
                stack.append(option)
            await asyncio.sleep(interval)

    async def main():
        deribit = Deribit()
        expiration = datetime(2025, 6, 20, 8, 0, 0, tzinfo=timezone.utc)
        options = deribit.fetch_calls(expiration)

        if not options:
            print("Keine Optionen gefunden.")
            return

        stack.extend(options)
        await run_ticker_loop(deribit, stack, interval=0.1)

    asyncio.run(main())

def start_plotting():
    fig, ax = plt.subplots()
    scatter = ax.scatter([], [], color="blue")

    # ✅ Achsenbereiche zu Beginn festlegen
    ax.set_xlim(80000, 150000)  # Beispielwerte – anpassen an deinen Markt
    ax.set_ylim(-0.01, 0.2)         # Beispiel: Mark Price grob geschätzt

    ax.set_title("Live Mark Prices")
    ax.set_xlabel("Strike")
    ax.set_ylabel("Mark Price")
    ax.grid(True)

    def update(frame):
        if not points:
            return scatter,

        strikes, prices = zip(*points)
        offsets = list(zip(strikes, prices))
        scatter.set_offsets(offsets)  # Nur Daten aktualisieren

        return scatter,

    ani = FuncAnimation(fig, update, interval=1000)
    plt.show()

if __name__ == "__main__":
    stack = deque()

    # Asyncio Loop im Hintergrund starten
    threading.Thread(target=start_asyncio_loop, args=(stack,), daemon=True).start()

    # Plot im Hauptthread starten (notwendig auf macOS)
    start_plotting()
