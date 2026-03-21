from __future__ import annotations

from dataclasses import fields, is_dataclass
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any
from unicodedata import normalize

from enum import Enum


class SerializableMixin:
    def to_dict(self) -> dict[str, Any]:
        return {
            field.name: serialize_value(getattr(self, field.name))
            for field in fields(self)
        }


def serialize_value(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if is_dataclass(value):
        return {
            field.name: serialize_value(getattr(value, field.name))
            for field in fields(value)
        }
    if isinstance(value, dict):
        return {key: serialize_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [serialize_value(item) for item in value]
    if isinstance(value, (set, frozenset)):
        return [serialize_value(item) for item in sorted(value, key=str)]
    return value


def normalize_token(value: str) -> str:
    ascii_value = normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    token = ascii_value.strip().lower().replace("-", "_").replace(" ", "_")
    while "__" in token:
        token = token.replace("__", "_")
    return token


def ensure_decimal(value: Any, field_name: str) -> Decimal:
    if isinstance(value, Decimal):
        return value
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError) as exc:
        raise ValueError(f"campo '{field_name}' deve ser numerico") from exc


def ensure_datetime(value: Any, field_name: str) -> datetime:
    if isinstance(value, datetime):
        result = value
    elif isinstance(value, str):
        normalized = value.replace("Z", "+00:00")
        try:
            result = datetime.fromisoformat(normalized)
        except ValueError as exc:
            raise ValueError(f"campo '{field_name}' deve ser datetime ISO-8601") from exc
    else:
        raise ValueError(f"campo '{field_name}' deve ser datetime")

    if result.tzinfo is None:
        raise ValueError(f"campo '{field_name}' deve conter timezone")
    return result


def ensure_date(value: Any, field_name: str) -> date:
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, str):
        try:
            return date.fromisoformat(value)
        except ValueError as exc:
            raise ValueError(f"campo '{field_name}' deve ser data ISO-8601") from exc
    raise ValueError(f"campo '{field_name}' deve ser data")


def ensure_string(value: Any, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"campo '{field_name}' deve ser texto nao vazio")
    return value.strip()
