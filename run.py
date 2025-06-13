import threading
import time
import sys
from datetime import datetime, timezone
from dash import Dash, dcc, html
from dash.dependencies import Input, Output, State
import plotly.graph_objs as go
import requests
import calendar
from collections import deque
import numpy as np


from scale import scale_x_value, unscale_x_value, unscale_splines
from deribit import Deribit
from model import fit_parameter, assemble_splines, plot_func
from exchange import Option


# === Einstellungen ===
DERIBIT_URL = "https://www.deribit.com/api/v2/"
FETCH_FUTURES_INTERVALL = 10 # Pause bevor erneut die OHLC Candles abgefragt werden
OPTIONS_REQUESTS_PER_SECOND = 10 # Anzahl der Anfragen pro Sekunde für die Optionen
UPDATE_FUNCTION_FIT_INTERVALL = 10 # Intervall in Sekunden, um die Funktion Fit zu aktualisieren
SAMPLING_INTERVAL = 0.01 # Intervall für die Abtastung der Spline-Funktion
MIN_MARK_PRICE = 0.0005 # Minimaler Mark-Preis für die Punkte, die in den Fit einfließen sollen


# === Globale Variablen ===
candles = []
points = []
stack = deque()
START_TIMESTAMP = int(datetime.now(timezone.utc).timestamp() * 1000)
future_name = None # Later initialized with the future name based on the input date
expiration = None # Will be set based on the input date
current_underlying_price = None # Wird später gesetzt, wenn die Optionen abgerufen werden
support_points = []



# === Argument prüfen ===
if len(sys.argv) < 2:
    print("1. Argument: expiration für Option fehlt (Format: 2025-06-20)")
    sys.exit(1)

try:
    date_str = sys.argv[1]
    date_obj = datetime.strptime(date_str, "%Y-%m-%d")
except ValueError:
    print("Ungültiges Datumsformat. Bitte verwende YYYY-MM-DD.")
    sys.exit(1)

day = date_obj.day
month_abbr = calendar.month_abbr[date_obj.month].upper()
year_suffix = str(date_obj.year)[-2:]
future_name = f"BTC-{day:02}{month_abbr}{year_suffix}"
expiration = datetime(
    year=date_obj.year,
    month=date_obj.month,
    day=date_obj.day,
    hour=8,
    minute=0,
    second=0,
    tzinfo=timezone.utc
)




