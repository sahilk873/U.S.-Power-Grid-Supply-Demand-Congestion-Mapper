from typing import Optional

import numpy as np
import pandas as pd

from config.settings import settings
from utils.logging_utils import logger
from utils.validation import flag_extreme_weather


class FeatureEngineer:
    def __init__(self):
        self.renewable_fuels = settings.RENEWABLE_FUELS
        self.thermal_fuels = settings.THERMAL_FUELS

    def compute_load_percentile(
        self,
        df: pd.DataFrame,
        load_col: str = "load_mw",
        group_col: str = "balancing_authority_code",
        window: str = None,
    ) -> pd.DataFrame:
        if window:
            df["load_percentile"] = df.groupby(group_col)[load_col].transform(
                lambda x: x.rank(pct=True)
            )
        else:
            df["load_percentile"] = df.groupby(group_col)[load_col].rank(pct=True)
        return df

    def compute_fuel_shares(
        self,
        mix_df: pd.DataFrame,
        fuel_col: str = "fuel_type",
        gen_col: str = "generation_mw",
        group_cols: Optional[list] = None,
    ) -> pd.DataFrame:
        if group_cols is None:
            group_cols = ["balancing_authority_code", "interval_start_utc"]

        total_gen = mix_df.groupby(group_cols)[gen_col].sum().reset_index()
        total_gen.rename(columns={gen_col: "total_generation_mw"}, inplace=True)

        mix_df = mix_df.merge(total_gen, on=group_cols, how="left")

        mix_df["renewable_share"] = np.where(
            mix_df[fuel_col]
            .str.lower()
            .isin({f.lower() for f in self.renewable_fuels}),
            mix_df[gen_col] / mix_df["total_generation_mw"],
            0,
        )
        mix_df["thermal_share"] = np.where(
            mix_df[fuel_col].str.lower().isin({f.lower() for f in self.thermal_fuels}),
            mix_df[gen_col] / mix_df["total_generation_mw"],
            0,
        )

        shares = (
            mix_df.groupby(group_cols)
            .agg(
                renewable_share=("renewable_share", "sum"),
                thermal_share=("thermal_share", "sum"),
                total_generation_mw=("total_generation_mw", "first"),
            )
            .reset_index()
        )
        return shares

    def compute_reserve_margin_proxy(
        self,
        load_df: pd.DataFrame,
        gen_df: pd.DataFrame,
        load_col: str = "load_mw",
        gen_col: str = "total_generation_mw",
        group_cols: Optional[list] = None,
    ) -> pd.DataFrame:
        if group_cols is None:
            group_cols = ["balancing_authority_code", "interval_start_utc"]

        merged = load_df.merge(
            gen_df, on=group_cols, how="left", suffixes=("_load", "_gen")
        )
        merged["reserve_margin_proxy"] = (
            (merged[f"{gen_col}_gen"] - merged[f"{load_col}_load"])
            / merged[f"{load_col}_load"]
        ).clip(-0.5, 1.0)
        return merged

    def compute_congestion_spread(
        self,
        price_df: pd.DataFrame,
        group_cols: Optional[list] = None,
        price_col: str = "lmp_price_usd_per_mwh",
        congestion_col: str = "congestion_component",
    ) -> pd.DataFrame:
        if group_cols is None:
            group_cols = ["balancing_authority_code", "interval_start_utc"]

        agg = (
            price_df.groupby(group_cols)
            .agg(
                avg_lmp_usd_per_mwh=(price_col, "mean"),
                congestion_spread_max=(congestion_col, "max"),
                congestion_spread_avg=(congestion_col, "mean"),
            )
            .reset_index()
        )
        return agg

    def flag_extreme_weather(
        self,
        weather_df: pd.DataFrame,
    ) -> pd.DataFrame:
        flags = weather_df.apply(flag_extreme_weather, axis=1, result_type="expand")
        flags.columns = ["is_extreme_weather", "extreme_type"]
        weather_df = pd.concat([weather_df, flags], axis=1)
        return weather_df

    def bin_features(
        self,
        df: pd.DataFrame,
        col: str,
        bins: list,
        labels: list,
        new_col: str = None,
    ) -> pd.DataFrame:
        if new_col is None:
            new_col = f"{col}_bin"
        df[new_col] = pd.cut(df[col], bins=bins, labels=labels, include_lowest=True)
        return df

    def compute_outage_impact(
        self,
        outage_df: pd.DataFrame,
        group_cols: Optional[list] = None,
        capacity_col: str = "capacity_affected_mw",
    ) -> pd.DataFrame:
        if group_cols is None:
            group_cols = ["balancing_authority_code", "interval_start_utc"]

        agg = (
            outage_df.groupby(group_cols)
            .agg(
                total_outage_mw=(capacity_col, "sum"),
                forced_outage_mw=(
                    capacity_col,
                    lambda x: x[
                        outage_df.loc[x.index, "outage_type"] == "forced"
                    ].sum(),
                ),
            )
            .reset_index()
        )
        return agg

    def build_feature_table(
        self,
        load_df: pd.DataFrame,
        mix_df: pd.DataFrame,
        price_df: pd.DataFrame,
        outage_df: pd.DataFrame = None,
        weather_df: pd.DataFrame = None,
    ) -> pd.DataFrame:
        group_cols = ["balancing_authority_code", "interval_start_utc"]

        load_pct = self.compute_load_percentile(load_df)
        load_agg = load_pct[group_cols + ["load_mw", "load_percentile"]]

        fuel_shares = self.compute_fuel_shares(mix_df, group_cols=group_cols)

        price_agg = self.compute_congestion_spread(price_df, group_cols=group_cols)

        features = load_agg.merge(fuel_shares, on=group_cols, how="left").merge(
            price_agg, on=group_cols, how="left"
        )

        features["reserve_margin_proxy"] = (
            (features["total_generation_mw"] - features["load_mw"])
            / features["load_mw"]
        ).clip(-0.5, 1.0)

        if outage_df is not None and not outage_df.empty:
            outage_agg = self.compute_outage_impact(outage_df, group_cols=group_cols)
            features = features.merge(outage_agg, on=group_cols, how="left")

        if weather_df is not None and not weather_df.empty:
            weather_df = self.flag_extreme_weather(weather_df)
            weather_agg = (
                weather_df.groupby(group_cols)
                .agg(
                    temperature_c=("temperature_c", "mean"),
                    is_extreme_weather=("is_extreme_weather", "max"),
                )
                .reset_index()
            )
            features = features.merge(weather_agg, on=group_cols, how="left")

        features.fillna(
            {
                "renewable_share": 0,
                "thermal_share": 0,
                "total_generation_mw": 0,
                "congestion_spread_max": 0,
                "congestion_spread_avg": 0,
                "avg_lmp_usd_per_mwh": 0,
                "reserve_margin_proxy": 0,
                "total_outage_mw": 0,
                "forced_outage_mw": 0,
                "temperature_c": 20,
                "is_extreme_weather": False,
            },
            inplace=True,
        )

        load_bins = [0, 0.25, 0.50, 0.75, 0.90, 0.95, 1.0]
        load_labels = ["very_low", "low", "medium", "high", "very_high", "peak"]
        features = self.bin_features(
            features,
            "load_percentile",
            load_bins,
            load_labels,
            new_col="load_percentile_bin",
        )

        renewable_bins = [0, 0.1, 0.25, 0.5, 0.75, 1.0]
        renewable_labels = ["minimal", "low", "moderate", "high", "very_high"]
        features = self.bin_features(
            features,
            "renewable_share",
            renewable_bins,
            renewable_labels,
            new_col="renewable_share_bin",
        )

        logger.info(
            "Built feature table: %d rows x %d cols",
            len(features),
            len(features.columns),
        )
        return features
