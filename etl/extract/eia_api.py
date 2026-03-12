import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import pandas as pd
import requests

from config.settings import settings
from utils.logging_utils import logger


class EIAAPIExtractor:
    BASE_URL = "https://api.eia.gov/v2"

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or settings.EIA_API_KEY
        if not self.api_key:
            logger.warning("No EIA API key set — using sample data fallback")

    def _request(
        self,
        endpoint: str,
        params: Dict[str, Any] | None = None,
        retries: int = 3,
    ) -> Dict[str, Any]:
        if not self.api_key:
            raise RuntimeError("EIA API key required but not configured")

        url = f"{self.BASE_URL}/{endpoint}"
        p = {"api_key": self.api_key, **(params or {})}

        for attempt in range(1, retries + 1):
            try:
                resp = requests.get(url, params=p, timeout=60)
                resp.raise_for_status()
                return resp.json()
            except requests.RequestException as e:
                logger.warning(
                    "EIA API request failed (attempt %d/%d): %s",
                    attempt,
                    retries,
                    e,
                )
                if attempt < retries:
                    time.sleep(2**attempt)
                else:
                    raise

    def fetch_electricity_generation(
        self,
        facility_code: str | None = None,
        start: str | None = None,
        end: str | None = None,
        frequency: str = "hourly",
    ) -> pd.DataFrame:
        """Fetch net electricity generation by fuel type."""
        params: Dict[str, Any] = {
            "frequency": frequency,
            "data[0]": "generation",
            "sort[0][column]": "period",
            "sort[0][direction]": "desc",
            "length": 5000,
        }
        if facility_code:
            params["facets[facility_code][]"] = facility_code
        if start:
            params["start"] = start
        if end:
            params["end"] = end

        data = self._request("electricity/rto/fuel-type/data", params)
        records = data.get("response", {}).get("data", [])
        if not records:
            logger.info("No generation data returned from EIA API")
            return pd.DataFrame()
        df = pd.DataFrame(records)
        logger.info("Fetched %d generation records from EIA", len(df))
        return df

    def fetch_electricity_demand(
        self,
        ba_code: str | None = None,
        start: str | None = None,
        end: str | None = None,
        frequency: str = "hourly",
    ) -> pd.DataFrame:
        """Fetch electricity demand for a balancing authority."""
        params: Dict[str, Any] = {
            "frequency": frequency,
            "data[0]": "value",
            "sort[0][column]": "period",
            "sort[0][direction]": "desc",
            "length": 5000,
        }
        if ba_code:
            params["facets[ba][]"] = ba_code
        if start:
            params["start"] = start
        if end:
            params["end"] = end

        data = self._request("electricity/rto/region-data/data", params)
        records = data.get("response", {}).get("data", [])
        if not records:
            logger.info("No demand data returned from EIA API")
            return pd.DataFrame()
        df = pd.DataFrame(records)
        logger.info("Fetched %d demand records from EIA", len(df))
        return df

    def fetch_plant_data(self, page: int = 1, per_page: int = 5000) -> pd.DataFrame:
        """Fetch power plant inventory data."""
        params: Dict[str, Any] = {
            "api_key": self.api_key,
            "data[]": [
                "plant_code",
                "plant_name",
                "street_address",
                "city",
                "county",
                "state",
                "zip",
                "latitude",
                "longitude",
                "balancing_authority_code",
                "balancing_authority_name",
                "prime_mover",
                "net_summer_capacity_mw",
                "net_winter_capacity_mw",
                "status",
                "commercial_online_date",
            ],
            "length": per_page,
            "offset": (page - 1) * per_page,
        }
        url = "https://api.eia.gov/v2/electricity/plant/inventory/data"
        try:
            resp = requests.get(url, params=params, timeout=60)
            resp.raise_for_status()
            data = resp.json()
            records = data.get("response", {}).get("data", [])
            if not records:
                return pd.DataFrame()
            df = pd.DataFrame(records)
            logger.info("Fetched %d plant records (page %d)", len(df), page)
            return df
        except requests.RequestException as e:
            logger.error("Failed to fetch plant data: %s", e)
            return pd.DataFrame()

    def fetch_fuel_receipts(
        self, start: str | None = None, end: str | None = None
    ) -> pd.DataFrame:
        """Fetch fuel receipts and costs for plants."""
        params: Dict[str, Any] = {
            "api_key": self.api_key,
            "data[]": [
                "plant_code",
                "plant_name",
                "fuel_type_code",
                "fuel_type_description",
                "fuel_group_code",
                "receipt_quantity",
                "price_per_unit",
                "heat_content_mmbtu_per_unit",
            ],
            "length": 5000,
        }
        if start:
            params["start"] = start
        if end:
            params["end"] = end

        url = "https://api.eia.gov/v2/electricity/fuel-receipts/data"
        try:
            resp = requests.get(url, params=params, timeout=60)
            resp.raise_for_status()
            data = resp.json()
            records = data.get("response", {}).get("data", [])
            if not records:
                return pd.DataFrame()
            df = pd.DataFrame(records)
            logger.info("Fetched %d fuel receipt records", len(df))
            return df
        except requests.RequestException as e:
            logger.error("Failed to fetch fuel receipts: %s", e)
            return pd.DataFrame()
