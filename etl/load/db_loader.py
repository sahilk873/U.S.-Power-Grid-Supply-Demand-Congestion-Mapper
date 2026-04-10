from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

from config.database import db_config
from utils.logging_utils import logger


class DatabaseLoader:
    def __init__(self, engine: Optional[Engine] = None):
        self.engine = engine or create_engine(db_config.pymysql_url, pool_pre_ping=True)

    def test_connection(self) -> bool:
        try:
            with self.engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            logger.info("Database connection OK")
            return True
        except Exception as e:
            logger.error("Database connection failed: %s", e)
            return False

    def table_exists(self, table_name: str) -> bool:
        query = text(
            "SELECT COUNT(*) FROM information_schema.tables "
            "WHERE table_schema = :schema AND table_name = :table"
        )
        with self.engine.connect() as conn:
            result = conn.execute(
                query,
                {"schema": db_config.DATABASE, "table": table_name},
            )
            return result.scalar() > 0

    def get_table_columns(self, table_name: str) -> List[str]:
        query = text(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_schema = :schema AND table_name = :table"
        )
        with self.engine.connect() as conn:
            result = conn.execute(
                query,
                {"schema": db_config.DATABASE, "table": table_name},
            )
            return [row[0] for row in result]

    def truncate_table(self, table_name: str) -> None:
        with self.engine.connect() as conn:
            conn.execute(text(f"TRUNCATE TABLE {table_name}"))
            conn.commit()
        logger.info("Truncated table: %s", table_name)

    def _prepare_df_for_insert(self, df: pd.DataFrame, table_name: str) -> pd.DataFrame:
        df = df.copy()
        db_cols = self.get_table_columns(table_name)
        valid_cols = [
            c for c in df.columns if c.lower() in {col.lower() for col in db_cols}
        ]
        df = df[valid_cols]

        df = df.replace([np.inf, -np.inf], np.nan)
        df = df.where(pd.notna(df), None)

        for col in df.select_dtypes(
            include=["datetime64[ns, UTC]", "datetime64[ns]"]
        ).columns:
            df[col] = df[col].astype(object).where(df[col].notna(), None)

        return df

    def insert_dataframe(
        self,
        df: pd.DataFrame,
        table_name: str,
        if_exists: str = "append",
        chunksize: int = 10000,
        truncate_first: bool = False,
    ) -> int:
        if df.empty:
            logger.warning("Empty DataFrame — skipping insert into %s", table_name)
            return 0

        if truncate_first:
            self.truncate_table(table_name)

        df = self._prepare_df_for_insert(df, table_name)

        before = len(df)
        df.to_sql(
            table_name,
            self.engine,
            if_exists=if_exists,
            index=False,
            method="multi",
            chunksize=chunksize,
        )
        after = len(df)
        logger.info("Inserted %d rows into %s", after, table_name)
        return after

    def upsert_dataframe(
        self,
        df: pd.DataFrame,
        table_name: str,
        unique_keys: List[str],
        chunksize: int = 5000,
    ) -> Tuple[int, int]:
        if df.empty:
            return 0, 0

        df = self._prepare_df_for_insert(df, table_name)
        existing = pd.read_sql(
            f"SELECT {', '.join(unique_keys)} FROM {table_name}",
            self.engine,
        )

        if not existing.empty:
            existing_keys = existing[unique_keys].astype(str).agg("_".join, axis=1)
            incoming_keys = df[unique_keys].astype(str).agg("_".join, axis=1)
            new = df[~incoming_keys.isin(existing_keys)]
        else:
            new = df

        inserted = 0
        updated = 0
        if not new.empty:
            new.to_sql(
                table_name,
                self.engine,
                if_exists="append",
                index=False,
                method="multi",
                chunksize=chunksize,
            )
            inserted = len(new)

        logger.info(
            "Upsert into %s: %d inserted, %d updated (skipped %d existing)",
            table_name,
            inserted,
            updated,
            len(df) - inserted,
        )
        return inserted, updated

    def execute_sql(self, sql: str) -> None:
        with self.engine.connect() as conn:
            conn.execute(text(sql))
            conn.commit()

    def execute_sql_file(self, filepath: str) -> None:
        with open(filepath, "r") as f:
            sql = f.read()
        statements = [s.strip() for s in sql.split(";") if s.strip()]
        with self.engine.connect() as conn:
            for stmt in statements:
                if stmt.upper().startswith(
                    "CREATE DATABASE"
                ) or stmt.upper().startswith("USE"):
                    continue
                conn.execute(text(stmt))
            conn.commit()
        logger.info("Executed schema file: %s", filepath)

    def close(self) -> None:
        self.engine.dispose()
        logger.info("Database connection closed")
