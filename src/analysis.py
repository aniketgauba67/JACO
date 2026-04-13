from __future__ import annotations

from dataclasses import dataclass

import geopandas as gpd
import pandas as pd
from rapidfuzz import fuzz, process

from src.cleaning import LOGGER, normalize_county_name, normalize_school_name, normalize_zip
from src.config import (
    FEASIBILITY_RADIUS_MILES,
    FUZZY_NAME_THRESHOLD,
    OHIO_FIPS,
    OHIO_STATE_ABBR,
    TRACKER_MATCH_THRESHOLD,
    YOUTH_AGE_GROUPS,
)


@dataclass
class PipelineArtifacts:
    county_summary: pd.DataFrame
    youth_by_region: pd.DataFrame
    schools_by_region: pd.DataFrame
    high_need_by_region: pd.DataFrame
    tracker_summary: pd.DataFrame
    feasibility_by_region: pd.DataFrame
    county_feasibility_detail: pd.DataFrame
    region_summary: pd.DataFrame
    schools_clean: pd.DataFrame
    school_list_by_region: pd.DataFrame
    high_need_match_detail: pd.DataFrame
    high_need_match_summary: pd.DataFrame
    tracker_match_detail: pd.DataFrame
    tracker_match_summary: pd.DataFrame
    tracker_value_audit: pd.DataFrame
    tracker_response_rules: pd.DataFrame
    join_audit_summary: pd.DataFrame
    region_geo: gpd.GeoDataFrame
    metadata: dict[str, object]


def inspect_age_groups(population_raw: pd.DataFrame) -> list[int]:
    return sorted(pd.to_numeric(population_raw["AGEGRP"], errors="coerce").dropna().astype(int).unique().tolist())


def analyze_population(population_raw: pd.DataFrame, region_lookup: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, object]]:
    population = population_raw.copy()
    population["STATE"] = population["STATE"].astype(str).str.zfill(2)
    population["SUMLEV"] = population["SUMLEV"].astype(str).str.zfill(3)
    population["YEAR"] = pd.to_numeric(population["YEAR"], errors="coerce")
    population["AGEGRP"] = pd.to_numeric(population["AGEGRP"], errors="coerce")
    population["TOT_POP"] = pd.to_numeric(population["TOT_POP"], errors="coerce")
    latest_year_code = int(population["YEAR"].max())

    available_age_groups = inspect_age_groups(population)
    required_youth_groups = list(YOUTH_AGE_GROUPS.keys())
    if not set(required_youth_groups).issubset(set(available_age_groups)):
        raise ValueError(
            f"Expected youth AGEGRP codes {required_youth_groups}, but found {available_age_groups[:20]} in JACO.csv."
        )

    county_rows = population[
        (population["STATE"] == OHIO_FIPS)
        & (population["SUMLEV"] == "050")
        & (population["YEAR"] == latest_year_code)
        & (population["AGEGRP"] == 0)
    ].copy()
    county_rows["county_name"] = county_rows["CTYNAME"].map(normalize_county_name)
    county_rows["county_fips"] = county_rows["COUNTY"].astype(str).str.zfill(3)
    county_rows["total_population"] = county_rows["TOT_POP"]

    youth_rows = population[
        (population["STATE"] == OHIO_FIPS)
        & (population["SUMLEV"] == "050")
        & (population["YEAR"] == latest_year_code)
        & (population["AGEGRP"].isin(required_youth_groups))
    ].copy()
    youth_rows["county_name"] = youth_rows["CTYNAME"].map(normalize_county_name)
    youth_by_county = youth_rows.groupby("county_name", as_index=False)["TOT_POP"].sum().rename(columns={"TOT_POP": "youth_population"})

    county_summary = county_rows[["county_name", "county_fips", "total_population"]].merge(youth_by_county, on="county_name", how="left")
    county_summary = county_summary.merge(region_lookup, on="county_name", how="left")
    county_summary["is_anchor"] = county_summary["county_name"] == county_summary["anchor_county"]

    youth_by_region = (
        county_summary[county_summary["region"].notna()]
        .groupby(["region_id", "region", "anchor_county"], as_index=False)
        .agg(
            counties_in_region=("county_name", lambda values: ", ".join(sorted(values))),
            youth_population=("youth_population", "sum"),
            total_population=("total_population", "sum"),
            county_count=("county_name", "nunique"),
        )
        .sort_values("region_id")
    )
    youth_by_region["region_id"] = youth_by_region["region_id"].astype(int)

    metadata = {
        "latest_year_code": latest_year_code,
        "available_age_groups": available_age_groups,
        "selected_youth_age_groups": required_youth_groups,
        "selected_youth_labels": [YOUTH_AGE_GROUPS[code] for code in required_youth_groups],
        "ohio_counties_found": int(len(county_summary)),
        "grouped_counties_found": int(county_summary["region"].notna().sum()),
        "grouped_counties_expected": int(region_lookup["county_name"].nunique()),
    }
    LOGGER.info("Population logic: latest YEAR=%s, youth AGEGRP=%s", latest_year_code, required_youth_groups)
    return county_summary, youth_by_region, metadata


