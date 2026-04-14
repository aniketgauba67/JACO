# JACO Regional Strategy Analytics

This repository contains a reproducible Python analytics project built for Junior Achievement of Central Ohio (JACO). It assembles county population, school inventory, high-need school indicators, ZIP-to-county mapping, outreach tracker activity, and supplemental school coordinates into a single report workflow.

The main deliverable is a polished HTML report generated with one command:

```bash
python run_pipeline.py
```

## What This Project Does

The project is designed to support regional planning and outreach analysis across five fixed JACO service groupings in Ohio. It helps a reviewer explore:

1. How the 25 JACO counties are grouped around the five anchor counties
2. Which regions have the largest youth population
3. Which regions contain the most schools for outreach
4. Where high-need schools are most concentrated
5. How outreach activity and interested responses are distributed across counties and regions
6. How the different lenses compare without forcing a recommendation

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

## Repository Contents

- `run_pipeline.py`
  Main entry point that runs the full pipeline and writes outputs.
- `src/config.py`
  Central project settings, fixed regions, filenames, and thresholds.
- `src/io_utils.py`
  Input validation, workbook inspection, and file loading helpers.
- `src/cleaning.py`
  Standardization functions for names, ZIP codes, and text fields.
- `src/mapping.py`
  ZIP-to-county logic, county geography, and region assignment helpers.
- `src/analysis.py`
  Population, school, high-need, outreach, and validation logic.
- `src/report.py`
  Final HTML report generation.
- `jaco_data_bundle.zip`
  Bundled raw data archive for reproducible setup on another machine.
- `outputs/report.html`
  Final generated report after the pipeline runs.

## Data Files

The pipeline expects these files in the project root:

- `JACO.csv`
- `ccd_sch_029_2425_w_1a_073025.csv`
- `FY25 TI NC SSI Sec 1003i Report FINAL.xlsx`
- `ZIP_TRACT_122025.xlsx`
- `JA Cold Call Tracker.xlsx`
- `BUILDING_HIGH_LEVEL_2425.xlsx`
- `ohio_schools_coordinates_v2.xlsx`

On GitHub, the raw files are bundled inside `jaco_data_bundle.zip` rather than tracked individually. A new user should extract that zip into the repository root before running the project.

## How To Run This On Another Machine

### 1. Clone the repository

```bash
git clone https://github.com/aniketgauba67/JACO.git
cd JACO
```

### 2. Create and activate a virtual environment

macOS / Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Windows PowerShell:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

### 3. Install dependencies

```bash
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

### 4. Extract the bundled data archive

You must unpack `jaco_data_bundle.zip` into the project root so the raw files sit next to `run_pipeline.py`.

Command line option:

```bash
unzip jaco_data_bundle.zip
```

Or extract it manually with Finder, Explorer, or your preferred archive tool.

After extraction, the root folder should contain the seven required data files listed above.

### 5. Run the pipeline

```bash
python run_pipeline.py
```

### 6. Open the final report

After the run finishes, open:

- `outputs/report.html`

That HTML file is the main deliverable. It contains the full narrative, interactive charts, outreach map, validation summaries, and supporting tables.

## What Gets Generated

### Main output

- `outputs/report.html`

### Supporting tables

The pipeline also writes CSV outputs to `outputs/tables/`, including:

- `region_summary.csv`
- `youth_by_region.csv`
- `schools_by_region.csv`
- `high_need_by_region.csv`
- `tracker_summary.csv`
- `grouped_counties.csv`
- `tracker_outcome_audit.csv`
- `join_audit_summary.csv`
- `school_coordinate_match_summary.csv`

These tables support the report and make the analysis easy to inspect outside the HTML.

## Analysis Workflow

At a high level, the pipeline does the following:

1. Validates that all required data files exist
2. Loads each dataset and inspects workbook sheets / columns defensively
3. Standardizes county names, school names, ZIP codes, and text fields
4. Builds the fixed five-region JACO geography
5. Filters and summarizes county population and youth population
6. Maps schools to counties and then to JACO regions
7. Matches high-need schools using IRN-first logic plus fallback school-name matching
8. Cleans and audits the cold-call tracker
9. Defines positive outreach strictly as `Outcome == Interested`
10. Generates the final HTML report and supporting audit tables

## Report Contents

The final report includes:

- project overview and business framing
- regional footprint views
- county and region population analysis
- school distribution and outreach visuals
- interested-outcome analysis
- high-need school analysis
- join validation and match-rate diagnostics
- county and region comparison tables
- method notes and caveats

## Important Notes For Reviewers

- The report is meant to be analytical and decision-support oriented.
- It presents patterns, comparisons, and tradeoffs rather than prescribing a final action plan.
- Outreach positives are defined only as tracker rows where `Outcome = Interested`.
- School mapping uses the supplemental coordinate workbook where exact matches are available.
- Any remaining unmatched school locations use a transparent fallback and are labeled accordingly in the report.

## Troubleshooting

If the pipeline does not run as expected:

- Make sure the zip file has been extracted into the repository root.
- Confirm the virtual environment is activated.
- Reinstall dependencies with `python -m pip install -r requirements.txt`.
- Check that `outputs/report.html` was regenerated after the run.
- If a workbook structure changes, the pipeline will usually log the chosen sheet or column logic to help diagnose the issue.

## Why This Repo Is Useful

This project is built to be both presentation-ready and reproducible. A reviewer can:

- inspect the code and methodology
- rerun the full workflow with one command
- open a polished report without using notebooks
- review output tables for validation and deeper analysis
