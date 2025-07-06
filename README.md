# option-implied-probability-density-function

### Introduction

Given a sparse set of BTC option prices (strike granularity > 1 000 USD), this project estimates a reliable probability density function (PDF) reflecting the market’s view of future volatility.

### Use Cases

- **Probability queries**: "What probability has the market priced in for BTC to expire in [a, b]?"
- **Pricing derivatives**: Compute fair values for instruments like binary options based on the implied PDF.

### Methodology Overview

The mathematical derivation is detailed in **methodology.pdf**. This README focuses on running the code in this repository.

### Generalization

While the reference implementation targets BTC options on Deribit, the same methodology applies to any options market. Minimal code adjustments allow you to extract an implied PDF for other underlyings and exchanges.

## File Overview

- **run.py**: Primary entry point for interactive use.
  ```bash
  python run.py YYYY-MM-DD [P|C]
  ```
  - `YYYY-MM-DD`: expiration date of the options.
  - `P` or `C`: choose put or call options.
  - Key parameters (e.g. spline degree, support points) can be adjusted via the web UI.
  - Continuously fetches new data points to refine the fit and updates plots at a fixed interval.
  - Optional export of the fitted function to `shared_data.pkl` for external use.

- **snapshot.py**: Non-interactive example with a hard‑coded expiration date.
  - Fetches data once and performs a single spline fit (no UI).
  - Useful for understanding the core workflow without real‑time updates.

- **options_visible.py**: A Streamlit script to inspect available option chains on Deribit.
  ```bash
  streamlit run options_visible.py
  ```

- **import_fitted_function.py**: Demonstrates loading the exported `shared_data.pkl` and using the fitted spline in a separate program.

- **model.py**: Core implementation of the spline-fitting methodology (CVXPY, convexity/concavity constraints).

- **scale.py**: Helper functions to scale strike values into a numerically stable range for polynomial fitting.

- **exchange.py**: Abstract base class defining the broker interface for option data providers.

- **deribit.py**: Concrete implementation of `exchange.py` for Deribit’s BTC options API.

## Dependencies

Install Python dependencies via:
```bash
pip install -r requirements.txt
```
