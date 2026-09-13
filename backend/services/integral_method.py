"""
integral_method.py
-------------------
Implements the Integral Method for Chemical Reaction Kinetics.

For an assumed order n, the general rate law:

    -dC_A/dt = k * C_A^n

is integrated and linearized. A coarse sweep of orders is tested first,
then a fine sweep is performed around whichever order gives the best
*physically meaningful* fit. Every tested order is fully reported so the
methodology stays transparent (no black-box "the order is X" answer).
"""

import numpy as np

from .regression import linear_regression

# Coarse initial sweep of candidate reaction orders
COARSE_ORDERS = [0, 0.25, 0.5, 0.75, 1, 1.25, 1.5, 1.75, 2, 2.25, 2.5, 2.75, 3]

R2_GOOD_THRESHOLD = 0.90


def _transform_for_order(t, C, n):
    """Return (x, y, x_label, y_label, equation_str) for the given order n."""
    t_arr = np.asarray(t, dtype=float)
    C_arr = np.asarray(C, dtype=float)

    if abs(n - 1) < 1e-9:
        y = np.log(C_arr)
        y_label = "ln(C_A)"
        equation = "ln(C_A) = ln(C_A0) - k*t"
    else:
        exponent = 1 - n
        y = np.power(C_arr, exponent)
        y_label = f"C_A^({exponent:.3g})"
        equation = f"C_A^({exponent:.3g}) = C_A0^({exponent:.3g}) + ({n:.3g} - 1)*k*t"

    return t_arr, y, "t", y_label, equation


def _compute_k_c0(n, slope, intercept):
    """Back out k and C_A0 from the regression slope/intercept for order n."""
    if abs(n - 1) < 1e-9:
        k = -slope
        try:
            c0 = float(np.exp(intercept))
        except OverflowError:
            c0 = None
        return k, c0

    if abs(n - 1) < 1e-12:
        return None, None  # avoid division by zero

    k = slope / (n - 1)
    b = intercept
    exponent = 1.0 / (1.0 - n)

    if b == 0:
        c0 = None
    elif b < 0 and not float(exponent).is_integer():
        # a negative number raised to a non-integer power is not real
        c0 = None
    else:
        try:
            c0 = float(np.sign(b) * (abs(b) ** exponent))
        except (ValueError, OverflowError):
            c0 = None

    return k, c0


def test_single_order(t, C, n):
    """
    Run Steps 1-6 of the integral-method methodology for one candidate order n:
    guess order -> transform -> regress -> compute k, C0 -> accept/reject.
    """
    x, y, x_label, y_label, equation = _transform_for_order(t, C, n)
    reg = linear_regression(x, y)
    k, c0 = _compute_k_c0(n, reg["slope"], reg["intercept"])

    reasons = []
    physically_valid = True

    if k is None or not np.isfinite(k):
        physically_valid = False
        reasons.append("Rate constant k could not be computed for this order.")
    elif k <= 0:
        physically_valid = False
        reasons.append("Calculated rate constant k is not positive (not physically meaningful).")

    if c0 is None or not np.isfinite(c0):
        physically_valid = False
        reasons.append("Initial concentration C_A0 could not be computed for this order.")
    elif c0 is not None and np.isfinite(c0) and c0 <= 0:
        physically_valid = False
        reasons.append("Calculated C_A0 is not positive (not physically meaningful).")

    if reg["r_squared"] < R2_GOOD_THRESHOLD:
        reasons.append(
            f"R\u00b2 = {reg['r_squared']:.4f} indicates poor linearity for this assumed order."
        )

    return {
        "order": round(float(n), 4),
        "x_label": x_label,
        "y_label": y_label,
        "equation": equation,
        "transformed_x": x.tolist(),
        "transformed_y": y.tolist(),
        "slope": reg["slope"],
        "intercept": reg["intercept"],
        "r_squared": reg["r_squared"],
        "k": k,
        "c0": c0,
        "physically_valid": physically_valid,
        "reasons": reasons,
    }


def run_order_sweep(t, C, orders):
    """Test a list of candidate orders (Steps 1-8) and mark decisions (Step 9)."""
    results = []
    for n in orders:
        try:
            results.append(test_single_order(t, C, n))
        except Exception as exc:  # keep sweeping even if one order fails
            results.append({
                "order": round(float(n), 4),
                "error": str(exc),
                "physically_valid": False,
                "r_squared": 0.0,
                "reasons": [f"Could not test this order: {exc}"],
            })

    valid_results = [r for r in results if r.get("physically_valid")]
    pool = valid_results if valid_results else results
    best = max(pool, key=lambda r: r.get("r_squared", 0.0))

    for r in results:
        if r is best:
            r["decision"] = "Best candidate"
        elif r.get("physically_valid"):
            r["decision"] = "Rejected (lower R\u00b2 than the best candidate)"
        else:
            r["decision"] = "Rejected (" + "; ".join(r.get("reasons", ["not physically valid"])) + ")"

    return results, best


def refine_around_order(t, C, center_order, span=0.10, step=0.02):
    """Fine sweep (Step: fractional order refinement) around the coarse best order."""
    raw_candidates = np.arange(center_order - span, center_order + span + step / 2, step)
    candidates = sorted({round(float(c), 4) for c in raw_candidates if c >= 0})
    return run_order_sweep(t, C, candidates)


def full_integral_analysis(t, C):
    """
    Complete Integral Method pipeline:
    coarse sweep -> refine around best -> select final physically-meaningful order.
    """
    coarse_results, coarse_best = run_order_sweep(t, C, COARSE_ORDERS)
    refine_results, refine_best = refine_around_order(t, C, coarse_best["order"])

    combined_valid = [
        r for r in (coarse_results + refine_results)
        if r.get("physically_valid") and "error" not in r
    ]
    final_best = max(combined_valid, key=lambda r: r["r_squared"]) if combined_valid else coarse_best

    n = round(final_best["order"], 4)
    k = final_best.get("k")
    c0 = final_best.get("c0")

    nearest_integer_note = None
    nearest_int = round(n)
    if abs(n - nearest_int) <= 0.1 and abs(n - nearest_int) > 1e-9:
        nearest_integer_note = f"Approximately order {nearest_int} reaction."

    if k is not None and n is not None:
        final_rate_equation = f"-r_A = {k:.5g} * C_A^{n:.3g}"
    else:
        final_rate_equation = "Could not determine a physically meaningful rate equation."

    return {
        "method": "Integral Method",
        "coarse_results": coarse_results,
        "refine_results": refine_results,
        "final_best": final_best,
        "reaction_order": n,
        "rate_constant": k,
        "initial_concentration": c0,
        "final_rate_equation": final_rate_equation,
        "nearest_integer_note": nearest_integer_note,
    }
