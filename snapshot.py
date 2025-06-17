# Standard Library
from datetime import datetime, timezone

# Lokal
from deribit import Deribit
from model import fit_parameter, assemble_splines, plot_func
from scale import scale_x_value, unscale_x_value, unscale_splines



# === User Inputs 1 ===
target = datetime(2025, 6, 20, 8, 0, 0, tzinfo=timezone.utc) # change YYYY-MM-DD but options alsways expire at 8:00 UTC at Deribit
use_calls = True  # Set to False if you want to use puts instead of calls
MIN_MARK_PRICE = 0.0005
MAX_MARK_PRICE = 0.1
SAMPLING_INTERVAL = 0.01 # Intervall für die Abtastung der Spline-Funktion beachte dass die range -1, 1 ist
SPLINE_DEGREE = 3  # Grad des Splines
# === User Inputs 1 End ===



deribit = Deribit()
calls = deribit.fetch_calls(target)
puts = deribit.fetch_puts(target)

if use_calls:
    options = calls
else:
    options = puts

konvex_until = underlying_price = options[0].underlying_price  # Assuming all calls have the same underlying price

strikes = [option.strike for option in options]
marks = [option.mark_price for option in options]



# === User Inputs 2 ===
support_points = [underlying_price - 10000, underlying_price - 5000, underlying_price, underlying_price + 5000]
# === User Inputs 2 End ===



# Filter 
filtered_strikes = []
filtered_marks = []
for strike, mark in zip(strikes, marks):
    if mark >= MIN_MARK_PRICE and mark <= MAX_MARK_PRICE:
        filtered_strikes.append(strike)
        filtered_marks.append(mark)

strikes = filtered_strikes
marks = filtered_marks

points = []
for i in range(len(strikes)):
    points.append((strikes[i], marks[i]))



# === Skaliere die Daten ===

# 1) alte bounds sichern
original_x_min = min(strikes)
original_x_max = max(strikes)
original_bounds = (original_x_min, original_x_max)

# 2) Strikes skalieren
strikes_scaled = [
    scale_x_value(x, original_x_min, original_x_max, scaled_bounds=(-1.0, 1.0))
    for x in strikes
]

# 3) Punkte für den Fit
points_scaled = list(zip(strikes_scaled, marks))

# 4) support_points und konvex_until skalieren
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
bounds_scaled = (-1.0, 1.0)

# 6) Fit function im skalierten Raum
status, value, matrix = fit_parameter(
    points=points_scaled,
    support_points=support_points_scaled,
    konvex_until=konvex_until_scaled,
    bounds=bounds_scaled,
    degree_of_spline=SPLINE_DEGREE,
    sampling_interval=SAMPLING_INTERVAL
)


print(f"Status: {status}")
print(f"Zielfunktionswert: {value}")
print("Koeffizientenmatrix:")
print(matrix)


# Baue die Funktion im skalierten Raum auf
scaled_spline_func = assemble_splines(matrix=matrix, support_points=support_points_scaled, bounds=bounds_scaled)

# hole die Funktion zurück in den originalen Raum
spline_func = unscale_splines(scaled_spline_func, original_x_min=original_x_min, original_x_max=original_x_max, scaled_bounds=(-1.0, 1.0))

plot_func(func=spline_func, bounds=original_bounds, points=points)



# === Berechne die erste Ableitung ===
first_deriv_scaled  = assemble_splines(matrix, support_points_scaled, bounds_scaled, derivative=1)

first_derivative = unscale_splines(first_deriv_scaled,  original_x_min, original_x_max)

plot_func(func=first_derivative,  bounds=original_bounds)


# === Berechne die zweite Ableitung ===
second_deriv_scaled = assemble_splines(matrix, support_points_scaled, bounds_scaled, derivative=2)

second_derivative= unscale_splines(second_deriv_scaled, original_x_min, original_x_max)

plot_func(func=second_derivative, bounds=original_bounds)
