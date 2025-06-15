"""
Rate Limits bei Deribit bei options fetch
Default Settings for Non-Matching Engine Requests
Cost per Request: 500 credits.

Maximum Credits: 50,000 credits.

Refill Rate: Credits are refilled at a rate that allows up to 20 requests per second (10,000 credits per second).

Burst Capacity: Allows up to 100 requests at once, considering the maximum credit pool.

=> jede minute alle options abrufen
"""


import time
from datetime import datetime

def func():
    print("Neue Minute gestartet:", datetime.now())

def wait_for_new_minute():
    last_minute = datetime.now().minute
    while True:
        now = datetime.now()
        if now.minute != last_minute:
            last_minute = now.minute
            func()
        time.sleep(0.5)  # kurze Pause, um CPU zu schonen

if __name__ == "__main__":
    wait_for_new_minute()
