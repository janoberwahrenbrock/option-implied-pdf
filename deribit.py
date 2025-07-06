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
        """
        The base URL for Deribit API endpoints.

        Returns:
            str: Base URL string for API calls.
        """
        return "https://www.deribit.com/api/v2/"

    def _fetch_instruments(self) -> List[dict]:
        """
        Fetches all active BTC option instruments from Deribit.

        Returns:
            List[dict]: A list of instrument info dictionaries as returned by the API.

        Raises:
            requests.HTTPError: If the HTTP request fails or returns a bad status code.
        """
        resp = requests.get(
            self.base_url + "public/get_instruments",
            params={"currency": "BTC", "expired": "false", "kind": "option"},
        )
        resp.raise_for_status()
        return resp.json()["result"]

    def _get_ticker(self, name: str) -> dict:
        """
        Retrieves ticker information for a specific instrument.

        Args:
            name (str): The instrument name (e.g., 'BTC-30JUN23-30000-C').

        Returns:
            dict: Ticker data dictionary for the given instrument.

        Raises:
            requests.HTTPError: If the HTTP request fails or returns a bad status code.
        """
        resp = requests.get(
            self.base_url + "public/ticker",
            params={"instrument_name": name},
        )
        resp.raise_for_status()
        return resp.json()["result"]

    def fetch_calls(self, expiration: datetime) -> List[Option]:
        """
        Fetches all call options with the specified expiration date.

        Args:
            expiration (datetime): UTC-aware expiration datetime to filter instruments.

        Returns:
            List[Option]: A list of Option objects for call options.

        Raises:
            ValueError: If `expiration` is not timezone-aware UTC.
            requests.HTTPError: If the HTTP request fails or returns a bad status code.
        """
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
                timestamp=ticker["timestamp"],
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
        """
        Fetches all put options with the specified expiration date.

        Args:
            expiration (datetime): UTC-aware expiration datetime to filter instruments.

        Returns:
            List[Option]: A list of Option objects for put options.

        Raises:
            ValueError: If `expiration` is not timezone-aware UTC.
            requests.HTTPError: If the HTTP request fails or returns a bad status code.
        """
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
                timestamp=ticker["timestamp"],
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
    
    def instrument_exists(self, instrument_name: str) -> bool:
        """
        Prüft, ob ein Instrument auf Deribit existiert.

        Args:
            instrument_name (str): z.B. 'BTC-30JUN23-30000-C'

        Returns:
            bool: True, wenn der Aufruf erfolgreich war und ein Ergebnis enthält,
                  False bei HTTP-Fehlern oder leerem Ergebnis.
        """
        try:
            resp = requests.get(
                self.base_url + "public/get_instrument",
                params={"instrument_name": instrument_name},
            )
            resp.raise_for_status()
            data = resp.json().get("result")
            return data is not None
        except Exception:
            return False


# Example usage
if __name__ == "__main__":
    '''
    target = datetime(2025, 6, 20, 8, 0, 0, tzinfo=timezone.utc)
    deribit = Deribit()
    calls = deribit.fetch_calls(target)
    from pprint import pprint
    pprint(calls, indent=1)
    '''
    api = Deribit()
    import calendar

    for date_str in ["2025-07-09", "2025-07-10", "2025-07-11"]:
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        day = dt.day
        month_abbr = calendar.month_abbr[dt.month].upper()
        year_suffix = str(dt.year)[-2:]
        future_name = f"BTC-{day:02}{month_abbr}{year_suffix}"

        exists = api.instrument_exists(future_name)
        print(f"{future_name}: {'✔️ exists' if exists else '❌ does not exist'}")