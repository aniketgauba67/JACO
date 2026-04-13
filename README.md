# JACO Regional Analytics Pipeline

This repository is a clean, reproducible Python analytics project for Junior Achievement of Central Ohio (JACO). It replaces a notebook-style workflow with a script-driven pipeline that validates source files, builds the five required JACO regions, analyzes youth reach and school inventory, measures concentrated need, summarizes cold outreach activity, generates presentation-ready figures, and publishes a polished HTML report.

## Business Questions

1. How should counties be grouped around anchor counties for mobile-unit coverage?
2. Which regions maximize youth reach?
3. Which regions contain the most schools for outreach?
4. Which regions show the strongest concentration of high-need schools?
5. What are the tradeoffs between scale and concentrated need?
6. What should JACO prioritize first?

## Required Input Files

Place these exact files in the project root before running the pipeline:

- `JACO.csv`
- `ccd_sch_029_2425_w_1a_073025.csv`
- `FY25 TI NC SSI Sec 1003i Report FINAL.xlsx`
- `ZIP_TRACT_122025.xlsx`
- `JA Cold Call Tracker.xlsx`

The pipeline validates file existence and raises a clear error if any are missing.

## Repository Structure

- `run_pipeline.py`: one-command entry point
- `src/config.py`: paths, regions, plotting settings, and match thresholds
- `src/io_utils.py`: file validation, workbook inspection, and data loading
- `src/cleaning.py`: normalization helpers, formatting helpers, and logging
- `src/mapping.py`: region lookup, ZIP-to-county mapping, and geography helpers
- `src/analysis.py`: population, school, high-need, and tracker analysis
- `src/visuals.py`: figure generation
- `src/report.py`: HTML report generation
- `outputs/figures/`: generated PNG charts and maps
- `outputs/tables/`: generated CSV tables
- `outputs/report.html`: final client-ready HTML report

## Fixed JACO Regions

- Group 1 - Columbus Core: Franklin anchor; Franklin, Delaware, Union, Fairfield, Pickaway, Fayette
- Group 2 - Newark / East-Central: Licking anchor; Licking, Knox, Perry
- Group 3 - Southeast Cluster: Athens anchor; Athens, Hocking, Vinton, Meigs, Morgan, Washington
- Group 4 - Southern Corridor: Jackson anchor; Jackson, Gallia, Pike, Ross
- Group 5 - Eastern Edge: Guernsey anchor; Guernsey, Noble, Monroe, Belmont, Harrison, Jefferson

## How To Run

1. Create a virtual environment:
   `python3 -m venv .venv`
2. Activate it and install dependencies:
   `python -m pip install -r requirements.txt`
3. Generate all outputs:
   `python run_pipeline.py`

That single command writes all tables, figures, and the HTML report to `outputs/`.

## What The Pipeline Produces

### Tables

- `outputs/tables/region_summary.csv`
- `outputs/tables/youth_by_region.csv`
- `outputs/tables/schools_by_region.csv`
- `outputs/tables/high_need_by_region.csv`
- `outputs/tables/tracker_summary.csv`
- `outputs/tables/grouped_counties.csv`
- `outputs/tables/school_list_by_region.csv`
- `outputs/tables/high_need_match_detail.csv`
- `outputs/tables/high_need_match_summary.csv`
- `outputs/tables/tracker_match_detail.csv`
- `outputs/tables/tracker_match_summary.csv`
- `outputs/tables/zip_to_county_lookup.csv`

### Figures

- `outputs/figures/region_map.png`
- `outputs/figures/county_population_heatmap.png`
- `outputs/figures/youth_population_heatmap.png`
- `outputs/figures/youth_by_region.png`
- `outputs/figures/schools_by_region.png`
- `outputs/figures/high_need_by_region.png`
- `outputs/figures/high_need_share_by_region.png`
- `outputs/figures/schools_map.png`
- `outputs/figures/outreach_map.png`
- `outputs/figures/strategy_tradeoff_matrix.png`

### Report

- `outputs/report.html`

## Method Summary

- Population logic filters to Ohio county rows, uses the latest county-level `YEAR` code in `JACO.csv`, inspects available `AGEGRP` values, and defines youth using AGEGRP 2-4.
- School logic filters the NCES extract to open Ohio schools, standardizes names and ZIPs, and maps ZIPs to counties using the strongest ratio field available from `ZIP_TRACT_122025.xlsx`.
- High-need logic uses the workbook sheet inspection step to find the building-level allocation sheet, then matches by Ohio building IRN first and normalized school name second.
- Tracker logic inspects workbook sheets and columns programmatically, standardizes organization names and counties, and reports match quality transparently.
- Mapping uses official Census TIGER/Line county boundaries cached locally on first run.

## Current Headline Findings

- Group 1 - Columbus Core is the clear scale leader with about 378,187 youth and 524 mapped schools.
- Group 4 - Southern Corridor has the highest high-need concentration at about 20.9% of mapped schools.
- Tracker school matching is strong enough for region-level outreach interpretation, at about 90.6% of tracker rows.
- The current recommendation is to launch first in Group 1 for scale and use Group 4 as the strongest equity-focused follow-on region.

## Notes And Limitations

- The NCES extract in this project does not include usable latitude/longitude columns, so the school point figure is rendered as an explicit placeholder instead of inventing coordinates.
- High-need results are based on the FY25 SSI building allocation file, so they represent a specific high-need lens rather than every possible statewide need indicator.
- Legacy notebook-era files remain in the repo for reference, but the production workflow runs entirely from `python run_pipeline.py`.
