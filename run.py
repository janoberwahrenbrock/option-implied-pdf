"""
Option Implied PDF App
======================

Datei-Übersicht
1. Imports
2. Einstellungen (Konstanten)
3. Globale Variablen
4. Argument Parsing
5. Data-Fetch Loops
   5.1 fetch_future_candles_loop
   5.2 fetch_points_loop
6. Dash App
   6.1 Layout
   6.2 Callbacks
7. Main (Thread-Start & app.run)
"""

# === 1. Imports ===
# Standard Library
import logging
import sys
import time
import calendar
from collections import deque
from datetime import datetime, timezone
from dataclasses import dataclass
from typing import List, Tuple
import pickle
import threading

# Third-Party
import numpy as np
import requests
import plotly.graph_objs as go
from dash import Dash, dcc, html
from dash.dependencies import Input, Output, State

# Lokal
from scale import scale_x_value, unscale_splines
from deribit import Deribit
from model import fit_parameter, assemble_splines



# === 2. Einstellungen (Konstanten) ===
DERIBIT_URL = "https://www.deribit.com/api/v2/"
FETCH_FUTURES_INTERVALL = 10 # Pause bevor erneut die OHLC Candles abgefragt werden
OPTIONS_REQUESTS_PER_SECOND = 10 # Anzahl der Anfragen pro Sekunde für die Optionen
UPDATE_FUNCTION_FIT_INTERVALL = 10 # Intervall in Sekunden, um den Funktion Fit zu aktualisieren
SAMPLING_INTERVAL = 0.01 # Intervall für die Abtastung der Spline-Funktion beachte dass die range -1, 1 ist
MIN_MARK_PRICE = 0.0005 # Minimaler Mark-Preis für die Punkte, die in den Fit einfließen sollen
MAX_MARK_PRICE = 0.1 # Maximaler Mark-Preis für die Punkte, die in den Fit einfließen sollen
EXPORT_FUNCTION_FIT = False # notwendige Daten werden in shared_data.pkl exportiert, damit sie in anderen Programmen verwendet werden können



# === 3. Globale Variablen ===
program_start_time = int(datetime.now(timezone.utc).timestamp() * 1000) # Startzeit des Programms in Millisekunden

future_name = None # based on sys arg, contains the name of the future, e.g. "BTC-20JUN24"
expiration = None # # based on sys arg, contains the expiration date of the options, e.g. datetime(2024, 6, 20, 8, 0, 0, tzinfo=timezone.utc)
use_calls = None # based on sys arg, True for Calls, False for Puts

candles = [] # die candle Daten für den Future
points = [] # die Punkte für den Fit, bestehend aus (strike - underlying_price, mark_price)
stack = deque() # Stack für die Optionen, die als nächstes abgefragt werden sollen

support_points = [] # wird vom User manuell in der UI gesetzt

current_underlying_price = None # Wird mit jeder Option aktualisiert, die abgefragt wird



# === 4. Argument Parsing ===
if len(sys.argv) < 3:
    print(f"Usage: {sys.argv[0]} <YYYY-MM-DD> [C|P]")
    print("  C = Calls,  P = Puts")
    sys.exit(1)

# 1. Argument prüfen: Ablaufdatum der Optionen
date_str = sys.argv[1]
opt_str = sys.argv[2].upper()

try:
    date_obj = datetime.strptime(date_str, "%Y-%m-%d")
except ValueError:
    print("Ungültiges Datumsformat. Bitte verwende YYYY-MM-DD.")
    sys.exit(1)

# 2. Argument prüfen: Optionstyp (C oder P)
if opt_str not in ("C", "P"):
    print("Ungültiger Optionstyp. Bitte verwende 'C' für Calls oder 'P' für Puts.")
    sys.exit(1)

use_calls = (opt_str == "C")
day = date_obj.day
month_abbr = calendar.month_abbr[date_obj.month].upper()
year_suffix = str(date_obj.year)[-2:]
future_name = f"BTC-{day}{month_abbr}{year_suffix}"
future_exists = Deribit().instrument_exists(future_name)
expiration = datetime(
    year=date_obj.year,
    month=date_obj.month,
    day=date_obj.day,
    hour=8,
    minute=0,
    second=0,
    tzinfo=timezone.utc
)