def detect_coordinate_columns(schools_raw: pd.DataFrame) -> dict[str, str | None]:
    columns = schools_raw.columns.tolist()
    lat_candidates = [name for name in columns if any(token in name.lower() for token in ["lat", "latitude"])]
    lon_candidates = [name for name in columns if any(token in name.lower() for token in ["lon", "longitude", "lng"])]
    return {
        "latitude": lat_candidates[0] if lat_candidates else None,
        "longitude": lon_candidates[0] if lon_candidates else None,
    }


def prepare_schools(
    schools_raw: pd.DataFrame,
    zip_lookup: pd.DataFrame,
    region_lookup: pd.DataFrame,
    counties_geo: gpd.GeoDataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, dict[str, object]]:
    coords = detect_coordinate_columns(schools_raw)
    schools = schools_raw.copy()
    schools = schools[(schools["ST"] == OHIO_STATE_ABBR) & (schools["SY_STATUS_TEXT"].fillna("").str.contains("Open", case=False))].copy()

    schools["NCESSCH"] = schools["NCESSCH"].astype(str).str.extract(r"(\d+)", expand=False)
    schools["school_name_clean"] = schools["SCH_NAME"].map(normalize_school_name)
    schools["district_name_clean"] = schools["LEA_NAME"].map(normalize_school_name)
    schools["zip5"] = schools["LZIP"].fillna(schools["MZIP"]).map(normalize_zip)
    schools["school_irn"] = schools["ST_SCHID"].astype(str).str.extract(r"(\d{6})$", expand=False)
    schools["county_name"] = schools["zip5"].map(dict(zip(zip_lookup["ZIP"], zip_lookup["county_name"])))
    schools["region"] = schools["county_name"].map(dict(zip(region_lookup["county_name"], region_lookup["region"])))
    schools["region_id"] = schools["county_name"].map(dict(zip(region_lookup["county_name"], region_lookup["region_id"])))
    schools["anchor_county"] = schools["county_name"].map(dict(zip(region_lookup["county_name"], region_lookup["anchor_county"])))
    schools["school_level"] = schools["LEVEL"]
    schools["school_type"] = schools["SCH_TYPE_TEXT"]
    schools["is_regular_or_cte"] = schools["SCH_TYPE_TEXT"].isin(["Regular School", "Career and Technical School"])

    if coords["latitude"] and coords["longitude"]:
        schools["latitude"] = pd.to_numeric(schools[coords["latitude"]], errors="coerce")
        schools["longitude"] = pd.to_numeric(schools[coords["longitude"]], errors="coerce")
    else:
        schools["latitude"] = pd.NA
        schools["longitude"] = pd.NA

    county_points = counties_geo.to_crs(3734)[["county_name", "geometry"]].copy()
    county_points["geometry"] = county_points.geometry.centroid
    county_points = county_points.to_crs(4326)
    county_points["county_latitude"] = county_points.geometry.y
    county_points["county_longitude"] = county_points.geometry.x
    schools = schools.merge(county_points[["county_name", "county_latitude", "county_longitude"]], on="county_name", how="left")

    # Approximate fallback coordinates: county centroid plus a deterministic jitter so schools do not stack perfectly.
    school_key = schools["NCESSCH"].fillna(schools["SCH_NAME"]).astype(str)
    offset_x = school_key.map(lambda value: ((abs(hash(f"{value}-x")) % 1000) / 999) - 0.5)
    offset_y = school_key.map(lambda value: ((abs(hash(f"{value}-y")) % 1000) / 999) - 0.5)
    schools["approx_longitude"] = schools["county_longitude"] + offset_x * 0.12
    schools["approx_latitude"] = schools["county_latitude"] + offset_y * 0.08
    schools["location_method"] = schools["county_name"].notna().map({True: "county_centroid_jitter", False: "unmapped"})

    schools_by_region = (
        schools[schools["region"].notna() & schools["is_regular_or_cte"]]
        .groupby(["region_id", "region", "anchor_county"], as_index=False)
        .agg(total_schools=("NCESSCH", "nunique"))
        .sort_values("region_id")
    )
    schools_by_region["region_id"] = schools_by_region["region_id"].astype(int)
    school_list_by_region = (
        schools[schools["region"].notna() & schools["is_regular_or_cte"]]
        .sort_values(["region_id", "county_name", "SCH_NAME"])
        [
            ["region_id", "region", "anchor_county", "county_name", "SCH_NAME", "LEA_NAME", "school_level", "school_type", "zip5"]
        ]
    )
    metadata = {
        "coordinate_columns": coords,
        "coordinate_rows_available": int(schools["latitude"].notna().sum() if coords["latitude"] else 0),
        "approximate_coordinate_rows": int(schools["approx_latitude"].notna().sum()),
        "schools_total_ohio": int(len(schools)),
        "schools_mapped_to_county": int(schools["county_name"].notna().sum()),
        "schools_mapped_to_region": int(schools["region"].notna().sum()),
        "zip_match_rate": float(schools["county_name"].notna().mean()),
        "region_match_rate": float(schools["region"].notna().mean()),
    }
    LOGGER.info("School coordinate columns: %s", coords)
    return schools, schools_by_region, school_list_by_region, metadata


