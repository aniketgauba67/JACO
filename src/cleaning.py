from __future__ import annotations

import logging
import re
import unicodedata
from pathlib import Path
from typing import Iterable

import pandas as pd


LOGGER = logging.getLogger("jaco")


def configure_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s",
        datefmt="%H:%M:%S",
    )


def ensure_directories(paths: Iterable[Path]) -> None:
    for path in paths:
        path.mkdir(parents=True, exist_ok=True)


def require_columns(df: pd.DataFrame, required: Iterable[str], label: str) -> None:
    missing = [column for column in required if column not in df.columns]
    if missing:
        raise ValueError(f"{label} is missing required columns: {missing}")


def normalize_county_name(value: object) -> str | None:
    if pd.isna(value):
        return None
    text = str(value).strip()
    text = re.sub(r"\s+county$", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s+", " ", text)
    return text.title() if text else None


def normalize_zip(value: object) -> str | None:
    if pd.isna(value):
        return None
    match = re.search(r"(\d{5})", str(value))
    return match.group(1) if match else None


def normalize_school_name(value: object) -> str | None:
    if pd.isna(value):
        return None

    text = unicodedata.normalize("NFKD", str(value))
    text = text.encode("ascii", "ignore").decode("ascii")
    text = text.lower().strip()
    substitutions = {
        "&": " and ",
        "@": " at ",
        " jr ": " junior ",
        " sr ": " senior ",
    }
    for old, new in substitutions.items():
        text = text.replace(old, new)

    text = re.sub(r"[\.,'\"/\\\-\(\)\[\]\{\}:;]", " ", text)
    text = re.sub(r"\b(school district|city school district|local school district)\b", " ", text)
    text = re.sub(r"\b(elementary school|middle school|high school|school)\b", " ", text)
    text = re.sub(r"\b(academy|campus|center|centre)\b", lambda m: f" {m.group(0)} ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text or None


def format_int(value: float | int | None) -> str:
    if value is None or pd.isna(value):
        return ""
    return f"{int(round(float(value))):,}"


def format_pct(value: float | None) -> str:
    if value is None or pd.isna(value):
        return ""
    return f"{float(value):.1%}"