def fetch_future_candles_loop(future_name: str):
    global candles
    while True:
        now = int(datetime.now(timezone.utc).timestamp() * 1000)
        start = START_TIMESTAMP

        payload = {
            "jsonrpc": "2.0",
            "id": 833,
            "method": "public/get_tradingview_chart_data",
            "params": {
                "instrument_name": future_name,
                "start_timestamp": start,
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


def fetch_points_loop(stack: deque):
    global current_underlying_price

    deribit = Deribit()
    options = deribit.fetch_calls(expiration)
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
        time.sleep(1/OPTIONS_REQUESTS_PER_SECOND)


# === Dash App ===
app = Dash(__name__)
app.layout = html.Div([
    html.H2("Option implied PDF"),

    dcc.Graph(id="future-plot"),
    dcc.Interval(id="future-refresh", interval=FETCH_FUTURES_INTERVALL * 1000, n_intervals=0),

    dcc.Graph(id='points-plot'),
    dcc.Interval(id='points-refresh', interval=1/OPTIONS_REQUESTS_PER_SECOND*1000, n_intervals=0),
    html.Div(id='points-count'),

    html.Div(f"Datenpunkte mit Mark Price < {MIN_MARK_PRICE} werden herausgefiltert", style={'marginTop': '10px', 'fontStyle': 'italic'}),
    html.Div("Current Best Practise: spline degree of 3 und viele support points (ruhig 15) die zur mitte hin enger werden", style={'marginTop': '10px', 'fontStyle': 'italic'}),
    html.Div(id='support-points-display'),
    html.Div("Support Points inklusive 0 aufsteigend; min(filtered(points)[0]) < min(support_points) and max(support_points) < max(filtered(points)[0]) ", style={'marginTop': '10px', 'fontStyle': 'italic'}),
    dcc.Input(id='support-points-input', type='text', placeholder='z.B. -10000, -5000, -1000, 0, 1000, 5000, 10000', style={'width': '60%'}),
    html.Button('Absenden', id='support-points-input-button'),

    # Auswahl für den Spline-Grad
    html.Div([
        html.Label("Degree of spline:"),
        dcc.RadioItems(
            id='spline-degree',
            options=[
                {'label': '3', 'value': 3},
                {'label': '4', 'value': 4},
                {'label': '5', 'value': 5},
            ],
            value=3,  # default
            labelStyle={'display': 'inline-block', 'margin-right': '10px'}
        )
    ], style={'margin': '20px 0'}),

    dcc.Graph(id="function-fit-plot"),
    dcc.Graph(id="first-derivative-plot"),
    dcc.Graph(id="second-derivative-plot"),
    dcc.Graph(id="second-derivative-original-plot"),
    dcc.Interval(id="function-fit-refresh", interval=UPDATE_FUNCTION_FIT_INTERVALL * 1000, n_intervals=0),


])









@app.callback(
    [Output("function-fit-plot", "figure"), 
     Output("first-derivative-plot", "figure"),
     Output("second-derivative-plot", "figure"),
     Output("second-derivative-original-plot", "figure")],
    Input("function-fit-refresh", "n_intervals"),
    State("spline-degree", "value")
)
def update_function_fit_plot(n, degree_of_spline):
    global current_underlying_price
    # kopiere die globalen Variablen in lokale Variablen um Seiten-Effekte zu vermeiden
    # current_underlying_price wird in konvex_until verwendet
    konvex_until = current_underlying_price


    if not points or not support_points:
        return go.Figure(), go.Figure(), go.Figure(), go.Figure()

    copied_points = points.copy()
    copied_support_points = support_points.copy()



    # === Filtern ===
    # entferne die Punkte aus copied_points die einen Mark-Price kleiner als 0.005 haben
    filtered_points = [
        (s, p) for s, p in copied_points
        if p >= MIN_MARK_PRICE
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

    #  Fit im skalierten Raum
    status, value, matrix = fit_parameter(
        points=scaled_points,
        support_points=scaled_support_points,
        konvex_until=scaled_konvex_until,
        bounds=scaled_bounds,
        degree_of_spline= degree_of_spline,
        sampling_interval=SAMPLING_INTERVAL
    )




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





    # 7) Fit-Kurve generieren
    xs_fit = np.linspace(min_strike, max_strike, 50)
    ys_fit = [spline(x) for x in xs_fit]

    # 8) Plot bauen
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




    # === Originale Punkte und Support-Punkte ===
    # wieder in der Range 85 000 bis 150 000 statt -20 000 bis 50 000

    original_points = []
    
    for strike, price in filtered_points:
        original_x = strike + konvex_until
        original_points.append((original_x, price))


    original_x_min = min(original_points, key=lambda x: x[0])[0] # 85 000
    original_x_max = max(original_points, key=lambda x: x[0])[0] # 150 000


    second_derivative_original = unscale_splines(
        second_derivative_scaled,
        original_x_min=original_x_min,
        original_x_max=original_x_max,
        scaled_bounds=scaled_bounds
    )


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




    # erste ableitung original
    first_derivative_original = unscale_splines(
        first_derivative_scaled,
        original_x_min=original_x_min,
        original_x_max=original_x_max,
        scaled_bounds=scaled_bounds
    )
    print(first_derivative_original(106000)-first_derivative_original(104000))
    print(first_derivative_original(119500)-first_derivative_original(85500))


    # first_derivative_original will ich exportieren




    return fig, fig_first_derivative, fig_second_derivative, fig_second_derivative_original  # Leerer Plot für den Original-Plot


    


@app.callback(
    Output("future-plot", "figure"),
    Input("future-refresh", "n_intervals") # n_intervals wird bei jedem Intervall-Update erhöht
)
def update_future_plot(n):
    if not candles:
        return go.Figure()

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
    fig.update_layout(
        xaxis_title="Zeit",
        yaxis_title="Preis",
        title=f"{future_name} 1min chart",
        xaxis_rangeslider_visible=False,
        uirevision='static'  # Zoom/Pan erhalten
    )
    return fig




@app.callback(
    [Output('points-plot', 'figure'), Output('points-count', 'children')],
    Input('points-refresh', 'n_intervals')
)
def update_points_plot(n):
    if not points:
        return go.Figure(), "Anzahl der Punkte: 0"
    strikes, prices = zip(*points)
    fig = go.Figure(
        data=[
            go.Scatter(
                x=strikes,
                y=prices,
                mode='markers',
                marker=dict(color='blue')
            )
        ],
        layout=go.Layout(
            xaxis=dict(title='Strike - underlying_price for every measured option'),
            yaxis=dict(title='Mark Price of measured option'),
            title='Datapoints',
            uirevision='static'  # Zoom/Pan erhalten
        )
    )
    return fig, f"Anzahl der Punkte: {len(points)}"




@app.callback(
    Output('support-points-display', 'children'),
    Input('support-points-input-button', 'n_clicks'),
    State('support-points-input', 'value'),
    prevent_initial_call=True
)
def update_support_points(n_clicks, input_text):
    global support_points, current_underlying_price

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
    if any(parsed[i] >= parsed[i+1] for i in range(len(parsed)-1)):
        return "Fehler: Die Werte müssen streng aufsteigend sein."

    # 4) Validierung bestanden → globales Array aktualisieren
    support_points = parsed.copy()

    return "Support Points gesetzt: " + ", ".join(map(str, support_points))






if __name__ == "__main__":

    threading.Thread(
        target=lambda: fetch_future_candles_loop(future_name),
        daemon=True
    ).start()

    threading.Thread(
        target=fetch_points_loop, args=(stack,), 
        daemon=True
    ).start()

    app.run()
