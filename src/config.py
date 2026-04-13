from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
OUTPUTS_DIR = PROJECT_ROOT / "outputs"
FIGURES_DIR = OUTPUTS_DIR / "figures"
TABLES_DIR = OUTPUTS_DIR / "tables"
REPORT_PATH = OUTPUTS_DIR / "report.html"
CACHE_DIR = PROJECT_ROOT / ".cache"
GEODATA_CACHE = CACHE_DIR / "geodata"

INPUT_FILES = {
    "population": PROJECT_ROOT / "JACO.csv",
    "schools": PROJECT_ROOT / "ccd_sch_029_2425_w_1a_073025.csv",
    "high_need": PROJECT_ROOT / "FY25 TI NC SSI Sec 1003i Report FINAL.xlsx",
    "zip_tract": PROJECT_ROOT / "ZIP_TRACT_122025.xlsx",
    "tracker": PROJECT_ROOT / "JA Cold Call Tracker.xlsx",
}

OHIO_FIPS = "39"
OHIO_STATE_ABBR = "OH"
OHIO_COUNTY_URL = "https://www2.census.gov/geo/tiger/GENZ2023/shp/cb_2023_us_county_500k.zip"
OHIO_PROJECTION_EPSG = 3734

REGION_COLORS = {
    "Group 1 - Columbus Core": "#0B5D7A",
    "Group 2 - Newark / East-Central": "#F28E2B",
    "Group 3 - Southeast Cluster": "#59A14F",
    "Group 4 - Southern Corridor": "#E15759",
    "Group 5 - Eastern Edge": "#4E79A7",
}

YOUTH_AGE_GROUPS = {
    2: "Ages 5-9",
    3: "Ages 10-14",
    4: "Ages 15-19",
}

TRACKER_MATCH_THRESHOLD = 0.75
FUZZY_NAME_THRESHOLD = 92
FEASIBILITY_RADIUS_MILES = 50.0


@dataclass(frozen=True)
class RegionDefinition:
    region_id: int
    region: str
    anchor_county: str
    counties: tuple[str, ...]


REGION_DEFINITIONS = (
    RegionDefinition(
        1,
        "Group 1 - Columbus Core",
        "Franklin",
        ("Franklin", "Delaware", "Union", "Fairfield", "Pickaway", "Fayette"),
    ),
    RegionDefinition(
        2,
        "Group 2 - Newark / East-Central",
        "Licking",
        ("Licking", "Knox", "Perry"),
    ),
    RegionDefinition(
        3,
        "Group 3 - Southeast Cluster",
        "Athens",
        ("Athens", "Hocking", "Vinton", "Meigs", "Morgan", "Washington"),
    ),
    RegionDefinition(
        4,
        "Group 4 - Southern Corridor",
        "Jackson",
        ("Jackson", "Gallia", "Pike", "Ross"),
    ),
    RegionDefinition(
        5,
        "Group 5 - Eastern Edge",
        "Guernsey",
        ("Guernsey", "Noble", "Monroe", "Belmont", "Harrison", "Jefferson"),
    ),
)