# === 5. Data-Fetch Loops ===

def fetch_future_candles_loop(future_name: str) -> None:
    """
    Continuously fetches 1-minute OHLC candle data for a given futures contract
    and updates the global `candles` list.

    Args:
        future_name (str):
            Der Deribit-Instrumentenname des Futures, z. B. "BTC-20JUN25-9000-P".
    Returns:
        None
    Globals:
        candles (list of dict):
            Eine Liste von Dikt-Einträgen mit den folgenden Keys:
              - "timestamp" (int): POSIX-Millisekundenzeitpunkt
              - "open"      (float): Eröffnungspreis
              - "high"      (float): Höchstpreis
              - "low"       (float): Tiefstpreis
              - "close"     (float): Schlusskurs
    Raises:
        Keine Exceptions werden geworfen: Netzwerk- oder Antwortfehler werden
        abgefangen und mit `print()` gemeldet.
    Side Effects:
        - Sendet HTTP-POST-Requests an DERIBIT_URL
        - Aktualisiert die globale Variable `candles`
        - Wartet jeweils FETCH_FUTURES_INTERVALL Sekunden zwischen den Aufrufen
    Example:
        >>> import threading
        >>> threading.Thread(
        ...     target=fetch_future_candles_loop,
        ...     args=("BTC-20JUN25-9000-P",),
        ...     daemon=True
        ... ).start()
    """
    global candles

    while True:
        now = int(datetime.now(timezone.utc).timestamp() * 1000)

        payload = {
            "jsonrpc": "2.0",
            "id": 833,
            "method": "public/get_tradingview_chart_data",
            "params": {
                "instrument_name": future_name,
                "start_timestamp": program_start_time,
                "end_timestamp": now,
                "resolution": "1"
            }
        }

        try:
            response = requests.post(DERIBIT_URL, json=payload)
            data = response.json()

            if "result" in data and data["result"]["status"] == "ok":
                result = data["result"]
                ticks = result["ticks"]
                open_ = result["open"]
                high = result["high"]
                low = result["low"]
                close = result["close"]

                candles.clear()
                for t, o, h, l, c in zip(ticks, open_, high, low, close):
                    candles.append({
                        "timestamp": t,
                        "open": o,
                        "high": h,
                        "low": l,
                        "close": c
                    })

        except Exception as e:
            print(f"Fehler beim Abruf: {e}")

        time.sleep(FETCH_FUTURES_INTERVALL)



def fetch_points_loop(stack: deque) -> None:
    """
    Continuously fetches mark prices for a rolling set of call or put options
    and updates the global `points` list as well as the global 
    `current_underlying_price`.

    On startup, it initializes the Deribit client, retrieves the full list of
    call or put instruments for the global `expiration` date (depending on
    `use_calls`), and seeds the `stack`. In each loop iteration, it:
      1. Pops the next option from `stack`.
      2. Retrieves the latest ticker (mark price and underlying price).
      3. Appends a tuple (strike - underlying_price, mark_price) to `points`.
      4. Updates `current_underlying_price`.
      5. Pushes the option back onto `stack`.
      6. Sleeps to respect the rate limit defined by `OPTIONS_REQUESTS_PER_SECOND`.

    Args:
        stack: A deque of Option objects to cycle through.

    Side Effects:
        - Mutates global `points`: adds (normalized_strike, mark_price) entries.
        - Mutates global `current_underlying_price`.
        - Sends repeated API calls to Deribit.
        - Sleeps 1/OPTIONS_REQUESTS_PER_SECOND seconds per iteration.

    Raises:
        None: All exceptions (network errors, JSON errors, etc.) are caught
        and logged via print().

    Example:
        >>> import threading
        >>> threading.Thread(
        ...     target=fetch_points_loop,
        ...     args=(stack,),
        ...     daemon=True
        ... ).start()
    """
    global current_underlying_price

    deribit = Deribit()
    if use_calls:
        options = deribit.fetch_calls(expiration)
    else:
        options = deribit.fetch_puts(expiration)
    stack.extend(options)

    while True:
        if stack:
            option = stack.popleft()
            try:
                ticker = deribit._get_ticker(option.instrument_name)
                mark = ticker["mark_price"]
                points.append((option.strike - ticker["underlying_price"], mark))
                current_underlying_price = ticker["underlying_price"]
            except Exception as e:
                print(f"Fehler bei {option.instrument_name}: {e}")
            stack.append(option)
        else:
            print(
                """
                Fehler!
                Keine Optionen zum Abfragen im Stack vorhanden.
                Prüfe bei Deribit, dass für das angegebene Ablaufdatum Optionen existieren.
                Bitte beende den Prozess und starte ihn neu mit einem gültigen Ablaufdatum.
                """
            )
            sys.exit(1)
        time.sleep(1/OPTIONS_REQUESTS_PER_SECOND)





