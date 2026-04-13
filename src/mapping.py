from __future__ import annotations

import geopandas as gpd
import pandas as pd

from src.cleaning import normalize_county_name, normalize_zip
from src.config import OHIO_PROJECTION_EPSG, REGION_DEFINITIONS


def build_region_lookup() -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for definition in REGION_DEFINITIONS:
        for county in definition.counties:
            rows.append(
                {
                    "region_id": definition.region_id,
                    "region": definition.region,
                    "anchor_county": definition.anchor_county,
                    "county_name": county,
                }
            )
    return pd.DataFrame(rows).sort_values(["region_id", "county_name"]).reset_index(drop=True)


def build_zip_to_county_lookup(zip_raw: pd.DataFrame, counties_geo: gpd.GeoDataFrame) -> tuple[pd.DataFrame, dict[str, object]]:
    zip_map = zip_raw.copy()
    zip_map["ZIP"] = zip_map["ZIP"].map(normalize_zip)
    zip_map["TRACT"] = zip_map["TRACT"].astype(str).str.replace(r"\.0$", "", regex=True)
    zip_map = zip_map[zip_map["USPS_ZIP_PREF_STATE"] == "OH"].copy()

    ratio_fields = ["RES_RATIO", "TOT_RATIO", "BUS_RATIO", "OTH_RATIO"]
    for field in ratio_fields:
        zip_map[field] = pd.to_numeric(zip_map[field], errors="coerce")

    chosen_ratio_field = "RES_RATIO" if zip_map["RES_RATIO"].notna().any() else "TOT_RATIO"
    zip_map["ranking_ratio"] = zip_map[chosen_ratio_field].fillna(zip_map["TOT_RATIO"]).fillna(zip_map["BUS_RATIO"]).fillna(zip_map["OTH_RATIO"])
    zip_map["county_fips"] = zip_map["TRACT"].str[:5].str[-3:]
    zip_map = zip_map.sort_values(["ZIP", "ranking_ratio"], ascending=[True, False]).drop_duplicates("ZIP")

    zip_map = zip_map.merge(counties_geo[["county_fips", "county_name"]], on="county_fips", how="left")
    metadata = {
        "chosen_ratio_field": chosen_ratio_field,
        "ohio_zip_rows": int(len(zip_map)),
        "mapped_counties": int(zip_map["county_name"].notna().sum()),
    }
    return zip_map[["ZIP", "county_fips", "county_name", "ranking_ratio"]], metadata


def attach_region_geography(counties_geo: gpd.GeoDataFrame, region_lookup: pd.DataFrame) -> gpd.GeoDataFrame:
    geo = counties_geo.merge(region_lookup, on="county_name", how="left")
    geo["is_anchor"] = geo["county_name"] == geo["anchor_county"]
    return geo


def anchor_points(counties_geo: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    anchors = counties_geo[counties_geo["is_anchor"]].copy()
    projected = anchors.to_crs(OHIO_PROJECTION_EPSG)
    projected["geometry"] = projected.geometry.centroid
    return projected.to_crs(anchors.crs)

