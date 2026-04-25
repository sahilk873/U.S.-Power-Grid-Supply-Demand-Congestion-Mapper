import pandas as pd
import numpy as np

from etl.transform.features import FeatureEngineer


class TestFeatureEngineer:
    def setup_method(self):
        self.eng = FeatureEngineer()

    def test_compute_load_percentile(self):
        df = pd.DataFrame(
            {
                "balancing_authority_code": ["PJM"] * 4,
                "interval_start_utc": pd.date_range("2024-01-01", periods=4, freq="h"),
                "load_mw": [100, 200, 300, 400],
            }
        )
        result = self.eng.compute_load_percentile(df)
        assert "load_percentile" in result.columns
        assert result["load_percentile"].iloc[-1] == 1.0

    def test_compute_fuel_shares(self):
        mix = pd.DataFrame(
            {
                "balancing_authority_code": ["PJM", "PJM"],
                "interval_start_utc": ["2024-01-01 01:00:00", "2024-01-01 01:00:00"],
                "fuel_type": ["solar", "natural gas"],
                "generation_mw": [500, 1500],
            }
        )
        result = self.eng.compute_fuel_shares(mix)
        assert len(result) == 1
        assert result["renewable_share"].iloc[0] == 0.25
        assert result["thermal_share"].iloc[0] == 0.75
        assert result["total_generation_mw"].iloc[0] == 2000

    def test_flag_extreme_weather(self):
        df = pd.DataFrame(
            {
                "temperature_c": [45.0, 20.0, -25.0],
                "wind_speed_ms": [5.0, 30.0, 5.0],
            }
        )
        result = self.eng.flag_extreme_weather(df)
        assert result["is_extreme_weather"].iloc[0] == True
        assert result["is_extreme_weather"].iloc[1] == True
        assert result["is_extreme_weather"].iloc[2] == True

    def test_bin_features(self):
        df = pd.DataFrame({"load_percentile": [0.1, 0.5, 0.95]})
        result = self.eng.bin_features(
            df,
            "load_percentile",
            bins=[0, 0.25, 0.75, 1.0],
            labels=["low", "medium", "high"],
        )
        assert result["load_percentile_bin"].iloc[0] == "low"
        assert result["load_percentile_bin"].iloc[2] == "high"

    def test_compute_congestion_spread(self):
        df = pd.DataFrame(
            {
                "balancing_authority_code": ["PJM", "PJM"],
                "interval_start_utc": ["2024-01-01 01:00:00", "2024-01-01 01:00:00"],
                "lmp_price_usd_per_mwh": [30.0, 50.0],
                "congestion_component": [5.0, 15.0],
            }
        )
        result = self.eng.compute_congestion_spread(df)
        assert result["avg_lmp_usd_per_mwh"].iloc[0] == 40.0
        assert result["congestion_spread_max"].iloc[0] == 15.0
        assert result["congestion_spread_avg"].iloc[0] == 10.0

    def test_build_feature_table(self):
        load = pd.DataFrame(
            {
                "balancing_authority_code": ["PJM", "PJM"],
                "interval_start_utc": ["2024-01-01 01:00:00", "2024-01-01 02:00:00"],
                "load_mw": [10000, 12000],
            }
        )
        mix = pd.DataFrame(
            {
                "balancing_authority_code": ["PJM", "PJM", "PJM", "PJM"],
                "interval_start_utc": [
                    "2024-01-01 01:00:00",
                    "2024-01-01 01:00:00",
                    "2024-01-01 02:00:00",
                    "2024-01-01 02:00:00",
                ],
                "fuel_type": ["solar", "coal", "wind", "natural gas"],
                "generation_mw": [1000, 9000, 2000, 10000],
            }
        )
        price = pd.DataFrame(
            {
                "balancing_authority_code": ["PJM", "PJM", "PJM", "PJM"],
                "interval_start_utc": [
                    "2024-01-01 01:00:00",
                    "2024-01-01 01:00:00",
                    "2024-01-01 02:00:00",
                    "2024-01-01 02:00:00",
                ],
                "lmp_price_usd_per_mwh": [25, 35, 40, 60],
                "congestion_component": [2, 8, 10, 20],
            }
        )
        result = self.eng.build_feature_table(load, mix, price)
        assert len(result) == 2
        assert "renewable_share" in result.columns
        assert "thermal_share" in result.columns
        assert "congestion_spread_max" in result.columns
        assert "load_percentile_bin" in result.columns
        assert "renewable_share_bin" in result.columns
        assert result["total_generation_mw"].iloc[0] == 10000
