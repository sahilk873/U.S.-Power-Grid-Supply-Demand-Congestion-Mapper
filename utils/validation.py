import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple


def validate_required_columns(
    df: pd.DataFrame, required: List[str], name: str = "DataFrame"
) -> List[str]:
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"{name} missing required columns: {missing}")
    return missing


def validate_no_null_in_columns(
    df: pd.DataFrame, columns: List[str], name: str = "DataFrame"
) -> pd.DataFrame:
    for col in columns:
        null_count = df[col].isnull().sum()
        if null_count > 0:
            raise ValueError(f"{name}: column '{col}' has {null_count} null values")
    return df


def validate_timestamps(
    df: pd.DataFrame,
    ts_column: str,
    name: str = "DataFrame",
    tz_aware: bool = False,
) -> pd.DataFrame:
    if ts_column not in df.columns:
        raise ValueError(f"{name}: timestamp column '{ts_column}' not found")
    try:
        df[ts_column] = pd.to_datetime(df[ts_column], utc=True)
    except Exception as e:
        raise ValueError(f"{name}: failed to parse '{ts_column}': {e}")
    return df


def validate_numeric_range(
    df: pd.DataFrame,
    column: str,
    min_val: float,
    max_val: float,
    name: str = "DataFrame",
) -> pd.DataFrame:
    out_of_range = df[(df[column] < min_val) | (df[column] > max_val)]
    if len(out_of_range) > 0:
        raise ValueError(
            f"{name}: column '{column}' has {len(out_of_range)} values "
            f"outside [{min_val}, {max_val}]"
        )
    return df


def reconcile_ba_name(name: str, alias_map: Dict[str, str]) -> str:
    key = name.strip().lower()
    return alias_map.get(key, name.strip())


def standardize_fuel_category(
    fuel_code: str, renewable_set: set, thermal_set: set
) -> str:
    fc = fuel_code.strip().lower()
    if fc in renewable_set:
        return "renewable"
    if fc in thermal_set:
        return "thermal"
    return "other"


def flag_extreme_weather(row: pd.Series) -> Tuple[bool, Optional[str]]:
    reasons = []
    if pd.notna(row.get("temperature_c")) and (
        row["temperature_c"] > 40 or row["temperature_c"] < -20
    ):
        reasons.append("extreme_temp")
    if pd.notna(row.get("wind_speed_ms")) and row["wind_speed_ms"] > 25:
        reasons.append("extreme_wind")
    if pd.notna(row.get("precipitation_mm")) and row["precipitation_mm"] > 50:
        reasons.append("heavy_precip")
    if pd.notna(row.get("humidity_pct")) and row["humidity_pct"] > 95:
        reasons.append("extreme_humidity")
    if reasons:
        return True, ",".join(reasons)
    return False, None
