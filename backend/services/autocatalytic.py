"""
autocatalytic.py
-----------------
Autocatalytic reaction module: A + B -> 2B, where the product B
participates in (accelerates) the rate.

Rate law:      -r_A = k * C_A * C_B

Since A + B is conserved (C_A + C_B = C_T, constant), this integrates to
the classic autocatalytic linear form:

    ln(C_B / C_A) = k * C_T * t + ln(C_B0 / C_A0)

which is linear in t with slope = k * C_T.
"""

import numpy as np

from .regression import linear_regression


def run_autocatalytic(t, C_A, C_B):
    t_arr = np.asarray(t, dtype=float)
    C_A_arr = np.asarray(C_A, dtype=float)
    C_B_arr = np.asarray(C_B, dtype=float)

    if len(t_arr) < 3:
        raise ValueError("At least three data points are required.")
    if len(t_arr) != len(C_A_arr) or len(t_arr) != len(C_B_arr):
        raise ValueError("Time, Concentration A, and Concentration B must have the same number of rows.")
    if not np.all(np.isfinite(t_arr)) or not np.all(np.isfinite(C_A_arr)) or not np.all(np.isfinite(C_B_arr)):
        raise ValueError("Data contains missing, NaN, or infinite values.")
    if np.any(t_arr < 0):
        raise ValueError("Time values must be >= 0.")
    if np.any(C_A_arr <= 0) or np.any(C_B_arr <= 0):
        raise ValueError("Concentrations of A and B must both be strictly positive.")

    order = np.argsort(t_arr)
    t_arr, C_A_arr, C_B_arr = t_arr[order], C_A_arr[order], C_B_arr[order]

    C_total = C_A_arr + C_B_arr
    mean_total = float(np.mean(C_total))
    relative_spread = float(np.std(C_total) / mean_total) if mean_total != 0 else float("inf")

    if relative_spread > 0.05:
        total_note = (
            "Note: A + B is not perfectly constant across the entered data "
            f"(relative spread {relative_spread * 100:.1f}%). The average total "
            "concentration is used as C_T. Large deviations may indicate the "
            "A + B -> 2B stoichiometry does not fit this data well."
        )
    else:
        total_note = "A + B is approximately constant, consistent with A + B -> 2B stoichiometry."

    Y = np.log(C_B_arr / C_A_arr)
    reg = linear_regression(t_arr, Y)

    k = reg["slope"] / mean_total if mean_total != 0 else None
    physically_valid = k is not None and np.isfinite(k) and k > 0

    if physically_valid:
        final_rate_equation = f"-r_A = {k:.5g} * C_A * C_B"
    else:
        final_rate_equation = "Calculated rate constant is not positive; the autocatalytic model does not fit this data."

    return {
        "method": "Autocatalytic Reaction",
        "reaction": "A + B -> 2B",
        "rate_equation": "-r_A = k * C_A * C_B",
        "assumption_note": total_note,
        "total_concentration": mean_total,
        "x_label": "t",
        "y_label": "ln(C_B / C_A)",
        "equation": "ln(C_B/C_A) = k*C_T*t + ln(C_B0/C_A0)",
        "transformed_x": t_arr.tolist(),
        "transformed_y": Y.tolist(),
        "slope": reg["slope"],
        "intercept": reg["intercept"],
        "r_squared": reg["r_squared"],
        "rate_constant": k,
        "physically_valid": physically_valid,
        "final_rate_equation": final_rate_equation,
        "original_data": [
            {"time": float(ti), "concentration_a": float(a), "concentration_b": float(b)}
            for ti, a, b in zip(t_arr, C_A_arr, C_B_arr)
        ],
    }
