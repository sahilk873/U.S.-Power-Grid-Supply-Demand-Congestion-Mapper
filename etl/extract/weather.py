import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import pandas as pd
import requests

from config.settings import settings
from utils.logging_utils import logger


class NOAAWeatherExtractor:
    BASE_URL = "https://www.ncdc.noaa.gov/cdo-web/api/v2"

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or settings.NOAA_API_KEY
        self.headers = {"token": self.api_key} if self.api_key else {}

    def _request(
        self,
        endpoint: str,
        params: Dict[str, Any] | None = None,
        retries: int = 3,
    ) -> Dict[str, Any]:
        if not self.api_key:
            raise RuntimeError("NOAA API key required but not configured")

        url = f"{self.BASE_URL}/{endpoint}"
        for attempt in range(1, retries + 1):
            try:
                resp = requests.get(
                    url, headers=self.headers, params=params, timeout=60
                )
                resp.raise_for_status()
                return resp.json()
            except requests.RequestException as e:
                logger.warning(
                    "NOAA API request failed (attempt %d/%d): %s",
                    attempt,
                    retries,
                    e,
                )
                if attempt < retries:
                    time.sleep(2**attempt)
                else:
                    raise

    def search_stations(
        self,
        lat: float,
        lon: float,
        radius_km: float = 50,
        limit: int = 25,
    ) -> List[Dict[str, Any]]:
        params = {
            "extent": f"{lat - 1},{lon - 1},{lat + 1},{lon + 1}",
            "datasetid": "GSOM",
            "limit": limit,
            "sortfield": "name",
            "sortorder": "asc",
        }
        data = self._request("stations", params)
        return data.get("results", [])

    def fetch_hourly_observations(
        self,
        station_id: str,
        start_date: str,
        end_date: str,
    ) -> pd.DataFrame:
        params = {
            "stationid": station_id,
            "datasetid": "GHCND",
            "startdate": start_date,
            "enddate": end_date,
            "units": "metric",
            "limit": 1000,
        }
        all_records = []
        offset = 1
        while True:
            params["offset"] = offset
            try:
                data = self._request("data", params)
                results = data.get("results", [])
                if not results:
                    break
                all_records.extend(results)
                if len(results) < 1000:
                    break
                offset += 1000
            except Exception as e:
                logger.error("Failed to fetch weather data: %s", e)
                break

        if not all_records:
            return pd.DataFrame()

        df = pd.DataFrame(all_records)
        df["date"] = pd.to_datetime(df["date"])
        df["station_id"] = station_id
        logger.info(
            "Fetched %d weather observations for station %s",
            len(df),
            station_id,
        )
        return df

    @staticmethod
    def pivot_observations(df: pd.DataFrame) -> pd.DataFrame:
        if df.empty:
            return df
        pivoted = df.pivot_table(
            index=["station_id", "date"],
            columns="datatype",
            values="value",
            aggfunc="mean",
        ).reset_index()
        pivoted.columns.name = None
        return pivoted
