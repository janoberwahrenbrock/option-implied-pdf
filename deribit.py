import requests
from datetime import datetime, timezone

BASE_URL = "https://www.deribit.com/api/v2/"


def fetch_options_data(expiration_datetime: datetime):
    """
    Returns bid/ask, IV, amount and open interest for calls and puts expiring at a specific UTC datetime.

    Parameters:
        expiration_datetime (datetime): UTC datetime for expiration (tzinfo=timezone.utc)

    Returns:
        dict: {
            'calls': [{instrument_name: {ticker_data}}],
            'puts':  [{instrument_name: {ticker_data}}]
        }
    """

    # 1) Get all active BTC options
    instruments_resp = requests.get(
        BASE_URL + "public/get_instruments",
        params={"currency": "BTC", "expired": "false", "kind": "option"}
    )
    instruments_resp.raise_for_status()
    instruments = instruments_resp.json()["result"]

    # 2) Convert target datetime to millisecond timestamp
    target_ts = int(expiration_datetime.timestamp() * 1000)

    # 3) Filter for this exact expiration timestamp
    matches = [inst for inst in instruments if inst["expiration_timestamp"] == target_ts]

    # 4) Separate calls and puts by instrument_name
    call_names = [inst["instrument_name"] for inst in matches if inst["instrument_name"].endswith("C")]
    put_names  = [inst["instrument_name"] for inst in matches if inst["instrument_name"].endswith("P")]

    def get_ticker_data(name: str):
        resp = requests.get(
            BASE_URL + "public/ticker",
            params={"instrument_name": name}
        )
        resp.raise_for_status()
        r = resp.json()["result"]
        return {
            "best_ask_price":  r["best_ask_price"],
            "ask_iv":          r["ask_iv"],
            "best_ask_amount": r["best_ask_amount"],
            "best_bid_price":  r["best_bid_price"],
            "bid_iv":          r["bid_iv"],
            "best_bid_amount": r["best_bid_amount"],
            "open_interest":   r["open_interest"],
        }

    # 5) Build data lists
    calls_data = [{name: get_ticker_data(name)} for name in call_names]
    puts_data  = [{name: get_ticker_data(name)} for name in put_names]

    return {"calls": calls_data, "puts": puts_data}


# Example usage
if __name__ == "__main__":
    target = datetime(2025, 5, 16, 8, 0, 0, tzinfo=timezone.utc)
    data = fetch_options_data(target)
    from pprint import pprint
    pprint(data, indent=2)