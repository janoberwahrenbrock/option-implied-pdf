from datetime import datetime, timezone
from deribit import Deribit

target = datetime(2025, 6,20, 8, 0, 0, tzinfo=timezone.utc)
deribit = Deribit()
calls = deribit.fetch_calls(target)
puts = deribit.fetch_puts(target)


strikes = [option.strike for option in puts]
marks = [option.mark_price for option in puts]





# Problem der Ungenauigkeit durch die kleinen BTC Beträge
# remove all Options with a mark price lower than 0.001
filtered_strikes = []
filtered_marks = []
for strike, mark in zip(strikes, marks):
    if mark >= 0.001:
        filtered_strikes.append(strike)
        filtered_marks.append(mark)

strikes = filtered_strikes
marks = filtered_marks





import matplotlib.pyplot as plt
import numpy as np

from scipy.interpolate import CubicSpline

cs = CubicSpline(strikes, marks)



# plot
fig, ax = plt.subplots()

ax.plot(strikes, marks, 'x')
ax.plot(np.linspace(min(strikes), max(strikes), 100), cs(np.linspace(min(strikes), max(strikes), 100)), label='Cubic Spline')
ax.set_xlabel('Strike')
# ax.set_yscale('log')

plt.show()




derivative_cs = cs.derivative()


# plot
fig, ax = plt.subplots()


ax.plot(np.linspace(min(strikes), max(strikes), 100), derivative_cs(np.linspace(min(strikes), max(strikes), 100)), label='1st Derivative', linestyle='--')
ax.set_xlabel('Strike')
#ax.set_yscale('log')

plt.show()




derivative_derivative_cs = cs.derivative(2)


# plot
fig, ax = plt.subplots()


ax.plot(np.linspace(min(strikes), max(strikes), 100), derivative_derivative_cs(np.linspace(min(strikes), max(strikes), 100)), label='2nd Derivative', linestyle='--')
ax.set_xlabel('Strike')

plt.show()