def prepare_high_need(high_need_raw: pd.DataFrame) -> pd.DataFrame:
    df = high_need_raw.copy()
    df["building_irn"] = (
        pd.to_numeric(df["Building IRN"], errors="coerce").astype("Int64").astype(str).str.replace("<NA>", "", regex=False).str.zfill(6)
    )
    df["school_name_clean"] = df["Building Name"].map(normalize_school_name)
    df["district_name_clean"] = df["LEA Name"].map(normalize_school_name)
    df["students_served"] = pd.to_numeric(df["TI NC SSI Students Served"], errors="coerce").fillna(0)
    df["high_need"] = df["students_served"] > 0
    return df[
        [
            "building_irn",
            "school_name_clean",
            "district_name_clean",
            "Building Name",
            "LEA Name",
            "Federal ESEA Identification ",
            "students_served",
            "high_need",
        ]
    ].drop_duplicates()


def match_high_need(schools: pd.DataFrame, high_need: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    merged = schools.merge(high_need, left_on="school_irn", right_on="building_irn", how="left", suffixes=("", "_high_need"))
    merged["match_method"] = None
    merged["match_score"] = pd.NA
    merged.loc[merged["building_irn"].notna(), "match_method"] = "exact_irn"

    unmatched = merged[merged["building_irn"].isna()].copy()
    unique_high_need_names = high_need["school_name_clean"].value_counts()
    unique_name_lookup = high_need[high_need["school_name_clean"].isin(unique_high_need_names[unique_high_need_names == 1].index)].copy()
    unique_name_lookup = unique_name_lookup.drop_duplicates("school_name_clean")
    exact_name_matches = unmatched.merge(
        unique_name_lookup[
            [
                "school_name_clean",
                "building_irn",
                "Building Name",
                "LEA Name",
                "Federal ESEA Identification ",
                "students_served",
                "high_need",
            ]
        ],
        on="school_name_clean",
        how="left",
        suffixes=("", "_name"),
    )
    exact_name_mask = exact_name_matches["building_irn_name"].notna()
    if exact_name_mask.any():
        for column in ["building_irn", "Building Name", "LEA Name", "Federal ESEA Identification ", "students_served", "high_need"]:
            exact_name_matches.loc[exact_name_mask, column] = exact_name_matches.loc[exact_name_mask, f"{column}_name"]
        exact_name_matches.loc[exact_name_mask, "match_method"] = "exact_unique_name"
        exact_name_matches.loc[exact_name_mask, "match_score"] = 100
    exact_name_matches = exact_name_matches.drop(columns=[column for column in exact_name_matches.columns if column.endswith("_name")])
    merged.loc[merged["building_irn"].isna(), exact_name_matches.columns] = exact_name_matches.values

    unmatched = merged[merged["building_irn"].isna()].copy()
    candidate_lookup = high_need.groupby("district_name_clean")
    fuzzy_records = []
    for _, school in unmatched.iterrows():
        district_key = school["district_name_clean"]
        if pd.isna(district_key) or district_key not in candidate_lookup.groups:
            fuzzy_records.append({"NCESSCH": school["NCESSCH"], "match_method": "unmatched", "match_score": None})
            continue
        candidates = candidate_lookup.get_group(district_key)
        choices = candidates["school_name_clean"].dropna().tolist()
        if not school["school_name_clean"] or not choices:
            fuzzy_records.append({"NCESSCH": school["NCESSCH"], "match_method": "unmatched", "match_score": None})
            continue
        best = process.extractOne(school["school_name_clean"], choices, scorer=fuzz.token_sort_ratio)
        if best and best[1] >= FUZZY_NAME_THRESHOLD:
            matched_row = candidates[candidates["school_name_clean"] == best[0]].iloc[0]
            fuzzy_records.append(
                {
                    "NCESSCH": school["NCESSCH"],
                    "building_irn": matched_row["building_irn"],
                    "Building Name": matched_row["Building Name"],
                    "LEA Name": matched_row["LEA Name"],
                    "Federal ESEA Identification ": matched_row["Federal ESEA Identification "],
                    "students_served": matched_row["students_served"],
                    "high_need": matched_row["high_need"],
                    "match_method": "normalized_name",
                    "match_score": best[1],
                }
            )
        else:
            fuzzy_records.append({"NCESSCH": school["NCESSCH"], "match_method": "unmatched", "match_score": best[1] if best else None})

    fuzzy_df = pd.DataFrame(fuzzy_records)
    if not fuzzy_df.empty:
        merged = merged.merge(fuzzy_df, on="NCESSCH", how="left", suffixes=("", "_fuzzy"))
        for column in ["building_irn", "Building Name", "LEA Name", "Federal ESEA Identification ", "students_served", "high_need"]:
            if f"{column}_fuzzy" in merged.columns:
                merged[column] = merged[column].fillna(merged[f"{column}_fuzzy"])
        merged["match_method"] = merged["match_method"].fillna(merged["match_method_fuzzy"])
        merged["match_score"] = merged["match_score"].fillna(merged["match_score_fuzzy"])
        merged = merged.drop(columns=[column for column in merged.columns if column.endswith("_fuzzy")])

    merged["high_need"] = merged["high_need"].fillna(False)
    merged["students_served"] = merged["students_served"].fillna(0)

    match_detail = merged[
        [
            "region_id",
            "region",
            "county_name",
            "NCESSCH",
            "SCH_NAME",
            "LEA_NAME_x" if "LEA_NAME_x" in merged.columns else "LEA_NAME",
            "school_irn",
            "Building Name",
            "students_served",
            "high_need",
            "match_method",
            "match_score",
        ]
    ].copy()
    if "LEA_NAME_x" in match_detail.columns:
        match_detail = match_detail.rename(columns={"LEA_NAME_x": "LEA_NAME"})
    match_summary = (
        match_detail.groupby("match_method", dropna=False, as_index=False)
        .agg(school_records=("NCESSCH", "count"))
        .sort_values("school_records", ascending=False)
    )
    LOGGER.info("High-need match summary:\n%s", match_summary.to_string(index=False))
    return merged, match_detail, match_summary


def summarize_high_need(schools_with_need: pd.DataFrame) -> pd.DataFrame:
    filtered = schools_with_need[schools_with_need["region"].notna() & schools_with_need["is_regular_or_cte"]].copy()
    filtered["high_need_int"] = filtered["high_need"].astype(int)
    high_need_by_region = (
        filtered.groupby(["region_id", "region", "anchor_county"], as_index=False)
        .agg(
            total_schools=("NCESSCH", "nunique"),
            high_need_schools=("high_need_int", "sum"),
            title_students_served=("students_served", "sum"),
        )
        .sort_values("region_id")
    )
    high_need_by_region["region_id"] = high_need_by_region["region_id"].astype(int)
    high_need_by_region["high_need_share"] = high_need_by_region["high_need_schools"] / high_need_by_region["total_schools"]
    return high_need_by_region


def prepare_tracker(tracker_raw: pd.DataFrame, region_lookup: pd.DataFrame, schools_with_need: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, dict[str, object]]:
    tracker = tracker_raw.copy().dropna(how="all")
    tracker["organization_name"] = tracker["Organization"].astype(str).str.strip()
    tracker["org_name_clean"] = tracker["Organization"].map(normalize_school_name)
    tracker["county_name"] = tracker["County"].map(normalize_county_name)
    tracker["outcome_clean"] = tracker["Outcome"].astype(str).str.lower().str.strip()
    tracker["positive_response"] = tracker["outcome_clean"] == "interested"
    tracker["region"] = tracker["county_name"].map(dict(zip(region_lookup["county_name"], region_lookup["region"])))
    tracker["region_id"] = tracker["county_name"].map(dict(zip(region_lookup["county_name"], region_lookup["region_id"])))

    tracker_value_audit = (
        tracker["outcome_clean"]
        .replace("", "(blank)")
        .fillna("(blank)")
        .value_counts(dropna=False)
        .rename_axis("outcome_clean")
        .reset_index(name="count")
        .sort_values(["count", "outcome_clean"], ascending=[False, True])
    )
    tracker_value_audit["is_positive"] = tracker_value_audit["outcome_clean"] == "interested"
    interested_rows = int(tracker["positive_response"].sum())
    LOGGER.info("Tracker outcome audit:\n%s", tracker_value_audit.to_string(index=False))
    LOGGER.info("Tracker outcome audit: total rows with outcome_clean == 'interested' = %s", interested_rows)

    school_reference = schools_with_need[schools_with_need["region"].notna() & schools_with_need["is_regular_or_cte"]].copy()
    school_reference = school_reference[
        ["NCESSCH", "SCH_NAME", "school_name_clean", "county_name", "region", "region_id", "high_need"]
    ].sort_values(["county_name", "school_name_clean", "NCESSCH"])
    school_reference = (
        school_reference.groupby(["school_name_clean", "county_name"], as_index=False)
        .agg(
            NCESSCH=("NCESSCH", "first"),
            SCH_NAME=("SCH_NAME", "first"),
            region=("region", "first"),
            region_id=("region_id", "first"),
            high_need=("high_need", "max"),
        )
    )
    unique_name_reference = (
        school_reference.groupby("school_name_clean", as_index=False)
        .agg(
            NCESSCH=("NCESSCH", "first"),
            SCH_NAME=("SCH_NAME", "first"),
            county_name_school=("county_name", "first"),
            region_school=("region", "first"),
            region_id_school=("region_id", "first"),
            high_need=("high_need", "max"),
            school_record_count=("NCESSCH", "nunique"),
        )
    )
    unique_name_reference = unique_name_reference[unique_name_reference["school_record_count"] == 1].drop(columns=["school_record_count"])

    exact = tracker.merge(
        school_reference,
        left_on=["org_name_clean", "county_name"],
        right_on=["school_name_clean", "county_name"],
        how="left",
        suffixes=("_tracker", "_school"),
    )
    exact["match_method"] = exact["NCESSCH"].notna().map({True: "normalized_name_county", False: "unmatched"})
    exact["match_score"] = pd.NA

    unmatched_mask = exact["NCESSCH"].isna()
    if unmatched_mask.any():
        name_only = exact.loc[unmatched_mask].merge(
            unique_name_reference,
            left_on="org_name_clean",
            right_on="school_name_clean",
            how="left",
            suffixes=("", "_name_only"),
        )
        name_only_mask = name_only["NCESSCH_name_only"].notna()
        if name_only_mask.any():
            exact.loc[unmatched_mask, "NCESSCH"] = name_only["NCESSCH_name_only"].values
            exact.loc[unmatched_mask, "SCH_NAME"] = name_only["SCH_NAME_name_only"].values
            exact.loc[unmatched_mask, "region_school"] = name_only["region_school_name_only"].values
            exact.loc[unmatched_mask, "region_id_school"] = name_only["region_id_school_name_only"].values
            exact.loc[unmatched_mask, "high_need"] = name_only["high_need_name_only"].values
            exact.loc[unmatched_mask, "match_method"] = name_only_mask.map({True: "normalized_name_unique", False: "unmatched"}).values

    if exact["NCESSCH"].isna().any():
        unmatched = exact[exact["NCESSCH"].isna()].copy()
        fuzzy_records = []
        for index, row in unmatched.iterrows():
            county_options = school_reference[school_reference["county_name"] == row["county_name"]]
            if county_options.empty or not row["org_name_clean"]:
                fuzzy_records.append((index, None, None, None, None, None, "unmatched"))
                continue
            best = process.extractOne(row["org_name_clean"], county_options["school_name_clean"].tolist(), scorer=fuzz.token_sort_ratio)
            if best and best[1] >= FUZZY_NAME_THRESHOLD:
                matched_school = county_options[county_options["school_name_clean"] == best[0]].iloc[0]
                fuzzy_records.append(
                    (
                        index,
                        matched_school["NCESSCH"],
                        matched_school["SCH_NAME"],
                        matched_school["region"],
                        matched_school["region_id"],
                        best[1],
                        "fuzzy_name_county",
                    )
                )
            else:
                fuzzy_records.append((index, None, None, None, None, best[1] if best else None, "unmatched"))

        for index, ncessch, matched_name, matched_region, matched_region_id, score, method in fuzzy_records:
            exact.loc[index, "NCESSCH"] = ncessch
            exact.loc[index, "SCH_NAME"] = matched_name
            exact.loc[index, "region_school"] = matched_region
            exact.loc[index, "region_id_school"] = matched_region_id
            exact.loc[index, "match_score"] = score
            exact.loc[index, "match_method"] = method

    school_match_rate = float(exact["NCESSCH"].notna().mean())
    exact["NCESSCH"] = exact["NCESSCH"].astype("string").str.replace(r"\.0$", "", regex=True)
    exact["final_region"] = exact["region_tracker"].fillna(exact["region_school"])
    tracker_summary = (
        exact.groupby(["final_region"], dropna=False, as_index=False)
        .agg(
            outreach_records=("organization_name", "count"),
            positive_responses=("positive_response", "sum"),
            matched_rows=("NCESSCH", lambda values: values.notna().sum()),
        )
        .rename(columns={"final_region": "region"})
    )
    tracker_summary["positive_response_rate"] = tracker_summary["positive_responses"] / tracker_summary["outreach_records"]
    tracker_summary["school_match_rate_within_region"] = tracker_summary["matched_rows"] / tracker_summary["outreach_records"]

    tracker_match_summary = (
        exact.groupby("match_method", dropna=False, as_index=False)
        .agg(rows=("organization_name", "count"))
        .sort_values("rows", ascending=False)
    )
    tracker_response_rules = pd.DataFrame(
        [
            {
                "field": "Outcome",
                "value": value,
                "included_as_positive": value == "interested",
                "rule": "positive_response = outcome_clean == 'interested'",
            }
            for value in tracker_value_audit["outcome_clean"].tolist()
        ]
    )
    matched_rows_total = int(exact["NCESSCH"].notna().sum())
    positive_matched_rows = int((exact["positive_response"].fillna(False) & exact["NCESSCH"].notna()).sum())
    positive_matched_schools = int(
        exact.loc[exact["positive_response"].fillna(False) & exact["NCESSCH"].notna(), "NCESSCH"].astype(str).nunique()
    )
    LOGGER.info("Tracker matching totals: tracker rows total = %s", int(len(exact)))
    LOGGER.info("Tracker matching totals: matched schools total = %s", matched_rows_total)
    LOGGER.info("Tracker matching totals: positive tracker rows total = %s", interested_rows)
    LOGGER.info("Tracker matching totals: positive matched schools total = %s", positive_matched_schools)
    if positive_matched_schools == 0:
        interested_school_names = (
            tracker.loc[tracker["positive_response"], "organization_name"].dropna().astype(str).str.strip().unique().tolist()
        )
        school_name_samples = school_reference["school_name_clean"].dropna().astype(str).unique().tolist()[:50]
        LOGGER.warning("No positive matched schools found — check school-name matching.")
        LOGGER.warning("Interested tracker school names: %s", interested_school_names)
        LOGGER.warning("First 50 normalized school names from school dataset: %s", school_name_samples)

    tracker_metadata = {
        "school_match_rate": school_match_rate,
        "suitable_for_school_overlay": school_match_rate >= TRACKER_MATCH_THRESHOLD,
        "total_rows": int(len(exact)),
        "matched_rows": matched_rows_total,
        "region_assignment_rate": float(exact["final_region"].notna().mean()),
        "positive_response_rows": interested_rows,
        "positive_matched_rows": positive_matched_rows,
        "positive_matched_schools": positive_matched_schools,
    }
    LOGGER.info("Tracker match summary:\n%s", tracker_match_summary.to_string(index=False))
    return exact, tracker_summary, tracker_match_summary, tracker_metadata, tracker_value_audit, tracker_response_rules


def analyze_anchor_feasibility(region_geo: gpd.GeoDataFrame) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, object]]:
    grouped = region_geo[region_geo["region"].notna()].copy().to_crs(3734)
    grouped["centroid"] = grouped.geometry.centroid

    anchor_lookup = (
        grouped[grouped["is_anchor"]]
        .set_index("region")[["anchor_county", "centroid"]]
        .rename(columns={"centroid": "anchor_centroid"})
    )
    grouped = grouped.merge(anchor_lookup, on=["region", "anchor_county"], how="left")
    grouped["anchor_to_county_miles"] = grouped.apply(
        lambda row: row["centroid"].distance(row["anchor_centroid"]) / 1609.34 if row["anchor_centroid"] is not None else pd.NA,
        axis=1,
    )
    grouped["feasible_1hr_proxy"] = grouped["anchor_to_county_miles"] <= FEASIBILITY_RADIUS_MILES
    detail = pd.DataFrame(
        {
            "region_id": grouped["region_id"].astype(int),
            "region": grouped["region"],
            "anchor_county": grouped["anchor_county"],
            "county_name": grouped["county_name"],
            "anchor_to_county_miles": grouped["anchor_to_county_miles"].round(1),
            "feasible_1hr_proxy": grouped["feasible_1hr_proxy"],
            "proxy_method": f"County centroid distance; feasible if <= {FEASIBILITY_RADIUS_MILES:.0f} miles",
        }
    ).sort_values(["region_id", "anchor_to_county_miles"], ascending=[True, False])

    summary = (
        detail.groupby(["region_id", "region", "anchor_county"], as_index=False)
        .agg(
            max_anchor_distance_miles=("anchor_to_county_miles", "max"),
            avg_anchor_distance_miles=("anchor_to_county_miles", "mean"),
            counties_in_proxy_radius=("feasible_1hr_proxy", "sum"),
            county_count=("county_name", "count"),
        )
        .sort_values("region_id")
    )
    summary["counties_outside_proxy_radius"] = summary["county_count"] - summary["counties_in_proxy_radius"]
    summary["feasible_1hr_proxy"] = summary["counties_outside_proxy_radius"] == 0
    summary["proxy_method"] = f"County centroid distance; feasible if <= {FEASIBILITY_RADIUS_MILES:.0f} miles"
    metadata = {"feasibility_radius_miles": FEASIBILITY_RADIUS_MILES}
    return detail, summary, metadata