# === 6. Dash App ===
app = Dash(__name__)


# 6.1 Layout dynamisch zusammenbauen
layout_children = [
    html.H2("Option implied PDF"),
]

if future_exists:
    layout_children += [
        dcc.Graph(id="future-plot"),
        dcc.Interval(
            id="future-refresh",
            interval=FETCH_FUTURES_INTERVALL * 1000,
            n_intervals=0
        ),
    ]

layout_children += [
    dcc.Graph(id='points-plot'),
    dcc.Interval(
        id='points-refresh',
        interval=1000 / OPTIONS_REQUESTS_PER_SECOND,
        n_intervals=0
    ),
    html.Div(id='points-count'),

    html.Div(
        f"Datenpunkte mit Mark Price < {MIN_MARK_PRICE} werden herausgefiltert",
        style={'marginTop': '10px', 'fontStyle': 'italic'}
    ),
    html.Div(
        f"Datenpunkte mit Mark Price > {MAX_MARK_PRICE} werden herausgefiltert",
        style={'marginTop': '10px', 'fontStyle': 'italic'}
    ),
    html.Div(
        "Current Best Practise: spline degree of 3 und viele support points die zur mitte hin dichter werden",
        style={'marginTop': '10px', 'fontStyle': 'italic'}
    ),
    html.Div(id='support-points-display'),
    html.Div(
        "Rule: Support Points inklusive 0 aufsteigend; "
        "min(filtered(points)[x-Wert]) < min(support_points) and "
        "max(support_points) < max(filtered(points)[x-Wert])",
        style={'marginTop': '10px', 'fontStyle': 'italic'}
    ),
    dcc.Input(
        id='support-points-input',
        type='text',
        placeholder='z.B. -10000, -5000, -1000, 0, 1000, 5000, 10000',
        style={'width': '60%'}
    ),
    html.Button('Absenden', id='support-points-input-button'),

    html.Div([
        html.Label("Degree of spline:"),
        dcc.RadioItems(
            id='spline-degree',
            options=[
                {'label': '3', 'value': 3},
                {'label': '4', 'value': 4},
                {'label': '5', 'value': 5},
            ],
            value=3,
            labelStyle={'display': 'inline-block', 'margin-right': '10px'}
        )
    ], style={'margin': '20px 0'}),

    dcc.Graph(id="function-fit-plot"),
    dcc.Graph(id="first-derivative-plot"),
    dcc.Graph(id="second-derivative-plot"),
    dcc.Graph(id="second-derivative-original-plot"),
    dcc.Interval(
        id="function-fit-refresh",
        interval=UPDATE_FUNCTION_FIT_INTERVALL * 1000,
        n_intervals=0
    ),

    html.Div(
        "Wähle a und b (a < b) für die Wahrscheinlichkeit (a = -1 setzt a auf original_x_min, b = 0 setzt b auf original_x_max):",
        style={'marginTop': '20px', 'fontWeight': 'bold'}
    ),
    dcc.Input(
        id='input-a',
        type='number',
        placeholder='a ( > original_x_min )',
        style={'marginRight': '10px'}
    ),
    dcc.Input(
        id='input-b',
        type='number',
        placeholder='b ( < original_x_max )'
    ),
    html.Div(
        id='probability-output',
        style={'marginTop': '10px', 'fontWeight': 'bold'}
    ),
]
    
app.layout = html.Div(layout_children)

# 6.2 Callbacks

