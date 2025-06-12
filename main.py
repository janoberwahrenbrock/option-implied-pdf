from datetime import datetime, timezone
from deribit import Deribit

from model import fit_parameter, assemble_splines, plot_func
from scale import scale_x_value, unscale_x_value, unscale_splines


target = datetime(2025, 6, 20, 8, 0, 0, tzinfo=timezone.utc)
deribit = Deribit()
calls = deribit.fetch_calls(target)
puts = deribit.fetch_puts(target)

options = calls  # or puts, depending on what you want to analyze


underlying_price = options[0].underlying_price  # Assuming all calls have the same underlying price


strikes = [option.strike for option in options]
marks = [option.mark_price for option in options]





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

min_strike = min(strikes)
max_strike = max(strikes)


points = []
for i in range(len(strikes)):
    points.append((strikes[i], marks[i]))


support_points = [underlying_price - 10000, underlying_price - 5000, underlying_price, underlying_price + 5000, underlying_price + 10000]
konvex_until = underlying_price
bounds = (min_strike, max_strike)




# Hier sollen alle Inputs skaliert werden
# 1) Originales min/max berechnen
original_x_min = min_strike
original_x_max = max_strike

# 2) Strikes skalieren
strikes_scaled = [
    scale_x_value(x, original_x_min, original_x_max, scaled_bounds=(-1.0, 1.0))
    for x in strikes
]

# 3) Punkte fürs Fit
points_scaled = list(zip(strikes_scaled, marks))

# Skalieren aller support_points auf [-1,1]
support_points_scaled = [
    scale_x_value(
        original_x=sp,
        original_x_min=original_x_min,
        original_x_max=original_x_max,
        scaled_bounds=(-1.0, 1.0)
    )
    for sp in support_points
]

# Ebenso den konvex_until-Wert
konvex_until_scaled = scale_x_value(
    original_x=konvex_until,
    original_x_min=original_x_min,
    original_x_max=original_x_max,
    scaled_bounds=(-1.0, 1.0)
)


# 5) Bounds skalieren (ergibt -1.0 und +1.0)
bounds_scaled = (
    scale_x_value(min_strike, original_x_min, original_x_max, scaled_bounds=(-1.0, 1.0)),
    scale_x_value(max_strike, original_x_min, original_x_max, scaled_bounds=(-1.0, 1.0))
)

# 6) Fit im skalierten Raum
status, value, matrix = fit_parameter(
    points=points_scaled,
    support_points=support_points_scaled,
    konvex_until=konvex_until_scaled,
    bounds=bounds_scaled,
    degree_of_spline=5,
    sampling_interval=0.01
)

print(f"Status: {status}")
print(f"Zielfunktionswert: {value}")
print("Koeffizientenmatrix:")
print(matrix)




# Baue die Funktion
scaled_spline_func = assemble_splines(
    matrix=matrix,
    support_points=support_points_scaled,
    bounds=bounds_scaled
)

spline_func = unscale_splines(scaled_spline_func, 
                              original_x_min=original_x_min,
                              original_x_max=original_x_max,
                              scaled_bounds=(-1.0, 1.0))

plot_func(func=spline_func, bounds=bounds, points=points)








# skaliert
first_deriv_scaled  = assemble_splines(matrix, support_points_scaled, bounds_scaled, derivative=1)
second_deriv_scaled = assemble_splines(matrix, support_points_scaled, bounds_scaled, derivative=2)

# unskaliert
first_derivative = unscale_splines(first_deriv_scaled,  original_x_min, original_x_max)
second_derivative= unscale_splines(second_deriv_scaled, original_x_min, original_x_max)

# plot
plot_func(func=first_derivative,  bounds=bounds)
plot_func(func=second_derivative, bounds=bounds)
