from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Any

from sqlalchemy.inspection import inspect as sqlalchemy_inspect


def jsonable_value(value: Any) -> Any:
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, list):
        return [jsonable_value(item) for item in value]
    if isinstance(value, dict):
        return {key: jsonable_value(val) for key, val in value.items()}
    return value


def model_to_dict(instance: Any) -> dict[str, Any]:
    mapper = sqlalchemy_inspect(instance.__class__)
    data: dict[str, Any] = {}
    for column in mapper.columns:
        data[column.key] = jsonable_value(getattr(instance, column.key))
    return data

