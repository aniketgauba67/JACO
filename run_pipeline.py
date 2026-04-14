from __future__ import annotations

import pandas as pd

from src.analysis import build_pipeline_artifacts
from src.cleaning import LOGGER, configure_logging, ensure_directories
from src.config import OUTPUTS_DIR, REPORT_PATH, TABLES_DIR
from src.io_utils import (
    get_ohio_counties,
    load_high_need_data,
    load_population_data,
    load_school_coordinate_data,
    load_school_data,
    load_tracker_data,
    load_zip_tract_data,
    validate_input_files,
)
from src.mapping import attach_region_geography, build_region_lookup, build_zip_to_county_lookup
from src.report import render_report


def save_table(df: pd.DataFrame, filename: str) -> None:
    df.to_csv(TABLES_DIR / filename, index=False)


def main() -> None:
    configure_logging()
    ensure_directories([OUTPUTS_DIR, TABLES_DIR, REPORT_PATH.parent])
    validate_input_files()

    LOGGER.info("Loading and inspecting source data.")
    population_raw, population_io_meta = load_population_data()
    schools_raw, schools_io_meta = load_school_data()
    school_coordinates_raw, school_coordinates_io_meta = load_school_coordinate_data()
    high_need_raw, high_need_io_meta = load_high_need_data()
    zip_raw, zip_io_meta = load_zip_tract_data()
    tracker_raw, tracker_io_meta = load_tracker_data()

    LOGGER.info("Building region lookup and Ohio county geography.")
    region_lookup = build_region_lookup()
    ohio_counties = get_ohio_counties()
    zip_lookup, zip_lookup_meta = build_zip_to_county_lookup(zip_raw, ohio_counties)
    region_geo = attach_region_geography(ohio_counties, region_lookup)

    LOGGER.info("Running analysis pipeline.")
    artifacts = build_pipeline_artifacts(
        population_raw=population_raw,
        schools_raw=schools_raw,
        high_need_raw=high_need_raw,
        zip_raw=zip_raw,
        tracker_raw=tracker_raw,
        region_lookup=region_lookup,
        region_geo=region_geo,
        zip_lookup=zip_lookup,
        school_coordinates_raw=school_coordinates_raw,
    )

    county_geo = region_geo.merge(
        artifacts.county_summary[["county_name", "total_population", "youth_population"]],
        on="county_name",
        how="left",
    )

    LOGGER.info("Saving output tables.")
    save_table(region_lookup, "grouped_counties.csv")
    save_table(artifacts.region_summary, "region_summary.csv")
    save_table(artifacts.youth_by_region, "youth_by_region.csv")
    save_table(artifacts.schools_by_region, "schools_by_region.csv")
    save_table(artifacts.high_need_by_region, "high_need_by_region.csv")
    save_table(artifacts.tracker_summary, "tracker_summary.csv")
    save_table(artifacts.feasibility_by_region, "feasibility_by_region.csv")
    save_table(artifacts.county_feasibility_detail, "county_feasibility_detail.csv")
    save_table(artifacts.county_summary, "county_population_summary.csv")
    save_table(zip_lookup, "zip_to_county_lookup.csv")
    save_table(artifacts.school_list_by_region, "school_list_by_region.csv")
    save_table(artifacts.school_coordinate_match_summary, "school_coordinate_match_summary.csv")
    save_table(artifacts.schools_clean, "schools_with_region_and_need.csv")
    save_table(artifacts.high_need_match_detail, "high_need_match_detail.csv")
    save_table(artifacts.high_need_match_summary, "high_need_match_summary.csv")
    save_table(artifacts.tracker_match_detail, "tracker_match_detail.csv")
    save_table(artifacts.tracker_match_summary, "tracker_match_summary.csv")
    save_table(artifacts.tracker_value_audit, "tracker_value_audit.csv")
    save_table(artifacts.tracker_value_audit, "tracker_outcome_audit.csv")
    save_table(artifacts.tracker_response_rules, "tracker_response_rules.csv")
    save_table(artifacts.join_audit_summary, "join_audit_summary.csv")

    LOGGER.info("Rendering HTML report.")
    report_metadata = {
        **artifacts.metadata,
        "high_need_match_summary": artifacts.high_need_match_summary,
        "tracker_match_summary": artifacts.tracker_match_summary,
        "tracker_value_audit": artifacts.tracker_value_audit,
        "tracker_response_rules": artifacts.tracker_response_rules,
        "join_audit_summary": artifacts.join_audit_summary,
        "io": {
            "population": population_io_meta,
            "schools": schools_io_meta,
            "school_coordinates": school_coordinates_io_meta,
            "high_need": high_need_io_meta,
            "zip_tract": zip_io_meta,
            "tracker": tracker_io_meta,
            "zip_lookup": zip_lookup_meta,
        },
    }
    render_report(artifacts, county_geo, report_metadata)
    LOGGER.info("HTML report written to %s", REPORT_PATH)


if __name__ == "__main__":
    main()
