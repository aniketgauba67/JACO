from __future__ import annotations

import shutil

import pandas as pd

from src.analysis import build_pipeline_artifacts
from src.cleaning import LOGGER, configure_logging, ensure_directories
from src.config import FIGURES_DIR, OUTPUTS_DIR, REPORT_PATH, TABLES_DIR
from src.io_utils import (
    get_ohio_counties,
    load_high_need_data,
    load_population_data,
    load_school_data,
    load_tracker_data,
    load_zip_tract_data,
    validate_input_files,
)
from src.mapping import attach_region_geography, build_region_lookup, build_zip_to_county_lookup
from src.report import render_report
from src.visuals import (
    draw_county_heatmap,
    draw_high_need_comparison,
    draw_horizontal_bar,
    draw_outreach_map,
    draw_region_map,
    draw_school_points_map,
    draw_feasibility_check,
    draw_strategy_tradeoff,
)


def save_table(df: pd.DataFrame, filename: str) -> None:
    df.to_csv(TABLES_DIR / filename, index=False)


def main() -> None:
    configure_logging()
    ensure_directories([OUTPUTS_DIR, FIGURES_DIR, TABLES_DIR, REPORT_PATH.parent])
    validate_input_files()

    LOGGER.info("Loading and inspecting source data.")
    population_raw, population_io_meta = load_population_data()
    schools_raw, schools_io_meta = load_school_data()
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
    save_table(artifacts.schools_clean, "schools_with_region_and_need.csv")
    save_table(artifacts.high_need_match_detail, "high_need_match_detail.csv")
    save_table(artifacts.high_need_match_summary, "high_need_match_summary.csv")
    save_table(artifacts.tracker_match_detail, "tracker_match_detail.csv")
    save_table(artifacts.tracker_match_summary, "tracker_match_summary.csv")
    save_table(artifacts.tracker_value_audit, "tracker_value_audit.csv")
    save_table(artifacts.tracker_value_audit, "tracker_outcome_audit.csv")
    save_table(artifacts.tracker_response_rules, "tracker_response_rules.csv")
    save_table(artifacts.join_audit_summary, "join_audit_summary.csv")

    LOGGER.info("Rendering figures.")
    figure_paths = {
        "region_map": draw_region_map(region_geo),
        "county_population_heatmap": draw_county_heatmap(
            county_geo,
            "total_population",
            "Ohio County Population Heatmap",
            "County-level population from the latest county rows in JACO.csv.",
            "county_population_heatmap.png",
            cmap="Blues",
        ),
        "youth_population_heatmap": draw_county_heatmap(
            county_geo,
            "youth_population",
            "Ohio Youth Population Heatmap",
            "Youth population uses AGEGRP 2-4 after inspecting the file's AGEGRP structure.",
            "youth_population_heatmap.png",
            cmap="YlGnBu",
        ),
        "youth_by_region": draw_horizontal_bar(
            artifacts.region_summary,
            "youth_population",
            "Youth Population by Region",
            "Group 1 is the clear scale leader on reachable youth population.",
            "youth_by_region.png",
        ),
        "schools_by_region": draw_horizontal_bar(
            artifacts.region_summary,
            "total_schools",
            "Total Schools by Region",
            "School count indicates the size of each region's partnership and outreach target list.",
            "schools_by_region.png",
        ),
        "high_need_by_region": draw_high_need_comparison(artifacts.region_summary),
        "high_need_share_by_region": draw_horizontal_bar(
            artifacts.region_summary,
            "high_need_share",
            "Percent High-Need Schools by Region",
            "Southern Corridor leads on concentration of identified high-need schools.",
            "high_need_share_by_region.png",
            value_format="pct",
        ),
        "schools_map": draw_school_points_map(region_geo, artifacts.schools_clean, artifacts.tracker_match_detail),
        "outreach_map": draw_outreach_map(region_geo, artifacts.region_summary, artifacts.metadata["tracker"]),
        "strategy_tradeoff_matrix": draw_strategy_tradeoff(artifacts.region_summary),
        "one_hour_radius_feasibility": draw_feasibility_check(artifacts.feasibility_by_region),
    }
    shutil.copyfile(OUTPUTS_DIR / figure_paths["schools_map"], OUTPUTS_DIR / "final_school_outreach_map.png")

    school_points_caption = (
        "School locations are approximate. All schools are shown in light gray, and positive-response schools are highlighted in green."
    )
    outreach_map_caption = (
        f"Positive outreach schools are defined as tracker rows where Outcome = Interested. The region map summarizes {artifacts.metadata['tracker']['positive_response_rows']} positive tracker rows and {artifacts.metadata['tracker']['positive_matched_schools']} matched positive schools."
        if artifacts.metadata["tracker"]["suitable_for_school_overlay"]
        else f"Positive outreach schools are defined as tracker rows where Outcome = Interested. School-level matching was limited, so the map safely summarizes outreach at the region level from {artifacts.metadata['tracker']['positive_response_rows']} positive tracker rows."
    )

    LOGGER.info("Rendering HTML report.")
    report_metadata = {
        **artifacts.metadata,
        "high_need_match_summary": artifacts.high_need_match_summary,
        "tracker_match_summary": artifacts.tracker_match_summary,
        "tracker_value_audit": artifacts.tracker_value_audit,
        "tracker_response_rules": artifacts.tracker_response_rules,
        "join_audit_summary": artifacts.join_audit_summary,
        "school_points_caption": school_points_caption,
        "outreach_map_caption": outreach_map_caption,
        "io": {
            "population": population_io_meta,
            "schools": schools_io_meta,
            "high_need": high_need_io_meta,
            "zip_tract": zip_io_meta,
            "tracker": tracker_io_meta,
            "zip_lookup": zip_lookup_meta,
        },
    }
    render_report(artifacts.region_summary, figure_paths, report_metadata)
    LOGGER.info("HTML report written to %s", REPORT_PATH)


if __name__ == "__main__":
    main()