def build_join_audit_summary(
    region_lookup: pd.DataFrame,
    county_summary: pd.DataFrame,
    zip_lookup: pd.DataFrame,
    schools: pd.DataFrame,
    high_need_match_detail: pd.DataFrame,
    tracker_match_detail: pd.DataFrame,
    high_need_match_summary: pd.DataFrame,
    tracker_match_summary: pd.DataFrame,
) -> pd.DataFrame:
    high_need_exact = int(high_need_match_summary.loc[high_need_match_summary["match_method"] == "exact_irn", "school_records"].sum())
    high_need_unique_name = int(
        high_need_match_summary.loc[high_need_match_summary["match_method"] == "exact_unique_name", "school_records"].sum()
    )
    high_need_normalized = int(
        high_need_match_summary.loc[high_need_match_summary["match_method"] == "normalized_name", "school_records"].sum()
    )
    tracker_name_county = int(
        tracker_match_summary.loc[tracker_match_summary["match_method"] == "normalized_name_county", "rows"].sum()
    )
    tracker_name_unique = int(
        tracker_match_summary.loc[tracker_match_summary["match_method"] == "normalized_name_unique", "rows"].sum()
    )
    tracker_fuzzy = int(
        tracker_match_summary.loc[tracker_match_summary["match_method"] == "fuzzy_name_county", "rows"].sum()
    )

    rows = [
        {
            "step": "Grouped counties present in population data",
            "matched_records": int(county_summary["region"].notna().sum()),
            "total_records": int(region_lookup["county_name"].nunique()),
            "match_rate": float(county_summary["region"].notna().sum() / region_lookup["county_name"].nunique()),
            "notes": "Checks whether all 25 required grouped counties appear in the population source.",
        },
        {
            "step": "ZIPs mapped to counties",
            "matched_records": int(zip_lookup["county_name"].notna().sum()),
            "total_records": int(len(zip_lookup)),
            "match_rate": float(zip_lookup["county_name"].notna().mean()),
            "notes": "Uses the strongest available ZIP-to-tract ratio field to choose a county per ZIP.",
        },
        {
            "step": "Ohio schools mapped to counties",
            "matched_records": int(schools["county_name"].notna().sum()),
            "total_records": int(len(schools)),
            "match_rate": float(schools["county_name"].notna().mean()),
            "notes": "Assigns each open Ohio NCES school to a county using ZIP-based mapping.",
        },
        {
            "step": "Ohio schools mapped to JACO regions",
            "matched_records": int(schools["region"].notna().sum()),
            "total_records": int(len(schools)),
            "match_rate": float(schools["region"].notna().mean()),
            "notes": "Only schools inside the 25 grouped counties receive a JACO region.",
        },
        {
            "step": "High-need exact IRN matches",
            "matched_records": high_need_exact,
            "total_records": int(len(high_need_match_detail)),
            "match_rate": float(high_need_exact / len(high_need_match_detail)),
            "notes": "Exact join between NCES-derived Ohio IRN and the Title I/SSI building IRN.",
        },
        {
            "step": "High-need exact unique-name matches",
            "matched_records": high_need_unique_name,
            "total_records": int(len(high_need_match_detail)),
            "match_rate": float(high_need_unique_name / len(high_need_match_detail)),
            "notes": "Exact normalized school-name match when the high-need workbook has only one school with that normalized name.",
        },
        {
            "step": "High-need normalized-name matches",
            "matched_records": high_need_normalized,
            "total_records": int(len(high_need_match_detail)),
            "match_rate": float(high_need_normalized / len(high_need_match_detail)),
            "notes": "Fallback matching within district after school-name normalization.",
        },
        {
            "step": "Tracker normalized-name county matches",
            "matched_records": tracker_name_county,
            "total_records": int(len(tracker_match_detail)),
            "match_rate": float(tracker_name_county / len(tracker_match_detail)),
            "notes": "Primary organization-to-school match using normalized school name with county as a secondary check.",
        },
        {
            "step": "Tracker normalized-name unique matches",
            "matched_records": tracker_name_unique,
            "total_records": int(len(tracker_match_detail)),
            "match_rate": float(tracker_name_unique / len(tracker_match_detail)),
            "notes": "Unique normalized school-name fallback when county does not produce a direct match.",
        },
        {
            "step": "Tracker fuzzy-name county matches",
            "matched_records": tracker_fuzzy,
            "total_records": int(len(tracker_match_detail)),
            "match_rate": float(tracker_fuzzy / len(tracker_match_detail)),
            "notes": "Cautious fuzzy fallback inside the same county when exact normalized matching fails.",
        },
        {
            "step": "Tracker rows assigned to JACO regions",
            "matched_records": int(tracker_match_detail["final_region"].notna().sum()),
            "total_records": int(len(tracker_match_detail)),
            "match_rate": float(tracker_match_detail["final_region"].notna().mean()),
            "notes": "Rows outside the 25 grouped counties remain unassigned and are shown as limitations.",
        },
    ]
    return pd.DataFrame(rows)


