# JACO Regional Strategy Analytics

This repository contains a portfolio-quality analytics project built for Junior Achievement of Central Ohio (JACO). It replaces a messy notebook workflow with a clean Python pipeline that validates source files, builds the five required JACO regions, analyzes youth reach and school inventory, measures high-need concentration, summarizes outreach activity, creates presentation-ready visuals, and publishes a full HTML report.

The project is designed so one command reproduces the analysis:

```bash
python run_pipeline.py
```

## Project Goal

The analysis supports mobile-unit strategy and school outreach planning across five fixed JACO service regions. It is built to answer:

1. Which county groupings make sense around the five anchor counties?
2. Which regions maximize youth reach?
3. Which regions contain the largest school inventory for outreach?
4. Which regions have the strongest concentration of high-need schools?
5. What are the tradeoffs between scale, need, outreach traction, and anchor feasibility?
6. What should JACO prioritize first?

## Required Input Files

Place these exact files in the project root:

- `JACO.csv`
- `ccd_sch_029_2425_w_1a_073025.csv`
- `FY25 TI NC SSI Sec 1003i Report FINAL.xlsx`
- `ZIP_TRACT_122025.xlsx`
- `JA Cold Call Tracker.xlsx`

The pipeline checks for these files before it runs and raises a clear error if anything is missing.

## Repository Structure

- `run_pipeline.py`
  Main one-command entry point.
- `src/config.py`
  Paths, fixed regions, thresholds, and output settings.
- `src/io_utils.py`
  File validation, workbook inspection, and data loading.
- `src/cleaning.py`
  Name standardization, ZIP cleaning, formatting helpers, and logging.
- `src/mapping.py`
  ZIP-to-county logic, county geography, and regional lookup creation.
- `src/analysis.py`
  Population, schools, high-need, tracker, and feasibility analysis.
- `src/visuals.py`
  Figure generation.
- `src/report.py`
  HTML report generation.
- `outputs/report.html`
  Full presentation-style report.
- `outputs/final_school_outreach_map.png`
  Final polished school outreach map for sharing or slides.

## Fixed JACO Regions

- `Group 1 - Columbus Core`
  Anchor: Franklin
  Counties: Franklin, Delaware, Union, Fairfield, Pickaway, Fayette
- `Group 2 - Newark / East-Central`
  Anchor: Licking
  Counties: Licking, Knox, Perry
- `Group 3 - Southeast Cluster`
  Anchor: Athens
  Counties: Athens, Hocking, Vinton, Meigs, Morgan, Washington
- `Group 4 - Southern Corridor`
  Anchor: Jackson
  Counties: Jackson, Gallia, Pike, Ross
- `Group 5 - Eastern Edge`
  Anchor: Guernsey
  Counties: Guernsey, Noble, Monroe, Belmont, Harrison, Jefferson

## How To Run

1. Create a virtual environment:

```bash
python3 -m venv .venv
```

2. Activate it and install dependencies:

```bash
python -m pip install -r requirements.txt
```

3. Run the pipeline:

```bash
python run_pipeline.py
```

That command regenerates all tables, visuals, and the HTML report in `outputs/`.

## Methodology Summary

- Population analysis filters `JACO.csv` to Ohio county-level rows and the latest available `YEAR` code.
- Youth reach is calculated only after inspecting the file’s `AGEGRP` structure; the current build uses `AGEGRP` 2, 3, and 4.
- School analysis filters the NCES extract to open Ohio schools and standardizes school names, ZIP codes, and identifiers.
- ZIP codes are mapped to counties using the strongest available ZIP-to-county ratio field from `ZIP_TRACT_122025.xlsx`.
- High-need schools are matched using the FY25 SSI workbook, prioritizing exact building IRN matching and then cleaned school-name matching.
- Cold-call tracker rows are standardized and matched to schools using normalized school names, with county used as a secondary check where available.
- Positive outreach is defined transparently as tracker rows where `Outcome = Interested`.
- The 1-hour feasibility screen uses county-centroid distance from each anchor county as a transparent proxy because no routing API is used.

## Outputs

### Main Deliverables

- [Full HTML report](/Users/aniketgauba/Documents/GitHub/JACO/outputs/report.html)
- [Final school outreach map](/Users/aniketgauba/Documents/GitHub/JACO/outputs/final_school_outreach_map.png)

### Core Figures

- `outputs/figures/region_map.png`
- `outputs/figures/county_population_heatmap.png`
- `outputs/figures/youth_population_heatmap.png`
- `outputs/figures/youth_by_region.png`
- `outputs/figures/schools_by_region.png`
- `outputs/figures/schools_map.png`
- `outputs/figures/outreach_map.png`
- `outputs/figures/high_need_by_region.png`
- `outputs/figures/high_need_share_by_region.png`
- `outputs/figures/one_hour_radius_feasibility.png`
- `outputs/figures/strategy_tradeoff_matrix.png`

### Core Tables

- `outputs/tables/region_summary.csv`
- `outputs/tables/final_strategy_summary.csv`
- `outputs/tables/youth_by_region.csv`
- `outputs/tables/schools_by_region.csv`
- `outputs/tables/high_need_by_region.csv`
- `outputs/tables/tracker_summary.csv`
- `outputs/tables/feasibility_by_region.csv`
- `outputs/tables/grouped_counties.csv`
- `outputs/tables/tracker_outcome_audit.csv`

Additional audit and intermediate tables are also saved in `outputs/tables/`.

## Key Findings

- `Group 1 - Columbus Core` is the scale leader, with the largest youth population and school inventory.
- `Group 4 - Southern Corridor` has the highest concentration of identified high-need schools.
- Tracker matching is strong enough to support region-level outreach interpretation.
- Positive outreach schools are currently defined only as tracker rows where `Outcome = Interested`.
- Under the centroid-distance proxy, the five fixed regions should be treated as strategic operating clusters rather than confirmed one-hour drive territories.

## School Outreach Map Notes

The final outreach map is intentionally styled for readability:

- all schools are shown as light-gray dots
- positive outreach schools are shown as green dots
- school locations are approximate rather than true coordinates

Because the NCES extract does not provide usable latitude/longitude for this workflow, school points are placed deterministically within their counties for visualization purposes.

## How To Access The Full Report

If you are sharing this project through GitHub:

1. open the repository
2. open the `outputs` folder
3. select `report.html`

The HTML report contains the full narrative, charts, summary tables, methodology, validation notes, and final recommendations.

## Limitations

- The school map uses approximate within-county placement because usable school coordinates were not available in the NCES extract used here.
- High-need analysis depends on the FY25 SSI workbook and should be interpreted as a specific need lens rather than a complete statewide need census.
- The 1-hour feasibility check uses centroid distance, not real road-network travel time.
- Outreach interpretation depends on tracker-school matching quality and the current `Outcome = Interested` rule.

## Why This Repo Is Useful

This project is built to be both presentation-ready and inspectable. It gives reviewers:

- a one-command reproducible workflow
- modular, readable Python code
- a polished final report
- cleaned summary tables
- shareable visuals for slides or discussion