@app.callback(
    Output("future-plot", "figure"),
    Input("future-refresh", "n_intervals")  # ausgelöst durch dcc.Interval(id="future-refresh")
)
def update_future_plot(n: int) -> go.Figure:
    """
    Trigger:
        Durch das dcc.Interval-Element 'future-refresh', das alle
        FETCH_FUTURES_INTERVALL Sekunden n_intervals inkrementiert.

    Inputs:
        n (int): Anzahl der bisherigen Interval-Auslösungen (nicht weiterverwendet,
                 dient nur als Trigger).

    Outputs:
        go.Figure: Candlestick-Chart des aktuellen Futures.

    Hinweise:
        - uirevision='static' sorgt dafür, dass Zoom/Pan im Chart erhalten bleiben
          auch wenn die Daten aktualisiert werden.
    """
    if not candles:
        return go.Figure()

    # Zeitstempel umwandeln und Candlestick-Daten vorbereiten
    timestamps = [datetime.fromtimestamp(c["timestamp"] / 1000) for c in candles]
    fig = go.Figure(
        data=[
            go.Candlestick(
                x=timestamps,
                open=[c["open"] for c in candles],
                high=[c["high"] for c in candles],
                low=[c["low"] for c in candles],
                close=[c["close"] for c in candles],
                name="1min Candles"
            )
        ]
    )

    # Layout konfigurieren
    fig.update_layout(
        xaxis_title="Zeit",
        yaxis_title="Preis",
        title=f"{future_name} 1min chart",
        xaxis_rangeslider_visible=False,
        uirevision="static"
    )
    return fig




@app.callback(
    [Output('points-plot', 'figure'), Output('points-count', 'children')],
    Input('points-refresh', 'n_intervals')  # ausgelöst bei jedem Interval-Update
)
def update_points_plot(n: int) -> Tuple[go.Figure, str]:
    """
    Trigger:
        Wird ausgelöst durch das dcc.Interval-Element 'points-refresh',
        das mit der Frequenz 1/OPTIONS_REQUESTS_PER_SECOND Seconds feuert.

    Inputs:
        n (int): Anzahl der bisherigen Interval-Auslösungen (nur als Trigger genutzt).

    Outputs:
        Tuple[go.Figure, str]:
            - go.Figure: Scatter-Plot aller aktuell gesammelten Punkte.
            - str:   Label mit der Gesamtanzahl der Punkte.

    Hinweise:
        - uirevision='static' sorgt dafür, dass Zoom/Pan-Einstellungen im Plot
          nach Aktualisierungen beibehalten werden.
    """
    # Falls noch keine Punkte vorhanden sind, leere Figure und 0 zurückgeben
    if not points:
        return go.Figure(), "Anzahl der Punkte: 0"

    # Daten für Scatter-Plot aufbereiten
    strikes, prices = zip(*points)
    fig = go.Figure(
        data=[
            go.Scatter(
                x=strikes,
                y=prices,
                mode='markers',
                marker=dict(color='blue'),
                name='Messpunkte'
            )
        ]
    )

    # Layout konfigurieren
    fig.update_layout(
        title='Datapoints',
        xaxis=dict(title='Strike - Underlying Price'),
        yaxis=dict(title='Mark Price'),
        uirevision='static'
    )

    # Anzahl der Punkte als String
    count_label = f"Anzahl der Punkte: {len(points)}"
    return fig, count_label




@app.callback(
    Output('support-points-display', 'children'),
    Input('support-points-input-button', 'n_clicks'),  # ausgelöst bei jedem Button-Klick
    State('support-points-input', 'value'),
    prevent_initial_call=True
)
def update_support_points(n_clicks: int, input_text: str) -> str:
    """
    Trigger:
        Wird durch Klick auf den Button 'Absenden' ausgelöst.

    Inputs:
        n_clicks (int): Anzahl der bisherigen Klicks auf den Button.
        input_text (str): Inhalt des Input-Feldes (Komma-separierte Ganzzahlen).

    Outputs:
        str: Statusnachricht, ob die Support Points erfolgreich gesetzt
             wurden oder welcher Validierungsfehler aufgetreten ist.

    Validierung:
        1. Eingabe darf nicht leer sein.
        2. Nur Ganzzahlen, getrennt durch Kommata.
        3. Die Liste muss die 0 enthalten.
        4. Werte müssen streng aufsteigend sein.
    """
    global support_points

    if not input_text:
        return "Keine Eingabe erkannt."

    # 1) Parsen aller durch Komma getrennten Werte in ints
    try:
        parsed = [int(x.strip()) for x in input_text.split(',')]
    except ValueError:
        return "Fehler: Bitte nur Ganzzahlen eingeben, getrennt durch Kommata."

    # 2) Muss 0 enthalten
    if 0 not in parsed:
        return "Fehler: Die Liste muss die 0 enthalten."

    # 3) Prüfen auf streng aufsteigende Reihenfolge
    if any(parsed[i] >= parsed[i + 1] for i in range(len(parsed) - 1)):
        return "Fehler: Die Werte müssen streng aufsteigend sein."

    # 4) Validierung bestanden → globales Array aktualisieren
    support_points = parsed.copy()
    return "Support Points gesetzt: " + ", ".join(map(str, support_points))