def build_priority_label(row: pd.Series) -> str:
    if row["youth_population"] == row["youth_population_max"] and row["high_need_share"] >= row["high_need_share_median"]:
        return "Scale + need"
    if row["youth_population"] == row["youth_population_max"]:
        return "Scale leader"
    if row["high_need_share"] == row["high_need_share_max"]:
        return "Need leader"
    return "Selective build"


def build_recommendation(row: pd.Series) -> str:
    if row["priority_label"] == "Scale + need":
        return "Use this as the lead region for mobile-unit deployment and outreach acceleration."
    if row["priority_label"] == "Scale leader":
        return "Use this region to maximize student reach and build the deepest school pipeline."
    if row["priority_label"] == "Need leader":
        return "Use this region for equity-focused targeting and high-need school partnerships."
    return "Support with anchor-led outreach while proving demand and partnership potential."


def build_region_summary(
    county_summary: pd.DataFrame,
    youth_by_region: pd.DataFrame,
    schools_by_region: pd.DataFrame,
    high_need_by_region: pd.DataFrame,
    tracker_summary: pd.DataFrame,
    feasibility_by_region: pd.DataFrame,
) -> pd.DataFrame:
    summary = youth_by_region.merge(schools_by_region, on=["region_id", "region", "anchor_county"], how="left")
    summary = summary.merge(high_need_by_region, on=["region_id", "region", "anchor_county", "total_schools"], how="left")
    summary = summary.merge(tracker_summary, on="region", how="left")
    summary = summary.merge(
        feasibility_by_region[
            [
                "region_id",
                "region",
                "anchor_county",
                "max_anchor_distance_miles",
                "avg_anchor_distance_miles",
                "counties_outside_proxy_radius",
                "feasible_1hr_proxy",
            ]
        ],
        on=["region_id", "region", "anchor_county"],
        how="left",
    )
    summary["youth_population_max"] = summary["youth_population"].max()
    summary["high_need_share_max"] = summary["high_need_share"].max()
    summary["high_need_share_median"] = summary["high_need_share"].median()
    summary["priority_label"] = summary.apply(build_priority_label, axis=1)
    summary["recommendation"] = summary.apply(build_recommendation, axis=1)
    summary["region_id"] = summary["region_id"].astype(int)
    summary = summary.drop(columns=["youth_population_max", "high_need_share_max", "high_need_share_median"])
    return summary.sort_values("region_id").reset_index(drop=True)


