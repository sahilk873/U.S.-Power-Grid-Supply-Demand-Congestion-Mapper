from typing import Dict, List, Optional, Set, Tuple

import numpy as np
import pandas as pd

from config.settings import settings
from utils.logging_utils import logger


class EntityReconciler:
    def __init__(self):
        self.ba_aliases = settings.BA_ALIASES
        self.iso_regions = settings.ISO_REGIONS
        self.renewable_fuels = settings.RENEWABLE_FUELS
        self.thermal_fuels = settings.THERMAL_FUELS

    def reconcile_ba_code(self, raw_code: str) -> str:
        if not isinstance(raw_code, str):
            return str(raw_code)
        key = raw_code.strip().lower()
        return self.ba_aliases.get(key, raw_code.strip().upper())

    def reconcile_ba_column(
        self, df: pd.DataFrame, col: str = "balancing_authority_code"
    ) -> pd.DataFrame:
        if col in df.columns:
            df[col] = df[col].apply(self.reconcile_ba_code)
        return df

    def map_ba_to_iso(self, ba_code: str) -> Optional[str]:
        ba_to_iso = {
            "PJM": "PJM",
            "MISO": "MISO",
            "CAISO": "CAISO",
            "ERCOT": "ERCOT",
            "ISONE": "ISO-NE",
            "NYISO": "NYISO",
            "SPP": "SPP",
            "AEC": "MISO",
            "AECI": "MISO",
            "AMPN": "MISO",
            "BREC": "MISO",
            "CINERGY": "PJM",
            "CISO": "CAISO",
            "CPLE": "PJM",
            "CPLW": "PJM",
            "DEOK": "SPP",
            "DOM": "PJM",
            "DUK": "PJM",
            "EEI": "SPP",
            "EES": "ERCOT",
            "GRDA": "SPP",
            "GRIF": "MISO",
            "GVL": "MISO",
            "HE": "ERCOT",
            "IPCO": "PJM",
            "JEA": "FRCC",
            "KACY": "SPP",
            "KCPL": "SPP",
            "LDWP": "CAISO",
            "LES": "SPP",
            "LGEE": "PJM",
            "MEC": "SPP",
            "MPS": "MISO",
            "NEVP": "CAISO",
            "NIPS": "MISO",
            "NWMT": "CAISO",
            "OKGE": "SPP",
            "OTT": "MISO",
            "PACE": "CAISO",
            "PGE": "CAISO",
            "PJM": "PJM",
            "PSCO": "CAISO",
            "SC": "PJM",
            "SCE": "CAISO",
            "SCEG": "PJM",
            "SDGE": "CAISO",
            "SEC": "MISO",
            "SOCO": "PJM",
            "SPA": "SPP",
            "SPP": "SPP",
            "SWPP": "SPP",
            "TEC": "ERCOT",
            "TVA": "PJM",
            "VP": "SPP",
            "WAUE": "MISO",
            "WACM": "CAISO",
            "WALC": "CAISO",
            "WFEC": "SPP",
        }
        return ba_to_iso.get(ba_code.upper() if isinstance(ba_code, str) else "")

    def assign_iso_region_id(
        self,
        df: pd.DataFrame,
        ba_col: str = "balancing_authority_code",
        iso_map: Optional[Dict[str, int]] = None,
    ) -> pd.DataFrame:
        if iso_map is not None and ba_col in df.columns:
            df["iso_region_id"] = df[ba_col].map(
                lambda x: iso_map.get(self.map_ba_to_iso(x))
            )
        return df

    def reconcile_fuel_type(
        self,
        raw_fuel: str,
        fuel_map: Optional[Dict[str, int]] = None,
    ) -> Tuple[str, str]:
        rf = raw_fuel.strip().lower() if isinstance(raw_fuel, str) else ""
        if rf in self.renewable_fuels:
            return rf, "renewable"
        if rf in self.thermal_fuels:
            return rf, "thermal"
        return rf, "other"

    def assign_fuel_type_id(
        self,
        df: pd.DataFrame,
        fuel_col: str = "fuel_type",
        fuel_id_map: Optional[Dict[str, int]] = None,
    ) -> pd.DataFrame:
        if fuel_col in df.columns and fuel_id_map:
            df["fuel_type_id"] = df[fuel_col].map(
                lambda x: fuel_id_map.get(x.strip().lower())
            )
        return df

    def reconcile_state_code(self, raw: str) -> str:
        if not isinstance(raw, str):
            return ""
        return raw.strip().upper()[:2]

    def reconcile_timestamp_tz(self, df: pd.DataFrame, col: str) -> pd.DataFrame:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], utc=True, errors="coerce")
        return df

    def reconcile_all(
        self,
        df: pd.DataFrame,
        fuel_id_map: Optional[Dict[str, int]] = None,
        ba_id_map: Optional[Dict[str, int]] = None,
        iso_map: Optional[Dict[str, int]] = None,
    ) -> pd.DataFrame:
        df = self.reconcile_ba_column(df)
        if iso_map:
            df = self.assign_iso_region_id(df, iso_map=iso_map)
        if fuel_id_map:
            df = self.assign_fuel_type_id(df, fuel_id_map=fuel_id_map)
        return df