@app.callback(
    [Output("function-fit-plot", "figure"), 
     Output("first-derivative-plot", "figure"),
     Output("second-derivative-plot", "figure"),
     Output("second-derivative-original-plot", "figure"),
     Output("probability-output", "children")],
    Input("function-fit-refresh", "n_intervals"),
    State("spline-degree", "value"),
    State("input-a", "value"),
    State("input-b", "value")
)
def update_function_fit_plot(n, degree_of_spline, a: float, b: float) -> Tuple[go.Figure, go.Figure, go.Figure, go.Figure, str]:
    """
    Updates all spline-related plots and computes probability for a given interval.

    Trigger:
        Durch das dcc.Interval-Element 'function-fit-refresh', das alle
        UPDATE_FUNCTION_FIT_INTERVALL Sekunden n_intervals inkrementiert.

    Args:
        n (int): Number of interval triggers (unused, serves as trigger flag).
        degree_of_spline (int): Desired polynomial degree for the spline fit.
        a (float): Lower bound 'a' for probability interval in original x units.
        b (float): Upper bound 'b' for probability interval in original x units.

    Returns:
        Tuple containing:
        - fig (go.Figure): Spline fit over filtered data points.
        - fig_first_derivative (go.Figure): Plot of first derivative f'(x).
        - fig_second_derivative (go.Figure): Plot of second derivative f''(x) in scaled domain.
        - fig_second_derivative_original (go.Figure): Plot of second derivative f''(x) in original x domain.
        - prob_text (str): Description of computed probability P(a < X < b).

    Workflow:
        1. Copy global lists `points` and `support_points` to avoid side effects.
        2. Filter raw points by MIN_MARK_PRICE and MAX_MARK_PRICE.
        3. Determine min_strike and max_strike from filtered data.
        4. Scale strikes and support points into [-1, 1] using scale_x_value.
        5. Call fit_parameter() to solve for spline coefficients in scaled space.
        6. Assemble spline functions for f, f', f'' via assemble_splines and unscale_splines.
        7. Reconstruct original domain functions for derivatives.
        8. (Optional) Export fit data to shared_data.pkl if EXPORT_FUNCTION_FIT is True.
        9. Generate Plotly figures for function and its derivatives.
        10. Compute total and interval probabilities via the unscaled first derivative.

    Raises:
        None: Any intermediate exceptions are caught or prevented by checks.
    """
    # kopiere die globalen Variablen in lokale Variablen um Seiten-Effekte zu vermeiden
    konvex_until = current_underlying_price

    # Points sind in der range -x < 0 < +y
    if not points or not support_points:
        return go.Figure(), go.Figure(), go.Figure(), go.Figure(), ""

    copied_points = points.copy()
    copied_support_points = support_points.copy()



    # === Filtern ===
    filtered_points = [
        (s, p) for s, p in copied_points
        if p >= MIN_MARK_PRICE and p <= MAX_MARK_PRICE
    ]

    min_strike = min(filtered_points, key=lambda x: x[0])[0]
    max_strike = max(filtered_points, key=lambda x: x[0])[0]



    # === Skalieren ===
    # Nun skalieren wir alles in den Raum [-1.0, 1.0] damit der solver arbeiten kann

    # 1) Skalieren der punkte
    scaled_points = [
        (scale_x_value(x, min_strike, max_strike, scaled_bounds=(-1.0, 1.0)), price)
        for x, price in filtered_points
    ]


    # Skalieren aller support_points auf [-1,1]
    scaled_support_points = [
        scale_x_value(
            original_x=sp,
            original_x_min=min_strike,
            original_x_max=max_strike,
            scaled_bounds=(-1.0, 1.0)
        )
        for sp in copied_support_points
    ]

    # Ebenso den konvex_until-Wert
    scaled_konvex_until = scale_x_value(
        original_x=0,
        original_x_min=min_strike,
        original_x_max=max_strike,
        scaled_bounds=(-1.0, 1.0)
    )

    # Bounds skalieren (ergibt -1.0 und +1.0)
    scaled_bounds = (-1.0, 1.0)




    #  === Fit im skalierten Raum ===
    status, value, matrix = fit_parameter(
        points=scaled_points,
        support_points=scaled_support_points,
        konvex_until=scaled_konvex_until,
        bounds=scaled_bounds,
        degree_of_spline= degree_of_spline,
        sampling_interval=SAMPLING_INTERVAL
    )



    # === Spline-Funktionen generieren und in gewünschte Ranges skalieren===
    spline_scaled = assemble_splines(
        matrix=matrix,
        support_points=scaled_support_points,
        bounds=scaled_bounds,
        derivative=0
    )
    spline = unscale_splines(
        spline_scaled,
        original_x_min=min_strike,
        original_x_max=max_strike,
        scaled_bounds=scaled_bounds
    )


    first_derivative_scaled = assemble_splines(
        matrix=matrix,
        support_points=scaled_support_points,
        bounds=scaled_bounds,
        derivative=1
    )
    first_derivative = unscale_splines(
        first_derivative_scaled,
        original_x_min=min_strike,
        original_x_max=max_strike,
        scaled_bounds=scaled_bounds
    )


    second_derivative_scaled = assemble_splines(
        matrix=matrix,
        support_points=scaled_support_points,
        bounds=scaled_bounds,
        derivative=2
    )
    second_derivative = unscale_splines(
        second_derivative_scaled,
        original_x_min=min_strike,
        original_x_max=max_strike,
        scaled_bounds=scaled_bounds
    )


    # === Originale Range konstruieren ===
    # wieder in der Range x < current_underlying_price < y

    original_points = []
    
    for strike, price in filtered_points:
        original_x = strike + konvex_until
        original_points.append((original_x, price))

    original_x_min = min(original_points, key=lambda x: x[0])[0] # 85 000
    original_x_max = max(original_points, key=lambda x: x[0])[0] # 150 000

    first_derivative_original = unscale_splines(
        first_derivative_scaled,
        original_x_min=original_x_min,
        original_x_max=original_x_max,
        scaled_bounds=scaled_bounds
    )

    second_derivative_original = unscale_splines(
        second_derivative_scaled,
        original_x_min=original_x_min,
        original_x_max=original_x_max,
        scaled_bounds=scaled_bounds
    )



    # === Daten exportieren ===
    if EXPORT_FUNCTION_FIT:
        @dataclass
        class SharedData:
            timestamp: datetime
            current_underlying_price: float
            expiration: datetime
            matrix: np.ndarray    
            scaled_support_points: List[float]                     
            scaled_bounds: Tuple[float, float]
            original_x_min: float
            original_x_max: float

        shared_data = SharedData(
            timestamp=datetime.now(timezone.utc),
            expiration=expiration,
            current_underlying_price=konvex_until,
            matrix=matrix,
            scaled_support_points=scaled_support_points,
            scaled_bounds=scaled_bounds,
            original_x_min=original_x_min,
            original_x_max=original_x_max
        )

        with open("shared_data.pkl", "wb") as f:
            pickle.dump(shared_data, f)



    # === Plot generieren ===
    #  Fit-Kurve generieren
    xs_fit = np.linspace(min_strike, max_strike, 50)
    ys_fit = [spline(x) for x in xs_fit]

    #  Plot bauen
    fig = go.Figure()
    xs, ys = zip(*filtered_points)
    fig.add_trace(go.Scatter(
        x=list(xs), y=list(ys),
        mode='markers', name='Originalpunkte',
        marker=dict(color='blue', size=6)
    ))
    fig.add_trace(go.Scatter(
        x=xs_fit, y=ys_fit,
        mode='lines', name=f'Spline (Grad={degree_of_spline})',
        line=dict(color='red', width=2)
    ))

    fig.update_layout(
        title=f"Spline-Fit (degree={degree_of_spline}), Status={status}, Ziel={value:.2e}",
        xaxis_title="Strike",
        yaxis_title="Mark Price",
        uirevision='static'
    )
    


    # === 1. Ableitung Plot ===
    xs_first_derivative = np.linspace(min_strike, max_strike, 50)
    ys_first_derivative = [first_derivative(x) for x in xs_first_derivative]

    fig_first_derivative = go.Figure()
    fig_first_derivative.add_trace(go.Scatter(
        x=xs_first_derivative, y=ys_first_derivative,
        mode='lines', name='1. Ableitung',
        line=dict(color='green', width=2)
    ))

    fig_first_derivative.update_layout(
        title="1. Ableitung der Spline-Funktion",
        xaxis_title="Strike",
        yaxis_title="1. Ableitung",
        uirevision='static'  # Zoom/Pan erhalten
    )



    # === 2. Ableitung Plot ===
    xs_second_derivative = np.linspace(min_strike, max_strike, 50)
    ys_second_derivative = [second_derivative(x) for x in xs_second_derivative]

    fig_second_derivative = go.Figure()
    fig_second_derivative.add_trace(go.Scatter(
        x=xs_second_derivative, y=ys_second_derivative,
        mode='lines', name='2. Ableitung',
        line=dict(color='orange', width=2)
    ))

    fig_second_derivative.update_layout(
        title="2. Ableitung der Spline-Funktion",
        xaxis_title="Strike",
        yaxis_title="2. Ableitung",
        uirevision='static'  # Zoom/Pan erhalten
    )



    # === 2. Ableitung Original Plot ===
    xs_second_derivative_original = np.linspace(original_x_min, original_x_max, 50)
    ys_second_derivative_original = [second_derivative_original(x) for x in xs_second_derivative_original]

    fig_second_derivative_original = go.Figure()
    fig_second_derivative_original.add_trace(go.Scatter(
        x=xs_second_derivative_original, y=ys_second_derivative_original,
        mode='lines', name='2. Ableitung (Original)',
        line=dict(color='orange', width=2)
    ))

    fig_second_derivative_original.update_layout(
        title="2. Ableitung der Spline-Funktion (Original)",
        xaxis_title="Strike (Original)",
        yaxis_title="2. Ableitung",
        uirevision='static'  # Zoom/Pan erhalten
    )

    if a == -1:
        a = original_x_min
    if b == 0:
        b = original_x_max


    total_prob = first_derivative_original(original_x_max) - first_derivative_original(original_x_min)

    prob_text = ""

    # Nur wenn beide Inputs gesetzt sind
    if a is not None and b is not None:
        # Gültigkeitsprüfung: in Range und a < b
        if not (original_x_min <= a < b <= original_x_max):
            prob_text = (
                f"Fehler: a und b müssen im Bereich "
                f"({original_x_min}, {original_x_max}) liegen und a < b sein."
            )
        else:
            # Teil-Wahrscheinlichkeit
            part_prob = first_derivative_original(b) - first_derivative_original(a)
            rel_prob = part_prob / total_prob
            prob_text = (
                f"Wenn der Preis zwischen {original_x_min} und {original_x_max} liegt, dann ist die Wahrscheinlichkeit, dass der Preis zwischen "
                f"{a} und {b} liegt, laut Markt {rel_prob}."
            )


    return fig, fig_first_derivative, fig_second_derivative, fig_second_derivative_original, prob_text



# === 7. Main ===
if __name__ == "__main__":
    logging.getLogger('werkzeug').setLevel(logging.WARNING) # verhindert, dass bei jedem Callback eine Nachricht im Terminal erscheint

    if future_exists:
        threading.Thread(
            target=lambda: fetch_future_candles_loop(future_name),
            daemon=True
        ).start()
    else:
        print(f"Future {future_name} could not be fetched. Check wether the future is available on Deribit. For some options the underlying is synthetic and not a traded future. In that case just ignore this message.")

    threading.Thread(
        target=fetch_points_loop, args=(stack,), 
        daemon=True
    ).start()

    app.run(debug=False) # port=8049, 
