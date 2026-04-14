from __future__ import annotations

from pathlib import Path

import geopandas as gpd
import pandas as pd
import requests

from src.cleaning import LOGGER, require_columns
from src.config import GEODATA_CACHE, INPUT_FILES, OHIO_COUNTY_URL, OHIO_FIPS, OPTIONAL_INPUT_FILES


def validate_input_files() -> None:
    missing = [path.name for path in INPUT_FILES.values() if not path.exists()]
    if missing:
        missing_display = ", ".join(missing)
        raise FileNotFoundError(
            f"Missing required input files: {missing_display}. "
            "Place the required source files in the project root and rerun `python run_pipeline.py`."
        )


def load_population_data() -> tuple[pd.DataFrame, dict[str, object]]:
    df = pd.read_csv(INPUT_FILES["population"])
    require_columns(df, ["SUMLEV", "STATE", "COUNTY", "CTYNAME", "YEAR", "AGEGRP", "TOT_POP"], "JACO.csv")
    metadata = {"columns": df.columns.tolist(), "age_groups": sorted(pd.to_numeric(df["AGEGRP"], errors="coerce").dropna().unique().tolist())}
    return df, metadata


def load_school_data() -> tuple[pd.DataFrame, dict[str, object]]:
    df = pd.read_csv(INPUT_FILES["schools"], low_memory=False)
    metadata = {"columns": df.columns.tolist()}
    return df, metadata


def load_school_coordinate_data() -> tuple[pd.DataFrame | None, dict[str, object]]:
    path = OPTIONAL_INPUT_FILES["school_coordinates"]
    if not path.exists():
        return None, {"available": False, "path": str(path)}

    workbook = pd.ExcelFile(path)
    preferred = [name for name in workbook.sheet_names if name.strip().lower() == "school coordinates"]
    sheet_name = preferred[0] if preferred else workbook.sheet_names[0]
    df = pd.read_excel(path, sheet_name=sheet_name)
    require_columns(df, ["School Name", "County", "Latitude", "Longitude"], "School coordinates workbook")
    metadata = {
        "available": True,
        "path": str(path),
        "sheet_name": sheet_name,
        "columns": df.columns.tolist(),
        "workbook_sheets": workbook.sheet_names,
        "row_count": int(len(df)),
    }
    return df, metadata


def inspect_workbook(path: Path) -> dict[str, dict[str, object]]:
    workbook = pd.ExcelFile(path)
    summary: dict[str, dict[str, object]] = {}
    for sheet in workbook.sheet_names:
        preview = workbook.parse(sheet, nrows=5)
        summary[sheet] = {
            "columns": preview.columns.tolist(),
            "rows": len(preview),
        }
    return summary


def choose_high_need_sheet(path: Path) -> str:
    workbook = pd.ExcelFile(path)
    preferred = [name for name in workbook.sheet_names if name.strip().lower() == "building allocations"]
    if preferred:
        return preferred[0]
    fallback = [name for name in workbook.sheet_names if "building" in name.lower()]
    if fallback:
        return fallback[0]
    raise ValueError("Could not find a building-level high-need sheet in the Title I workbook.")


def load_high_need_data() -> tuple[pd.DataFrame, dict[str, object]]:
    path = INPUT_FILES["high_need"]
    sheet_name = choose_high_need_sheet(path)
    df = pd.read_excel(path, sheet_name=sheet_name, header=1)
    require_columns(
        df,
        ["Building IRN", "Building Name", "LEA Name", "Federal ESEA Identification ", "TI NC SSI Students Served"],
        "High-need workbook",
    )
    metadata = {"sheet_name": sheet_name, "columns": df.columns.tolist(), "workbook_sheets": pd.ExcelFile(path).sheet_names}
    return df, metadata


def load_zip_tract_data() -> tuple[pd.DataFrame, dict[str, object]]:
    path = INPUT_FILES["zip_tract"]
    workbook = pd.ExcelFile(path)
    sheet_name = "Export Worksheet" if "Export Worksheet" in workbook.sheet_names else workbook.sheet_names[0]
    df = pd.read_excel(path, sheet_name=sheet_name)
    require_columns(df, ["ZIP", "TRACT", "USPS_ZIP_PREF_STATE", "RES_RATIO", "BUS_RATIO", "OTH_RATIO", "TOT_RATIO"], "ZIP_TRACT workbook")
    metadata = {"sheet_name": sheet_name, "columns": df.columns.tolist(), "workbook_sheets": workbook.sheet_names}
    return df, metadata


def choose_tracker_sheet(path: Path) -> str:
    workbook = pd.ExcelFile(path)
    preferred = [name for name in workbook.sheet_names if name.strip().lower() == "call log"]
    if preferred:
        return preferred[0]
    return workbook.sheet_names[0]


def load_tracker_data() -> tuple[pd.DataFrame, dict[str, object]]:
    path = INPUT_FILES["tracker"]
    workbook = pd.ExcelFile(path)
    sheet_name = choose_tracker_sheet(path)
    df = pd.read_excel(path, sheet_name=sheet_name, header=1)
    require_columns(df, ["Organization", "City", "County", "Outcome", "Stage"], "JA Cold Call Tracker")
    metadata = {
        "sheet_name": sheet_name,
        "columns": df.columns.tolist(),
        "workbook_sheets": workbook.sheet_names,
        "sheet_inspection": inspect_workbook(path),
    }
    return df, metadata


def get_ohio_counties() -> gpd.GeoDataFrame:
    GEODATA_CACHE.mkdir(parents=True, exist_ok=True)
    zip_path = GEODATA_CACHE / "cb_2023_us_county_500k.zip"
    if not zip_path.exists():
        LOGGER.info("Downloading Ohio county boundaries from Census TIGER/Line.")
        response = requests.get(OHIO_COUNTY_URL, timeout=60)
        response.raise_for_status()
        zip_path.write_bytes(response.content)

    counties = gpd.read_file(zip_path)
    counties = counties[counties["STATEFP"] == OHIO_FIPS].copy()
    counties = counties[["GEOID", "NAME", "geometry"]].rename(columns={"NAME": "county_name"})
    counties["county_name"] = counties["county_name"].str.title()
    counties["county_fips"] = counties["GEOID"].str[-3:]
    return counties