def build_pipeline_artifacts(
    population_raw: pd.DataFrame,
    schools_raw: pd.DataFrame,
    high_need_raw: pd.DataFrame,
    zip_raw: pd.DataFrame,
    tracker_raw: pd.DataFrame,
    region_lookup: pd.DataFrame,
    region_geo: gpd.GeoDataFrame,
    zip_lookup: pd.DataFrame,
) -> PipelineArtifacts:
    county_summary, youth_by_region, population_metadata = analyze_population(population_raw, region_lookup)
    schools_clean, schools_by_region, school_list_by_region, schools_metadata = prepare_schools(schools_raw, zip_lookup, region_lookup, region_geo)
    high_need_clean = prepare_high_need(high_need_raw)
    schools_with_need, high_need_match_detail, high_need_match_summary = match_high_need(schools_clean, high_need_clean)
    high_need_by_region = summarize_high_need(schools_with_need)
    tracker_match_detail, tracker_summary, tracker_match_summary, tracker_metadata, tracker_value_audit, tracker_response_rules = prepare_tracker(tracker_raw, region_lookup, schools_with_need)
    county_feasibility_detail, feasibility_by_region, feasibility_metadata = analyze_anchor_feasibility(region_geo)
    region_summary = build_region_summary(county_summary, youth_by_region, schools_by_region, high_need_by_region, tracker_summary, feasibility_by_region)
    join_audit_summary = build_join_audit_summary(
        region_lookup=region_lookup,
        county_summary=county_summary,
        zip_lookup=zip_lookup,
        schools=schools_clean,
        high_need_match_detail=high_need_match_detail,
        tracker_match_detail=tracker_match_detail,
        high_need_match_summary=high_need_match_summary,
        tracker_match_summary=tracker_match_summary,
    )

    return PipelineArtifacts(
        county_summary=county_summary,
        youth_by_region=youth_by_region,
        schools_by_region=schools_by_region,
        high_need_by_region=high_need_by_region,
        tracker_summary=tracker_summary,
        feasibility_by_region=feasibility_by_region,
        county_feasibility_detail=county_feasibility_detail,
        region_summary=region_summary,
        schools_clean=schools_with_need,
        school_list_by_region=school_list_by_region,
        high_need_match_detail=high_need_match_detail,
        high_need_match_summary=high_need_match_summary,
        tracker_match_detail=tracker_match_detail,
        tracker_match_summary=tracker_match_summary,
        tracker_value_audit=tracker_value_audit,
        tracker_response_rules=tracker_response_rules,
        join_audit_summary=join_audit_summary,
        region_geo=region_geo,
        metadata={
            "population": population_metadata,
            "schools": schools_metadata,
            "tracker": tracker_metadata,
            "feasibility": feasibility_metadata,
        },
    )
