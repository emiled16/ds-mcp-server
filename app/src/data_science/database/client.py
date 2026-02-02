import datetime
from collections.abc import Hashable
from functools import reduce
from pathlib import Path
from typing import Any, Dict, List, Literal, Type, TypeVar

import pandas as pd
import snowflake.snowpark.functions as f
from loguru import logger
from pydantic import BaseModel
from snowflake.snowpark import DataFrame, Session, Window

from src.data_science.database.base import Base
from src.data_science.snowflake.buffered_table import BufferedTable
from src.data_science.treasury_forecasting.constants import STAGE_PATH

T = TypeVar("T", bound=Base)


def table_path_from_orm(table_orm: Type[T]) -> str:
    return f"{table_orm.__table__.schema}.{table_orm.__table__.name}"


class Qualify(BaseModel):
    fn: Literal["row_number"] = "row_number"
    partition_by: list[str] | None = None
    order_by: list[str] | None = None
    asc: bool = True
    target: int | None = None

    def qualify(self, table: DataFrame) -> DataFrame:
        window = Window
        if self.partition_by:
            window = window.partition_by(*self.partition_by)
        if self.order_by:
            window = window.order_by(
                [f.col(order_by).asc() if self.asc else f.col(order_by).desc() for order_by in self.order_by],
            )

        table = table.with_column("rn", f.row_number().over(window).alias("rn"))

        return table.filter(f.col("rn") == self.target).drop("rn")


class DBClient:
    def __init__(self, session: Session, files_stage: str | None = STAGE_PATH):
        self.session = session
        self.files_stage = files_stage

    def insert_records(self, table_orm: Type[T], records: List[Dict[str, Any]]) -> None:
        if len(records) == 0:
            return
        columns = {k: categorize_column(v) for k, v in records[0].items()}

        buffered_table = BufferedTable(self.session, table_path_from_orm(table_orm), columns)
        with buffered_table:
            for record in records:
                buffered_table.add(record)

    def fetch_records(
        self,
        table_orm: Type[T],
        filters: dict[str, Any],
        qualify: Qualify | None = None,
    ) -> list[dict[Hashable, Any]]:
        table = self.session.table(table_path_from_orm(table_orm))
        if filters:
            table = table.filter(reduce(lambda x, y: x & y, [f.col(key) == value for key, value in filters.items()]))
        if qualify:
            table = qualify.qualify(table)
        return table.to_pandas().rename(columns=str.lower).to_dict(orient="records")

    def append_table(self, table_orm: Type[T], df: pd.DataFrame) -> None:
        if len(df) == 0:
            return

        table_path = f"{table_orm.__table__.schema}.{table_orm.__table__.name}"
        self.session.create_dataframe(df.rename(columns=str.upper)).write.mode("append").save_as_table(
            table_path, column_order="name"
        )
        # write_pandas(session=self.session, df=df.rename(columns=str.lower), table_path=table_path)

    def fetch_table(self, table_path: str, filters: dict[str, Any] | None = None) -> pd.DataFrame:
        """
        Example:
        filters = {
            "feature_store_id": "123",
            "workday_of_month_reverse": 1,
        }
        table = self.fetch_table(table_path, filters)
        table = table.assign(data=lambda _d: _d["data"].apply(json.loads))
        """

        # TODO: manage more complex filters (like in_list, etc.)
        table = self.session.table(table_path)
        if filters:
            table = table.filter(reduce(lambda x, y: x & y, [f.col(key) == value for key, value in filters.items()]))

        print(table.queries)
        return table.to_pandas().rename(columns=str.lower)

    def upload_files(self, path: Path, identifier: str, stage: str | None = None) -> str | None:
        session = self.session
        stage = stage or self.files_stage

        files_to_save: list[Path] = list(path.glob("**/*"))
        if len(files_to_save) == 0:
            return None

        directory_to_upload: list[Path] = []
        for model in files_to_save:
            if model.parent not in directory_to_upload:
                directory_to_upload.append(model.parent)

        target = f"{stage}/{identifier}"

        for directory in directory_to_upload:
            files = [f for f in directory.glob("*") if f.is_file() and f.suffix]
            if not files:
                continue

            target_path = directory.relative_to(path).as_posix()
            final_target = f"{target}/{target_path}" if target_path != "." else target
            session.file.put(
                # can't use `*`, or it fails, so the files NEED and extension to be uploaded
                f"{directory.as_posix()}/*.*",
                final_target,
            )
        return target

    def download_files(self, path: Path, identifier: str, stage: str | None = None) -> None:
        session = self.session
        stage = stage or self.files_stage

        logger.info(f"Downloading files from {stage}/{identifier}")

        session.file.get(identifier, str(path))


def categorize_column(col: Any) -> str:
    if isinstance(col, str):
        return "TEXT"
    if isinstance(col, int):
        return "NUMBER"
    if isinstance(col, float):
        return "FLOAT"
    if isinstance(col, bool):
        return "BOOLEAN"
    if isinstance(col, (datetime.datetime, pd.Timestamp)):
        return "TIMESTAMP"
    return "OBJECT"
