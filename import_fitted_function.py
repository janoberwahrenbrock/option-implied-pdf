"""
This is a blueprint for extracting the fitted function from run.py via shared_data.pkl and enables further processing.
You need to set EXPORT_FUNCTION_FIT=True in run.py so that run.py always expots the fitted function via shared_data.pkl.
"""


import pickle
import numpy as np
import pandas as pd
from dataclasses import dataclass
from typing import List, Tuple
from datetime import datetime, timedelta, timezone

from model import assemble_splines
from scale import unscale_splines

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


with open("shared_data.pkl", "rb") as f:
    shared_data = pickle.load(f)

data = SharedData(
    timestamp=shared_data.timestamp,
    current_underlying_price=shared_data.current_underlying_price,
    expiration=shared_data.expiration,
    matrix=shared_data.matrix,
    scaled_support_points=shared_data.scaled_support_points,
    scaled_bounds=shared_data.scaled_bounds,
    original_x_min=shared_data.original_x_min,
    original_x_max=shared_data.original_x_max   
)


# Erste Ableitung im skalierten Raum berechnen
spline_deriv_scaled = assemble_splines(
    matrix=data.matrix,
    support_points=data.scaled_support_points,
    bounds=data.scaled_bounds,
    derivative=1
)

# Unscale der Ableitung in den originalen X-Bereich
spline_deriv = unscale_splines(
    spline_deriv_scaled,
    original_x_min=data.original_x_min,
    original_x_max=data.original_x_max,
    scaled_bounds=data.scaled_bounds
)

# === Your Calculations Here ===
