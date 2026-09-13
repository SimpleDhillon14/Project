"""
validation.py
--------------
Input validation for the Chemical Reaction Kinetics Analyzer.

Only validates data typed/uploaded directly by the user (time & concentration
values). No file-system access, no external data, no credentials.
"""

import math


class ValidationError(Exception):
    """Raised when user-supplied data fails validation."""
    pass


def validate_time_concentration(times, concentrations):
    """
    Validate parallel arrays of time and concentration values.

    Rules enforced:
        - both lists provided and of equal length
        - at least 3 valid data points
        - no empty values
        - numeric values only
        - no NaN / infinity
        - t >= 0
        - C_A > 0 (needed for logarithms and fractional powers)
        - time values must vary (otherwise regression is undefined)

    Returns:
        (list[float], list[float]) cleaned (time, concentration) arrays,
        sorted by time.
    """
    if times is None or concentrations is None:
        raise ValidationError("Both Time and Concentration data are required.")

    if len(times) == 0 or len(concentrations) == 0:
        raise ValidationError("No data was provided. Please enter or upload data.")

    if len(times) != len(concentrations):
        raise ValidationError(
            "Time and Concentration columns must have the same number of rows."
        )

    if len(times) < 3:
        raise ValidationError(
            "At least three valid data points are required for regression analysis."
        )

    cleaned_t = []
    cleaned_c = []

    for i, (t_raw, c_raw) in enumerate(zip(times, concentrations)):
        row = i + 1

        if t_raw is None or c_raw is None or str(t_raw).strip() == "" or str(c_raw).strip() == "":
            raise ValidationError(f"Row {row}: empty values are not allowed.")

        try:
            t_val = float(t_raw)
            c_val = float(c_raw)
        except (ValueError, TypeError):
            raise ValidationError(f"Row {row}: Time and Concentration must be numeric.")

        if math.isnan(t_val) or math.isnan(c_val):
            raise ValidationError(f"Row {row}: NaN values are not allowed.")

        if math.isinf(t_val) or math.isinf(c_val):
            raise ValidationError(f"Row {row}: infinite values are not allowed.")

        if t_val < 0:
            raise ValidationError(f"Row {row}: time must be greater than or equal to 0.")

        if c_val <= 0:
            raise ValidationError(
                f"Row {row}: concentration must be strictly greater than 0 "
                "(zero or negative concentrations are not physically meaningful "
                "and break logarithms / fractional powers)."
            )

        cleaned_t.append(t_val)
        cleaned_c.append(c_val)

    if len(set(cleaned_t)) < 2:
        raise ValidationError(
            "All time values are identical; regression against time requires variation."
        )

    # sort by time to make numerical differentiation and plotting well-behaved
    pairs = sorted(zip(cleaned_t, cleaned_c), key=lambda p: p[0])
    cleaned_t = [p[0] for p in pairs]
    cleaned_c = [p[1] for p in pairs]

    return cleaned_t, cleaned_c


def validate_csv_dataframe(df):
    """
    Validate that an uploaded CSV (already parsed into a pandas DataFrame)
    contains the required 'Time' and 'Concentration' columns
    (case-insensitive, whitespace-tolerant).

    Returns the matching column names as (time_col, concentration_col).
    """
    if df is None or len(df.columns) == 0:
        raise ValidationError("The uploaded CSV file appears to be empty.")

    normalized = {str(c).strip().lower(): c for c in df.columns}

    if "time" not in normalized or "concentration" not in normalized:
        raise ValidationError(
            "CSV file must contain exactly two columns named 'Time' and 'Concentration'."
        )

    return normalized["time"], normalized["concentration"]
