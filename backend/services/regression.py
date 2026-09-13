"""
regression.py
--------------
Shared linear regression utility used by every kinetic method.
"""

import numpy as np
from scipy import stats


def linear_regression(x, y):
    """
    Perform simple linear regression y = m*x + b using SciPy.

    Returns a dict with slope, intercept, r_squared, r_value and std_err,
    all as plain Python floats (JSON-serializable).
    """
    x_arr = np.asarray(x, dtype=float)
    y_arr = np.asarray(y, dtype=float)

    if x_arr.size < 2:
        raise ValueError("At least two points are required to perform a linear regression.")

    if not np.all(np.isfinite(x_arr)) or not np.all(np.isfinite(y_arr)):
        raise ValueError("Regression failed because the transformed data contains NaN or infinite values.")

    result = stats.linregress(x_arr, y_arr)

    return {
        "slope": float(result.slope),
        "intercept": float(result.intercept),
        "r_squared": float(result.rvalue ** 2),
        "r_value": float(result.rvalue),
        "std_err": float(result.stderr) if result.stderr is not None else None,
    }
