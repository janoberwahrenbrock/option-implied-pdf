from datetime import datetime, timezone
from deribit import Deribit

target = datetime(2025, 6,13, 8, 0, 0, tzinfo=timezone.utc)
deribit = Deribit()
calls = deribit.fetch_calls(target)


strikes = [call.strike for call in calls]
marks = [call.mark_price for call in calls]

import matplotlib.pyplot as plt
import numpy as np

# plot
fig, ax = plt.subplots()

ax.plot(strikes, marks, 'x')

plt.show()