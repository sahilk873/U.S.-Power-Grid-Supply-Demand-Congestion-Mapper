import re
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from utils.logging_utils import logger


class DataCleaner:
    @staticmethod
    def standardize_ba_column(df: pd.DataFrame) -> pd.DataFrame:
        col_map = {
            "ba": "balancing_authority_code",
            "ba_code": "balancing_authority_code",
            "ba_code_": "balancing_authority_code",
            "balancing_authority": "balancing_authority_code",
            "bal_auth": "balancing_authority_code",
            "ba_name": "balancing_authority_name",
        }
        return df.rename(columns={k: v for k, v in col_map.items() if k in df.columns})

    @staticmethod
    def standardize_datetime_columns(
        df: pd.DataFrame,
        time_cols: Optional[List[str]] = None,
    ) -> pd.DataFrame:
        if time_cols is None:
            time_cols = [
                c
                for c in df.columns
                if any(
                    kw in c.lower()
                    for kw in ["time", "date", "period", "interval", "utc"]
                )
            ]
        for col in time_cols:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], errors="coerce", utc=True)
        return df

    @staticmethod
    def clean_numeric_columns(
        df: pd.DataFrame,
        numeric_cols: Optional[List[str]] = None,
    ) -> pd.DataFrame:
        if numeric_cols is None:
            numeric_cols = [
                c
                for c in df.columns
                if any(
                    kw in c.lower()
                    for kw in [
                        "mw",
                        "price",
                        "cost",
                        "capacity",
                        "load",
                        "gen",
                        "temp",
                        "spread",
                    ]
                )
            ]
        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce").replace(
                    [np.inf, -np.inf], np.nan
                )
        return df

    @staticmethod
    def remove_duplicates(
        df: pd.DataFrame,
        subset: Optional[List[str]] = None,
        keep: str = "first",
    ) -> pd.DataFrame:
        before = len(df)
        df = df.drop_duplicates(subset=subset, keep=keep)
        after = len(df)
        if before != after:
            logger.info("Removed %d duplicate rows", before - after)
        return df

    @staticmethod
    def fill_missing_timestamps(
        df: pd.DataFrame,
        time_col: str,
        freq: str = "h",
        group_cols: Optional[List[str]] = None,
    ) -> pd.DataFrame:
        if group_cols:
            groups = df.groupby(group_cols)
            result = []
            for _, grp in groups:
                grp = grp.set_index(time_col)
                full_idx = pd.date_range(
                    start=grp.index.min(),
                    end=grp.index.max(),
                    freq=freq,
                    name=time_col,
                )
                grp = grp.reindex(full_idx)
                for gcol in group_cols:
                    if gcol in grp.columns:
                        grp[gcol] = grp[gcol].ffill()
                result.append(grp.reset_index())
            return pd.concat(result, ignore_index=True)
        else:
            df = df.set_index(time_col)
            full_idx = pd.date_range(
                start=df.index.min(),
                end=df.index.max(),
                freq=freq,
                name=time_col,
            )
            df = df.reindex(full_idx).reset_index()
            return df

    @staticmethod
    def clean_string_columns(df: pd.DataFrame) -> pd.DataFrame:
        for col in df.select_dtypes(include=["object", "str"]).columns:
            df[col] = (
                df[col]
                .astype(str)
                .str.strip()
                .str.replace(r"\s+", " ", regex=True)
                .replace("nan", np.nan)
                .replace("", np.nan)
            )
        return df

    def clean_all(self, df: pd.DataFrame) -> pd.DataFrame:
        df = self.standardize_ba_column(df)
        df = self.standardize_datetime_columns(df)
        df = self.clean_numeric_columns(df)
        df = self.clean_string_columns(df)
        return df
