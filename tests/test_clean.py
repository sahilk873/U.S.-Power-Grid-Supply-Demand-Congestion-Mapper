import pandas as pd
import numpy as np

from etl.transform.clean import DataCleaner


class TestDataCleaner:
    def setup_method(self):
        self.cleaner = DataCleaner()

    def test_standardize_ba_column_renames(self):
        df = pd.DataFrame({"ba": ["PJM"], "value": [100]})
        result = self.cleaner.standardize_ba_column(df)
        assert "balancing_authority_code" in result.columns
        assert "ba" not in result.columns

    def test_standardize_datetime_columns_parses(self):
        df = pd.DataFrame({"interval_start_utc": ["2024-01-01 00:00:00"]})
        result = self.cleaner.standardize_datetime_columns(df)
        assert pd.api.types.is_datetime64_any_dtype(result["interval_start_utc"])

    def test_clean_numeric_columns_converts(self):
        df = pd.DataFrame({"load_mw": ["100.5", "200", "N/A", "300"]})
        result = self.cleaner.clean_numeric_columns(df, numeric_cols=["load_mw"])
        assert pd.api.types.is_float_dtype(result["load_mw"])
        assert result["load_mw"].isna().sum() == 1

    def test_remove_duplicates_drops(self):
        df = pd.DataFrame({"id": [1, 1, 2], "val": [10, 10, 20]})
        result = self.cleaner.remove_duplicates(df)
        assert len(result) == 2

    def test_clean_string_columns_strips(self):
        df = pd.DataFrame({"name": ["  PJM  ", "MISO ", None]})
        result = self.cleaner.clean_string_columns(df)
        assert result["name"].iloc[0] == "PJM"
        assert result["name"].iloc[1] == "MISO"

    def test_clean_all_integration(self):
        df = pd.DataFrame(
            {
                "ba": [" pjm "],
                "interval_start_utc": ["2024-06-01 00:00:00"],
                "load_mw": ["15000.5"],
                "name": ["  test plant  "],
            }
        )
        result = self.cleaner.clean_all(df)
        assert "balancing_authority_code" in result.columns
        assert pd.api.types.is_datetime64_any_dtype(result["interval_start_utc"])
        assert pd.api.types.is_float_dtype(result["load_mw"])
