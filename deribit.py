import requests
from datetime import datetime, timezone
from typing import List

from exchange import Exchange, Option  # passe den Import-Pfad an


class Deribit(Exchange):
    """
    Concrete Exchange implementation for Deribit (BTC options).
    """

    @property
    def base_url(self) -> str:
        return "https://www.deribit.com/api/v2/"

    def _fetch_instruments(self) -> List[dict]:
        resp = requests.get(
            self.base_url + "public/get_instruments",
            params={"currency": "BTC", "expired": "false", "kind": "option"},
        )
        resp.raise_for_status()
        return resp.json()["result"]

    def _get_ticker(self, name: str) -> dict:
        resp = requests.get(
            self.base_url + "public/ticker",
            params={"instrument_name": name},
        )
        resp.raise_for_status()
        return resp.json()["result"]

    def fetch_calls(self, expiration: datetime) -> List[Option]:
        if expiration.tzinfo != timezone.utc:
            raise ValueError("`expiration` must be UTC-aware")

        target_ts = int(expiration.timestamp() * 1000)
        instruments = self._fetch_instruments()

        # 1-Zeiler: filter nach expiry + Calls
        calls = [
            inst for inst in instruments
            if inst["expiration_timestamp"] == target_ts
               and inst["instrument_name"].endswith("C")
        ]

        results: List[Option] = []
        for inst in calls:
            name = inst["instrument_name"]
            ticker = self._get_ticker(name)

            # Inline-Extraktion:
            # strike = dritter Chunk, type = 'call'
            strike = int(name.split("-", 3)[2])

            results.append(Option(
                instrument_name=name,
                expiration=expiration,
                strike=strike,
                type="call",
                underlying_price=ticker["underlying_price"],
                open_interest=ticker["open_interest"],
                mark_price=ticker["mark_price"],
                best_ask_amount=ticker["best_ask_amount"],
                best_ask_price=ticker["best_ask_price"],
                ask_iv=ticker["ask_iv"],
                best_bid_price=ticker["best_bid_price"],
                best_bid_amount=ticker["best_bid_amount"],
                bid_iv=ticker["bid_iv"],
            ))
        return results

    def fetch_puts(self, expiration: datetime) -> List[Option]:
        if expiration.tzinfo != timezone.utc:
            raise ValueError("`expiration` must be UTC-aware")

        target_ts = int(expiration.timestamp() * 1000)
        instruments = self._fetch_instruments()

        # 1-Zeiler: filter nach expiry + Puts
        puts = [
            inst for inst in instruments
            if inst["expiration_timestamp"] == target_ts
               and inst["instrument_name"].endswith("P")
        ]

        results: List[Option] = []
        for inst in puts:
            name = inst["instrument_name"]
            ticker = self._get_ticker(name)

            # Inline-Extraktion:
            strike = int(name.split("-", 3)[2])

            results.append(Option(
                instrument_name=name,
                expiration=expiration,
                strike=strike,
                type="put",
                underlying_price=ticker["underlying_price"],
                open_interest=ticker["open_interest"],
                mark_price=ticker["mark_price"],
                best_ask_amount=ticker["best_ask_amount"],
                best_ask_price=ticker["best_ask_price"],
                ask_iv=ticker["ask_iv"],
                best_bid_price=ticker["best_bid_price"],
                best_bid_amount=ticker["best_bid_amount"],
                bid_iv=ticker["bid_iv"],
            ))
        return results


# Example usage
if __name__ == "__main__":
    target = datetime(2025, 6, 13, 8, 0, 0, tzinfo=timezone.utc)
    deribit = Deribit()
    calls = deribit.fetch_calls(target)
    from pprint import pprint
    pprint(calls, indent=1)