"""
reversible.py
--------------
Reversible reaction module: A <=> B, with forward rate constant kf and
reverse rate constant kr.

Rate law:   -r_A = kf*C_A - kr*C_B

For a closed system starting with pure A (C_A0) and no B, the system
approaches equilibrium concentration C_Ae. Integrating the rate law gives:

    ln[(C_A - C_Ae) / (C_A0 - C_Ae)] = -(kf + kr) * t

The equilibrium constant K = kf/kr = (C_A0 - C_Ae) / C_Ae, which combined
with (kf + kr) from the slope lets us solve for kf and kr individually.
"""

import numpy as np

from .regression import linear_regression


def run_reversible(t, C_A, C_A0=None, C_Ae=None):
    t_arr = np.asarray(t, dtype=float)
    C_A_arr = np.asarray(C_A, dtype=float)

    order = np.argsort(t_arr)
    t_arr, C_A_arr = t_arr[order], C_A_arr[order]

    C_A0_val = float(C_A0) if C_A0 not in (None, "") else float(C_A_arr[0])
    C_Ae_val = float(C_Ae) if C_Ae not in (None, "") else float(C_A_arr[-1])

    if C_A0_val <= 0:
        raise ValueError("Initial concentration C_A0 must be positive.")
    if C_Ae_val <= 0:
        raise ValueError("Equilibrium concentration C_Ae must be positive.")
    if C_A0_val <= C_Ae_val:
        raise ValueError(
            "Initial concentration C_A0 must be greater than the equilibrium "
            "concentration C_Ae for an A <=> B reversible analysis starting from pure A."
        )

    ratio = (C_A_arr - C_Ae_val) / (C_A0_val - C_Ae_val)
    if np.any(ratio <= 0):
        raise ValueError(
            "Invalid data: (C_A - C_Ae) must remain strictly positive for every point. "
            "Check the equilibrium concentration value or the data itself."
        )

    Y = np.log(ratio)
    reg = linear_regression(t_arr, Y)

    k_sum = -reg["slope"]  # kf + kr
    if k_sum <= 0:
        raise ValueError(
            "Calculated (kf + kr) is not positive; the reversible model does not fit this data."
        )

    Keq = (C_A0_val - C_Ae_val) / C_Ae_val
    if Keq <= 0 or not np.isfinite(Keq):
        raise ValueError("Could not compute a physically meaningful equilibrium constant.")

    kf = k_sum * Keq / (1 + Keq)
    kr = k_sum / (1 + Keq)

    physically_valid = kf > 0 and kr > 0
    if physically_valid:
        final_rate_equation = f"-r_A = {kf:.5g} * C_A - {kr:.5g} * C_B"
    else:
        final_rate_equation = "Calculated kf/kr are not both positive; results are not physically meaningful."

    return {
        "method": "Reversible Reaction",
        "reaction": "A <=> B",
        "rate_equation": "-r_A = kf*C_A - kr*C_B",
        "C_A0": C_A0_val,
        "C_Ae": C_Ae_val,
        "equilibrium_constant": Keq,
        "x_label": "t",
        "y_label": "ln[(C_A - C_Ae) / (C_A0 - C_Ae)]",
        "equation": "ln[(C_A - C_Ae)/(C_A0 - C_Ae)] = -(kf + kr) * t",
        "transformed_x": t_arr.tolist(),
        "transformed_y": Y.tolist(),
        "slope": reg["slope"],
        "intercept": reg["intercept"],
        "r_squared": reg["r_squared"],
        "forward_rate_constant": kf,
        "reverse_rate_constant": kr,
        "physically_valid": physically_valid,
        "final_rate_equation": final_rate_equation,
        "original_data": [{"time": float(ti), "concentration": float(c)} for ti, c in zip(t_arr, C_A_arr)],
    }
