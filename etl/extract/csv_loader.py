from pathlib import Path
from typing import Dict, List, Optional

import pandas as pd

from utils.logging_utils import logger


class CSVLoader:
    def __init__(self, data_dir: str | Path):
        self.data_dir = Path(data_dir)

    def list_available(self, pattern: str = "*.csv") -> List[Path]:
        return sorted(self.data_dir.glob(pattern))

    def load(
        self,
        filename: str | Path,
        parse_dates: Optional[List[str]] = None,
        dtype: Optional[Dict] = None,
        **kwargs,
    ) -> pd.DataFrame:
        path = Path(filename) if isinstance(filename, str) else filename
        if not path.is_absolute():
            path = self.data_dir / path

        if not path.exists():
            raise FileNotFoundError(f"CSV not found: {path}")

        df = pd.read_csv(
            path,
            parse_dates=parse_dates,
            dtype=dtype,
            low_memory=False,
            **kwargs,
        )
        logger.info("Loaded %s: %d rows x %d cols", path.name, len(df), len(df.columns))
        return df

    def load_all(
        self,
        pattern: str = "*.csv",
        parse_dates: Optional[List[str]] = None,
        **kwargs,
    ) -> Dict[str, pd.DataFrame]:
        files = self.list_available(pattern)
        result = {}
        for f in files:
            try:
                result[f.stem] = self.load(f, parse_dates=parse_dates, **kwargs)
            except Exception as e:
                logger.error("Failed to load %s: %s", f.name, e)
        return result

    @staticmethod
    def load_iso_prices(
        path: str | Path,
        iso: str,
        **kwargs,
    ) -> pd.DataFrame:
        df = pd.read_csv(path, low_memory=False, **kwargs)
        df["iso"] = iso
        logger.info("Loaded ISO prices for %s: %d rows", iso, len(df))
        return df

    @staticmethod
    def save_processed(
        df: pd.DataFrame,
        output_dir: str | Path,
        filename: str,
        index: bool = False,
    ) -> Path:
        path = Path(output_dir) / filename
        path.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(path, index=index)
        logger.info("Saved processed data: %s (%d rows)", path, len(df))
        return path
