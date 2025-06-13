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
