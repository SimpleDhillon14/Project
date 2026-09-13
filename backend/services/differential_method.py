"""
differential_method.py
-----------------------
Implements the Differential Method for Chemical Reaction Kinetics.

Steps implemented:
  1. Plot C_A vs t
  2. Numerically differentiate to get -dC_A/dt (forward diff at the first
     point, central diff for interior points, backward diff at the last
     point -- this is exactly what numpy.gradient does, and it also
     handles non-uniform time spacing correctly).
  3. log(-r_A) = log(k) + n*log(C_A)  -> linear regression gives a
     *continuous* (possibly fractional) order n directly as the slope.
  4. A transparent "guess-and-test" table is also provided, testing the
     same candidate orders used in the Integral Method for comparison.
"""

import numpy as np

from .regression import linear_regression
from .integral_method import COARSE_ORDERS


def numerical_derivative(t, C):
    """
    Compute dC/dt using forward difference at the first point, central
    difference for interior points, and backward difference at the last
    point. numpy.gradient implements exactly this scheme and correctly
    supports non-uniform time spacing.
    """
    t_arr = np.asarray(t, dtype=float)
    C_arr = np.asarray(C, dtype=float)

    order = np.argsort(t_arr)
    t_sorted = t_arr[order]
    C_sorted = C_arr[order]

    if len(set(t_sorted.tolist())) != len(t_sorted):
        raise ValueError("Duplicate time values are not allowed for numerical differentiation.")

    dCdt = np.gradient(C_sorted, t_sorted)
    return t_sorted, C_sorted, dCdt


def run_differential_method(t, C):
    """Main log-log differential analysis producing a continuous fractional order."""
    t_sorted, C_sorted, dCdt = numerical_derivative(t, C)
    rate = -dCdt  # -r_A

    valid_mask = rate > 0
    if valid_mask.sum() < 3:
        raise ValueError(
            "Not enough points with a positive reaction rate (-dC_A/dt > 0) to perform "
            "the log-log regression. Concentration data should be decreasing over time."
        )

    log_C = np.log(C_sorted[valid_mask])
    log_rate = np.log(rate[valid_mask])

    reg = linear_regression(log_C, log_rate)
    n = reg["slope"]
    k = float(np.exp(reg["intercept"]))

    table = []
    for i in range(len(t_sorted)):
        table.append({
            "time": float(t_sorted[i]),
            "concentration": float(C_sorted[i]),
            "dC_dt": float(dCdt[i]),
            "neg_dC_dt": float(-dCdt[i]),
        })

    physically_valid = k > 0
    final_rate_equation = (
        f"-r_A = {k:.5g} * C_A^{n:.3g}" if physically_valid
        else "Calculated k is not positive; the fitted model is not physically meaningful."
    )

    return {
        "method": "Differential Method",
        "derivative_table": table,
        "x_label": "ln(C_A)",
        "y_label": "ln(-r_A)",
        "equation": "ln(-r_A) = ln(k) + n*ln(C_A)",
        "transformed_x": log_C.tolist(),
        "transformed_y": log_rate.tolist(),
        "slope": reg["slope"],
        "intercept": reg["intercept"],
        "r_squared": reg["r_squared"],
        "reaction_order": n,
        "rate_constant": k,
        "physically_valid": physically_valid,
        "final_rate_equation": final_rate_equation,
    }


def guess_and_test_differential(t, C, orders=None):
    """
    Transparent guess-and-test mode: for each candidate order n, regress
    -r_A against C_A^n directly (Y = k * X, forced through methodology
    rather than the log-log shortcut) so each order can be individually
    accepted/rejected, mirroring the Integral Method comparison table.
    """
    orders = orders if orders is not None else COARSE_ORDERS
    t_sorted, C_sorted, dCdt = numerical_derivative(t, C)
    rate = -dCdt
    valid_mask = rate > 0

    if valid_mask.sum() < 3:
        return [], None

    C_valid = C_sorted[valid_mask]
    rate_valid = rate[valid_mask]

    results = []
    for n in orders:
        try:
            X = np.power(C_valid, n)
            reg = linear_regression(X, rate_valid)
            k = reg["slope"]
            valid = k > 0
            reasons = [] if valid else ["Calculated k is not positive for this assumed order."]
            if reg["r_squared"] < 0.90:
                reasons.append(f"R\u00b2 = {reg['r_squared']:.4f} indicates poor linearity.")
            results.append({
                "order": n,
                "x_label": f"C_A^{n:.3g}",
                "y_label": "-dC_A/dt",
                "equation": f"-dC_A/dt = k * C_A^{n:.3g}",
                "slope": reg["slope"],
                "intercept": reg["intercept"],
                "r_squared": reg["r_squared"],
                "k": k,
                "physically_valid": valid,
                "reasons": reasons,
            })
        except Exception as exc:
            results.append({"order": n, "error": str(exc), "physically_valid": False, "r_squared": 0.0})

    valid_results = [r for r in results if r.get("physically_valid")]
    pool = valid_results if valid_results else results
    best = max(pool, key=lambda r: r.get("r_squared", 0.0)) if pool else None

    for r in results:
        if best is not None and r is best:
            r["decision"] = "Best candidate"
        elif r.get("physically_valid"):
            r["decision"] = "Rejected (lower R\u00b2 than the best candidate)"
        else:
            r["decision"] = "Rejected (" + "; ".join(r.get("reasons", ["not physically valid"])) + ")"

    return results, best
