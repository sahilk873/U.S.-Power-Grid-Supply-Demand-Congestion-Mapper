import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

import pandas as pd

from config.database import db_config
from config.settings import settings
from etl.extract.csv_loader import CSVLoader
from etl.extract.eia_api import EIAAPIExtractor
from etl.extract.weather import NOAAWeatherExtractor
from etl.load.db_loader import DatabaseLoader
from etl.transform.clean import DataCleaner
from etl.transform.features import FeatureEngineer
from etl.transform.reconcile import EntityReconciler
from utils.logging_utils import logger


@dataclass
class PipelineResult:
    success: bool = False
    duration_seconds: float = 0.0
    records_loaded: Dict[str, int] = field(default_factory=dict)
    error: Optional[str] = None


class ETLPipeline:
    def __init__(
        self,
        db_loader: Optional[DatabaseLoader] = None,
        csv_loader: Optional[CSVLoader] = None,
        eia_extractor: Optional[EIAAPIExtractor] = None,
        weather_extractor: Optional[NOAAWeatherExtractor] = None,
        cleaner: Optional[DataCleaner] = None,
        reconciler: Optional[EntityReconciler] = None,
        feature_engineer: Optional[FeatureEngineer] = None,
    ):
        self.db = db_loader or DatabaseLoader()
        self.csv = csv_loader or CSVLoader(settings.RAW_DATA_DIR)
        self.eia = eia_extractor or EIAAPIExtractor()
        self.noaa = weather_extractor or NOAAWeatherExtractor()
        self.cleaner = cleaner or DataCleaner()
        self.reconciler = reconciler or EntityReconciler()
        self.feature_eng = feature_engineer or FeatureEngineer()

    def run_reference_tables(
        self,
        iso_data: Optional[pd.DataFrame] = None,
        fuel_data: Optional[pd.DataFrame] = None,
        ba_data: Optional[pd.DataFrame] = None,
    ) -> Dict[str, int]:
        loaded = {}
        iso_map = {}
        fuel_map = {}
        ba_map = {}

        if iso_data is not None and not iso_data.empty:
            n = self.db.insert_dataframe(iso_data, "iso_regions", truncate_first=True)
            loaded["iso_regions"] = n
            iso_rows = pd.read_sql("SELECT id, code FROM iso_regions", self.db.engine)
            iso_map = dict(zip(iso_rows["code"], iso_rows["id"]))

        if fuel_data is not None and not fuel_data.empty:
            n = self.db.insert_dataframe(fuel_data, "fuel_types", truncate_first=True)
            loaded["fuel_types"] = n
            fuel_rows = pd.read_sql("SELECT id, code FROM fuel_types", self.db.engine)
            fuel_map = dict(zip(fuel_rows["code"], fuel_rows["id"]))

        if ba_data is not None and not ba_data.empty:
            if iso_map:
                ba_data["iso_region_id"] = ba_data["code"].map(
                    lambda x: iso_map.get(self.reconciler.map_ba_to_iso(x))
                )
            n = self.db.insert_dataframe(
                ba_data, "balancing_authorities", truncate_first=True
            )
            loaded["balancing_authorities"] = n
            ba_rows = pd.read_sql(
                "SELECT id, code FROM balancing_authorities", self.db.engine
            )
            ba_map = dict(zip(ba_rows["code"], ba_rows["id"]))

        self._db_maps = {"iso": iso_map, "fuel": fuel_map, "ba": ba_map}
        logger.info("Reference tables loaded: %s", loaded)
        return loaded

    def run_assets(
        self,
        plants_df: Optional[pd.DataFrame] = None,
        generators_df: Optional[pd.DataFrame] = None,
    ) -> Dict[str, int]:
        loaded = {}

        if plants_df is not None and not plants_df.empty:
            plants_df = self.cleaner.clean_all(plants_df)
            plants_df = self.reconciler.reconcile_all(plants_df)
            if ba_map := self._db_maps.get("ba"):
                plants_df["balancing_authority_id"] = plants_df[
                    "balancing_authority_code"
                ].map(ba_map)
            n = self.db.insert_dataframe(plants_df, "plants", truncate_first=True)
            loaded["plants"] = n

        if generators_df is not None and not generators_df.empty:
            generators_df = self.cleaner.clean_all(generators_df)
            if fuel_map := self._db_maps.get("fuel"):
                generators_df["fuel_type_id"] = generators_df["fuel_type_code"].map(
                    lambda x: fuel_map.get(x.strip().lower()) if pd.notna(x) else None
                )
            n = self.db.insert_dataframe(
                generators_df, "generators", truncate_first=True
            )
            loaded["generators"] = n

        return loaded

    def run_market_topology(
        self,
        zones_df: Optional[pd.DataFrame] = None,
        hubs_df: Optional[pd.DataFrame] = None,
        nodes_df: Optional[pd.DataFrame] = None,
    ) -> Dict[str, int]:
        loaded = {}

        if zones_df is not None and not zones_df.empty:
            n = self.db.insert_dataframe(zones_df, "load_zones", truncate_first=True)
            loaded["load_zones"] = n
        if hubs_df is not None and not hubs_df.empty:
            n = self.db.insert_dataframe(hubs_df, "hubs", truncate_first=True)
            loaded["hubs"] = n
        if nodes_df is not None and not nodes_df.empty:
            n = self.db.insert_dataframe(nodes_df, "nodes", truncate_first=True)
            loaded["nodes"] = n

        return loaded

    def run_time_series(
        self,
        load_df: Optional[pd.DataFrame] = None,
        mix_df: Optional[pd.DataFrame] = None,
        price_df: Optional[pd.DataFrame] = None,
        spread_df: Optional[pd.DataFrame] = None,
        outage_df: Optional[pd.DataFrame] = None,
        weather_df: Optional[pd.DataFrame] = None,
    ) -> Dict[str, int]:
        loaded = {}

        if load_df is not None and not load_df.empty:
            load_df = self.cleaner.clean_all(load_df)
            load_df = self.reconciler.reconcile_ba_column(load_df)
            if ba_map := self._db_maps.get("ba"):
                load_df["balancing_authority_id"] = load_df[
                    "balancing_authority_code"
                ].map(ba_map)
            n = self.db.insert_dataframe(load_df, "hourly_load")
            loaded["hourly_load"] = n

        if mix_df is not None and not mix_df.empty:
            mix_df = self.cleaner.clean_all(mix_df)
            mix_df = self.reconciler.reconcile_ba_column(mix_df)
            if ba_map := self._db_maps.get("ba"):
                mix_df["balancing_authority_id"] = mix_df[
                    "balancing_authority_code"
                ].map(ba_map)
            if fuel_map := self._db_maps.get("fuel"):
                mix_df["fuel_type_id"] = mix_df["fuel_type_code"].map(
                    lambda x: fuel_map.get(x.strip().lower()) if pd.notna(x) else None
                )
            n = self.db.insert_dataframe(mix_df, "generation_mix")
            loaded["generation_mix"] = n

        if price_df is not None and not price_df.empty:
            price_df = self.cleaner.clean_all(price_df)
            n = self.db.insert_dataframe(price_df, "prices")
            loaded["prices"] = n

        if spread_df is not None and not spread_df.empty:
            spread_df = self.cleaner.clean_all(spread_df)
            n = self.db.insert_dataframe(spread_df, "price_spreads")
            loaded["price_spreads"] = n

        if outage_df is not None and not outage_df.empty:
            outage_df = self.cleaner.clean_all(outage_df)
            n = self.db.insert_dataframe(outage_df, "outages")
            loaded["outages"] = n

        if weather_df is not None and not weather_df.empty:
            weather_df = self.cleaner.clean_all(weather_df)
            weather_df = self.feature_eng.flag_extreme_weather(weather_df)
            n = self.db.insert_dataframe(weather_df, "weather_conditions")
            loaded["weather_conditions"] = n

        return loaded

    def run_features(self) -> int:
        try:
            load_df = pd.read_sql("SELECT * FROM hourly_load", self.db.engine)
            mix_df = pd.read_sql("SELECT * FROM generation_mix", self.db.engine)
            price_df = pd.read_sql("SELECT * FROM prices", self.db.engine)
            outage_df = pd.read_sql("SELECT * FROM outages", self.db.engine)
            weather_df = pd.read_sql("SELECT * FROM weather_conditions", self.db.engine)
        except Exception as e:
            logger.warning("Could not read from DB for feature engineering: %s", e)
            return 0

        if load_df.empty:
            logger.warning("No load data — skipping feature engineering")
            return 0

        features = self.feature_eng.build_feature_table(
            load_df,
            mix_df,
            price_df,
            outage_df,
            weather_df,
        )

        if not features.empty:
            if ba_map := self._db_maps.get("ba"):
                features["balancing_authority_id"] = features[
                    "balancing_authority_code"
                ].map(ba_map)
            n = self.db.insert_dataframe(
                features, "derived_features", truncate_first=True
            )
            logger.info("Feature table built: %d rows", n)
            return n
        return 0

    def run_all(
        self,
        reference_kwargs: Optional[Dict] = None,
        asset_kwargs: Optional[Dict] = None,
        topology_kwargs: Optional[Dict] = None,
        timeseries_kwargs: Optional[Dict] = None,
        skip_features: bool = False,
    ) -> PipelineResult:
        start = time.time()
        result = PipelineResult()
        self._db_maps = {"iso": {}, "fuel": {}, "ba": {}}

        try:
            if not self.db.test_connection():
                result.error = "Database connection failed"
                return result

            logger.info("=" * 60)
            logger.info("Starting ETL Pipeline")
            logger.info("=" * 60)

            result.records_loaded.update(
                self.run_reference_tables(**(reference_kwargs or {}))
            )
            result.records_loaded.update(self.run_assets(**(asset_kwargs or {})))
            result.records_loaded.update(
                self.run_market_topology(**(topology_kwargs or {}))
            )
            result.records_loaded.update(
                self.run_time_series(**(timeseries_kwargs or {}))
            )

            if not skip_features:
                n = self.run_features()
                if n > 0:
                    result.records_loaded["derived_features"] = n

            result.success = True
            logger.info("=" * 60)
            logger.info("Pipeline completed successfully")
            logger.info("Records loaded: %s", result.records_loaded)
            logger.info("=" * 60)

        except Exception as e:
            result.error = str(e)
            logger.error("Pipeline failed: %s", e, exc_info=True)

        result.duration_seconds = time.time() - start
        return result

    def run_from_csv(
        self,
        file_map: Dict[str, str],
        skip_features: bool = False,
    ) -> PipelineResult:
        return self.run_all(
            reference_kwargs={
                "iso_data": self.csv.load(file_map.get("iso", "")),
                "fuel_data": self.csv.load(file_map.get("fuel", "")),
                "ba_data": self.csv.load(file_map.get("ba", "")),
            },
            asset_kwargs={
                "plants_df": self.csv.load(file_map.get("plants", "")),
                "generators_df": self.csv.load(file_map.get("generators", "")),
            },
            topology_kwargs={
                "zones_df": self.csv.load(file_map.get("zones", "")),
                "hubs_df": self.csv.load(file_map.get("hubs", "")),
                "nodes_df": self.csv.load(file_map.get("nodes", "")),
            },
            timeseries_kwargs={
                "load_df": self.csv.load(file_map.get("load", "")),
                "mix_df": self.csv.load(file_map.get("mix", "")),
                "price_df": self.csv.load(file_map.get("prices", "")),
                "spread_df": self.csv.load(file_map.get("spreads", "")),
                "outage_df": self.csv.load(file_map.get("outages", "")),
                "weather_df": self.csv.load(file_map.get("weather", "")),
            },
            skip_features=skip_features,
        )
