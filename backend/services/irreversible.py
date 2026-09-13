"""
irreversible.py
----------------
Irreversible reaction module: -r_A = k * C_A^n

Reuses the same transparent guess-and-test order sweep as the Integral
Method (mode="integral", the default) and also exposes the Differential
Method (mode="differential") for the same dataset, since both are valid
ways to analyze irreversible kinetics data.
"""

from .integral_method import full_integral_analysis
from .differential_method import run_differential_method


def run_irreversible(t, C, mode="integral"):
    if mode == "differential":
        result = run_differential_method(t, C)
    else:
        result = full_integral_analysis(t, C)

    result["method"] = "Irreversible Reaction"
    result["analysis_mode"] = mode
    return result
