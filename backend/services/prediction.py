"""
prediction.py
--------------
Prediction calculator built on the final selected kinetic model
(-r_A = k * C_A^n). Every prediction is checked for physical meaning
before being returned (C_A > 0, t >= 0, k > 0).
"""

import numpy as np


def predict_concentration(t, n, k, C_A0):
    """Given t, compute predicted C_A using the integrated rate law."""
    if t < 0:
        raise ValueError("Time must be greater than or equal to 0.")
    if k <= 0:
        raise ValueError("Rate constant k must be positive for a physically meaningful prediction.")
    if C_A0 <= 0:
        raise ValueError("Initial concentration C_A0 must be positive.")

    if abs(n - 1) < 1e-9:
        C_A = C_A0 * np.exp(-k * t)
    else:
        base = C_A0 ** (1 - n) + (n - 1) * k * t
        if base <= 0:
            raise ValueError(
                "The predicted concentration is not physically meaningful "
                "(the reaction would have gone to completion before this time)."
            )
        C_A = base ** (1 / (1 - n))

    if not np.isfinite(C_A) or C_A <= 0:
        raise ValueError("Predicted concentration is not physically meaningful.")

    return float(C_A)


def predict_time(C_A, n, k, C_A0):
    """Given a target C_A, compute the time at which it is reached."""
    if C_A <= 0:
        raise ValueError("Target concentration must be positive.")
    if C_A0 <= 0:
        raise ValueError("Initial concentration C_A0 must be positive.")
    if C_A > C_A0:
        raise ValueError("Target concentration cannot exceed the initial concentration.")
    if k <= 0:
        raise ValueError("Rate constant k must be positive.")

    if abs(n - 1) < 1e-9:
        t = -np.log(C_A / C_A0) / k
    else:
        t = (C_A ** (1 - n) - C_A0 ** (1 - n)) / ((n - 1) * k)

    if not np.isfinite(t) or t < 0:
        raise ValueError("Predicted time is not physically meaningful (negative or undefined).")

    return float(t)


def predict_rate(C_A, n, k):
    """Given C_A, compute the instantaneous rate -r_A = k * C_A^n."""
    if C_A <= 0:
        raise ValueError("Concentration must be positive.")
    if k <= 0:
        raise ValueError("Rate constant k must be positive.")

    rate = k * (C_A ** n)

    if not np.isfinite(rate):
        raise ValueError("Predicted rate is not physically meaningful.")

    return float(rate)
